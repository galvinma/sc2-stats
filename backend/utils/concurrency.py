import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Thread

from backend.utils.log import get_logger

logger = get_logger(__name__)


def run_threaded(kwargs):
    job_thread = Thread(target=kwargs.get("target"), kwargs=kwargs, daemon=True)
    job_thread.start()
    return job_thread


def thread_pool_max_workers():
    return min(32, os.cpu_count() * 5)


def yield_futures(func, iterable, workers=None):
    if workers is None:
        workers = thread_pool_max_workers()

    logger.info(f"Initializing ThreadPoolExecutor with {workers} workers...")
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(func, arg): arg for arg in iterable}
        for future in as_completed(futures):
            yield future.result(), futures[future]
