import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.storage.queries import InfluxDBQueries
from src.utils.config_loader import load_config
from src.utils.logger import setup_logger


logger = setup_logger("record_count")


def main() -> int:
    """Print the total number of stored environment readings."""
    config = load_config()
    queries = InfluxDBQueries(config)

    try:
        count = queries.get_record_count()
    finally:
        queries.close()

    logger.info("Total environment records: %s", count)
    print(f"Total environment records: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
