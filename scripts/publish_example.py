import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import paho.mqtt.client as mqtt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.config_loader import load_config
from src.utils.logger import setup_logger


logger = setup_logger("example_publisher")


def _current_timestamp(offset_seconds: int = 0) -> str:
    """Return an ISO UTC timestamp suitable for sensor payloads."""
    timestamp = datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)
    return timestamp.isoformat(timespec="seconds").replace("+00:00", "Z")


def _build_payload(
    example_path: Path,
    use_current_time: bool,
    sequence_index: int,
) -> dict:
    """Load and optionally time-shift one example payload."""
    payload = json.loads(example_path.read_text(encoding="utf-8"))

    if use_current_time:
        payload["timestamp"] = _current_timestamp(sequence_index)

    return payload


def publish_example(
    example_path: Path,
    use_current_time: bool = False,
    repeat: int = 1,
    interval_seconds: float = 1.0,
) -> int:
    """Publish one or more example JSON payloads to the configured MQTT topic."""
    config = load_config()
    mqtt_config = config["mqtt"]
    broker = os.getenv("MQTT_BROKER", mqtt_config["broker"])
    port = int(os.getenv("MQTT_PORT", mqtt_config["port"]))
    topic = os.getenv("MQTT_TOPIC_RAW", mqtt_config["topic_raw"])

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="environment_example_publisher",
    )
    client.connect(broker, port, mqtt_config["keepalive"])
    client.loop_start()

    try:
        for index in range(repeat):
            payload = _build_payload(example_path, use_current_time, index)
            result = client.publish(topic, json.dumps(payload), qos=1)
            result.wait_for_publish()

            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error("Failed to publish %s to %s", example_path, topic)
                return 1

            logger.info(
                "Published %s to %s via %s:%s with timestamp %s",
                example_path,
                topic,
                broker,
                port,
                payload.get("timestamp"),
            )

            if index < repeat - 1:
                time.sleep(interval_seconds)
    finally:
        client.loop_stop()
        client.disconnect()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish an example MQTT payload.")
    parser.add_argument(
        "example",
        nargs="?",
        default="examples/valid_reading.json",
        help="Path to an example JSON payload",
    )
    parser.add_argument(
        "--use-current-time",
        action="store_true",
        help="Replace the payload timestamp with the current UTC time",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Number of messages to publish",
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=1.0,
        help="Seconds to wait between repeated messages",
    )
    args = parser.parse_args()

    if args.repeat < 1:
        parser.error("--repeat must be at least 1")

    return publish_example(
        Path(args.example),
        use_current_time=args.use_current_time,
        repeat=args.repeat,
        interval_seconds=args.interval_seconds,
    )


if __name__ == "__main__":
    raise SystemExit(main())
