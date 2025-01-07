import logging

from backend.static import APPLICATION_LOG_PATH


def get_logger(name):

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(APPLICATION_LOG_PATH)
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
