"""Pure parsing helpers for the charger's WebSocket messages.

Kept free of Home Assistant imports so it can be reused by standalone tooling
(see ``tools/probe.py``).
"""

from __future__ import annotations

import json
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Interfaces whose ``args`` values are themselves JSON-encoded strings.
_JSON_INTERFACES = ("de.bebro.WebServer", "de.bebro.iCAN", "de.bebro.SCC")


def flatten(obj: dict, parent: str = "", sep: str = ".") -> dict[str, Any]:
    """Flatten a nested dict into dotted keys."""
    items: dict[str, Any] = {}
    for key, value in obj.items():
        new_key = f"{parent}{sep}{key}" if parent else key
        if isinstance(value, dict):
            items.update(flatten(value, new_key, sep))
        else:
            items[new_key] = value
    return items


def convert_properties(obj: dict) -> dict[str, Any]:
    """Turn one charger WebSocket message into flattened ``de.bebro.*`` keys."""
    if "interface" not in obj or "args" not in obj:
        _LOGGER.debug("Ignoring unrecognised charger message: %s", obj)
        return {}

    intf = obj["interface"]
    path = obj.get("path", "").lstrip("/")
    parsed: dict[str, Any] = {}
    for key, value in obj["args"].items():
        if intf in _JSON_INTERFACES and isinstance(value, str):
            try:
                parsed[key] = json.loads(value)
            except (TypeError, json.JSONDecodeError):
                parsed[key] = value
        else:
            parsed[key] = value

    nested = {path: parsed} if path else parsed
    return flatten({intf: nested})
