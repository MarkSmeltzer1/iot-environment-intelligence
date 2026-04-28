"""
InfluxDB Writer for IoT Environmental Intelligence Pipeline.

Writes processed sensor data to InfluxDB time-series database.
Uses InfluxDB v2 API with bucket, org, and measurement structure.
"""
import logging
import os
from datetime import datetime
from typing import Any, Dict, List

from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from src.utils.config_loader import load_config

# Configure logging
logger = logging.getLogger(__name__)


class InfluxDBWriter:
    """
    Writer class for storing processed environmental data in InfluxDB.
    """

    def __init__(self, config: Dict[str, Any]):
        load_dotenv()
        self.config = config
        self.storage_config = config["storage"]
        token = self.storage_config.get("token") or os.getenv("INFLUXDB_TOKEN", "")
        url = os.getenv("INFLUXDB_URL", self.storage_config["influx_url"])
        org = os.getenv("INFLUXDB_ORG", self.storage_config["org"])

        # Initialize InfluxDB client
        self.client = InfluxDBClient(
            url=url,
            org=org,
            token=token,
            timeout=10000  # 10 second timeout
        )

        # Get write API
        self.write_api = self.client.write_api(
            write_options=SYNCHRONOUS
        )

        # Statistics
        self.records_written = 0
        self.write_errors = 0

    def _build_point(self, processed_result: Dict[str, Any]) -> Point:
        """
        Build an InfluxDB Point from processed result.

        Args:
            processed_result: Output from transformer (with raw data + event info)

        Returns:
            InfluxDB Point ready for writing
        """
        raw = processed_result["raw"]

        # Create point with measurement name
        measurement = self.storage_config["measurement"]
        point = Point(measurement)

        # Add timestamp
        timestamp = raw.get("timestamp")
        if timestamp:
            # Parse ISO timestamp to nanoseconds
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            point.time(dt)

        # Add fields (numeric values)
        point.field("temperature_f", raw.get("temperature_f", 0))
        point.field("humidity", raw.get("humidity", 0))
        point.field("pressure_hpa", raw.get("pressure_hpa", 0))
        point.field("light_lux", raw.get("light_lux", 0))

        # Add event data as fields
        point.field("event_label", processed_result.get(
            "event_label", "unknown"))
        point.field("anomaly_flag", 1 if processed_result.get(
            "anomaly_flag", False) else 0)

        # Add tags (for efficient querying)
        device_id = raw.get("device_id", "unknown")
        location = raw.get("location", "unknown")

        point.tag("device_id", device_id)
        point.tag("location", location)

        # Add validation status as tag
        valid_status = "valid" if processed_result.get(
            "valid", False) else "invalid"
        point.tag("valid_status", valid_status)

        return point

    def write(self, processed_result: Dict[str, Any]) -> bool:
        """
        Write a single processed result to InfluxDB.

        Args:
            processed_result: Output from transformer pipeline

        Returns:
            True if successful, False otherwise
        """
        try:
            point = self._build_point(processed_result)

            bucket = os.getenv("INFLUXDB_BUCKET", self.storage_config["bucket"])
            org = os.getenv("INFLUXDB_ORG", self.storage_config["org"])

            self.write_api.write(
                bucket=bucket,
                org=org,
                record=point
            )

            self.records_written += 1
            logger.debug(
                f"Written point for device {processed_result['raw'].get('device_id')}")

            return True

        except Exception as e:
            self.write_errors += 1
            logger.error(f"Failed to write to InfluxDB: {e}")
            return False

    def write_batch(self, processed_results: List[Dict[str, Any]]) -> int:
        """
        Write multiple processed results to InfluxDB.

        Args:
            processed_results: List of outputs from transformer pipeline

        Returns:
            Number of successfully written records
        """
        success_count = 0

        for result in processed_results:
            if self.write(result):
                success_count += 1

        logger.info(
            f"Batch write complete: {success_count}/{len(processed_results)} successful")
        return success_count

    def write_callback(self, processed_result: Dict[str, Any]):
        """
        Callback function for MQTT consumer.
        This can be passed to consumer.set_message_callback()

        Args:
            processed_result: Output from transformer pipeline
        """
        self.write(processed_result)

    def get_statistics(self) -> Dict[str, int]:
        """Get write statistics."""
        return {
            "records_written": self.records_written,
            "write_errors": self.write_errors
        }

    def close(self):
        """Close the InfluxDB client."""
        self.write_api.close()
        self.client.close()
        logger.info("InfluxDB client closed")

    def test_connection(self) -> bool:
        """
        Test the connection to InfluxDB.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to get buckets to verify connection
            buckets = self.client.buckets_api().find_buckets()
            logger.info(
                f"Connected to InfluxDB, found {len(buckets.buckets)} buckets")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            return False


def main():
    """Test the InfluxDB writer connection."""
    config = load_config()
    writer = InfluxDBWriter(config)

    if writer.test_connection():
        print("✅ InfluxDB connection successful")
    else:
        print("❌ InfluxDB connection failed")

    writer.close()


if __name__ == "__main__":
    main()
