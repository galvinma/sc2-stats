import logging
import os


def process_pool_max_workers():
    max_workers = os.cpu_count() - 1 if os.cpu_count() > 1 else 1
    logging.info(f"ProcessPoolExecutor {max_workers=}")
    return max_workers


def thread_pool_max_workers():
    max_workers = os.cpu_count() * 5
    logging.info(f"ThreadPoolExecutor {max_workers=}")
    return max_workers
