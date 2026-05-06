"""
InfluxDB Queries for IoT Environmental Intelligence Pipeline.

Provides reusable query functions for retrieving environmental data
from InfluxDB for dashboard visualization and analysis.
"""
import os
import warnings
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

import pandas as pd
from dotenv import load_dotenv
from influxdb_client import InfluxDBClient
from influxdb_client.client.warnings import MissingPivotFunction
from influxdb_client.rest import ApiException

from src.utils.config_loader import load_config
from src.utils.logger import setup_logger

logger = setup_logger("storage_queries")
warnings.simplefilter("ignore", MissingPivotFunction)


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
        display_timezone = config.get("processing", {}).get(
            "display_timezone", "UTC"
        )
        self.display_timezone = ZoneInfo(display_timezone)

    def _get_time_range(self, hours: int = 24) -> str:
        """Get ISO time range for queries."""
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(hours=hours)
        return start_time.strftime("%Y-%m-%dT%H:%M:%SZ"), end_time.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _query_data_frame(self, query: str) -> pd.DataFrame:
        """Run a Flux query and normalize InfluxDB results to one DataFrame."""
        result = self.query_api.query_data_frame(query)

        if isinstance(result, list):
            frames = [frame for frame in result if not frame.empty]
            if not frames:
                return pd.DataFrame()
            return pd.concat(frames, ignore_index=True)

        return result

    def _format_display_time(self, value: Any) -> str:
        """Convert an InfluxDB UTC timestamp to the configured display timezone."""
        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is None:
            timestamp = timestamp.tz_localize(timezone.utc)
        return timestamp.tz_convert(self.display_timezone).isoformat()

    @staticmethod
    def _describe_event(event_label: str) -> str:
        """Return a readable explanation for an event label."""
        descriptions = {
            "high_temp_alert": "Temperature exceeded the configured high-temperature threshold",
            "high_humidity_alert": "Humidity exceeded the configured high-humidity threshold",
            "rapid_temp_change": "Temperature changed rapidly compared with the previous reading",
            "rapid_humidity_change": "Humidity changed rapidly compared with the previous reading",
            "rapid_light_change": "Light changed rapidly compared with the previous reading",
            "sunlight_heating": "High light coincided with a temperature rise",
            "sudden_cooling": "Temperature dropped sharply compared with the previous reading",
            "normal": "No event rule was triggered",
            "unknown": "The reading could not be classified",
        }
        return descriptions.get(event_label, "Event rule triggered")

    def _get_numeric_reading_rows(
        self,
        hours: int,
        device_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Return raw numeric sensor readings grouped by timestamp."""
        start, end = self._get_time_range(hours)

        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: {start})
          |> filter(fn: (r) => r._measurement == "{self.measurement}")
          |> filter(fn: (r) => r._field == "temperature_f" or r._field == "humidity" or r._field == "pressure_hpa" or r._field == "light_lux")
          |> sort(columns: ["_time"])
        '''

        if device_id:
            query += f'\n          |> filter(fn: (r) => r.device_id == "{device_id}")'

        result = self._query_data_frame(query)
        if result.empty:
            return []

        rows: Dict[tuple, Dict[str, Any]] = {}
        for _, row in result.iterrows():
            key = (
                pd.Timestamp(row["_time"]),
                row.get("device_id", "unknown"),
                row.get("location", "unknown"),
            )
            reading = rows.setdefault(
                key,
                {
                    "_time": pd.Timestamp(row["_time"]),
                    "device_id": row.get("device_id", "unknown"),
                    "location": row.get("location", "unknown"),
                },
            )
            reading[str(row["_field"])] = float(row["_value"])

        return sorted(rows.values(), key=lambda item: item["_time"])

    def _derive_anomalies(
        self,
        hours: int,
        device_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Derive explanatory anomalies from stored sensor values."""
        thresholds = self.config["thresholds"]
        rows = self._get_numeric_reading_rows(hours=hours, device_id=device_id)
        anomalies: Dict[tuple, Dict[str, Any]] = {}
        previous: Optional[Dict[str, Any]] = None

        def add_anomaly(row: Dict[str, Any], event_label: str, reason: str) -> None:
            key = (row["_time"], row["device_id"], row["location"], event_label)
            anomalies[key] = {
                "timestamp": self._format_display_time(row["_time"]),
                "device_id": row["device_id"],
                "location": row["location"],
                "event_label": event_label,
                "reason": reason,
            }

        for row in rows:
            temperature = row.get("temperature_f")
            humidity = row.get("humidity")
            light = row.get("light_lux")

            if temperature is not None and temperature >= thresholds["high_temp_f"]:
                add_anomaly(
                    row,
                    "high_temp_alert",
                    f"Temperature reached {temperature:.1f} F, above the {thresholds['high_temp_f']} F threshold",
                )

            if humidity is not None and humidity >= thresholds["high_humidity"]:
                add_anomaly(
                    row,
                    "high_humidity_alert",
                    f"Humidity reached {humidity:.1f}%, above the {thresholds['high_humidity']}% threshold",
                )

            if previous is not None:
                previous_temp = previous.get("temperature_f")
                previous_humidity = previous.get("humidity")
                previous_light = previous.get("light_lux")

                if temperature is not None and previous_temp is not None:
                    temp_delta = temperature - previous_temp
                    if abs(temp_delta) >= thresholds["rapid_temp_change_f"]:
                        add_anomaly(
                            row,
                            "rapid_temp_change",
                            f"Temperature changed by {temp_delta:+.1f} F between readings",
                        )

                if humidity is not None and previous_humidity is not None:
                    humidity_delta = humidity - previous_humidity
                    if abs(humidity_delta) >= thresholds["rapid_humidity_change"]:
                        add_anomaly(
                            row,
                            "rapid_humidity_change",
                            f"Humidity changed by {humidity_delta:+.1f} percentage points between readings",
                        )

                if light is not None and previous_light is not None:
                    light_delta = light - previous_light
                    if abs(light_delta) >= thresholds["rapid_light_change_lux"]:
                        add_anomaly(
                            row,
                            "rapid_light_change",
                            f"Light changed by {light_delta:+.0f} lux between readings",
                        )

            previous = row

        return sorted(
            anomalies.values(),
            key=lambda item: pd.Timestamp(item["timestamp"]),
            reverse=True,
        )

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
            result = self._query_data_frame(query)

            if result.empty:
                return []

            # Convert to list of dicts
            readings = []
            for _, row in result.iterrows():
                readings.append({
                    "timestamp": self._format_display_time(row["_time"]),
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
            result = self._query_data_frame(query)

            if result.empty:
                return None

            row = result.iloc[-1]
            return {
                "timestamp": self._format_display_time(row["_time"]),
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
          |> map(fn: (r) => ({ r with event_label: string(v: r._value), count_value: 1 }))
          |> group(columns: ["event_label"])
          |> sum(column: "count_value")
        '''

        try:
            result = self._query_data_frame(query)

            if result.empty:
                return {}

            event_counts = {}
            for _, row in result.iterrows():
                event_label = row["event_label"]
                count = row["count_value"]
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

        try:
            return len(self._derive_anomalies(hours=hours, device_id=device_id))

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
            result = self._query_data_frame(query)

            if result.empty:
                return []

            trend = []
            for _, row in result.iterrows():
                trend.append({
                    "timestamp": self._format_display_time(row["_time"]),
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
            result = self._query_data_frame(query)

            if result.empty:
                return 0

            return int(result.iloc[0]["_value"])

        except ApiException as e:
            logger.error(f"Query failed: {e}")
            return 0

    def get_sensor_trends(
        self,
        device_id: Optional[str] = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get temperature, humidity, pressure, and light trends.

        Returns:
            Long-form rows with timestamp, sensor, and value for charting.
        """
        start, end = self._get_time_range(hours)

        query = f'''
        from(bucket: "{self.bucket}")
          |> range(start: {start})
          |> filter(fn: (r) => r._measurement == "{self.measurement}")
          |> filter(fn: (r) => r._field == "temperature_f" or r._field == "humidity" or r._field == "pressure_hpa" or r._field == "light_lux")
        '''

        if device_id:
            query += f'\n          |> filter(fn: (r) => r.device_id == "{device_id}")'

        query += '\n          |> aggregateWindow(every: 1m, fn: mean, createEmpty: false)'

        try:
            result = self._query_data_frame(query)

            if result.empty:
                return []

            trends = []
            for _, row in result.iterrows():
                trends.append({
                    "timestamp": self._format_display_time(row["_time"]),
                    "sensor": row["_field"],
                    "value": row["_value"],
                    "device_id": row.get("device_id", "unknown"),
                    "location": row.get("location", "unknown"),
                })

            return trends

        except ApiException as e:
            logger.error(f"Query failed: {e}")
            return []

    def get_recent_anomalies(
        self,
        hours: int = 24,
        limit: int = 50,
        device_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent anomaly records for timeline/table views.

        Returns:
            List of anomaly records with timestamp, device, location, and value.
        """
        try:
            return self._derive_anomalies(hours=hours, device_id=device_id)[:limit]

        except ApiException as e:
            logger.error(f"Query failed: {e}")
            return []

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
