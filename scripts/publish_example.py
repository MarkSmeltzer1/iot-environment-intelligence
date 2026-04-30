import argparse
import json
import os
import sys
from pathlib import Path

import paho.mqtt.client as mqtt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.config_loader import load_config
from src.utils.logger import setup_logger


logger = setup_logger("example_publisher")


def publish_example(example_path: Path) -> int:
    """Publish one example JSON payload to the configured MQTT topic."""
    config = load_config()
    mqtt_config = config["mqtt"]
    broker = os.getenv("MQTT_BROKER", mqtt_config["broker"])
    port = int(os.getenv("MQTT_PORT", mqtt_config["port"]))
    topic = os.getenv("MQTT_TOPIC_RAW", mqtt_config["topic_raw"])

    payload = json.loads(example_path.read_text(encoding="utf-8"))
    encoded_payload = json.dumps(payload)

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="environment_example_publisher",
    )
    client.connect(broker, port, mqtt_config["keepalive"])
    client.loop_start()
    result = client.publish(topic, encoded_payload, qos=1)
    result.wait_for_publish()
    client.loop_stop()
    client.disconnect()

    if result.rc != mqtt.MQTT_ERR_SUCCESS:
        logger.error("Failed to publish %s to %s", example_path, topic)
        return 1

    logger.info("Published %s to %s via %s:%s", example_path, topic, broker, port)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish an example MQTT payload.")
    parser.add_argument(
        "example",
        nargs="?",
        default="examples/valid_reading.json",
        help="Path to an example JSON payload",
    )
    args = parser.parse_args()
    return publish_example(Path(args.example))


if __name__ == "__main__":
    raise SystemExit(main())
