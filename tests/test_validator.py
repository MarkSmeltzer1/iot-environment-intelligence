from src.processing.validator import validate_message
from src.utils.config_loader import load_config


def test_validate_message_valid():
    config = load_config()

    message = {
        "timestamp": "2026-04-22T18:30:00Z",
        "device_id": "esp32_room_1",
        "location": "bedroom",
        "temperature_f": 72.5,
        "humidity": 45.2,
        "pressure_hpa": 1012.3,
        "light_lux": 540,
    }

    is_valid, errors = validate_message(message, config)

    assert is_valid is True
    assert errors == []


def test_validate_message_missing_field():
    config = load_config()

    message = {
        "timestamp": "2026-04-22T18:30:00Z",
        "device_id": "esp32_room_1",
        "location": "bedroom",
        "temperature_f": 72.5,
        "humidity": 45.2,
        "pressure_hpa": 1012.3,
    }

    is_valid, errors = validate_message(message, config)

    assert is_valid is False
    assert "Missing required field: light_lux" in errors


def test_validate_message_bad_range():
    config = load_config()

    message = {
        "timestamp": "2026-04-22T18:30:00Z",
        "device_id": "esp32_room_1",
        "location": "bedroom",
        "temperature_f": 200,
        "humidity": 45.2,
        "pressure_hpa": 1012.3,
        "light_lux": 540,
    }

    is_valid, errors = validate_message(message, config)

    assert is_valid is False
    assert "temperature_f out of allowed range" in errors
