"""
MQTT Consumer for IoT Environmental Intelligence Pipeline.

Receives sensor data from ESP32 devices via MQTT, processes it through
the pipeline (validation -> transformation -> event detection), and
optionally writes to InfluxDB.
"""
import json
import logging
from typing import Any, Dict, Optional

import paho.mqtt.client as mqtt

from src.processing.transformer import process_message
from src.utils.config_loader import load_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MQTTConsumer:
    """
    MQTT Consumer that listens for sensor data and processes it.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.mqtt_config = config["mqtt"]
        self.client = mqtt.Client(client_id=self.mqtt_config["client_id"])
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

        # Store last processed message for event detection
        self.previous_message: Optional[Dict[str, Any]] = None

        # Message counters
        self.messages_received = 0
        self.messages_valid = 0
        self.messages_invalid = 0

        # Callback for processed messages (can be used by storage layer)
        self.message_callback = None

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker."""
        if rc == 0:
            logger.info(
                f"Connected to MQTT broker at {self.mqtt_config['broker']}:{self.mqtt_config['port']}")
            # Subscribe to raw sensor topic
            topic = self.mqtt_config["topic_raw"]
            client.subscribe(topic)
            logger.info(f"Subscribed to topic: {topic}")
        else:
            logger.error(
                f"Failed to connect to MQTT broker, return code: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker."""
        logger.warning(f"Disconnected from MQTT broker, return code: {rc}")

    def _on_message(self, client, userdata, msg):
        """
        Callback when message is received on subscribed topic.
        Parses JSON, processes through pipeline, and handles results.
        """
        self.messages_received += 1
        topic = msg.topic
        payload = msg.payload.decode('utf-8')

        logger.info(f"Received message #{self.messages_received} on {topic}")

        try:
            # Parse JSON payload
            message = json.loads(payload)
            logger.debug(f"Parsed message: {message}")

            # Process through pipeline
            result = process_message(
                message, self.config, self.previous_message)

            # Handle result
            if result["valid"]:
                self.messages_valid += 1
                logger.info(
                    f"Valid message - Event: {result['event_label']}, Anomaly: {result['anomaly_flag']}")

                # Store for next iteration (for event detection)
                self.previous_message = message.copy()

                # Call callback if set (for storage layer)
                if self.message_callback:
                    self.message_callback(result)
            else:
                self.messages_invalid += 1
                logger.warning(f"Invalid message - Errors: {result['errors']}")

            # Log statistics every 10 messages
            if self.messages_received % 10 == 0:
                self._log_statistics()

        except json.JSONDecodeError as e:
            self.messages_invalid += 1
            logger.error(f"Failed to parse JSON: {e}, payload: {payload}")
        except Exception as e:
            self.messages_invalid += 1
            logger.error(f"Error processing message: {e}")

    def _log_statistics(self):
        """Log message processing statistics."""
        logger.info("=== Message Statistics ===")
        logger.info(f"Total received: {self.messages_received}")
        logger.info(f"Valid: {self.messages_valid}")
        logger.info(f"Invalid: {self.messages_invalid}")
        logger.info(
            f"Success rate: {self.messages_valid/self.messages_received*100:.1f}%")

    def set_message_callback(self, callback):
        """
        Set a callback function to be called for each processed message.
        Use this to connect to storage layer.
        """
        self.message_callback = callback

    def connect(self):
        """Connect to MQTT broker."""
        try:
            self.client.connect(
                self.mqtt_config["broker"],
                self.mqtt_config["port"],
                self.mqtt_config["keepalive"]
            )
            logger.info("MQTT client connecting...")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise

    def start(self):
        """Start the MQTT client loop (blocking)."""
        logger.info("Starting MQTT consumer loop...")
        self.client.loop_forever()

    def start_non_blocking(self):
        """Start the MQTT client loop in a non-blocking way."""
        logger.info("Starting MQTT consumer loop (non-blocking)...")
        self.client.loop_start()

    def stop(self):
        """Stop the MQTT client."""
        logger.info("Stopping MQTT consumer...")
        self.client.loop_stop()
        self.client.disconnect()

    def get_statistics(self) -> Dict[str, int]:
        """Get message processing statistics."""
        return {
            "received": self.messages_received,
            "valid": self.messages_valid,
            "invalid": self.messages_invalid
        }


def main():
    """Main entry point for running the MQTT consumer."""
    # Load configuration
    config = load_config()
    logger.info("Configuration loaded")

    # Create consumer
    consumer = MQTTConsumer(config)

    # Connect and start
    try:
        consumer.connect()
        consumer.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        consumer.stop()
    except Exception as e:
        logger.error(f"Consumer error: {e}")
        raise


if __name__ == "__main__":
    main()
