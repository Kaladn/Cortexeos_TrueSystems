"""
Wolf Engine — Plugin Configuration.

Dual config source:
  1. forest.config.json ["wolf_engine"] section (when running inside Forest AI)
  2. WOLF_* environment variables (override anything)
  3. DEFAULTS dict (always present fallback)

Backward-compatible: existing `from wolf_engine.config import X` still works.
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
    "genome_path": os.path.join(os.path.dirname(__file__), "data", "symbol_genome_master_dictionary.json"),
    "db_path": os.path.join(os.path.dirname(__file__), "data", "wolf_engine.db"),
    "genome_version": "v1.0",
    "context_window_size": 6,
    "forge_window_size": 10000,
    "log_level": "INFO",
    "log_format": "json",
    "sql_max_retries": 3,
    "sql_retry_base_wait": 0.1,
    "modules": {},
}


# ── Config Loader ────────────────────────────────────────────

def load_config(config_path: Path | str | None = None) -> Dict[str, Any]:
    """Load config. Priority: DEFAULTS < forest.config.json < WOLF_* env vars."""
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
            section = full.get("wolf_engine", {})
            config.update(section)
    except Exception as e:
        logger.warning("Failed to load Wolf Engine config from %s: %s", config_path, e)

    # Env var overrides (WOLF_* prefix)
    env_map = {
        "WOLF_GENOME_PATH": ("genome_path", str),
        "WOLF_DB_PATH": ("db_path", str),
        "WOLF_GENOME_VERSION": ("genome_version", str),
        "WOLF_CONTEXT_WINDOW_SIZE": ("context_window_size", int),
        "WOLF_FORGE_WINDOW_SIZE": ("forge_window_size", int),
        "WOLF_LOG_LEVEL": ("log_level", str),
        "WOLF_LOG_FORMAT": ("log_format", str),
        "WOLF_SQL_MAX_RETRIES": ("sql_max_retries", int),
        "WOLF_SQL_RETRY_BASE_WAIT": ("sql_retry_base_wait", float),
    }
    for env_key, (cfg_key, cast) in env_map.items():
        val = os.environ.get(env_key)
        if val is not None:
            try:
                config[cfg_key] = cast(val)
            except (ValueError, TypeError):
                pass

    return config


# ── Load once at import time ─────────────────────────────────

_cfg = load_config()

# ── Backward-compatible module-level constants ───────────────
# Every existing `from wolf_engine.config import X` keeps working.

SYMBOL_GENOME_PATH: str = _cfg["genome_path"]
DB_PATH: str = _cfg["db_path"]
GENOME_VERSION: str = _cfg["genome_version"]
CONTEXT_WINDOW_SIZE: int = _cfg["context_window_size"]
FORGE_WINDOW_SIZE: int = _cfg["forge_window_size"]
LOG_LEVEL: str = _cfg["log_level"]
LOG_FORMAT: str = _cfg["log_format"]
SQL_MAX_RETRIES: int = _cfg["sql_max_retries"]
SQL_RETRY_BASE_WAIT: float = _cfg["sql_retry_base_wait"]
