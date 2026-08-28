"""Citation Sidecar Store — day-sharded, dual-indexed, plaintext JSON.

One JSON sidecar per day alongside the JSONL chat log:
    D:\\CLEARBOX\\data\\citations\\2026-02-12.citations.json

Dual index:
    by_block: { "msg_1_173...:b3": ["cite_id_1"] }   ← hot path (render)
    by_id:    { "cite_id_1": { ...record... } }       ← resolve path

All disk I/O goes through security.gateway (audited zone writes).
Stored as plaintext JSON — not encrypted.

Phase 1 Intake: All citation creation funnels through citation_intake.py
"""
from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Clearbox AI security stack ───────────────────────────────────
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from security.data_paths import CHAT_CITATIONS_DIR

try:
    from security.gateway import WriteZone, gateway as _gw
    _GOVERNED = True
except ImportError:
    _GOVERNED = False

# ── Phase 1 citation intake gate ───────────────────────────────
from Conversations.citations.citation_intake import (
    create_citation_record,
    backfill_phase1_fields,
)


# ── Constants ──────────────────────────────────────────────────

_DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SIDECAR_VERSION = 0


# ── Data structures ────────────────────────────────────────────

@dataclass
class Sidecar:
    """In-memory representation of one day's citation sidecar."""
    day: str
    version: int = _SIDECAR_VERSION
    by_block: Dict[str, List[str]] = field(default_factory=dict)
    by_id: Dict[str, dict] = field(default_factory=dict)


def _block_key(message_id: str, block_id: str) -> str:
    """Composite key for the by_block index."""
    return f"{message_id}:{block_id}"


# ── Store ──────────────────────────────────────────────────────

