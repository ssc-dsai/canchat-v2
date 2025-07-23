from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.open_webui.scheduler.jobs import job

SCHEDULER = AsyncIOScheduler()

# SCHEDULER.add_jobstore("sqlalchemy", url=url)
SCHEDULER.add_job(
    job.test(),
)
