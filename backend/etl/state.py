from threading import active_count

import schedule

from backend.blizzard.api import BlizzardAPIState
from backend.enums import RegionId
from backend.etl.execution import latest_etl_execution
from backend.static import JOB_NAMES
from backend.utils.datetime import current_epoch_time
from backend.utils.log import get_logger

logger = get_logger(__name__)


class FormatText:
    end = "\033[0m"
    underline = "\033[4m"
    bold = "\033[1m"


def underline(text):
    return FormatText.underline + text + FormatText.end


def bold(text):
    return FormatText.bold + text + FormatText.end


def log_app_state(**kwargs):
    stmt = ""
    stmt += "\n" + log_threads()
    stmt += "\n" + log_blizzard_api_state()
    stmt += "\n" + log_recent_jobs()
    stmt += "\n" + log_scheduled_jobs()
    logger.info(stmt)


def log_threads():
    stmt = underline("Concurrency") + "\n"
    stmt += f"Active threads: {active_count()} \n"
    return stmt


def log_recent_jobs():
    jobs = []
    for region in RegionId:
        for name in JOB_NAMES:
            latest = latest_etl_execution(name=name, region_id=region.value)
            if latest:
                jobs.append(latest)

    stmt = underline("Recent Jobs") + "\n"
    if not jobs:
        stmt += "No Recent jobs.\n"
        return stmt

    for job in jobs:
        since_last = (
            current_epoch_time() - job.end_timestamp
            if job.end_timestamp
            else current_epoch_time() - job.start_timestamp
        )
        stmt += (
            f"name={job.name}, region_id={job.region_id}, "
            + f"start={job.start_timestamp}, end={job.end_timestamp}, "
            + f"duration={job.duration}, since_last={since_last} \n"
        )

    return stmt


def log_scheduled_jobs():
    jobs = schedule.get_jobs()
    stmt = underline("Scheduled Jobs") + "\n"
    if not jobs:
        stmt += "No scheduled jobs.\n"
    else:
        for job in jobs:
            tags = "".join(sorted(job.tags))
            stmt += f"name={tags}, next={job.next_run}, last={job.last_run} \n"

    return stmt


def log_blizzard_api_state():
    stmt = underline("API Requests") + "\n"
    for region in RegionId:
        stmt = (
            stmt
            + f"Blizzard API day request count for {region.name}: "
            + f"{BlizzardAPIState.get_day_request_count(region_id=region.value)}"
            + "\n"
        )
    return stmt
