"""
Distributed Locking for Vector Database Operations

This module provides distributed locks using Redis to prevent race conditions
during concurrent operations across multiple instances/processes.

Performance Characteristics:
- Uses synchronous redis-py with run_in_executor for event-loop safety
- Lua scripts registered once per lock instance (not per operation)
- Heartbeat uses asyncio.Event for efficient signaling (no polling)

Usage:
    lock_manager = get_collection_lock_manager()

    async with lock_manager.acquire_lock("collection-name") as lock:
        # Critical section - only one instance can execute this at a time
        pass

Monitoring:
    lock.get_metrics()  # Returns dict with acquire_attempts, heartbeat_extensions, etc.
"""

import asyncio
import logging
import threading
import time
import uuid
import weakref
from functools import partial
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

import redis

from open_webui.env import REDIS_URL, SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["RAG"])


# Lua script for atomic compare-and-delete
# Returns 1 if lock was deleted, 0 if lock was not owned by us
RELEASE_LOCK_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""

# Lua script for atomic compare-and-extend (for lease renewal)
# Returns 1 if TTL was extended, 0 if lock was not owned by us
EXTEND_LOCK_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("expire", KEYS[1], ARGV[2])
else
    return 0
end
"""


class AsyncRedisLock:
    """
    Async Redis-based distributed lock with automatic expiration.

    Features:
    - Distributed: Works across multiple processes and servers
    - Async: Compatible with FastAPI's async/await
    - Non-blocking: Uses run_in_executor to avoid blocking the event loop
    - Resilient: Dynamically accesses manager's current client, survives Redis restarts
    - Auto-expire: Prevents deadlocks if process crashes
    - Task-safe reentrancy: Tracks ownership per asyncio task, not globally
    - Atomic release: Uses Lua script to prevent releasing other processes' locks
    - Lease renewal: Background task extends TTL for long-running operations
    """

    # Default heartbeat interval (extend TTL every N seconds)
    HEARTBEAT_INTERVAL = 10.0  # seconds

    def __init__(
        self,
        manager: "RedisCollectionLockManager",
        lock_name: str,
        timeout_secs: int = 30,
    ):
        self.manager = manager
        self.lock_name = f"lock:collection:{lock_name}"
        self.lock_id = str(uuid.uuid4())
        self.timeout_secs = timeout_secs

        # Task-safe ownership tracking: {task_id: reentry_count}
        # Each asyncio task gets its own entry
        self._owners: Dict[int, int] = {}
        self._owners_lock = threading.Lock()  # Thread-safe access to _owners

        # Heartbeat task for renewal
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._heartbeat_stop: Optional[asyncio.Event] = (
            None  # Created when loop available
        )

        # Track which client was used for script registration (for reconnection handling)
        self._last_registered_client = None
        self._release_script = None
        self._extend_script = None

        # Eagerly register scripts if manager has a client ready
        self._ensure_scripts_registered()

        # Metrics for observability
        self._acquire_attempts = 0
        self._heartbeat_extensions = 0
        self._script_registration_time = time.time()

    @property
    def redis_client(self):
        """Access the manager's current Redis client (survives reconnections)."""
        return self.manager.redis_client

    def _ensure_scripts_registered(self):
        """
        Register Lua scripts on the current client if it has changed.

        This handles Redis reconnection scenarios where the manager creates
        a new client instance. Cached lock objects will detect the change
        and re-register their scripts on the new client.
        """
        current_client = self.redis_client
        if current_client is None:
            return  # Manager hasn't initialized yet, will register on first operation

        if self._last_registered_client is not current_client:
            log.info(
                f"[LOCK:SCRIPT_REG] Registering Lua scripts on new client: {self.lock_name}, "
                f"client_changed={self._last_registered_client is not None}"
            )
            self._release_script = current_client.register_script(RELEASE_LOCK_LUA)
            self._extend_script = current_client.register_script(EXTEND_LOCK_LUA)
            self._last_registered_client = current_client
            self._script_registration_time = time.time()

    async def _run_in_executor(self, func, *args, **kwargs):
        """Run a blocking function in the default executor.

        Moves blocking redis-py (synchronous) calls off the asyncio
        event loop into a threadpool so other coroutines remain
        responsive. Uses `functools.partial` to support keyword args.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))

    def _get_task_id(self) -> int:
        """Get unique identifier for current asyncio task."""
        try:
            task = asyncio.current_task()
            return id(task) if task else id(threading.current_thread())
        except RuntimeError:
            # No event loop running
            return id(threading.current_thread())

    def _try_reentrant_acquire(self, task_id: Optional[int] = None) -> bool:
        """Return True if current task already owns the lock and increment the counter."""
        if task_id is None:
            task_id = self._get_task_id()
        with self._owners_lock:
            if task_id in self._owners:
                self._owners[task_id] += 1
                log.info(
                    f"[LOCK:REENTRY_DETECTED] Reentrant lock acquisition detected: {self.lock_name}, "
                    f"task={task_id}, new_count={self._owners[task_id]}"
                )
                return True
        return False

    async def _heartbeat_loop(self):
        """
        Background task that periodically extends the lock TTL.

        This prevents lock expiration during long-running operations.
        Uses asyncio.Event for efficient signaling (no polling).
        """
        try:
            while True:
                try:
                    # Wait for interval or stop signal using asyncio.Event
                    # This is more efficient than polling with threading.Event
                    await asyncio.wait_for(
                        self._heartbeat_stop.wait(), timeout=self.HEARTBEAT_INTERVAL
                    )
                    # If we reach here, stop was signaled
                    break
                except asyncio.TimeoutError:
                    # Timeout is expected - time to extend the lock
                    pass

                # Extend the lock TTL using atomic Lua script (via executor)
                try:
                    # Ensure scripts are registered on current client (handles reconnection)
                    await self._run_in_executor(self._ensure_scripts_registered)

                    result = await self._run_in_executor(
                        self._extend_script,
                        keys=[self.lock_name],
                        args=[self.lock_id, self.timeout_secs],
                    )

                    if result == 0:
                        # Lock was lost (expired or taken by someone else)
                        log.warning(
                            f"[LOCK:HEARTBEAT_LOST] Lock lost during heartbeat: {self.lock_name}. "
                            f"Another process may have acquired it."
                        )
                        # Clear all owners since we lost the lock
                        with self._owners_lock:
                            self._owners.clear()
                        break
                    else:
                        self._heartbeat_extensions += 1
                        log.debug(
                            f"[LOCK:HEARTBEAT] Extended TTL for lock: {self.lock_name} "
                            f"(total: {self._heartbeat_extensions})"
                        )
                except Exception as e:
                    # Log error but keep trying (transient Redis issues)
                    log.error(
                        f"[LOCK:HEARTBEAT_ERROR] Error extending lock TTL: {self.lock_name}, "
                        f"error={type(e).__name__}: {e}"
                    )
        except asyncio.CancelledError:
            log.debug(
                f"[LOCK:HEARTBEAT_CANCELLED] Heartbeat cancelled for lock: {self.lock_name}"
            )
        except Exception as e:
            log.error(
                f"[LOCK:HEARTBEAT_FATAL] Fatal error in heartbeat: {type(e).__name__}: {e}"
            )

    def _start_heartbeat(self):
        """Start the background heartbeat task."""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            try:
                loop = asyncio.get_running_loop()
                # Create asyncio.Event for efficient async signaling
                self._heartbeat_stop = asyncio.Event()
                self._heartbeat_task = loop.create_task(self._heartbeat_loop())
            except RuntimeError:
                # No running loop - heartbeat will be started when needed
                pass

    def _stop_heartbeat(self):
        """Stop the background heartbeat task."""
        if self._heartbeat_stop is not None and not self._heartbeat_stop.is_set():
            self._heartbeat_stop.set()
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
        self._heartbeat_task = None

    async def acquire(
        self, blocking: bool = True, timeout: Optional[float] = None
    ) -> bool:
        """
        Acquire the distributed lock.

        Task-safe: Each asyncio task is tracked separately. If the same task
        calls acquire() multiple times, it increments a reentry counter.
        Different tasks block on the Redis lock.

        Args:
            blocking: If True, wait until lock is available
            timeout: Maximum time to wait (None = wait forever)

        Returns:
            bool: True if lock acquired, False otherwise
        """
        task_id = self._get_task_id()
        if self._try_reentrant_acquire(task_id):
            return True

        log.info(
            f"[LOCK:ACQUIRE_START] Starting lock acquisition: {self.lock_name}, task={task_id}"
        )
        start_time = time.time()
        attempt = 0

        while True:
            attempt += 1
            self._acquire_attempts += 1
            try:
                # Ensure scripts are registered on current client (handles reconnection)
                await self._run_in_executor(self._ensure_scripts_registered)

                # Verify redis_client exists
                client = self.redis_client
                if not client:
                    log.error(f"Redis client is None for lock: {self.lock_name}")
                    return False

                # Execute blocking Redis SET NX call in thread pool
                acquired = await self._run_in_executor(
                    self.redis_client.set,
                    self.lock_name,
                    self.lock_id,
                    nx=True,
                    ex=self.timeout_secs,
                )

                if acquired:
                    with self._owners_lock:
                        self._owners[task_id] = 1

                    # Start heartbeat for renewal
                    self._start_heartbeat()

                    elapsed = time.time() - start_time
                    if elapsed > 1.0:  # Only log if took longer than 1 second
                        log.info(
                            f"[LOCK:ACQUIRED] Lock acquired after {attempt} attempts "
                            f"({elapsed:.2f}s): {self.lock_name}, task={task_id}"
                        )
                    else:
                        log.debug(
                            f"[LOCK:ACQUIRED] Lock acquired: {self.lock_name}, task={task_id}"
                        )
                    return True

                # Lock not available
                if not blocking:
                    return False

                # Check timeout
                if timeout is not None:
                    elapsed = time.time() - start_time
                    if elapsed >= timeout:
                        log.warning(
                            f"[LOCK:TIMEOUT] Lock acquisition timeout after {attempt} attempts "
                            f"({elapsed:.1f}s): {self.lock_name}"
                        )
                        return False

                # Wait before retrying
                await asyncio.sleep(0.05)

            except Exception as e:
                log.error(
                    f"Exception acquiring Redis lock {self.lock_name}: {type(e).__name__}: {e}"
                )
                return False

    async def release(self) -> bool:
        """
        Release the distributed lock.

        Uses atomic Lua script to ensure we only delete the lock if we own it.
        This prevents accidentally deleting a lock that expired and was acquired
        by another process.

        Returns:
            bool: True if lock was released, False otherwise
        """
        task_id = self._get_task_id()

        with self._owners_lock:
            # Check if this task owns the lock
            if task_id not in self._owners:
                log.warning(
                    f"[LOCK:RELEASE_NOT_OWNER] Attempted to release lock not owned by this task: "
                    f"{self.lock_name}, task={task_id}"
                )
                return False

            # Handle reentrant unlocking
            if self._owners[task_id] > 1:
                self._owners[task_id] -= 1
                log.debug(
                    f"[LOCK:REENTRY_RELEASE] Reentrant lock release: {self.lock_name}, "
                    f"task={task_id}, remaining_count={self._owners[task_id]}"
                )
                return True

            # Last release - remove from owners
            del self._owners[task_id]

        # Check if any other tasks still hold the lock
        with self._owners_lock:
            if self._owners:
                # Other tasks still hold it - don't release Redis lock yet
                log.debug(
                    f"[LOCK:RELEASE_PARTIAL] Lock still held by other tasks: {self.lock_name}, "
                    f"remaining_tasks={len(self._owners)}"
                )
                return True

        # No more owners - stop heartbeat and release Redis lock
        self._stop_heartbeat()

        try:
            # Ensure scripts are registered on current client (handles reconnection)
            await self._run_in_executor(self._ensure_scripts_registered)

            # Use atomic Lua script for compare-and-delete (via executor)
            result = await self._run_in_executor(
                self._release_script, keys=[self.lock_name], args=[self.lock_id]
            )

            if result == 1:
                log.debug(
                    f"[LOCK:RELEASED] Lock released: {self.lock_name}, task={task_id}"
                )
                return True
            else:
                # Lock expired or taken by someone else
                log.warning(
                    f"[LOCK:RELEASE_EXPIRED] Lock expired or owned by another process: "
                    f"{self.lock_name}. This may indicate the operation took too long."
                )
                return False

        except Exception as e:
            log.error(
                f"Exception releasing Redis lock {self.lock_name}: {type(e).__name__}: {e}"
            )
            return False

    def is_owned_by_current_task(self) -> bool:
        """Check if the current task owns this lock."""
        task_id = self._get_task_id()
        with self._owners_lock:
            return task_id in self._owners

    def get_owner_count(self) -> int:
        """Get the number of tasks currently holding this lock."""
        with self._owners_lock:
            return len(self._owners)

    async def extend(self, additional_secs: Optional[int] = None) -> bool:
        """
        Manually extend the lock TTL.

        Useful for operations that know they'll take a long time.

        Args:
            additional_secs: New TTL in seconds (default: self.timeout_secs)

        Returns:
            bool: True if TTL was extended, False if lock not owned
        """
        if not self.is_owned_by_current_task():
            return False

        try:
            ttl = additional_secs if additional_secs else self.timeout_secs
            # Ensure scripts are registered on current client (handles reconnection)
            await self._run_in_executor(self._ensure_scripts_registered)

            result = await self._run_in_executor(
                self._extend_script, keys=[self.lock_name], args=[self.lock_id, ttl]
            )
            return result == 1
        except Exception as e:
            log.error(f"Error extending lock TTL: {type(e).__name__}: {e}")
            return False

    def get_metrics(self) -> Dict[str, Any]:
        """Get lock metrics for monitoring and debugging."""
        return {
            "lock_name": self.lock_name,
            "lock_id": self.lock_id,
            "timeout_secs": self.timeout_secs,
            "acquire_attempts": self._acquire_attempts,
            "heartbeat_extensions": self._heartbeat_extensions,
            "owner_count": self.get_owner_count(),
            "is_owned": self.is_owned_by_current_task(),
            "heartbeat_active": self._heartbeat_task is not None
            and not self._heartbeat_task.done(),
            "script_registration_age_secs": time.time()
            - self._script_registration_time,
        }

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.release()
        return False


class RedisCollectionLockManager:
    """
    Manages distributed locks for vector database collections using Redis.

    Singleton pattern: Only ONE instance exists globally.

    Features:
    - Singleton: Enforced via __new__ (only one instance ever created)
    - Single Redis connection: Reused across all operations
    - Thread-safe initialization: Uses threading.Lock
    - Lock caching: Reuses same lock instance per collection name to support nested locks
      from the same task on the same collection. Uses WeakValueDictionary to avoid memory leaks.
    - Connection Recovery: Automatically attempts to reconnect if Redis connectivity is lost.
    """

    _instance: Optional["RedisCollectionLockManager"] = None  # Singleton instance
    _instance_lock: threading.Lock = threading.Lock()  # Thread-safe singleton creation

    def __new__(cls, redis_url: Optional[str] = None) -> "RedisCollectionLockManager":
        """
        Enforce singleton pattern: return same instance always.
        """
        if cls._instance is None:
            with cls._instance_lock:
                # Double-check: another thread may have created it
                if cls._instance is None:
                    instance: RedisCollectionLockManager = super().__new__(cls)
                    instance.redis_url = redis_url or REDIS_URL
                    instance._initialized = False
                    instance.redis_client = None

                    # Lock cache: Map collection_name -> AsyncRedisLock instance
                    # Use WeakValueDictionary so we don't leak memory for unused locks
                    instance._lock_cache = weakref.WeakValueDictionary()
                    instance._lock_cache_lock = threading.Lock()

                    # Try initial connection
                    instance._init_redis_client()

                    cls._instance = instance

        return cls._instance

    def _init_redis_client(self):
        """
        Initialize the synchronous Redis client (called in new or recovery).
        Can be run in executor for non-blocking recovery.
        """
        try:
            import redis

            self.redis_client = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=False,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )
            self.redis_client.ping()
            self._initialized = True
            log.info(
                f"[LOCK:INIT] Redis lock manager initialized successfully: "
                f"url={self.redis_url}, mode=synchronous_wrapped"
            )
        except Exception as e:
            log.error(
                f"[LOCK:INIT_ERROR] Failed to initialize Redis lock manager: "
                f"error={type(e).__name__}: {e}"
            )
            self._initialized = False

    async def _ensure_initialized(self):
        """Check that Redis client is initialized, attempt recovery if not key."""
        if self._initialized and self.redis_client:
            return

        log.warning(
            "[LOCK:RECOVER] Redis client not initialized, attempting to reconnect..."
        )

        # Run initialization in executor to avoid blocking event loop
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._init_redis_client)

        if not self._initialized:
            raise RuntimeError("Redis lock manager not initialized and recovery failed")

    def _create_lock(
        self,
        collection_name: str,
        timeout_secs: int = 30,
    ) -> AsyncRedisLock:
        """
        Get or create a lock instance for a collection.

        Locks are cached and reused for reentrancy. They dynamically access
        the manager's current redis_client, so they survive reconnections.
        """
        log.info(
            f"[LOCK:_CREATE_LOCK_CALLED] collection={collection_name}, timeout={timeout_secs}s"
        )
        with self._lock_cache_lock:
            # Check cache (WeakValueDictionary handles cleanup)
            lock = self._lock_cache.get(collection_name)

            if lock is None:
                lock = AsyncRedisLock(self, collection_name, timeout_secs)
                self._lock_cache[collection_name] = lock
                log.info(
                    f"[LOCK:CACHE_MISS] Created new cached lock for collection: {collection_name}, "
                    f"timeout={timeout_secs}s"
                )
            else:
                log.info(
                    f"[LOCK:CACHE_HIT] Reusing cached lock for collection: {collection_name}"
                )
            return lock

    @asynccontextmanager
    async def acquire_lock(self, collection_name: str, timeout_secs: int = 30):
        """
        Context manager for acquiring a collection lock.
        """
        await self._ensure_initialized()

        log.info(
            f"[LOCK:CONTEXT_ENTER] Entering lock context manager: "
            f"collection={collection_name}, timeout={timeout_secs}s"
        )

        # Create or retrieve lock instance (lock will access manager's client dynamically)
        lock = self._create_lock(collection_name, timeout_secs)

        if lock._try_reentrant_acquire():
            log.info(
                f"[LOCK:CONTEXT_REENTER] Reentering lock context manager: "
                f"collection={collection_name}, lock_id={id(lock)}"
            )
            acquired = True
        else:
            acquired = await lock.acquire(blocking=True, timeout=timeout_secs * 2)

        if not acquired:
            log.error(
                f"[LOCK:CONTEXT_ERROR] Failed to acquire lock for collection: "
                f"{collection_name}, timeout={timeout_secs}s"
            )
            raise TimeoutError(
                f"Failed to acquire lock for collection: {collection_name}"
            )

        log.debug(
            f"[LOCK:CONTEXT_ACTIVE] Lock acquired and context active: "
            f"collection={collection_name}"
        )
        try:
            yield lock
        finally:
            try:
                await lock.release()
                log.debug(
                    f"[LOCK:CONTEXT_EXIT] Exiting lock context manager: "
                    f"collection={collection_name}"
                )
            except Exception as e:
                log.error(
                    f"[LOCK:CONTEXT_ERROR] Error releasing lock in context manager: "
                    f"collection={collection_name}, error={type(e).__name__}: {e}"
                )

    async def health_check(self) -> bool:
        """
        Check if Redis connection is healthy.
        """
        try:
            await self._ensure_initialized()

            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.redis_client.ping)

            log.debug(f"[LOCK:HEALTH_OK] Redis health check passed")
            return True
        except Exception as e:
            log.error(
                f"[LOCK:HEALTH_ERROR] Redis health check failed: {type(e).__name__}: {e}"
            )
            return False

    async def close(self):
        """Close Redis connection and cleanup active locks."""
        # Use a copy of values since we iterate
        with self._lock_cache_lock:
            # We only need to stop heartbeats for locks that are still alive
            locks = list(self._lock_cache.values())

        for lock in locks:
            lock._stop_heartbeat()

        if self.redis_client:
            try:
                self.redis_client.close()
            except Exception as e:
                log.error(
                    f"[LOCK:CLOSE_ERROR] Error closing Redis client: {type(e).__name__}: {e}"
                )
        self._initialized = False


# Global singleton instance - managed by RedisCollectionLockManager.__new__
# This is only for type hints and direct access if needed
_redis_collection_lock_manager: Optional[RedisCollectionLockManager] = None


def get_collection_lock_manager() -> RedisCollectionLockManager:
    """
    Get the global Redis collection lock manager instance (singleton).

    This enforces a single manager across the entire application:
    - First call: Creates the singleton instance
    - Subsequent calls: Returns same instance
    - Thread-safe: Uses threading.Lock internally in __new__

    Returns:
        RedisCollectionLockManager: The singleton lock manager instance

    Example:
        lock_manager = get_collection_lock_manager()
        async with lock_manager.acquire_lock("my-collection") as lock:
            # Only one instance can execute this across ALL processes
            pass
    """
    global _redis_collection_lock_manager

    if _redis_collection_lock_manager is None:
        # Calling RedisCollectionLockManager() multiple times returns same instance
        # This is enforced by RedisCollectionLockManager.__new__
        _redis_collection_lock_manager = RedisCollectionLockManager()

    return _redis_collection_lock_manager
