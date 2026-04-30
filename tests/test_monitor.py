from src.monitor.app import add_message, get_messages


def test_monitor_add_message_stores_pretty_json():
    """Test monitor stores raw MQTT payloads and pretty-prints JSON."""
    add_message("iot/environment/raw", '{"temperature_f":72.0,"humidity":45.0}')

    messages = get_messages()

    assert messages[0]["topic"] == "iot/environment/raw"
    assert messages[0]["payload"] == '{"temperature_f":72.0,"humidity":45.0}'
    assert '"temperature_f": 72.0' in messages[0]["pretty_payload"]
