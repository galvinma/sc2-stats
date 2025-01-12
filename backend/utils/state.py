from threading import active_count

import schedule

from backend.api.blizzard import APIState
from backend.utils.log import get_logger

logger = get_logger(__name__)


def log_app_state(**kwargs):
    jobs = schedule.get_jobs()
    jobs_logging = "Jobs:\n"
    for job in jobs:
        tags = "".join(sorted(job.tags))
        jobs_logging += f"\tname={tags}, next={job.next_run}, last={job.last_run}\n"

    logger.info(
        "\n"
        "Application state: \n"
        f"Active threads: {active_count()} \n"
        f"Blizzard API second request count: {APIState.get_second_request_count()} \n"
        f"Blizzard API day request count: {APIState.get_day_request_count()} \n"
        f"{jobs_logging}"
    )
