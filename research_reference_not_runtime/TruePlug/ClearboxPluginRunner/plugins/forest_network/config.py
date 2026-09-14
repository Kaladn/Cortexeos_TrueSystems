"""Forest Network — configuration loader.

Reads forest.config.json and extracts:
  - allow_roots:   list of resolved absolute Paths this node is allowed to serve
  - require_auth:  bool (default True)
  - nodes:         list of node entries with id/host/port/api_key
  - peer_keys:     list of non-null api_keys (for auth validation)

All path resolution is done once per call; no module-level caching so that
config changes during a session take effect without restart.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

LOGGER = logging.getLogger("forest.network.config")

# Repo root: plugins/forest_network/config.py → ../../
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_CONFIG_FILE = _REPO_ROOT / "forest.config.json"


def get_repo_root() -> Path:
    """Return the absolute path to the repository root."""
    return _REPO_ROOT


def _load_raw() -> dict[str, Any]:
    """Load and parse forest.config.json. Returns {} on any error."""
    try:
        return json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        LOGGER.warning("forest.config.json not found at %s", _CONFIG_FILE)
        return {}
    except json.JSONDecodeError as exc:
        LOGGER.error("forest.config.json parse error: %s", exc)
        return {}


def get_network_config() -> dict[str, Any]:
    """Return the 'network' section of forest.config.json (or empty dict)."""
    return _load_raw().get("network", {})


def get_allow_roots() -> list[Path]:
    """Return list of resolved absolute Paths that this node is allowed to serve.

    Paths in config may be relative (resolved against repo root) or absolute.
    Returns empty list if 'network.allow_roots' is missing — all paths will be rejected.
    """
    roots = get_network_config().get("allow_roots", [])
    resolved: list[Path] = []
    for r in roots:
        p = Path(r)
        if not p.is_absolute():
            p = _REPO_ROOT / p
        try:
            resolved.append(p.resolve())
        except (OSError, RuntimeError) as exc:
            LOGGER.warning("Cannot resolve allow_root %r: %s", r, exc)
    return resolved


def is_auth_required() -> bool:
    """Return True if X-Forest-Node-Key auth is required on serve endpoints."""
    return bool(get_network_config().get("require_auth", True))


def get_nodes() -> list[dict[str, Any]]:
    """Return the full nodes list from forest.config.json."""
    return _load_raw().get("nodes", [])


def get_node(node_id: str) -> Optional[dict[str, Any]]:
    """Return the node dict for node_id, or None if not found."""
    for node in get_nodes():
        if node.get("id") == node_id:
            return node
    return None


def get_allow_root_paths() -> list[str]:
    """Return allow_roots as normalized relative path strings (no ./ prefix).

    These are the browsable root paths the UI shows per node.
    E.g. ["docs/GENESIS", "Lexical Data/Canonical", "forest_ai/data"]
    """
    roots = get_network_config().get("allow_roots", [])
    result: list[str] = []
    for r in roots:
        # Strip leading ./ or / — always relative to repo root
        clean = r.lstrip("./").lstrip("/")
        if clean:
            result.append(clean)
    return result


def get_peer_keys() -> list[str]:
    """Return all non-null, non-empty api_key values from the nodes list.

    These are the keys that remote peers present in X-Forest-Node-Key.
    The local 'this' node has api_key: null and is excluded.
    """
    return [
        str(n["api_key"])
        for n in get_nodes()
        if n.get("api_key")
    ]
