import os

from backend.static import MAX_WORKERS


def process_pool_max_workers():
    cpu_count = max(1, os.cpu_count())
    return cpu_count if cpu_count <= MAX_WORKERS else MAX_WORKERS


def thread_pool_max_workers():
    return os.cpu_count() * 5
