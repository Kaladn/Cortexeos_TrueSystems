"""Routing profile configuration — defaults, loading, validation.

Follows the same config pattern as LakeSpeak and Wolf Engine:
  Defaults dict → JSON section in clearbox.config.json → profile overrides.

All profile persistence goes through helpers in this module.
Endpoint handlers never write files directly.
"""

from __future__ import annotations

import copy
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

from security.data_paths import ROUTING_PROFILES_DIR

# ── Valid stage types ─────────────────────────────────────────
VALID_STAGE_TYPES = frozenset({
    "inject_616",
    "retrieval_gate",
    "model_call",
    "plugin_chain",
    "engine_parking",
    "reasoning_engine",
})

# ── Default profile ──────────────────────────────────────────
# These values MUST match the current chat handler behavior exactly.
# Changing a default here changes the baseline — do it intentionally.
DEFAULTS: dict = {
    "version": 1,
    "name": "default",
    "dev_mode": True,
    "pipeline": [
        {
            "id": "inject_616",
            "type": "inject_616",
            "enabled": True,
            "config": {
                "max_chars": 4000,
                "days_limit": 30,
            },
        },
        {
            "id": "retrieval_gate",
            "type": "retrieval_gate",
            "enabled": False,
            "config": {
                "policy": "warn",
                "min_docs": 1,
                "min_score": 0.0,
            },
        },
        {
            "id": "model_call",
            "type": "model_call",
            "enabled": True,
            "config": {
                "provider": "local",
                "model": "qwen2.5:7b-instruct",
                "gemini_model": "gemini-2.5-flash",
                "temperature": 0.2,
                "max_tokens": 4096,
            },
        },
        {
            "id": "plugin_chain",
            "type": "plugin_chain",
            "enabled": True,
            "config": {
                "bypass": False,
                "plugins": [
                    {"name": "lakespeak", "enabled": True},
                    {"name": "wolf_engine", "enabled": False},
                ],
            },
        },
        {
            "id": "engine_parking",
            "type": "engine_parking",
            "enabled": False,
            "config": {
                "park_modes": [],
                "redirect_mode": "llm",
            },
        },
        {
            "id": "reasoning_engine",
            "type": "reasoning_engine",
            "enabled": True,
            "config": {
                "url": "http://127.0.0.1:5051",
                "timeout_s": 10,
            },
        },
    ],
    "ui": {
        "show_route_badge": True,
        "badge_color": "orange",
    },
}

# Max profile size (bytes) — reject oversized profiles
MAX_PROFILE_SIZE = 51200  # 50 KB


def load_routing_profile(config: dict | None = None) -> dict:
    """Load routing profile from a config dict (clearbox.config.json['routing']).

    Falls back to DEFAULTS if config is None or missing required keys.
    Returns a deep copy so callers can't mutate the defaults.
    """
    if config is None:
        return copy.deepcopy(DEFAULTS)

    # Basic structural check — if pipeline is missing, fall back to defaults
    if "pipeline" not in config:
        return copy.deepcopy(DEFAULTS)

    return copy.deepcopy(config)


def validate_profile(profile: dict) -> Tuple[bool, str]:
    """Validate a routing profile.

    Returns (ok, error_msg). On success, error_msg is empty string.

    Rules:
      - version present
      - name present
      - pipeline present and is a list
      - Exactly one enabled model_call
      - All stage types are known (in VALID_STAGE_TYPES)
      - 4 core stage types must be present (inject_616, retrieval_gate, model_call, plugin_chain)
      - Serialized size under MAX_PROFILE_SIZE
    """
    if "version" not in profile:
        return False, "Missing 'version'"
    if "name" not in profile:
        return False, "Missing 'name'"
    if "pipeline" not in profile or not isinstance(profile["pipeline"], list):
        return False, "Missing or invalid 'pipeline'"

    # ── Check stage types ────────────────────────────────────
    present_types: set[str] = set()
    enabled_model_calls = 0

    for stage in profile["pipeline"]:
        stype = stage.get("type")
        if stype is None:
            return False, f"Stage missing 'type': {stage.get('id', '?')}"
        if stype not in VALID_STAGE_TYPES:
            return False, f"Unknown stage type: {stype}"

        present_types.add(stype)

        if stype == "model_call" and stage.get("enabled"):
            enabled_model_calls += 1

    # ── Exactly one enabled model_call ───────────────────────
    if enabled_model_calls != 1:
        return False, (
            f"Exactly 1 enabled model_call required, found {enabled_model_calls}"
        )

    # ── Required stage types must be present ────────────────
    _REQUIRED_STAGE_TYPES = frozenset({"inject_616", "retrieval_gate", "model_call", "plugin_chain"})
    missing = _REQUIRED_STAGE_TYPES - present_types
    if missing:
        return False, f"Pipeline missing required stage types: {missing}"

    # ── Size guard ───────────────────────────────────────────
    try:
        serialized = json.dumps(profile)
    except (TypeError, ValueError) as e:
        return False, f"Profile not JSON-serializable: {e}"

    if len(serialized) > MAX_PROFILE_SIZE:
        return False, f"Profile exceeds {MAX_PROFILE_SIZE // 1024}KB limit"

    return True, ""


# ── Named profile persistence ────────────────────────────────
# Named profiles live under ROUTING_PROFILES_DIR as JSON files.
# All writes go through these helpers — no raw file writes in endpoints.

_SAFE_NAME = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


def _sanitize_name(name: str) -> str | None:
    """Return sanitized profile name or None if invalid."""
    name = name.strip()
    if _SAFE_NAME.match(name):
        return name
    return None


def list_named_profiles() -> list[dict]:
    """List all saved named profiles.

    Returns list of {name, version, updated_utc} sorted by name.
    """
    profiles = []
    if not ROUTING_PROFILES_DIR.exists():
        return profiles
    for fp in sorted(ROUTING_PROFILES_DIR.glob("*.json")):
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            profiles.append({
                "name": data.get("name", fp.stem),
                "version": data.get("version", 0),
                "updated_utc": data.get("_saved_utc", ""),
            })
        except (json.JSONDecodeError, OSError):
            pass
    return profiles


def load_named_profile(name: str) -> dict | None:
    """Load a named profile by name. Returns None if not found."""
    safe = _sanitize_name(name)
    if not safe:
        return None
    fp = ROUTING_PROFILES_DIR / f"{safe}.json"
    if not fp.exists():
        return None
    try:
        return json.loads(fp.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def save_named_profile(name: str, profile: dict) -> Tuple[bool, str]:
    """Save a profile as a named profile.

    Validates before writing. Returns (ok, error_msg).
    """
    safe = _sanitize_name(name)
    if not safe:
        return False, "Invalid profile name (alphanumeric, hyphens, underscores, max 64 chars)"

    ok, err = validate_profile(profile)
    if not ok:
        return False, err

    save_data = copy.deepcopy(profile)
    save_data["name"] = safe
    save_data["_saved_utc"] = datetime.now(timezone.utc).isoformat()

    fp = ROUTING_PROFILES_DIR / f"{safe}.json"
    fp.write_text(json.dumps(save_data, indent=2), encoding="utf-8")
    return True, ""
