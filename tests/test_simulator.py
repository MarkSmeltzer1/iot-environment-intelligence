from src.simulation.generator import SimulatorState, build_reading


def test_build_reading_has_required_fields():
    """Test simulated normal reading matches the project schema."""
    reading = build_reading(
        index=1,
        state=SimulatorState(),
        device_id="esp32_room_1",
        include_failures=False,
    )

    assert reading["device_id"] == "esp32_room_1"
    assert reading["location"] == "bedroom"
    assert "timestamp" in reading
    assert isinstance(reading["temperature_f"], float)
    assert isinstance(reading["humidity"], float)
    assert isinstance(reading["pressure_hpa"], float)
    assert isinstance(reading["light_lux"], int)


def test_build_reading_can_simulate_dropout():
    """Test simulator can skip publishing to represent a dropout."""
    reading = build_reading(
        index=75,
        state=SimulatorState(),
        device_id="esp32_room_1",
        include_failures=True,
    )

    assert reading is None


def test_build_reading_can_simulate_out_of_range_value():
    """Test simulator can generate a validation failure."""
    reading = build_reading(
        index=95,
        state=SimulatorState(),
        device_id="esp32_room_1",
        include_failures=True,
    )

    assert reading["temperature_f"] == 130.0
