import subprocess
import sys


def main() -> int:
    """Start the Streamlit dashboard with a simple Python entry point."""
    command = [sys.executable, "-m", "streamlit", "run", "src/dashboard/app.py"]
    return subprocess.call(command)


if __name__ == "__main__":
    raise SystemExit(main())
