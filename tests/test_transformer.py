from src.processing.transformer import process_message
from src.utils.config_loader import load_config


def test_process_message_valid_with_previous():
    """Test processing a valid message with previous data for event detection."""
    config = load_config()

    current = {
        "timestamp": "2026-04-28T10:00:00Z",
        "device_id": "esp32_room_1",
        "location": "bedroom",
        "temperature_f": 75.0,
        "humidity": 45.0,
        "pressure_hpa": 1013.0,
        "light_lux": 800,
    }

    previous = {
        "timestamp": "2026-04-28T09:59:00Z",
        "device_id": "esp32_room_1",
        "location": "bedroom",
        "temperature_f": 70.0,
        "humidity": 44.0,
        "pressure_hpa": 1013.0,
        "light_lux": 100,
    }

    result = process_message(current, config, previous)

    assert result["valid"] is True
    assert len(result["errors"]) == 0
    assert "event_label" in result
    assert "anomaly_flag" in result
    assert "reasons" in result


def test_process_message_invalid():
    """Test processing an invalid message (missing required fields)."""
    config = load_config()

    message = {
        "timestamp": "2026-04-28T10:00:00Z",
        "device_id": "esp32_room_1",
        # missing location, temperature_f, humidity, etc.
    }

    result = process_message(message, config, None)

    assert result["valid"] is False
    assert len(result["errors"]) > 0
    assert result["event_label"] == "unknown"
    assert result["anomaly_flag"] is False


def test_process_message_out_of_range():
    """Test processing a message with out-of-range values."""
    config = load_config()

    message = {
        "timestamp": "2026-04-28T10:00:00Z",
        "device_id": "esp32_room_1",
        "location": "bedroom",
        "temperature_f": 150.0,  # Out of range (max is 120)
        "humidity": 45.0,
        "pressure_hpa": 1013.0,
        "light_lux": 500,
    }

    result = process_message(message, config, None)

    assert result["valid"] is False
    assert any(
        "temperature_f out of allowed range" in err for err in result["errors"])


def test_process_message_no_previous():
    """Test processing a valid first message without previous data."""
    config = load_config()

    message = {
        "timestamp": "2026-04-28T10:00:00Z",
        "device_id": "esp32_room_1",
        "location": "bedroom",
        "temperature_f": 72.0,
        "humidity": 45.0,
        "pressure_hpa": 1013.0,
        "light_lux": 500,
    }

    result = process_message(message, config, None)

    assert result["valid"] is True
    assert result["event_label"] == "normal"
    assert result["anomaly_flag"] is False
