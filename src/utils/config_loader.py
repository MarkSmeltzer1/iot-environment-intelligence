from pathlib import Path
from typing import Any, Dict

import yaml


def load_config(config_path: str = "config/settings.yaml") -> Dict[str, Any]:
    """
    Load YAML configuration file and return as a dictionary.
    """
    path = Path(config_path)

    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file)

    if not isinstance(config, dict):
        raise ValueError("Configuration file did not load as a dictionary.")

    return config
