"""
InfluxDB Queries for IoT Environmental Intelligence Pipeline.

Provides reusable query functions for retrieving environmental data
from InfluxDB for dashboard visualization and analysis.
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
from influxdb_client.rest import ApiException

from src.utils.config_loader import load_config
from src.utils.logger import setup_logger

logger = setup_logger("storage_queries")


class InfluxDBQueries:
    """
    Query class for retrieving environmental data from InfluxDB.
    """

    def __init__(self, config: Dict[str, Any]):
        load_dotenv()
        self.config = config
        self.storage_config = config["storage"]
        token = self.storage_config.get("token") or os.getenv("INFLUXDB_TOKEN", "")
        url = os.getenv("INFLUXDB_URL", self.storage_config["influx_url"])
        org = os.getenv("INFLUXDB_ORG", self.storage_config["org"])

        self.client = InfluxDBClient(
            url=url,
            org=org,
            token=token,
            timeout=10000
        )

        self.query_api = self.client.query_api()
        self.bucket = os.getenv("INFLUXDB_BUCKET", self.storage_config["bucket"])
        self.org = org
        self.measurement = self.storage_config["measurement"]

    def _get_time_range(self, hours: int = 24) -> str:
        """Get ISO time range for queries."""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        return start_time.strftime("%Y-%m-%dT%H:%M:%SZ"), end_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    def get_recent_readings(
        self,
        device_id: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent sensor readings.

        Args:
            device_id: Filter by device (optional)
            location: Filter by location (optional)
            limit: Maximum number of records

        Returns:
            List of reading dictionaries
        """
        # Build flux query
        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: -24h)
          |> filter(fn: (r) => r._measurement == "{self.measurement}")
          |> filter(fn: (r) => r._field == "temperature_f")
        '''

        if device_id:
            query += f'\n          |> filter(fn: (r) => r.device_id == "{device_id}")'
        if location:
            query += f'\n          |> filter(fn: (r) => r.location == "{location}")'

        query += f'\n          |> limit(n: {limit})'

        try:
            result = self.query_api.query_data_frame(query)

            if result.empty:
                return []

            # Convert to list of dicts
            readings = []
            for _, row in result.iterrows():
                readings.append({
                    "timestamp": row["_time"].isoformat() if hasattr(row["_time"], 'isoformat') else str(row["_time"]),
                    "device_id": row.get("device_id", "unknown"),
                    "location": row.get("location", "unknown"),
                    "temperature_f": row["_value"],
                })

            return readings

        except ApiException as e:
            logger.error(f"Query failed: {e}")
            return []

    def get_latest_reading(
        self,
        device_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get the most recent sensor reading.

        Args:
            device_id: Filter by device (optional)

        Returns:
            Latest reading dictionary or None
        """
        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: -1h)
          |> filter(fn: (r) => r._measurement == "{self.measurement}")
          |> filter(fn: (r) => r._field == "temperature_f")
        '''

        if device_id:
            query += f'\n          |> filter(fn: (r) => r.device_id == "{device_id}")'

        query += '\n          |> last()'

        try:
            result = self.query_api.query_data_frame(query)

            if result.empty:
                return None

            row = result.iloc[-1]
            return {
                "timestamp": str(row["_time"]),
                "device_id": row.get("device_id", "unknown"),
                "location": row.get("location", "unknown"),
                "temperature_f": row["_value"],
            }

        except ApiException as e:
            logger.error(f"Query failed: {e}")
            return None

    def get_event_counts(
        self,
        hours: int = 24,
        device_id: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Get counts of each event type.

        Args:
            hours: Number of hours to look back
            device_id: Filter by device (optional)

        Returns:
            Dictionary of event_label -> count
        """
        start, end = self._get_time_range(hours)

        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: {start})
          |> filter(fn: (r) => r._measurement == "{self.measurement}")
          |> filter(fn: (r) => r._field == "event_label")
        '''

        if device_id:
            query += f'\n          |> filter(fn: (r) => r.device_id == "{device_id}")'

        query += '''
          |> group(columns: ["_value"])
          |> count()
        '''

        try:
            result = self.query_api.query_data_frame(query)

            if result.empty:
                return {}

            event_counts = {}
            for _, row in result.iterrows():
                event_label = row["_value"]
                count = row["_value_y"] if "_value_y" in row else row.get(
                    "_value", 0)
                event_counts[event_label] = int(count)

            return event_counts

        except ApiException as e:
            logger.error(f"Query failed: {e}")
            return {}

    def get_anomaly_count(
        self,
        hours: int = 24,
        device_id: Optional[str] = None
    ) -> int:
        """
        Get count of anomalies detected.

        Args:
            hours: Number of hours to look back
            device_id: Filter by device (optional)

        Returns:
            Number of anomaly records
        """
        start, end = self._get_time_range(hours)

        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: {start})
          |> filter(fn: (r) => r._measurement == "{self.measurement}")
          |> filter(fn: (r) => r._field == "anomaly_flag")
          |> filter(fn: (r) => r._value == 1)
        '''

        if device_id:
            query += f'\n          |> filter(fn: (r) => r.device_id == "{device_id}")'

        query += '\n          |> count()'

        try:
            result = self.query_api.query_data_frame(query)

            if result.empty:
                return 0

            return int(result.iloc[0]["_value"])

        except ApiException as e:
            logger.error(f"Query failed: {e}")
            return 0

    def get_temperature_trend(
        self,
        device_id: Optional[str] = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get temperature data for trend visualization.

        Args:
            device_id: Filter by device (optional)
            hours: Number of hours to look back

        Returns:
            List of timestamp -> temperature mappings
        """
        start, end = self._get_time_range(hours)

        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: {start})
          |> filter(fn: (r) => r._measurement == "{self.measurement}")
          |> filter(fn: (r) => r._field == "temperature_f")
        '''

        if device_id:
            query += f'\n          |> filter(fn: (r) => r.device_id == "{device_id}")'

        query += '\n          |> aggregateWindow(every: 5m, fn: mean, createEmpty: false)'

        try:
            result = self.query_api.query_data_frame(query)

            if result.empty:
                return []

            trend = []
            for _, row in result.iterrows():
                trend.append({
                    "timestamp": str(row["_time"]),
                    "temperature_f": row["_value"],
                })

            return trend

        except ApiException as e:
            logger.error(f"Query failed: {e}")
            return []

    def get_record_count(self) -> int:
        """
        Get total number of records in the database.

        Returns:
            Total record count
        """
        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: -30d)
          |> filter(fn: (r) => r._measurement == "{self.measurement}")
          |> filter(fn: (r) => r._field == "temperature_f")
          |> count()
        '''

        try:
            result = self.query_api.query_data_frame(query)

            if result.empty:
                return 0

            return int(result.iloc[0]["_value"])

        except ApiException as e:
            logger.error(f"Query failed: {e}")
            return 0

    def close(self):
        """Close the InfluxDB client."""
        self.client.close()


def main():
    """Test query functionality."""
    config = load_config()
    queries = InfluxDBQueries(config)

    # Test connection by getting record count
    count = queries.get_record_count()
    print(f"Total records in database: {count}")

    queries.close()


if __name__ == "__main__":
    main()
