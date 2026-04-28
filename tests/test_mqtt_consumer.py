"""
Test for MQTT Consumer module.
"""
import json
from unittest.mock import Mock

from src.ingestion.mqtt_consumer import MQTTConsumer
from src.utils.config_loader import load_config


def test_mqtt_consumer_init():
    """Test MQTTConsumer initialization."""
    config = load_config()
    consumer = MQTTConsumer(config)

    assert consumer.config == config
    assert consumer.messages_received == 0
    assert consumer.messages_valid == 0
    assert consumer.messages_invalid == 0
    assert consumer.previous_message is None


def test_mqtt_consumer_statistics():
    """Test get_statistics method."""
    config = load_config()
    consumer = MQTTConsumer(config)

    stats = consumer.get_statistics()

    assert stats["received"] == 0
    assert stats["valid"] == 0
    assert stats["invalid"] == 0


def test_mqtt_consumer_callback():
    """Test message callback functionality."""
    config = load_config()
    consumer = MQTTConsumer(config)

    callback_called = Mock()
    consumer.set_message_callback(callback_called)

    assert consumer.message_callback == callback_called


def test_on_connect_callback():
    """Test _on_connect callback."""
    config = load_config()
    consumer = MQTTConsumer(config)

    # Mock client
    mock_client = Mock()

    # Test successful connection (rc=0)
    consumer._on_connect(mock_client, None, {}, 0)
    # Should not raise any errors


def test_on_message_valid():
    """Test _on_message with valid JSON."""
    config = load_config()
    consumer = MQTTConsumer(config)

    # Create a mock message
    mock_client = Mock()
    mock_msg = Mock()
    mock_msg.topic = "iot/environment/raw"
    mock_msg.payload = json.dumps({
        "timestamp": "2026-04-28T10:00:00Z",
        "device_id": "esp32_room_1",
        "location": "bedroom",
        "temperature_f": 72.0,
        "humidity": 45.0,
        "pressure_hpa": 1013.0,
        "light_lux": 500,
    }).encode('utf-8')

    # Process the message
    consumer._on_message(mock_client, None, mock_msg)

    assert consumer.messages_received == 1
    assert consumer.messages_valid == 1
    assert consumer.messages_invalid == 0


def test_on_message_invalid_json():
    """Test _on_message with invalid JSON."""
    config = load_config()
    consumer = MQTTConsumer(config)

    mock_client = Mock()
    mock_msg = Mock()
    mock_msg.topic = "iot/environment/raw"
    mock_msg.payload = b"not valid json"

    consumer._on_message(mock_client, None, mock_msg)

    assert consumer.messages_received == 1
    assert consumer.messages_valid == 0
    assert consumer.messages_invalid == 1


def test_on_message_missing_fields():
    """Test _on_message with missing required fields."""
    config = load_config()
    consumer = MQTTConsumer(config)

    mock_client = Mock()
    mock_msg = Mock()
    mock_msg.topic = "iot/environment/raw"
    mock_msg.payload = json.dumps({
        "timestamp": "2026-04-28T10:00:00Z",
        "device_id": "esp32_room_1",
        # missing location, temperature_f, etc.
    }).encode('utf-8')

    consumer._on_message(mock_client, None, mock_msg)

    assert consumer.messages_received == 1
    assert consumer.messages_valid == 0
    assert consumer.messages_invalid == 1
