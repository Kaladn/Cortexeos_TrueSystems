"""
Forest Node -- Plugin Configuration.

Dual config source:
  1. forest.config.json ["forest_node"] section (when running inside Forest AI)
  2. FOREST_NODE_* environment variables (override anything)
  3. DEFAULTS dict (always present fallback)
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

# -- Defaults -----------------------------------------------------------------

DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "require_hello": True,
}


# -- Config Loader ------------------------------------------------------------

def load_config(config_path: Path | str | None = None) -> Dict[str, Any]:
    """Load config. Priority: DEFAULTS < forest.config.json < env vars."""
    config = dict(DEFAULTS)

    # Try forest.config.json
    secure_loader = None
    if config_path is None:
        try:
            from security.data_paths import FOREST_CONFIG_PATH
            from security.secure_storage import secure_json_load
            config_path = FOREST_CONFIG_PATH
            secure_loader = secure_json_load
        except ImportError:
            config_path = Path("forest.config.json")

    try:
        p = Path(config_path)
        if p.exists():
            if secure_loader is not None:
                full = secure_loader(p)
            else:
                with open(p, "r", encoding="utf-8") as f:
                    full = json.load(f)
            section = full.get("forest_node", {})
            config.update(section)
    except Exception as e:
        logger.warning("Failed to load Forest Node config from %s: %s", config_path, e)

    # Env var overrides
    env_map = {
        "FOREST_NODE_ENABLED": ("enabled", lambda v: v.lower() in ("1", "true", "yes")),
        "FOREST_NODE_REQUIRE_HELLO": ("require_hello", lambda v: v.lower() in ("1", "true", "yes")),
    }
    for env_key, (cfg_key, cast) in env_map.items():
        val = os.environ.get(env_key)
        if val is not None:
            try:
                config[cfg_key] = cast(val)
            except (ValueError, TypeError):
                pass

    return config


# -- Load once at import time -------------------------------------------------

_cfg = load_config()

ENABLED: bool = _cfg["enabled"]
REQUIRE_HELLO: bool = _cfg["require_hello"]
