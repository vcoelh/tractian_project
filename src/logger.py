import logging
from datetime import datetime


def setup_logger(name, level="DEBUG"):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    file_handler = logging.FileHandler(
        f"./logs/{name}_{datetime.now().strftime('%Y_%m_%d__%H_%M')}.log",
        encoding="utf-8",
    )
    formatter = logging.Formatter(
        "[%(asctime)s - %(name)s - %(funcName)20s] - %(levelname)s - %(message)s",
        datefmt="%d-%m-%Y %I:%M:%S",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger