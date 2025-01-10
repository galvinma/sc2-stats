from threading import Lock, active_count

import schedule

from backend.static import REQUEST_MAX_PER_DAY, REQUEST_MAX_PER_SECOND
from backend.utils.log import get_logger

logger = get_logger(__name__)


class AppState:

    second_request_count = 0
    day_request_count = 0

    lock = Lock()

    @classmethod
    def get_second_request_count(cls):
        with AppState.lock:
            return AppState.second_request_count

    @classmethod
    def reset_second_request_count(cls):
        with AppState.lock:
            AppState.second_request_count = 0

    @classmethod
    def increment_second_request_count(cls):
        with AppState.lock:
            AppState.second_request_count += 1

    @classmethod
    def get_day_request_count(cls):
        with AppState.lock:
            return AppState.day_request_count

    @classmethod
    def reset_day_request_count(cls):
        with AppState.lock:
            AppState.day_request_count = 0

    @classmethod
    def increment_day_request_count(cls):
        with AppState.lock:
            AppState.day_request_count += 1

    @classmethod
    def exceeded_max_requests(cls):
        second_request_count = AppState.get_second_request_count()
        day_request_count = AppState.get_day_request_count()
        exceeded = second_request_count >= REQUEST_MAX_PER_SECOND or day_request_count >= REQUEST_MAX_PER_DAY
        if exceeded:
            logger.info(f"Exceeded max API requests. {second_request_count=}, {day_request_count=}")
        return exceeded

    @classmethod
    def log_app_state(cls):
        logger.info(
            "\n"
            "Application state: \n"
            f"Active threads: {active_count()} \n"
            f"Blizzard API second request count: {AppState.get_second_request_count()} \n"
            f"Blizzard API day request count: {AppState.get_day_request_count()} \n"
            f"{AppState.parse_jobs()}"
        )

    @classmethod
    def parse_jobs(cls):
        jobs = schedule.get_jobs()
        stmt = "Jobs:\n"
        for job in jobs:
            job_name = job.job_func.args[0].__name__
            stmt += f"\tname={job_name}, next={job.next_run}, last={job.last_run}\n"
        return stmt

    @classmethod
    def bytes2human(cls, n):
        # https://psutil.readthedocs.io/en/latest/#recipes
        symbols = ("K", "M", "G", "T", "P", "E", "Z", "Y")
        prefix = {}
        for i, s in enumerate(symbols):
            prefix[s] = 1 << (i + 1) * 10
        for s in reversed(symbols):
            if abs(n) >= prefix[s]:
                value = float(n) / prefix[s]
                return "%.1f%s" % (value, s)
        return "%sB" % n
