import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore, Thread

from backend.utils.log import get_logger

logger = get_logger(__name__)


def run_threaded(job_func):
    job_thread = Thread(target=job_func)
    job_thread.start()
    return job_thread


def thread_pool_max_workers():
    return min(32, os.cpu_count() * 5)


class TaskManager:
    def __init__(self, workers=None):
        if workers is None:
            workers = thread_pool_max_workers()

        logger.info(f"Initializing TaskManager with {workers} workers...")
        self.workers = workers
        self.pool = ThreadPoolExecutor(max_workers=workers)
        self.semaphore = Semaphore(workers)

    def submit(self, func, arg):
        self.semaphore.acquire()
        future = self.pool.submit(func, arg)
        future.add_done_callback(lambda _: self.release())
        return future

    def release(self):
        self.semaphore.release()

    def yield_futures(self, func, iterable):
        futures = {self.submit(func, arg): arg for arg in iterable}
        for future in as_completed(futures):
            yield future.result(), futures[future]

        self.pool.shutdown()
