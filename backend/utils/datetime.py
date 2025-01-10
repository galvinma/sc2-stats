import time


def current_epoch_time():
    return int(time.time())


def datetime_to_epoch(datetime):
    return int(datetime.timestamp())
