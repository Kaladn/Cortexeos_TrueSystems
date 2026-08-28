"""Note Sidecar Store — day-sharded, dual-indexed, plaintext JSON.

One JSON sidecar per day alongside the JSONL chat log:
    D:\\CLEARBOX\\data\\notes\\2026-02-20.notes.json

Dual index:
    by_block: { "msg_1_173...:b3": ["note_id_1"] }   <- hot path (render)
    by_id:    { "note_id_1": { ...record... } }        <- resolve path

All disk I/O goes through security.gateway (audited zone writes).
Stored as plaintext JSON — not encrypted.

Mirrors CitationStore pattern for consistency.
"""
from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# ── Clearbox AI security stack ───────────────────────────────────
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from security.data_paths import CHAT_NOTES_DIR

try:
    from security.gateway import WriteZone, gateway as _gw
    _GOVERNED = True
except ImportError:
    _GOVERNED = False


# ── Constants ──────────────────────────────────────────────────

_DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_SIDECAR_VERSION = 0


# ── Data structures ────────────────────────────────────────────

@dataclass
class NoteSidecar:
    """In-memory representation of one day's note sidecar."""
    day: str
    version: int = _SIDECAR_VERSION
    by_block: Dict[str, List[str]] = field(default_factory=dict)
    by_id: Dict[str, dict] = field(default_factory=dict)


def _block_key(message_id: str, block_id: str) -> str:
    """Composite key for the by_block index."""
    return f"{message_id}:{block_id}"


# ── Store ──────────────────────────────────────────────────────

