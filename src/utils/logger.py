import logging


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Create a consistently formatted logger for project modules."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)
    return logger
