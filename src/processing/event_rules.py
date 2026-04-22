from typing import Any, Dict, Optional


def detect_event(
    current: Dict[str, Any],
    previous: Optional[Dict[str, Any]],
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Detect environmental events using simple rule-based logic.

    Returns a dictionary with:
        - event_label
        - anomaly_flag
        - reasons
    """
    thresholds = config["thresholds"]

    event_label = "normal"
    anomaly_flag = False
    reasons = []

    current_temp = current["temperature_f"]
    current_humidity = current["humidity"]
    current_light = current["light_lux"]

    if current_temp >= thresholds["high_temp_f"]:
        event_label = "high_temp_alert"
        anomaly_flag = True
        reasons.append("temperature exceeds high temperature threshold")

    elif current_humidity >= thresholds["high_humidity"]:
        event_label = "high_humidity_alert"
        anomaly_flag = True
        reasons.append("humidity exceeds high humidity threshold")

    if previous is not None:
        previous_temp = previous["temperature_f"]
        previous_light = previous["light_lux"]

        temp_change = current_temp - previous_temp
        light_change = current_light - previous_light

        if (
            current_light >= thresholds["high_light_lux"]
            and temp_change >= thresholds["sunlight_temp_rise_f"]
            and light_change > 0
        ):
            event_label = "sunlight_heating"
            reasons.append(
                "light is high and temperature increased since previous reading")

        elif temp_change <= -thresholds["sudden_temp_drop_f"]:
            event_label = "sudden_cooling"
            anomaly_flag = True
            reasons.append(
                "temperature dropped sharply since previous reading")

    return {
        "event_label": event_label,
        "anomaly_flag": anomaly_flag,
        "reasons": reasons,
    }
