import time
from datetime import datetime


def current_epoch_time():
    return int(time.time())


def datetime_to_epoch(datetime):
    return int(datetime.timestamp())


def epoch_to_datetime(timestamp):
    return datetime.fromtimestamp(timestamp)
