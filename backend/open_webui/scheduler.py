# scheduler.py
import logging
import asyncio
import threading
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from open_webui.env import SRC_LOG_LEVELS, WEBSOCKET_REDIS_URL, WEBSOCKET_MANAGER
from open_webui.config import (
    CHAT_LIFETIME_ENABLED,
    CHAT_LIFETIME_DAYS,
    CHAT_CLEANUP_PRESERVE_PINNED,
    CHAT_CLEANUP_PRESERVE_ARCHIVED,
    CHAT_CLEANUP_LOCK_TIMEOUT,
    CHAT_CLEANUP_LOCK_RENEWAL_INTERVAL,
    CHAT_CLEANUP_SCHEDULE_CRON,
    CHAT_CLEANUP_SCHEDULE_TIMEZONE,
    CHAT_CLEANUP_SCHEDULER_MISFIRE_GRACE_SECONDS,
    CHAT_CLEANUP_ALLOW_LOCAL_NO_REDIS,
)
from open_webui.socket.utils import RedisLock, renew_lock_periodically

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["SCHEDULER"])

# Global scheduler instance
scheduler = None
CLEANUP_JOB_ID = "chat_lifetime_cleanup"


def describe_cron_schedule(cron_expr: str) -> str:
    """Return raw cron expression for schedule display."""
    return cron_expr


def get_scheduler():
    """Get or create the global scheduler instance"""
    global scheduler
    if scheduler is None:
        scheduler = AsyncIOScheduler(timezone=CHAT_CLEANUP_SCHEDULE_TIMEZONE)
        scheduler.start()
        log.info("Chat lifetime scheduler started")
    return scheduler


async def automated_chat_cleanup():
    """
    Automated chat cleanup job that respects current configuration.
    This is called by the scheduler when chat lifetime is enabled.

    Uses Redis-based distributed locking to ensure only one replica runs cleanup at a time.
    Strict policy: if lock safety cannot be guaranteed (no Redis manager, lock contention,
    or Redis lock error), the cleanup run is skipped.

    Cleanup is executed in an executor thread to avoid blocking the main event loop.
    If lock ownership is lost mid-run, the cleanup function is signaled to stop early.
    """
    # Distributed lock to ensure only one replica runs cleanup
    lock = None
    lock_renewal_task = None
    lock_lost_flag = threading.Event()

    try:
        # Import here to avoid circular imports
        from open_webui.routers.retrieval import cleanup_expired_chats_streaming

        # Get current configuration values
        enabled = CHAT_LIFETIME_ENABLED.value
        days = CHAT_LIFETIME_DAYS.value
        preserve_pinned = CHAT_CLEANUP_PRESERVE_PINNED.value
        preserve_archived = CHAT_CLEANUP_PRESERVE_ARCHIVED.value

        if not enabled:
            log.info("Chat lifetime is disabled - skipping automated cleanup")
            return

        if WEBSOCKET_MANAGER == "redis":
            lock = RedisLock(
                redis_url=WEBSOCKET_REDIS_URL,
                lock_name="chat_cleanup_job",
                timeout_secs=CHAT_CLEANUP_LOCK_TIMEOUT,
            )

            if not await lock.acquire_lock():
                if lock.last_error:
                    log.error(
                        f"Skipping automated chat cleanup: lock acquisition failed due to Redis error: {lock.last_error}"
                    )
                else:
                    log.info(
                        "Another replica is already running chat cleanup - skipping this run"
                    )
                return
        elif not CHAT_CLEANUP_ALLOW_LOCAL_NO_REDIS:
            # Strict policy by default: skip cleanup when single-run guarantees are unavailable.
            log.warning(
                "Skipping automated chat cleanup: distributed lock is unavailable "
                "(WEBSOCKET_MANAGER is not 'redis'). Set CHAT_CLEANUP_ALLOW_LOCAL_NO_REDIS=true "
                "for single-instance local development."
            )
            return
        else:
            log.warning(
                "Running automated chat cleanup without distributed lock "
                "(CHAT_CLEANUP_ALLOW_LOCAL_NO_REDIS=true). Use only in single-instance environments."
            )

        log.info(
            f"Starting automated chat cleanup (age > {days} days, preserve_pinned={preserve_pinned}, preserve_archived={preserve_archived})"
        )

        # Start lock renewal task to keep lock alive during long-running cleanup
        if lock:
            lock_renewal_task = asyncio.create_task(
                renew_lock_periodically(
                    lock,
                    renewal_interval_secs=CHAT_CLEANUP_LOCK_RENEWAL_INTERVAL,
                    lock_name="chat_cleanup_job",
                    on_lock_lost=lock_lost_flag.set,
                )
            )

        # Run cleanup in thread pool to avoid blocking the main event loop.
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: asyncio.run(
                cleanup_expired_chats_streaming(
                    max_age_days=days,
                    preserve_pinned=preserve_pinned,
                    preserve_archived=preserve_archived,
                    force_cleanup_all=False,  # Always use age-based cleanup for automation
                    should_continue=lambda: not lock_lost_flag.is_set(),
                )
            ),
        )

        if lock_lost_flag.is_set():
            log.error("Chat cleanup lock lost during execution; cleanup stopped early.")

        log.info(f"Automated chat cleanup completed: {result}")

    except Exception as e:
        log.error(f"Automated chat cleanup failed: {str(e)}", exc_info=True)
    finally:
        # Cancel lock renewal task
        if lock_renewal_task:
            lock_renewal_task.cancel()
            try:
                await lock_renewal_task
            except asyncio.CancelledError:
                pass

        # Always release the lock
        if lock and lock.lock_obtained:
            released = await lock.release_lock()
            if released:
                log.info("Released chat cleanup lock")
            else:
                log.warning("Could not confirm chat cleanup lock release")


