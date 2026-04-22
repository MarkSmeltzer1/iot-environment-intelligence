from src.processing.event_rules import detect_event
from src.utils.config_loader import load_config


def test_detect_event_normal():
    config = load_config()

    current = {
        "timestamp": "2026-04-22T18:30:00Z",
        "device_id": "esp32_room_1",
        "location": "bedroom",
        "temperature_f": 72.0,
        "humidity": 45.0,
        "pressure_hpa": 1012.0,
        "light_lux": 300,
    }

    result = detect_event(current=current, previous=None, config=config)

    assert result["event_label"] == "normal"
    assert result["anomaly_flag"] is False


def test_detect_event_high_temp():
    config = load_config()

    current = {
        "timestamp": "2026-04-22T18:30:00Z",
        "device_id": "esp32_room_1",
        "location": "bedroom",
        "temperature_f": 85.0,
        "humidity": 45.0,
        "pressure_hpa": 1012.0,
        "light_lux": 300,
    }

    result = detect_event(current=current, previous=None, config=config)

    assert result["event_label"] == "high_temp_alert"
    assert result["anomaly_flag"] is True


def test_detect_event_sunlight_heating():
    config = load_config()

    previous = {
        "timestamp": "2026-04-22T18:29:00Z",
        "device_id": "esp32_room_1",
        "location": "bedroom",
        "temperature_f": 72.0,
        "humidity": 45.0,
        "pressure_hpa": 1012.0,
        "light_lux": 400,
    }

    current = {
        "timestamp": "2026-04-22T18:30:00Z",
        "device_id": "esp32_room_1",
        "location": "bedroom",
        "temperature_f": 75.0,
        "humidity": 45.0,
        "pressure_hpa": 1012.0,
        "light_lux": 900,
    }

    result = detect_event(current=current, previous=previous, config=config)

    assert result["event_label"] == "sunlight_heating"
    assert result["anomaly_flag"] is False


def test_detect_event_sudden_cooling():
    config = load_config()

    previous = {
        "timestamp": "2026-04-22T18:29:00Z",
        "device_id": "esp32_room_1",
        "location": "bedroom",
        "temperature_f": 76.0,
        "humidity": 45.0,
        "pressure_hpa": 1012.0,
        "light_lux": 500,
    }

    current = {
        "timestamp": "2026-04-22T18:30:00Z",
        "device_id": "esp32_room_1",
        "location": "bedroom",
        "temperature_f": 71.0,
        "humidity": 45.0,
        "pressure_hpa": 1012.0,
        "light_lux": 500,
    }

    result = detect_event(current=current, previous=previous, config=config)

    assert result["event_label"] == "sudden_cooling"
    assert result["anomaly_flag"] is True
