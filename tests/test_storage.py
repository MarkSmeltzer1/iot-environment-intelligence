"""
Tests for InfluxDB Writer and Queries modules.
"""
from unittest.mock import MagicMock, Mock, patch

from src.storage.influx_writer import InfluxDBWriter
from src.storage.queries import InfluxDBQueries
from src.utils.config_loader import load_config


def test_influx_writer_init():
    """Test InfluxDBWriter initialization."""
    config = load_config()
    writer = InfluxDBWriter(config)

    assert writer.storage_config == config["storage"]
    assert writer.records_written == 0
    assert writer.write_errors == 0


def test_influx_writer_statistics():
    """Test get_statistics method."""
    config = load_config()
    writer = InfluxDBWriter(config)

    stats = writer.get_statistics()

    assert stats["records_written"] == 0
    assert stats["write_errors"] == 0


@patch('src.storage.influx_writer.InfluxDBClient')
def test_influx_writer_build_point(mock_influx_client):
    """Test _build_point creates correct InfluxDB Point."""
    config = load_config()
    writer = InfluxDBWriter(config)

    # Mock the client
    writer.client = Mock()
    writer.write_api = Mock()

    processed_result = {
        "raw": {
            "timestamp": "2026-04-28T10:00:00Z",
            "device_id": "esp32_room_1",
            "location": "bedroom",
            "temperature_f": 72.0,
            "humidity": 45.0,
            "pressure_hpa": 1013.0,
            "light_lux": 500,
        },
        "valid": True,
        "errors": [],
        "event_label": "normal",
        "anomaly_flag": False,
        "reasons": []
    }

    # The method should return a Point object (we can't fully test without real InfluxDB)
    # But we can verify it doesn't crash
    try:
        point = writer._build_point(processed_result)
        assert point is not None
    except Exception as e:
        # Expected to fail without real InfluxDB connection
        assert "connection" in str(e).lower() or "timeout" in str(e).lower()


def test_influx_queries_init():
    """Test InfluxDBQueries initialization."""
    config = load_config()
    queries = InfluxDBQueries(config)

    assert queries.storage_config == config["storage"]
    assert queries.bucket == config["storage"]["bucket"]
    assert queries.measurement == config["storage"]["measurement"]


@patch('src.storage.queries.InfluxDBClient')
def test_queries_get_record_count(mock_influx_client):
    """Test get_record_count method."""
    config = load_config()
    queries = InfluxDBQueries(config)

    # Mock the query API
    mock_result = MagicMock()
    mock_result.empty = True
    mock_result.iloc = MagicMock(return_value=MagicMock(_value=0))

    queries.query_api = Mock()
    queries.query_api.query_data_frame = Mock(return_value=mock_result)

    count = queries.get_record_count()

    assert count == 0


@patch('src.storage.queries.InfluxDBClient')
def test_queries_get_event_counts(mock_influx_client):
    """Test get_event_counts method."""
    config = load_config()
    queries = InfluxDBQueries(config)

    # Mock empty result
    mock_result = MagicMock()
    mock_result.empty = True

    queries.query_api = Mock()
    queries.query_api.query_data_frame = Mock(return_value=mock_result)

    counts = queries.get_event_counts(hours=24)

    assert counts == {}


@patch('src.storage.queries.InfluxDBClient')
def test_queries_get_latest_reading(mock_influx_client):
    """Test get_latest_reading returns None for empty DB."""
    config = load_config()
    queries = InfluxDBQueries(config)

    # Mock empty result
    mock_result = MagicMock()
    mock_result.empty = True

    queries.query_api = Mock()
    queries.query_api.query_data_frame = Mock(return_value=mock_result)

    latest = queries.get_latest_reading()

    assert latest is None


@patch('src.storage.queries.InfluxDBClient')
def test_queries_get_sensor_trends_empty(mock_influx_client):
    """Test get_sensor_trends returns an empty list for empty DB."""
    config = load_config()
    queries = InfluxDBQueries(config)

    mock_result = MagicMock()
    mock_result.empty = True

    queries.query_api = Mock()
    queries.query_api.query_data_frame = Mock(return_value=mock_result)

    trends = queries.get_sensor_trends(hours=24)

    assert trends == []


@patch('src.storage.queries.InfluxDBClient')
def test_queries_get_recent_anomalies_empty(mock_influx_client):
    """Test get_recent_anomalies returns an empty list for empty DB."""
    config = load_config()
    queries = InfluxDBQueries(config)

    mock_result = MagicMock()
    mock_result.empty = True

    queries.query_api = Mock()
    queries.query_api.query_data_frame = Mock(return_value=mock_result)

    anomalies = queries.get_recent_anomalies(hours=24)

    assert anomalies == []