def update_cleanup_schedule():
    """
    Update the cleanup schedule based on current configuration.
    This should be called whenever chat lifetime settings change.
    """
    try:
        scheduler_instance = get_scheduler()

        # Remove existing job if it exists
        if scheduler_instance.get_job(CLEANUP_JOB_ID):
            scheduler_instance.remove_job(CLEANUP_JOB_ID)
            log.info("Removed existing chat cleanup schedule")

        # Check if chat lifetime is enabled
        if CHAT_LIFETIME_ENABLED.value:
            trigger = CronTrigger.from_crontab(
                CHAT_CLEANUP_SCHEDULE_CRON,
                timezone=CHAT_CLEANUP_SCHEDULE_TIMEZONE,
            )
            scheduler_instance.add_job(
                automated_chat_cleanup,
                trigger=trigger,
                id=CLEANUP_JOB_ID,
                name="Automated Chat Lifetime Cleanup",
                replace_existing=True,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=max(
                    1, int(CHAT_CLEANUP_SCHEDULER_MISFIRE_GRACE_SECONDS)
                ),
            )

            days = CHAT_LIFETIME_DAYS.value
            log.info(
                f"Scheduled chat cleanup with cron '{CHAT_CLEANUP_SCHEDULE_CRON}' "
                f"(timezone: {CHAT_CLEANUP_SCHEDULE_TIMEZONE}, lifetime: {days} days)"
            )
        else:
            log.info("Chat lifetime disabled - no automated cleanup scheduled")

    except Exception as e:
        log.error(f"Failed to update cleanup schedule: {str(e)}")


def start_chat_lifetime_scheduler():
    """
    Initialize the chat lifetime scheduler.
    This should be called once when the application starts.
    """
    try:
        log.info("Initializing chat lifetime scheduler...")
        get_scheduler()  # Initialize scheduler
        update_cleanup_schedule()  # Set up initial schedule
        log.info("Chat lifetime scheduler initialization complete")
    except Exception as e:
        log.error(f"Failed to start chat lifetime scheduler: {str(e)}")


def stop_chat_lifetime_scheduler():
    """
    Stop the chat lifetime scheduler.
    This should be called when the application shuts down.
    """
    global scheduler
    if scheduler:
        try:
            scheduler.shutdown()
            scheduler = None
            log.info("Chat lifetime scheduler stopped")
        except Exception as e:
            log.error(f"Error stopping scheduler: {str(e)}")


def get_schedule_info():
    """
    Get information about the current cleanup schedule.
    Returns dict with schedule status and next run time.
    """
    try:
        if not CHAT_LIFETIME_ENABLED.value:
            return {
                "enabled": False,
                "status": "Disabled",
                "next_run": None,
                "lifetime_days": CHAT_LIFETIME_DAYS.value,
                "schedule": describe_cron_schedule(CHAT_CLEANUP_SCHEDULE_CRON),
                "schedule_cron": CHAT_CLEANUP_SCHEDULE_CRON,
                "schedule_timezone": CHAT_CLEANUP_SCHEDULE_TIMEZONE,
            }

        if WEBSOCKET_MANAGER != "redis" and not CHAT_CLEANUP_ALLOW_LOCAL_NO_REDIS:
            return {
                "enabled": True,
                "status": "Blocked",
                "next_run": None,
                "lifetime_days": CHAT_LIFETIME_DAYS.value,
                "schedule": describe_cron_schedule(CHAT_CLEANUP_SCHEDULE_CRON),
                "schedule_cron": CHAT_CLEANUP_SCHEDULE_CRON,
                "schedule_timezone": CHAT_CLEANUP_SCHEDULE_TIMEZONE,
                "reason": "WEBSOCKET_MANAGER is not 'redis'; distributed lock is unavailable. "
                "Set CHAT_CLEANUP_ALLOW_LOCAL_NO_REDIS=true for single-instance local development.",
            }

        scheduler_instance = get_scheduler()
        job = scheduler_instance.get_job(CLEANUP_JOB_ID)

        if job:
            next_run = job.next_run_time
            return {
                "enabled": True,
                "status": "Scheduled",
                "next_run": next_run.isoformat() if next_run else None,
                "lifetime_days": CHAT_LIFETIME_DAYS.value,
                "schedule": describe_cron_schedule(CHAT_CLEANUP_SCHEDULE_CRON),
                "schedule_cron": CHAT_CLEANUP_SCHEDULE_CRON,
                "schedule_timezone": CHAT_CLEANUP_SCHEDULE_TIMEZONE,
            }
        else:
            return {
                "enabled": True,
                "status": "Error",
                "next_run": None,
                "lifetime_days": CHAT_LIFETIME_DAYS.value,
                "schedule": describe_cron_schedule(CHAT_CLEANUP_SCHEDULE_CRON),
                "schedule_cron": CHAT_CLEANUP_SCHEDULE_CRON,
                "schedule_timezone": CHAT_CLEANUP_SCHEDULE_TIMEZONE,
                "error": "Job not found in scheduler",
            }

    except Exception as e:
        return {
            "enabled": CHAT_LIFETIME_ENABLED.value,
            "status": "Error",
            "next_run": None,
            "lifetime_days": CHAT_LIFETIME_DAYS.value,
            "schedule": describe_cron_schedule(CHAT_CLEANUP_SCHEDULE_CRON),
            "schedule_cron": CHAT_CLEANUP_SCHEDULE_CRON,
            "schedule_timezone": CHAT_CLEANUP_SCHEDULE_TIMEZONE,
            "error": str(e),
        }
