"""Clearbox AI — Runtime Trace Rail (in-repo producer library).

Deterministic structured logging for service boundaries, tool execution,
auth decisions, and error boundaries.  Append-only JSONL to the audit dir.

Usage (from any Clearbox AI module):
    from security.runtime_log import log_error, log_event, debug_enter, debug_exit

    log_error("documap", "map_create", "Bridge unreachable", level=3)
    log_event("documap", "citation_created", extra={"cite_id": "abc123"})

    debug_enter("documap", "maps/create", trace_id=tid)
    debug_exit("documap", "maps/create", ok=True, ms=42, trace_id=tid)

DEBUGWIRE toggle (entry/exit tracing):
    CLEARBOX_DEBUGWIRE=1                   # all components
    CLEARBOX_DEBUGWIRE=documap,bridge      # specific components only

All callsites tagged:  # DEBUGWIRE:<COMPONENT>
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

# ── Output path (same JSONL the error report tool reads) ──────
from security.data_paths import AUDIT_DIR
RUNTIME_LOG_PATH = AUDIT_DIR / "runtime_errors.jsonl"

# ── DEBUGWIRE toggle (env var seeds, runtime-mutable) ─────────
_DEBUGWIRE_RAW = os.environ.get("CLEARBOX_DEBUGWIRE", "")
_debugwire_all: bool = _DEBUGWIRE_RAW.strip() == "1"
_debugwire_components: set[str] = set(
    c.strip().lower() for c in _DEBUGWIRE_RAW.split(",") if c.strip()
) if not _debugwire_all else set()


def debugwire_active(component: str) -> bool:
    """Check if DEBUGWIRE tracing is active for a component."""
    return _debugwire_all or component.lower() in _debugwire_components


def debugwire_set(enabled: bool, components: list[str] | None = None):
    """Runtime toggle: enable/disable DEBUGWIRE tracing.

    Args:
        enabled: True = tracing on, False = tracing off.
        components: If None and enabled=True, trace ALL components.
                    If list provided, trace only those components.
    """
    global _debugwire_all, _debugwire_components
    if not enabled:
        _debugwire_all = False
        _debugwire_components = set()
    elif components:
        _debugwire_all = False
        _debugwire_components = set(c.strip().lower() for c in components if c.strip())
    else:
        _debugwire_all = True
        _debugwire_components = set()


def debugwire_status() -> dict:
    """Return current DEBUGWIRE state for API/UI consumption."""
    return {
        "enabled": _debugwire_all or bool(_debugwire_components),
        "mode": "all" if _debugwire_all else ("selective" if _debugwire_components else "off"),
        "components": sorted(_debugwire_components) if _debugwire_components else [],
    }


# ── Rotation ──────────────────────────────────────────────────
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_KEEP_ROTATED = 3


def _maybe_rotate():
    try:
        if not RUNTIME_LOG_PATH.exists():
            return
        if RUNTIME_LOG_PATH.stat().st_size < _MAX_BYTES:
            return
        ts = int(time.time() * 1000)
        rotated = RUNTIME_LOG_PATH.with_name(f"runtime_errors.{ts}.jsonl")
        RUNTIME_LOG_PATH.rename(rotated)
        audit_dir = RUNTIME_LOG_PATH.parent
        archives = sorted(
            audit_dir.glob("runtime_errors.*.jsonl"),
            key=lambda p: p.stat().st_mtime,
        )
        while len(archives) > _KEEP_ROTATED:
            archives.pop(0).unlink(missing_ok=True)
    except Exception:
        pass


def _append(entry: dict):
    """Append a JSON line to the runtime log. Never throws."""
    _maybe_rotate()
    try:
        RUNTIME_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(RUNTIME_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ── Public API ────────────────────────────────────────────────

def log_error(
    component: str,
    action: str,
    detail: str,
    level: int = 3,
    trace_id: str | None = None,
    extra: dict | None = None,
):
    """Log a runtime error (permanent, always written).

    Levels: 1=info, 2=warning, 3=feature broken, 4=critical.
    """
    entry = {
        "type": "error",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "component": component,
        "action": action,
        "detail": detail,
        "level": min(4, max(1, level)),
    }
    if trace_id:
        entry["trace_id"] = trace_id
    if extra:
        entry["extra"] = extra
    _append(entry)


def log_event(
    component: str,
    action: str,
    trace_id: str | None = None,
    extra: dict | None = None,
):
    """Log a non-error runtime event (telemetry / auditing)."""
    entry = {
        "type": "event",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "component": component,
        "action": action,
    }
    if trace_id:
        entry["trace_id"] = trace_id
    if extra:
        entry["extra"] = extra
    _append(entry)


def debug_enter(
    component: str,
    action: str,
    trace_id: str | None = None,
    extra: dict | None = None,
):
    """DEBUGWIRE: log entry into a service boundary. No-op if toggle is off."""
    if not debugwire_active(component):
        return
    entry = {
        "type": "debug_enter",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "component": component,
        "action": action,
    }
    if trace_id:
        entry["trace_id"] = trace_id
    if extra:
        entry["extra"] = extra
    _append(entry)


def debug_exit(
    component: str,
    action: str,
    ok: bool = True,
    detail: str = "",
    ms: float | None = None,
    trace_id: str | None = None,
    extra: dict | None = None,
):
    """DEBUGWIRE: log exit from a service boundary. No-op if toggle is off."""
    if not debugwire_active(component):
        return
    entry = {
        "type": "debug_exit",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "component": component,
        "action": action,
        "ok": ok,
    }
    if detail:
        entry["detail"] = detail
    if ms is not None:
        entry["ms"] = round(ms, 1)
    if trace_id:
        entry["trace_id"] = trace_id
    if extra:
        entry["extra"] = extra
    _append(entry)