class NoteStore:
    """Day-sharded note persistence with in-memory LRU cache.

    Usage:
        store = NoteStore()
        store.attach(day, message_id, block_id, block_ordinal, note_text)
        notes = store.get_block_notes(day, message_id, block_id)
        store.detach(day, message_id, block_id, note_id)
    """

    def __init__(self, max_cached_days: int = 14):
        self._root = CHAT_NOTES_DIR
        self._root.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self._cache: Dict[str, NoteSidecar] = {}
        self._lru: List[str] = []
        self._max_cached = max_cached_days

    # ── File paths ─────────────────────────────────────────────

    def _path(self, day: str) -> Path:
        return self._root / f"{day}.notes.json"

    # ── LRU management ─────────────────────────────────────────

    def _touch(self, day: str) -> None:
        if day in self._lru:
            self._lru.remove(day)
        self._lru.append(day)
        while len(self._lru) > self._max_cached:
            evict = self._lru.pop(0)
            self._cache.pop(evict, None)

    # ── Load / Save ────────────────────────────────────────────

    def load_day(self, day: str) -> NoteSidecar:
        """Load a day's note sidecar (from cache or disk). Creates empty if missing."""
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
                    sc = NoteSidecar(
                        day=raw.get("day", day),
                        version=raw.get("version", _SIDECAR_VERSION),
                        by_block=raw.get("by_block", {}),
                        by_id=raw.get("by_id", {}),
                    )
                except Exception:
                    sc = NoteSidecar(day=day)
            else:
                sc = NoteSidecar(day=day)

            self._cache[day] = sc
            self._touch(day)
            return sc

    def _save(self, sc: NoteSidecar) -> None:
        """Write note sidecar to disk through gateway (plaintext JSON + audit)."""
        payload = json.dumps({
            "day": sc.day,
            "version": sc.version,
            "by_block": sc.by_block,
            "by_id": sc.by_id,
        }, ensure_ascii=False, indent=2)

        filename = f"{sc.day}.notes.json"

        if _GOVERNED:
            result = _gw.write("system", WriteZone.CHAT_NOTES, filename, payload, encrypt=False)
            if not result.success:
                raise OSError(f"Gateway write failed: {result.error}")
        else:
            out = self._path(sc.day)
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "w", encoding="utf-8") as _f:
                _f.write(payload)

    # ── Attach / Detach ────────────────────────────────────────

    def attach(
        self,
        day: str,
        message_id: str,
        block_id: str,
        block_ordinal: int,
        note_text: str,
    ) -> dict:
        """Attach a note to a block. Returns the note record."""
        with self._lock:
            sc = self.load_day(day)
            key = _block_key(message_id, block_id)

            note_id = f"n_{int(time.time() * 1000)}_{id(note_text) % 0xFFFF:04x}"

            record = {
                "note_id": note_id,
                "note": note_text,
                "day": day,
                "message_id": message_id,
                "block_id": block_id,
                "block_ordinal": block_ordinal,
                "ts": int(time.time() * 1000),
            }

            sc.by_id[note_id] = record
            if key not in sc.by_block:
                sc.by_block[key] = []
            sc.by_block[key].append(note_id)

            self._save(sc)
            return record

    def detach(self, day: str, message_id: str, block_id: str, note_id: str) -> bool:
        """Remove a note from a block. Returns True if found and removed."""
        with self._lock:
            sc = self.load_day(day)
            key = _block_key(message_id, block_id)

            ids = sc.by_block.get(key, [])
            if note_id not in ids:
                return False
            ids.remove(note_id)
            if not ids:
                del sc.by_block[key]

            sc.by_id.pop(note_id, None)
            self._save(sc)
            return True

    # ── Queries ────────────────────────────────────────────────

    def get_block_notes(self, day: str, message_id: str, block_id: str) -> List[dict]:
        """Get all notes attached to a specific block (hot path)."""
        with self._lock:
            sc = self.load_day(day)
            key = _block_key(message_id, block_id)
            ids = sc.by_block.get(key, [])
            return [sc.by_id[nid] for nid in ids if nid in sc.by_id]

    def get_day_notes(self, day: str) -> Dict[str, List[dict]]:
        """Get all notes for a day, keyed by block."""
        with self._lock:
            sc = self.load_day(day)
            result = {}
            for key, ids in sc.by_block.items():
                result[key] = [sc.by_id[nid] for nid in ids if nid in sc.by_id]
            return result

    def get_note(self, note_id: str) -> Optional[dict]:
        """Resolve a single note by ID. Scans cached days then disk."""
        with self._lock:
            for day, sc in self._cache.items():
                rec = sc.by_id.get(note_id)
                if rec:
                    return rec

        # Disk scan (recent 30 sidecars)
        candidates = sorted(self._root.glob("*.notes.json"),
                          key=lambda p: p.stat().st_mtime, reverse=True)[:30]
        for p in candidates:
            try:
                with open(p, encoding="utf-8") as _f:
                    raw = json.load(_f)
                rec = raw.get("by_id", {}).get(note_id)
                if rec:
                    return rec
            except Exception:
                continue
        return None

    def list_days(self) -> List[str]:
        """List all days that have note sidecars."""
        days = []
        for p in sorted(self._root.glob("*.notes.json")):
            stem = p.stem.replace(".notes", "")
            if _DAY_RE.match(stem):
                days.append(stem)
        return days

    def distribution(self) -> dict:
        """Note count per day, for the Explorer day-distribution chart.

        Returns: { "days": [{"day": "2026-02-21", "count": 5}, ...], "total": 42 }
        Sorted newest first.
        """
        self.invalidate()
        days = list(reversed(self.list_days()))
        result = []
        total = 0
        for day in days:
            sc = self.load_day(day)
            count = len(sc.by_id)
            total += count
            result.append({"day": day, "count": count})
        return {"days": result, "total": total}

    def get_all_paginated(
        self,
        cursor: Optional[str] = None,
        limit: int = 5,
    ) -> dict:
        """Return notes paginated by day (newest first).

        Args:
            cursor: Day string to start AFTER (exclusive). None = start from newest.
            limit:  Max number of days to include per page.

        Returns:
            {"days": [...], "items": [{note}, ...],
             "next_cursor": "2026-02-13" or None, "total_days": 42}
        """
        self.invalidate()
        all_days = list(reversed(self.list_days()))
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

    def update_note(self, note_id: str, note_text: str) -> Optional[dict]:
        """Update a note's text. Returns updated record or None."""
        rec = self.get_note(note_id)
        if not rec:
            return None
        day = rec.get("day")
        if not day:
            return None

        with self._lock:
            sc = self.load_day(day)
            r = sc.by_id.get(note_id)
            if not r:
                return None
            r["note"] = note_text
            sc.by_id[note_id] = r
            self._save(sc)
            return r

    def hard_delete(self, note_id: str) -> bool:
        """Permanently remove a note from all indexes. Returns True if found."""
        rec = self.get_note(note_id)
        if not rec:
            return False
        day = rec.get("day")
        if not day:
            return False

        with self._lock:
            sc = self.load_day(day)
            if note_id not in sc.by_id:
                return False

            sc.by_id.pop(note_id, None)

            for key in list(sc.by_block.keys()):
                if note_id in sc.by_block[key]:
                    sc.by_block[key].remove(note_id)
                    if not sc.by_block[key]:
                        del sc.by_block[key]

            self._save(sc)
            return True

    def invalidate(self, day: Optional[str] = None) -> None:
        """Evict cached sidecar(s) so next load_day reads fresh from disk."""
        with self._lock:
            if day:
                self._cache.pop(day, None)
                if day in self._lru:
                    self._lru.remove(day)
            else:
                self._cache.clear()
                self._lru.clear()
