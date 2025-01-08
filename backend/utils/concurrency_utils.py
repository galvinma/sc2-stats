import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore

from backend.utils.logging_utils import get_logger

logger = get_logger(__name__)

TASK_MANAGER = None


def thread_pool_max_workers():
    max_threads = os.cpu_count() * 10
    logger.info(f"Will submit tasks with {max_threads=}")
    return max_threads


class TaskManager:
    def __init__(self, workers=thread_pool_max_workers()):
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


def get_task_manager():
    return TASK_MANAGER if TASK_MANAGER is not None else TaskManager()
