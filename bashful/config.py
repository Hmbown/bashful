"""User configuration overrides for agent capabilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".bashful"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict[str, Any]:
    """Load user config from ~/.bashful/config.json.

    Returns an empty dict if the file doesn't exist or is invalid.
    """
    if not CONFIG_FILE.is_file():
        return {}
    try:
        with open(CONFIG_FILE) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except (json.JSONDecodeError, OSError):
        return {}


def get_agent_overrides(config: dict[str, Any] | None = None) -> dict[str, dict]:
    """Return the per-agent override map from config.

    The config file uses::

        {
          "agents": {
            "gemini": {"modes": ["read", "write"]},
            "claude": {"modes": ["read"]}
          }
        }

    Returns a dict mapping agent id -> override fields.
    """
    if config is None:
        config = load_config()
    return config.get("agents", {})


def apply_overrides(agent_data: list[dict], overrides: dict[str, dict]) -> list[dict]:
    """Merge per-agent overrides into raw agent catalog entries.

    Only ``modes`` is supported as an override field today.  Unknown fields
    are silently ignored so the config file can evolve without breaking.
    """
    if not overrides:
        return agent_data

    ALLOWED_FIELDS = {"modes"}

    for entry in agent_data:
        agent_id = entry.get("id", "")
        if agent_id in overrides:
            for key, value in overrides[agent_id].items():
                if key in ALLOWED_FIELDS:
                    entry[key] = value
    return agent_data


def show_config() -> str:
    """Return a human-readable summary of the current config state."""
    lines = [f"Config file: {CONFIG_FILE}"]
    config = load_config()
    if not config:
        lines.append("  (no config file or empty)")
        return "\n".join(lines)

    overrides = get_agent_overrides(config)
    if not overrides:
        lines.append("  No agent overrides.")
    else:
        lines.append("  Agent overrides:")
        for agent_id, fields in sorted(overrides.items()):
            lines.append(f"    {agent_id}: {fields}")
    return "\n".join(lines)
