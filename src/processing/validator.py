from datetime import datetime
from typing import Any, Dict, List, Tuple


def _is_iso_timestamp(value: str) -> bool:
    """
    Return True if value is a valid ISO timestamp.
    Accepts timestamps ending in 'Z' by converting to +00:00.
    """
    try:
        normalized = value.replace("Z", "+00:00")
        datetime.fromisoformat(normalized)
        return True
    except Exception:
        return False


def validate_message(message: Dict[str, Any], config: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a raw sensor message against required fields and allowed ranges.

    Returns:
        (is_valid, errors)
    """
    errors: List[str] = []

    required_fields = config["processing"]["required_fields"]
    validation = config["validation"]

    for field in required_fields:
        if field not in message:
            errors.append(f"Missing required field: {field}")

    if errors:
        return False, errors

    if not isinstance(message["timestamp"], str) or not _is_iso_timestamp(message["timestamp"]):
        errors.append("Invalid timestamp format")

    numeric_fields = [
        "temperature_f",
        "humidity",
        "pressure_hpa",
        "light_lux",
    ]

    for field in numeric_fields:
        value = message.get(field)
        if not isinstance(value, (int, float)):
            errors.append(f"Field must be numeric: {field}")

    if errors:
        return False, errors

    temp_min, temp_max = validation["allowed_temp_range_f"]
    humidity_min, humidity_max = validation["allowed_humidity_range"]
    pressure_min, pressure_max = validation["allowed_pressure_range_hpa"]
    light_min, light_max = validation["allowed_light_range_lux"]

    if not (temp_min <= message["temperature_f"] <= temp_max):
        errors.append("temperature_f out of allowed range")

    if not (humidity_min <= message["humidity"] <= humidity_max):
        errors.append("humidity out of allowed range")

    if not (pressure_min <= message["pressure_hpa"] <= pressure_max):
        errors.append("pressure_hpa out of allowed range")

    if not (light_min <= message["light_lux"] <= light_max):
        errors.append("light_lux out of allowed range")

    return len(errors) == 0, errors
