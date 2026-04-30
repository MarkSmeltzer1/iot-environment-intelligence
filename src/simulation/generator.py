"""
Realistic pre-device MQTT data simulator.

This is for testing the pipeline before the ESP32 is connected. The final
capstone still uses the physical ESP32 as the required device layer.
"""
import json
import math
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt

from src.utils.config_loader import load_config
from src.utils.logger import setup_logger


logger = setup_logger("simulator")


@dataclass
class SimulatorState:
    """Mutable simulator state for realistic gradual sensor changes."""
    temperature_f: float = 72.0
    humidity: float = 45.0
    pressure_hpa: float = 1013.0
    light_lux: float = 450.0
    location: str = "bedroom"


def utc_now() -> str:
    """Return current UTC timestamp in the project message format."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def build_reading(
    index: int,
    state: SimulatorState,
    device_id: str,
    include_failures: bool,
) -> Optional[Dict[str, Any]]:
    """
    Build one simulated sensor reading.

    Returns None for a simulated dropout, meaning no MQTT message should be sent.
    """
    day_wave = math.sin(index / 20)
    short_wave = math.sin(index / 5)

    state.temperature_f += random.uniform(-0.08, 0.08)
    state.humidity += random.uniform(-0.18, 0.18)
    state.pressure_hpa += random.uniform(-0.06, 0.06)
    state.light_lux = max(15, 430 + 250 * max(0, day_wave) + random.uniform(-25, 25))

    reading = {
        "timestamp": utc_now(),
        "device_id": device_id,
        "location": state.location,
        "temperature_f": round(state.temperature_f + 1.4 * day_wave + 0.3 * short_wave, 2),
        "humidity": round(max(20, min(85, state.humidity - 2.0 * day_wave)), 2),
        "pressure_hpa": round(state.pressure_hpa, 2),
        "light_lux": int(round(state.light_lux)),
    }

    if not include_failures:
        return reading

    # Repeatable demo scenarios that exercise processing and validation.
    if index > 0 and index % 75 == 0:
        logger.warning("Simulating sensor dropout at index %s", index)
        return None

    if index > 0 and index % 60 == 0:
        reading["temperature_f"] = 86.0
        reading["light_lux"] = 900
        logger.warning("Simulating high temperature/light event at index %s", index)

    if index > 0 and index % 95 == 0:
        reading["temperature_f"] = 130.0
        logger.warning("Simulating out-of-range temperature at index %s", index)

    if index > 0 and index % 120 == 0:
        state.location = "living_room" if state.location == "bedroom" else "bedroom"
        reading["location"] = state.location
        logger.warning("Simulating location change to %s", state.location)

    return reading


def create_mqtt_client(client_id: str) -> mqtt.Client:
    """Create a paho MQTT client for publishing simulator messages."""
    return mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=client_id,
    )


def publish_simulated_readings(
    count: int,
    interval_seconds: float,
    include_failures: bool,
    device_id: Optional[str] = None,
) -> int:
    """Publish simulated readings to the configured raw MQTT topic."""
    config = load_config()
    mqtt_config = config["mqtt"]
    defaults = config["device_defaults"]
    broker = os.getenv("MQTT_BROKER", mqtt_config["broker"])
    port = int(os.getenv("MQTT_PORT", mqtt_config["port"]))
    topic = os.getenv("MQTT_TOPIC_RAW", mqtt_config["topic_raw"])
    selected_device_id = device_id or defaults["device_id"]

    state = SimulatorState(location=defaults["location"])
    client = create_mqtt_client("environment_simulator")
    client.connect(broker, port, mqtt_config["keepalive"])
    client.loop_start()

    published = 0
    try:
        for index in range(count):
            reading = build_reading(index, state, selected_device_id, include_failures)

            if reading is not None:
                result = client.publish(topic, json.dumps(reading), qos=1)
                result.wait_for_publish()

                if result.rc != mqtt.MQTT_ERR_SUCCESS:
                    logger.error("Failed to publish simulated reading %s", index)
                    return 1

                published += 1
                logger.info(
                    "Published simulated reading %s/%s to %s: temp=%s humidity=%s light=%s",
                    index + 1,
                    count,
                    topic,
                    reading.get("temperature_f"),
                    reading.get("humidity"),
                    reading.get("light_lux"),
                )

            if index < count - 1:
                time.sleep(interval_seconds)
    finally:
        client.loop_stop()
        client.disconnect()

    logger.info("Simulation complete: published %s/%s attempted readings", published, count)
    return 0
