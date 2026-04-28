from typing import Any, Dict, Optional

from .event_rules import detect_event
from .validator import validate_message


def process_message(
    message: Dict[str, Any],
    config: Dict[str, Any],
    previous: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Main transformation function that:
    1. Validates the message
    2. Detects events
    3. Returns combined result

    Args:
        message: Raw sensor message dictionary
        config: Configuration dictionary
        previous: Previous message for event detection (optional)

    Returns:
        Dictionary with:
        - raw: original message
        - valid: boolean indicating if message passed validation
        - errors: list of validation errors
        - event_label: detected event type
        - anomaly_flag: boolean for anomaly detection
        - reasons: list of reasons for event classification
    """
    # Step 1: Validate
    is_valid, errors = validate_message(message, config)

    # Step 2: Build result
    result = {
        "raw": message,
        "valid": is_valid,
        "errors": errors,
    }

    # Step 3: If valid, run event detection
    if is_valid:
        event_result = detect_event(message, previous, config)
        result["event_label"] = event_result["event_label"]
        result["anomaly_flag"] = event_result["anomaly_flag"]
        result["reasons"] = event_result["reasons"]
    else:
        result["event_label"] = "unknown"
        result["anomaly_flag"] = False
        result["reasons"] = []

    return result
