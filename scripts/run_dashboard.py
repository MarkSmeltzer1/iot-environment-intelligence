import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.logger import setup_logger


logger = setup_logger("dashboard_runner")


def main() -> int:
    """Start the Streamlit dashboard with a simple Python entry point."""
    command = [sys.executable, "-m", "streamlit", "run", "src/dashboard/app.py"]
    logger.info("Starting Streamlit dashboard")
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
