"""Governed I/O — bridges the ForestLexiconBridge to gateway-managed storage.

This module provides write/read functions that route all bridge I/O through
the Reader-Writer Gateway.  The bridge itself stays pure (compute-only);
this module owns the filesystem boundaries.

Write paths governed:
    map output     → WriteZone.DATA_MAPPED  (data/mapped/{run_id}/616_map.json)
    raw snapshot   → WriteZone.DATA_RAW     (data/raw/{run_id}/*)
    custom entries → WriteZone.LEXICON_USER (lexicon/user/custom_entries.json)
    snapshots      → WriteZone.STATE        (state/snapshots/{tag}_{ts}/*)

Read paths:
    system lexicon → ProtectedZone.LEXICON_SYSTEM (lexicon/system/*.json)
    user lexicon   → LEXICON_USER (lexicon/user/*.json)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from security.gateway import WriteZone, gateway
from scripts.session_manager import session as _session
from security.storage_layout import (
    DATA_MAPPED_DIR,
    DATA_RAW_DIR,
    LEXICON_SYSTEM_DIR,
    LEXICON_USER_DIR,
    build_mapped_manifest,
    build_raw_manifest,
    content_hash,
    generate_run_id,
)

LOGGER = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# MAP OUTPUT — write through gateway
# ═══════════════════════════════════════════════════════════════

def write_map_report(
    report: Dict[str, Any],
    source: str = "inline",
    input_text: Optional[str] = None,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Write a 616 map report to governed storage.

    Creates:
        data/mapped/{run_id}/616_map.json   (the map output)
        data/mapped/{run_id}/manifest.json  (provenance)
        data/raw/{run_id}/manifest.json     (input provenance)
        data/raw/{run_id}/input.txt         (if input_text provided)

    Returns:
        Dict with run_id, mapped_path, raw_path, success status.
    """
    run_id = run_id or generate_run_id()

    # ── Serialize the map ─────────────────────────────────────
    map_text = json.dumps(report, ensure_ascii=False, indent=2)
    map_hash = content_hash(map_text)

    # ── Count mapped vs unmapped ──────────────────────────────
    items = report.get("items", {})
    entry_count = len(items)
    mapped_count = sum(
        1 for info in items.values()
        if isinstance(info, dict) and info.get("symbol")
    )
    unmapped_count = entry_count - mapped_count

    # ── Write map to data/mapped/ ─────────────────────────────
    map_result = gateway.write(
        caller="system",
        zone=WriteZone.DATA_MAPPED,
        name=f"{run_id}/616_map.json",
        content=map_text,
        encrypt=False,  # Maps are large, keep readable
    )
    if not map_result.success:
        LOGGER.error("Failed to write map: %s", map_result.error)
        return {"success": False, "error": map_result.error, "run_id": run_id}

    # ── Write mapped manifest ─────────────────────────────────
    mapped_manifest = build_mapped_manifest(
        run_id=run_id,
        raw_run_id=run_id,
        source=source,
        lexicon_version="wordnet_147k_v2.0.0",
        entry_count=entry_count,
        mapped_count=mapped_count,
        unmapped_count=unmapped_count,
        output_hash=map_hash,
    )
    manifest_text = json.dumps(mapped_manifest, indent=2)
    gateway.write(
        caller="system",
        zone=WriteZone.DATA_MAPPED,
        name=f"{run_id}/manifest.json",
        content=manifest_text,
        encrypt=False,
    )

    # ── Write raw input snapshot ──────────────────────────────
    input_hash = content_hash(input_text) if input_text else "not_provided"
    token_count = report.get("total_tokens", 0)

    raw_manifest = build_raw_manifest(
        run_id=run_id,
        source=source,
        token_count=token_count,
        input_hash=input_hash,
        lexicon_version="wordnet_147k_v2.0.0",
    )
    gateway.write(
        caller="system",
        zone=WriteZone.DATA_RAW,
        name=f"{run_id}/manifest.json",
        content=json.dumps(raw_manifest, indent=2),
        encrypt=False,
    )

    if input_text:
        gateway.write(
            caller="system",
            zone=WriteZone.DATA_RAW,
            name=f"{run_id}/input.txt",
            content=input_text,
            encrypt=False,
        )

    LOGGER.info(
        "Map written: %s (%d entries, %d mapped, %d unmapped)",
        run_id, entry_count, mapped_count, unmapped_count,
    )

    # ── Persist run_id to session pointer-state ───────────────
    try:
        _session.set("last_map_run_id", run_id)
    except Exception as e:
        LOGGER.warning("Session persist (map run) failed: %s", e)

    return {
        "success": True,
        "run_id": run_id,
        "mapped_path": str(DATA_MAPPED_DIR / run_id / "616_map.json"),
        "raw_path": str(DATA_RAW_DIR / run_id / "manifest.json"),
        "entry_count": entry_count,
        "mapped_count": mapped_count,
        "unmapped_count": unmapped_count,
    }


