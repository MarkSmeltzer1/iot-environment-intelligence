import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.simulation.generator import publish_simulated_readings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Publish realistic simulated MQTT readings before ESP32 setup."
    )
    parser.add_argument("--count", type=int, default=30, help="Number of readings to attempt")
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=1.0,
        help="Seconds to wait between readings",
    )
    parser.add_argument(
        "--include-failures",
        action="store_true",
        help="Include dropouts, out-of-range values, high-temp events, and location changes",
    )
    parser.add_argument("--device-id", default=None, help="Override simulated device_id")
    args = parser.parse_args()

    if args.count < 1:
        parser.error("--count must be at least 1")
    if args.interval_seconds < 0:
        parser.error("--interval-seconds cannot be negative")

    return publish_simulated_readings(
        count=args.count,
        interval_seconds=args.interval_seconds,
        include_failures=args.include_failures,
        device_id=args.device_id,
    )


if __name__ == "__main__":
    raise SystemExit(main())
