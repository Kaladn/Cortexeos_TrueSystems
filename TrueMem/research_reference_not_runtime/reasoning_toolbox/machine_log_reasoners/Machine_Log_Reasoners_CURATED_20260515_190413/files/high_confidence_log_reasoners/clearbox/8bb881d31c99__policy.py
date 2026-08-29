"""Deny-list privacy policy for the observe system.

Everything is enabled by default. Users disable specific sensor IDs,
categories, or sources. Policy stored as plaintext JSON under D:\\CLEARBOX\\data\\logs\\observe\\.
"""
from __future__ import annotations

import fnmatch
import json
from typing import Any

from security.data_paths import OBSERVE_DIR

POLICY_PATH = OBSERVE_DIR / "observe_policy.json"

DEFAULT_POLICY: dict[str, Any] = {
    "mode": "allow_all_default",
    "disabled_sensor_ids": [],
    "disabled_categories": [],
    "disabled_sources": [],
    "notes": "default policy v1",
}


def load_policy() -> dict:
    """Load current policy. Returns default if file missing."""
    if not POLICY_PATH.exists():
        return dict(DEFAULT_POLICY)
    try:
        with open(POLICY_PATH, encoding="utf-8") as _f:
            return json.load(_f)
    except Exception:
        return dict(DEFAULT_POLICY)


def save_policy(policy: dict) -> dict:
    """Save policy. Merges with defaults for missing keys."""
    merged = dict(DEFAULT_POLICY)
    for key in ("disabled_sensor_ids", "disabled_categories", "disabled_sources", "notes"):
        if key in policy:
            merged[key] = policy[key]
    POLICY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(POLICY_PATH, "w", encoding="utf-8") as _f:
        json.dump(merged, _f, indent=2, ensure_ascii=False)
    return merged


def is_allowed(sensor: dict, policy: dict) -> bool:
    """Check if a sensor is allowed under the current policy."""
    sid = sensor.get("id", "")
    cat = sensor.get("category", "")
    src = sensor.get("source", "")

    # Check disabled categories
    if cat in policy.get("disabled_categories", []):
        return False

    # Check disabled sources
    if src in policy.get("disabled_sources", []):
        return False

    # Check disabled sensor IDs (with wildcard support)
    for pattern in policy.get("disabled_sensor_ids", []):
        if fnmatch.fnmatch(sid, pattern):
            return False

    return True


def filter_catalog(
    catalog: list[dict], policy: dict | None = None,
) -> tuple[list[dict], list[dict]]:
    """Split catalog into (allowed, blocked) based on policy."""
    if policy is None:
        policy = load_policy()
    allowed = []
    blocked = []
    for s in catalog:
        if is_allowed(s, policy):
            allowed.append(s)
        else:
            blocked.append(s)
    return allowed, blocked