# ═══════════════════════════════════════════════════════════════
# CUSTOM ENTRIES — user lexicon writes through gateway
# ═══════════════════════════════════════════════════════════════

def write_custom_entries(entries: Dict[str, Any]) -> bool:
    """Persist custom lexicon entries through the gateway.

    Writes to: lexicon/user/custom_entries.json
    """
    if not entries:
        return True

    text = json.dumps(entries, ensure_ascii=False, indent=2)
    result = gateway.write(
        caller="system",
        zone=WriteZone.LEXICON_USER,
        name="custom_entries.json",
        content=text,
        encrypt=False,
    )

    if not result.success:
        LOGGER.error("Failed to write custom entries: %s", result.error)
    return result.success


def read_custom_entries() -> Dict[str, Any]:
    """Read custom entries from governed storage."""
    path = LEXICON_USER_DIR / "custom_entries.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        LOGGER.error("Failed to read custom entries: %s", e)
        return {}


# ═══════════════════════════════════════════════════════════════
# SNAPSHOTS — state persistence through gateway
# ═══════════════════════════════════════════════════════════════

def write_snapshot(tag: str, lexicon_dump: Dict[str, Any]) -> str:
    """Write a bridge snapshot through the gateway.

    Writes to: state/snapshots/{tag}_{timestamp}/lexicon.json
    Returns: snapshot directory name
    """
    from datetime import datetime, timezone
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    safe_tag = f"{tag}_" if tag else ""
    snapshot_name = f"snapshot_{safe_tag}{timestamp}"

    text = json.dumps(lexicon_dump, ensure_ascii=False, indent=2)
    result = gateway.write(
        caller="system",
        zone=WriteZone.STATE,
        name=f"snapshots/{snapshot_name}/lexicon.json",
        content=text,
        encrypt=False,
    )

    if not result.success:
        LOGGER.error("Failed to write snapshot: %s", result.error)
        raise OSError(f"Snapshot write failed: {result.error}")

    return snapshot_name


# ═══════════════════════════════════════════════════════════════
# LEXICON READING — system partitions
# ═══════════════════════════════════════════════════════════════

def get_system_lexicon_root() -> Path:
    """Return the governed system lexicon directory."""
    return LEXICON_SYSTEM_DIR


def get_user_lexicon_root() -> Path:
    """Return the governed user lexicon directory."""
    return LEXICON_USER_DIR


def get_full_lexicon_roots() -> list[Path]:
    """Return both lexicon roots in load order (system first, user overlay)."""
    roots = [LEXICON_SYSTEM_DIR]
    if LEXICON_USER_DIR.exists():
        roots.append(LEXICON_USER_DIR)
    return roots


# ═══════════════════════════════════════════════════════════════
# MAP HISTORY — list previous runs
# ═══════════════════════════════════════════════════════════════

def list_map_runs() -> list[Dict[str, Any]]:
    """List all mapping runs from governed storage."""
    runs = []
    if not DATA_MAPPED_DIR.exists():
        return runs

    for run_dir in sorted(DATA_MAPPED_DIR.iterdir()):
        if not run_dir.is_dir():
            continue
        manifest_path = run_dir / "manifest.json"
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                runs.append(manifest)
            except (json.JSONDecodeError, OSError):
                runs.append({"run_id": run_dir.name, "error": "unreadable manifest"})
        else:
            runs.append({"run_id": run_dir.name, "manifest": False})

    return runs


def read_map_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Read a specific map output from governed storage."""
    map_path = DATA_MAPPED_DIR / run_id / "616_map.json"
    if not map_path.exists():
        return None
    try:
        return json.loads(map_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        LOGGER.error("Failed to read map %s: %s", run_id, e)
        return None
