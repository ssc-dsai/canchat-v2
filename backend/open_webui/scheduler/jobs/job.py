import time

from apscheduler.schedulers.base import BaseScheduler


@BaseScheduler.scheduled_job()
def test():
    current_time = time.localtime
    print(f"TASK: test job running at {current_time}")