class CitationStore:
    """Day-sharded citation persistence with in-memory LRU cache.

    Usage:
        store = CitationStore()
        store.attach(day, message_id, block_id, block_ordinal, canonical, subject, source)
        cites = store.get_block_cites(day, message_id, block_id)
        cite  = store.get_citation(cite_id)
        all_  = store.load_day(day)
    """

    def __init__(self, max_cached_days: int = 14):
        self._root = CHAT_CITATIONS_DIR
        self._root.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self._cache: Dict[str, Sidecar] = {}
        self._lru: List[str] = []
        self._max_cached = max_cached_days

        # Best-effort: cite_id → day (avoids disk scan on resolve)
        self._cite_day_hint: Dict[str, str] = {}

    # ── File paths ─────────────────────────────────────────────

    def _path(self, day: str) -> Path:
        return self._root / f"{day}.citations.json"

    # ── LRU management ─────────────────────────────────────────

    def _touch(self, day: str) -> None:
        if day in self._lru:
            self._lru.remove(day)
        self._lru.append(day)
        while len(self._lru) > self._max_cached:
            evict = self._lru.pop(0)
            self._cache.pop(evict, None)

    # ── Load / Save ────────────────────────────────────────────

    def load_day(self, day: str) -> Sidecar:
        """Load a day's sidecar (from cache or disk). Creates empty if missing."""
        if not _DAY_RE.match(day):
            raise ValueError(f"Invalid day format: {day}")

        with self._lock:
            if day in self._cache:
                self._touch(day)
                return self._cache[day]

            path = self._path(day)
            if path.exists():
                try:
                    with open(path, encoding="utf-8") as _f:
                        raw = json.load(_f)

                    # Backfill Phase 1 fields for legacy records
                    by_id_backfilled = {}
                    for cid, rec in raw.get("by_id", {}).items():
                        by_id_backfilled[cid] = backfill_phase1_fields(rec)

                    sc = Sidecar(
                        day=raw.get("day", day),
                        version=raw.get("version", _SIDECAR_VERSION),
                        by_block=raw.get("by_block", {}),
                        by_id=by_id_backfilled,
                    )
                    # Rebuild cite→day hints
                    for cid in sc.by_id:
                        self._cite_day_hint[cid] = day
                except Exception:
                    sc = Sidecar(day=day)
            else:
                sc = Sidecar(day=day)

            self._cache[day] = sc
            self._touch(day)
            return sc

    def _save(self, sc: Sidecar) -> None:
        """Write sidecar to disk through gateway (plaintext JSON + audit)."""
        payload = json.dumps({
            "day": sc.day,
            "version": sc.version,
            "by_block": sc.by_block,
            "by_id": sc.by_id,
        }, ensure_ascii=False, indent=2)

        filename = f"{sc.day}.citations.json"

        if _GOVERNED:
            result = _gw.write("system", WriteZone.CHAT_CITATIONS, filename, payload, encrypt=False)
            if not result.success:
                raise OSError(f"Gateway write failed: {result.error}")
        else:
            out = self._path(sc.day)
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "w", encoding="utf-8") as _f:
                _f.write(payload)

    def invalidate(self, day: str | None = None) -> None:
        """Evict cached sidecar(s) so next load_day reads fresh from disk.

        Args:
            day: Specific day to invalidate, or None to clear entire cache.
        """
        with self._lock:
            if day:
                self._cache.pop(day, None)
                if day in self._lru:
                    self._lru.remove(day)
            else:
                self._cache.clear()
                self._lru.clear()

    # ── Attach / Detach ────────────────────────────────────────

    def attach(
        self,
        day: str,
        message_id: str,
        block_id: str,
        block_ordinal: int,
        canonical: str,
        subject: Optional[str] = None,
        note: Optional[str] = None,
        source: str = "ui",
    ) -> dict:
        """Attach a citation to a block. Returns the citation record.

        Phase 1: All citations funnel through citation_intake gate.
        """
        with self._lock:
            sc = self.load_day(day)
            key = _block_key(message_id, block_id)

            # Dedup check (use coord or canonical)
            existing_ids = sc.by_block.get(key, [])
            for cid in existing_ids:
                rec = sc.by_id.get(cid, {})
                existing_coord = rec.get("coord") or rec.get("canonical")
                if existing_coord == canonical:
                    raise ValueError(f"Citation {canonical} already on block {block_id}")

            # Create citation through shared intake gate (validates coord)
            record = create_citation_record(
                coord=canonical,
                source=source,
                subject=subject,
                note=note,
            )

            # Add store-specific fields (legacy compatibility)
            record["day"] = day
            record["message_id"] = message_id
            record["block_id"] = block_id
            record["block_ordinal"] = block_ordinal
            record["linked"] = []  # Phase 2 field (keep for compat)
            record["data_lake"] = None  # Phase 2 field (keep for compat)

            cite_id = record["cite_id"]

            # Write to both indexes
            sc.by_id[cite_id] = record
            if key not in sc.by_block:
                sc.by_block[key] = []
            sc.by_block[key].append(cite_id)

            # Deterministic ordering: sort by (created_at_utc, cite_id)
            sc.by_block[key].sort(key=lambda cid: (
                sc.by_id.get(cid, {}).get("created_at_utc", ""),
                sc.by_id.get(cid, {}).get("cite_id", "")
            ))

            self._cite_day_hint[cite_id] = day
            self._save(sc)
            return record

    def detach(self, day: str, message_id: str, block_id: str, cite_id: str) -> bool:
        """Remove a citation from a block. Returns True if found and removed."""
        with self._lock:
            sc = self.load_day(day)
            key = _block_key(message_id, block_id)

            # Remove from by_block index
            ids = sc.by_block.get(key, [])
            if cite_id not in ids:
                return False
            ids.remove(cite_id)
            if not ids:
                del sc.by_block[key]

            # Remove from by_id index
            sc.by_id.pop(cite_id, None)
            self._cite_day_hint.pop(cite_id, None)

            self._save(sc)
            return True

    # ── Queries ────────────────────────────────────────────────

    def get_block_cites(self, day: str, message_id: str, block_id: str) -> List[dict]:
        """Get all citations attached to a specific block (hot path)."""
        with self._lock:
            sc = self.load_day(day)
            key = _block_key(message_id, block_id)
            ids = sc.by_block.get(key, [])
            return [sc.by_id[cid] for cid in ids if cid in sc.by_id]

    def get_citation(self, cite_id: str) -> Optional[dict]:
        """Resolve a single citation by ID."""
        with self._lock:
            # Try hint first
            hinted = self._cite_day_hint.get(cite_id)
            if hinted:
                sc = self.load_day(hinted)
                rec = sc.by_id.get(cite_id)
                if rec:
                    return rec

            # Try all cached days
            for day, sc in self._cache.items():
                rec = sc.by_id.get(cite_id)
                if rec:
                    self._cite_day_hint[cite_id] = day
                    return rec

        # Bounded disk scan (recent 30 days max)
        candidates = sorted(self._root.glob("*.citations.json"),
                          key=lambda p: p.stat().st_mtime, reverse=True)[:30]
        for p in candidates:
            try:
                with open(p, encoding="utf-8") as _f:
                    raw = json.load(_f)
                rec = raw.get("by_id", {}).get(cite_id)
                if rec:
                    with self._lock:
                        self._cite_day_hint[cite_id] = rec.get("day", p.stem.split(".")[0])
                    return rec
            except Exception:
                continue
        return None

    def get_day_cites_by_block(self, day: str) -> Dict[str, List[dict]]:
        """Get all citations for a day, grouped by block key.

        Returns: { "msg_1_173...:b3": [{cite_record}, ...], ... }
        Used by chat history hydration.
        """
        with self._lock:
            sc = self.load_day(day)
            result: Dict[str, List[dict]] = {}
            for key, ids in sc.by_block.items():
                result[key] = [sc.by_id[cid] for cid in ids if cid in sc.by_id]
            return result

    def list_days(self) -> List[str]:
        """List all days that have citation sidecars."""
        days = []
        for p in sorted(self._root.glob("*.citations.json")):
            stem = p.stem.replace(".citations", "")
            if _DAY_RE.match(stem):
                days.append(stem)
        return days

    def distribution(self) -> dict:
        """Citation count per day, for the Explorer day-distribution chart.

        Returns: { "days": [{"day": "2026-02-21", "count": 5}, ...], "total": 42 }
        Sorted newest first.
        """
        self.invalidate()  # Fresh read (cross-process writes)
        days = list(reversed(self.list_days()))
        result = []
        total = 0
        for day in days:
            sc = self.load_day(day)
            count = len(sc.by_id)
            total += count
            result.append({"day": day, "count": count})
        return {"days": result, "total": total}

    # ── Browse (paginated by day) ─────────────────────────────

    def get_all_paginated(
        self,
        cursor: Optional[str] = None,
        limit: int = 5,
    ) -> dict:
        """Return citations paginated by day (newest first).

        Args:
            cursor: Day string to start AFTER (exclusive). None = start from newest.
            limit:  Max number of days to include per page.

        Returns:
            {"days": ["2026-02-18", ...], "items": [{cite}, ...],
             "next_cursor": "2026-02-13" or None, "total_days": 42}
        """
        self.invalidate()  # Fresh read (cross-process writes)
        all_days = list(reversed(self.list_days()))  # newest first
        total = len(all_days)

        if cursor:
            try:
                idx = all_days.index(cursor) + 1
            except ValueError:
                idx = 0
        else:
            idx = 0

        page_days = all_days[idx : idx + limit]
        items: List[dict] = []
        for day in page_days:
            sc = self.load_day(day)
            for rec in sc.by_id.values():
                items.append(rec)

        next_cursor = page_days[-1] if len(all_days) > idx + limit and page_days else None

        return {
            "days": page_days,
            "items": items,
            "next_cursor": next_cursor,
            "total_days": total,
        }

    # ── Edit ──────────────────────────────────────────────────

    def update_cite(self, cite_id: str, fields: dict) -> Optional[dict]:
        """Update mutable fields on a citation. Returns updated record or None.

        Mutable fields: subject, note.
        If 'coord' is in fields, re-validates through intake gate and updates
        the canonical/coord fields.
        """
        # Find which day owns this cite
        day = self._cite_day_hint.get(cite_id)
        if not day:
            rec = self.get_citation(cite_id)
            if not rec:
                return None
            day = self._cite_day_hint.get(cite_id)
        if not day:
            return None

        with self._lock:
            sc = self.load_day(day)
            rec = sc.by_id.get(cite_id)
            if not rec:
                return None

            # Mutable simple fields
            if "subject" in fields:
                rec["subject"] = fields["subject"] or None
            if "note" in fields:
                rec["note"] = fields["note"] or None

            # Coord change: re-validate through intake gate
            if "coord" in fields and fields["coord"] != rec.get("coord"):
                from Conversations.citations.citation_intake import canonicalize_coord
                canon = canonicalize_coord(fields["coord"])
                rec["coord"] = canon.coord
                rec["canonical"] = canon.coord  # legacy alias

            sc.by_id[cite_id] = rec
            self._save(sc)
            return rec

    # ── Hard delete ───────────────────────────────────────────

    def hard_delete(self, cite_id: str) -> bool:
        """Permanently remove a citation from all indexes. Returns True if found."""
        day = self._cite_day_hint.get(cite_id)
        if not day:
            rec = self.get_citation(cite_id)
            if not rec:
                return False
            day = self._cite_day_hint.get(cite_id)
        if not day:
            return False

        with self._lock:
            sc = self.load_day(day)
            if cite_id not in sc.by_id:
                return False

            # Remove from by_id
            sc.by_id.pop(cite_id, None)

            # Remove from all by_block lists
            for key in list(sc.by_block.keys()):
                if cite_id in sc.by_block[key]:
                    sc.by_block[key].remove(cite_id)
                    if not sc.by_block[key]:
                        del sc.by_block[key]

            self._cite_day_hint.pop(cite_id, None)
            self._save(sc)
            return True

    # ── Health check ──────────────────────────────────────────

    def health_check(self, days: Optional[int] = None) -> dict:
        """Structural health scan across citation sidecars.

        Args:
            days: Max recent days to scan. None = scan all.

        Checks:
            orphaned:      cite in by_id but not referenced in any by_block list
            dangling:      by_block references cite_id not found in by_id
            stale:         sidecar file exists but has 0 citations
            duplicates:    same canonical coord attached to same block twice
            cross_day:     same cite_id found in multiple day sidecars
        """
        orphaned: List[dict] = []
        dangling: List[dict] = []
        stale: List[str] = []
        duplicates: List[dict] = []
        cross_day: List[dict] = []

        seen_ids: Dict[str, str] = {}  # cite_id → first day seen
        total_cites = 0

        all_days = self.list_days()
        scan_days = list(reversed(all_days))[:days] if days else all_days
        for day in scan_days:
            sc = self.load_day(day)
            total_cites += len(sc.by_id)

            if not sc.by_id and not sc.by_block:
                stale.append(day)
                continue

            # Cross-day collision check
            for cid in sc.by_id:
                if cid in seen_ids:
                    cross_day.append({
                        "cite_id": cid,
                        "day_a": seen_ids[cid],
                        "day_b": day,
                    })
                else:
                    seen_ids[cid] = day

            # Collect all referenced IDs from by_block
            referenced = set()
            for key, ids in sc.by_block.items():
                for cid in ids:
                    referenced.add(cid)
                    if cid not in sc.by_id:
                        dangling.append({
                            "day": day,
                            "block_key": key,
                            "cite_id": cid,
                        })

                # Duplicate coord check within same block
                coords_on_block = []
                for cid in ids:
                    rec = sc.by_id.get(cid, {})
                    coord = rec.get("coord") or rec.get("canonical")
                    if coord and coord in coords_on_block:
                        duplicates.append({
                            "day": day,
                            "block_key": key,
                            "cite_id": cid,
                            "coord": coord,
                        })
                    if coord:
                        coords_on_block.append(coord)

            # Orphaned: in by_id but not referenced
            for cid in sc.by_id:
                if cid not in referenced:
                    orphaned.append({
                        "day": day,
                        "cite_id": cid,
                        "coord": sc.by_id[cid].get("coord", "?"),
                    })

        return {
            "total_cites": total_cites,
            "total_days": len(all_days),
            "scanned_days": len(scan_days),
            "orphaned": orphaned,
            "dangling": dangling,
            "stale": stale,
            "duplicates": duplicates,
            "cross_day": cross_day,
            "clean": (
                not orphaned and not dangling and not stale
                and not duplicates and not cross_day
            ),
        }
