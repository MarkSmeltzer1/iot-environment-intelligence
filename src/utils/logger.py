import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_dir: str = "logs",
) -> logging.Logger:
    """Create a console and file logger for project modules."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(level)
    logger.propagate = False

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    file_name = name.replace(".", "_")
    file_handler = RotatingFileHandler(
        log_path / f"{file_name}.log",
        maxBytes=1_000_000,
        backupCount=3,
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
