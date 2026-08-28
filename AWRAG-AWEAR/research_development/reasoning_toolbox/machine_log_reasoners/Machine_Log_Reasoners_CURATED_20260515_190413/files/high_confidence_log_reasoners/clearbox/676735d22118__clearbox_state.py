#!/usr/bin/env python3
"""Clearbox AI — State Snapshot & Restore

Captures runtime state (active model, services, config) before shutdown
and restores it on next boot.

State file: state/last_state.json
"""

import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

import sys
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from security.data_paths import STATE_DIR, LAST_STATE_PATH
from security.gateway import WriteZone, gateway as _gw

STATE_FILE = LAST_STATE_PATH

SERVICES = {
    "bridge":  {"port": 5050,  "health": "http://localhost:5050/api/stats"},
    "llm":     {"port": 11435, "health": "http://localhost:11435/health"},
    "ui":      {"port": 8080,  "health": "http://localhost:8080"},
}


def _probe(url: str, timeout: float = 2.0) -> dict | None:
    """Hit a health endpoint, return parsed JSON or None."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def snapshot() -> dict:
    """Capture current runtime state from live services."""
    state = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "services": {},
        "active_model": None,
        "user_display_name": None,
    }

    # Bridge
    bridge = _probe(SERVICES["bridge"]["health"])
    state["services"]["bridge"] = {
        "alive": bridge is not None,
        "port": SERVICES["bridge"]["port"],
    }

    # LLM
    llm = _probe(SERVICES["llm"]["health"])
    if llm:
        state["services"]["llm"] = {
            "alive": True,
            "port": SERVICES["llm"]["port"],
            "active_model": llm.get("active_model"),
            "available_models": llm.get("available_models", []),
            "logging_mode": llm.get("logging_mode"),
            "user_display_name": llm.get("user_display_name"),
        }
        state["active_model"] = llm.get("active_model")
        state["user_display_name"] = llm.get("user_display_name")
    else:
        state["services"]["llm"] = {"alive": False, "port": SERVICES["llm"]["port"]}

    # UI
    ui = _probe(SERVICES["ui"]["health"])
    state["services"]["ui"] = {
        "alive": ui is not None,
        "port": SERVICES["ui"]["port"],
    }

    return state


def save(state: dict | None = None) -> Path:
    """Snapshot (or accept pre-built state) and write to disk via gateway."""
    if state is None:
        state = snapshot()

    result = _gw.write(
        "system", WriteZone.STATE,
        "last_state.json",
        json.dumps(state, indent=2),
        encrypt=True,
    )
    if not result.success:
        raise OSError(f"Gateway write failed: {result.error}")
    return STATE_FILE


def load() -> dict | None:
    """Load last saved state from disk (gateway reads are unrestricted)."""
    if not STATE_FILE.exists():
        return None
    try:
        content = _gw.read(WriteZone.STATE, "last_state.json")
        return json.loads(content) if content else None
    except Exception:
        return None


def print_state(state: dict | None = None):
    """Pretty-print current or saved state."""
    if state is None:
        state = load()
    if state is None:
        print("  (no saved state)")
        return

    ts = state.get("captured_at", "?")
    print(f"  Snapshot: {ts}")
    print(f"  Model:    {state.get('active_model', '?')}")
    print(f"  User:     {state.get('user_display_name', '?')}")
    for name, info in state.get("services", {}).items():
        icon = "🟢" if info.get("alive") else "🔴"
        print(f"  {icon} {name:10s}  port {info.get('port')}")


# ── CLI ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "snapshot"

    if cmd == "snapshot":
        state = snapshot()
        path = save(state)
        print(f"📸 State saved → {path}")
        print_state(state)
    elif cmd == "show":
        print_state()
    else:
        print(f"Usage: python {__file__} [snapshot|show]")
