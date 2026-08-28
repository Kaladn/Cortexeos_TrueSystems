"""Chat Packs configuration -- reads from forest.config.json.

All config is optional with sensible defaults.
Reads the 'chat_packs' key from the main config if present.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ── Defaults ─────────────────────────────────────────────────

DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "default_model": "gpt_oss:20b",
    "max_sections": 50,
    "max_questions": 20,
    "ollama_timeout": 120.0,
    "max_install_size_mb": 10,
    "allowed_install_roots": [],
}


def load_config(config_path: Path = None) -> Dict[str, Any]:
    """Load Chat Packs config from forest.config.json.

    Returns merged config: file values override defaults.
    """
    secure_loader = None
    if config_path is None:
        try:
            from security.data_paths import FOREST_CONFIG_PATH
            from security.secure_storage import secure_json_load
            config_path = FOREST_CONFIG_PATH
            secure_loader = secure_json_load
        except ImportError:
            config_path = Path("forest.config.json")

    config = dict(DEFAULTS)

    try:
        if config_path.exists():
            if secure_loader is not None:
                full = secure_loader(config_path)
            else:
                with open(config_path, "r", encoding="utf-8") as f:
                    full = json.load(f)
            section = full.get("chat_packs", {})
            config.update(section)
    except Exception as e:
        logger.warning("Failed to load Chat Packs config: %s", e)

    # Env var overrides
    if os.environ.get("CHAT_PACKS_ENABLED"):
        config["enabled"] = os.environ["CHAT_PACKS_ENABLED"].lower() in ("1", "true")
    if os.environ.get("CHAT_PACKS_DEFAULT_MODEL"):
        config["default_model"] = os.environ["CHAT_PACKS_DEFAULT_MODEL"]

    return config
