"""Help System configuration -- reads from forest.config.json.

All config is optional with sensible defaults.
Reads the 'help_system' key from the main config if present.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

# ── Defaults ─────────────────────────────────────────────────

DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "content_path": str(Path(__file__).parent / "content" / "help_content.json"),
    "default_layer": 1,
    "panel_width_px": 360,
    "search_min_chars": 2,
}


def load_config(config_path: Path = None) -> Dict[str, Any]:
    """Load Help System config from forest.config.json.

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
            section = full.get("help_system", {})
            config.update(section)
    except Exception as e:
        logger.warning("Failed to load Help System config: %s", e)

    return config
