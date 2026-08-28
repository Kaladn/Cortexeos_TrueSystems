"""Reach configuration loader.

Reads from clearbox.config.json reach block or falls back to defaults.
Each channel adapter has its own enable flag — nothing runs unless you turn it on.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

_DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "bridge_url": "https://127.0.0.1:5050",
    "bridge_ws_url": "ws://127.0.0.1:5051",
    "pairing_required": True,
    "audit_all_messages": True,
    "max_message_length": 4000,
    "channels": {
        "discord": {
            "enabled": False,
            "token_env": "REACH_DISCORD_TOKEN",
            "allowed_guilds": [],
            "pairing_required": True,
        },
        "telegram": {
            "enabled": False,
            "token_env": "REACH_TELEGRAM_TOKEN",
            "allowed_chats": [],
            "pairing_required": True,
        },
        "webhook": {
            "enabled": False,
            "secret_env": "REACH_WEBHOOK_SECRET",
            "allowed_origins": [],
        },
        "websocket": {
            "enabled": False,
            "port": 5053,
            "pairing_required": True,
        },
    },
}


def load_reach_config(config_path: Path | None = None) -> Dict[str, Any]:
    """Load reach config from clearbox.config.json or defaults."""
    if config_path is None:
        config_path = Path("clearbox.config.json")

    config = dict(_DEFAULTS)

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                full = json.load(f)
            reach_block = full.get("reach", {})
            _deep_merge(config, reach_block)
        except Exception as e:
            logger.warning("Failed to load reach config: %s — using defaults", e)

    return config


def _deep_merge(base: Dict, override: Dict) -> None:
    """Merge override into base, recursing into dicts."""
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v
