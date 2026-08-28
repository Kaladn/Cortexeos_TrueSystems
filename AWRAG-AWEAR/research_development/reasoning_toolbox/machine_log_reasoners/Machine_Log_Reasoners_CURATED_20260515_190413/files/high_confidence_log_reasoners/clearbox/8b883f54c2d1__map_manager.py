"""Citation-Map Manager: Persistent storage for 6-1-6 document mappings.

Architecture:
- Citations: Documents uploaded and fingerprinted (cite_id = hash)
- Maps: 6-1-6 analysis results linked to citations
- Anchor Index: Inverted index for fast keyword search

Storage:
- citations.db (SQLite): metadata + indexes
- citations/*.json: full citation records
- maps/*.json: full map data

Phase 1 Intake: All citation creation funnels through citation_intake.py
"""
from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

# Security integration
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from security.data_paths import CHAT_CITATIONS_DIR, CHAT_MAPS_DIR, CITATION_DB_PATH

# ── Phase 1 citation intake gate ───────────────────────────────
from Conversations.citations.citation_intake import (
    create_citation_record,
    backfill_phase1_fields,
)

# Contract D: shared mapped predicate — must not be duplicated here
from bridges.governed_io import _is_lexicon_matched

logger = logging.getLogger(__name__)


def _infer_corpus_id_from_filename(filename: str) -> str:
    name = (filename or "").lower()
    if name.startswith("chat_") and name.endswith(".jsonl"):
        return "chats"
    return "general"


# ── Database Schema ────────────────────────────────────────────

DB_PATH = CITATION_DB_PATH

SCHEMA_SQL = """
-- Citations table
CREATE TABLE IF NOT EXISTS citations (
    cite_id TEXT PRIMARY KEY,
    canonical TEXT UNIQUE NOT NULL,
    source_hash TEXT NOT NULL,
    uploaded_at TEXT NOT NULL,
    filename TEXT NOT NULL,
    filesize INTEGER,
    content_preview TEXT,
    metadata_json TEXT,
    source_type TEXT DEFAULT 'user',
    source_metadata TEXT
);

-- Maps table
CREATE TABLE IF NOT EXISTS maps (
    map_id TEXT PRIMARY KEY,
    cite_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    window_size INTEGER DEFAULT 6,
    total_tokens INTEGER,
    unique_anchors INTEGER,
    lexicon_coverage REAL,
    stats_json TEXT,
    FOREIGN KEY (cite_id) REFERENCES citations(cite_id) ON DELETE CASCADE
);

-- Anchor index (inverted)
CREATE TABLE IF NOT EXISTS anchor_index (
    anchor TEXT NOT NULL,
    cite_id TEXT NOT NULL,
    map_id TEXT NOT NULL,
    count INTEGER NOT NULL,
    PRIMARY KEY (anchor, map_id)
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_anchor ON anchor_index(anchor);
CREATE INDEX IF NOT EXISTS idx_cite_maps ON maps(cite_id);
CREATE INDEX IF NOT EXISTS idx_maps_created ON maps(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_citations_uploaded ON citations(uploaded_at DESC);

-- Enforce one active map per (citation, window_size)
-- Note: This prevents duplicate maps but allows remapping by dropping old map first
CREATE UNIQUE INDEX IF NOT EXISTS uq_maps_cite_window ON maps(cite_id, window_size);
"""

# ── Phase 1 Schema Migration ───────────────────────────────────
# Additive-only: add Phase 1 fields without breaking existing columns
PHASE1_MIGRATION_SQL = [
    "ALTER TABLE citations ADD COLUMN coord TEXT",
    "ALTER TABLE citations ADD COLUMN created_at_utc TEXT",
    "ALTER TABLE citations ADD COLUMN unresolved INTEGER DEFAULT 1",
    "ALTER TABLE citations ADD COLUMN source TEXT",
    "ALTER TABLE citations ADD COLUMN subject TEXT",
    "ALTER TABLE citations ADD COLUMN note TEXT",
]


# ── Data Classes ───────────────────────────────────────────────

@dataclass
class Citation:
    cite_id: str
    canonical: str
    source_hash: str
    uploaded_at: str
    filename: str
    filesize: int
    content_preview: str
    metadata: dict


@dataclass
class MapRecord:
    map_id: str
    cite_id: str
    created_at: str
    window_size: int
    total_tokens: int
    unique_anchors: int
    lexicon_coverage: float
    stats: dict


# ── Manager Class ──────────────────────────────────────────────

class MapManager:
    """Manages citations and maps with SQLite persistence."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Ensure storage directories exist
        CHAT_CITATIONS_DIR.mkdir(parents=True, exist_ok=True)
        CHAT_MAPS_DIR.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()
        self._init_db()

    def _init_db(self):
        """Initialize database schema + run Phase 1 migration."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

            # Phase 1 migration: add new columns (ignore if already exist)
            for migration_sql in PHASE1_MIGRATION_SQL:
                try:
                    conn.execute(migration_sql)
                except sqlite3.OperationalError as e:
                    # Ignore "duplicate column" errors (already migrated)
                    if "duplicate column" not in str(e).lower():
                        raise
            conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection with row factory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ── Citation Operations ────────────────────────────────────

    def create_citation(
        self,
        content: str,
        filename: str,
        metadata: Optional[dict] = None,
        source_type: str = "user",
        source_metadata: Optional[dict] = None,
        subject: Optional[str] = None,
        note: Optional[str] = None,
    ) -> Citation:
        """Create citation for a document (idempotent by content hash).

        Phase 1: All citations funnel through citation_intake gate.

        Args:
            content: Document text content
            filename: Original filename
            metadata: Optional metadata dict
            source_type: Source of citation ('user', 'test', 'stream_*')
            source_metadata: Optional source-specific metadata
            subject: Optional Phase 1 subject tag
            note: Optional Phase 1 note

        Returns:
            Citation record (new or existing)
        """
        # Generate deterministic cite_id from content
        content_bytes = content.encode('utf-8')
        content_hash = hashlib.sha256(content_bytes).hexdigest()
        cite_id = f"cite_{content_hash[:16]}"

        with self._lock:
            # Check if citation already exists (deduplication)
            existing = self.get_citation(cite_id)
            if existing:
                return existing

            # Create canonical coord (library format)
            today = datetime.now(timezone.utc).date().isoformat()
            coord = f"{today}:DOC:{filename}"

            # Create citation through shared intake gate (validates coord)
            # Map source_type to intake source
            intake_source = "system" if source_type in ["test", "system"] else "import"
            phase1_record = create_citation_record(
                coord=coord,
                source=intake_source,
                subject=subject,
                note=note,
                cite_id=cite_id,  # Provide deterministic cite_id
            )

            # Legacy fields (keep for backward compat)
            now = phase1_record["created_at_utc"]
            canonical = phase1_record["coord"]

            citation = Citation(
                cite_id=cite_id,
                canonical=canonical,
                source_hash=content_hash,
                uploaded_at=now,
                filename=filename,
                filesize=len(content_bytes),
                content_preview=content[:500],
                metadata=metadata or {}
            )

            # Store to database (include Phase 1 fields)
            with self._get_conn() as conn:
                conn.execute(
                    """INSERT INTO citations
                       (cite_id, canonical, source_hash, uploaded_at, filename,
                        filesize, content_preview, metadata_json, source_type, source_metadata,
                        coord, created_at_utc, unresolved, source, subject, note)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        citation.cite_id,
                        citation.canonical,
                        citation.source_hash,
                        citation.uploaded_at,
                        citation.filename,
                        citation.filesize,
                        citation.content_preview,
                        json.dumps(citation.metadata),
                        source_type,
                        json.dumps(source_metadata) if source_metadata else None,
                        # Phase 1 fields
                        phase1_record["coord"],
                        phase1_record["created_at_utc"],
                        1 if phase1_record["unresolved"] else 0,  # SQLite boolean
                        phase1_record["source"],
                        phase1_record.get("subject"),
                        phase1_record.get("note"),
                    )
                )
                conn.commit()

            # Store full content to file (include Phase 1 fields)
            cite_file = CHAT_CITATIONS_DIR / f"{cite_id}.json"
            cite_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cite_file, "w", encoding="utf-8") as _f:
                json.dump({
                    "cite_id": cite_id,
                    "canonical": canonical,
                    "coord": phase1_record["coord"],
                    "filename": filename,
                    "uploaded_at": now,
                    "created_at_utc": phase1_record["created_at_utc"],
                    "unresolved": phase1_record["unresolved"],
                    "source": phase1_record["source"],
                    "subject": phase1_record.get("subject"),
                    "note": phase1_record.get("note"),
                    "content": content,
                    "metadata": citation.metadata
                }, _f, indent=2, ensure_ascii=False)

            return citation

    def get_citation(self, cite_id: str) -> Optional[Citation]:
        """Get citation by ID."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM citations WHERE cite_id = ?",
                (cite_id,)
            ).fetchone()

            if not row:
                return None

            return Citation(
                cite_id=row['cite_id'],
                canonical=row['canonical'],
                source_hash=row['source_hash'],
                uploaded_at=row['uploaded_at'],
                filename=row['filename'],
                filesize=row['filesize'],
                content_preview=row['content_preview'],
                metadata=json.loads(row['metadata_json']) if row['metadata_json'] else {}
            )

    def list_citations(self, limit: int = 100) -> List[Citation]:
        """List recent citations."""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM citations ORDER BY uploaded_at DESC LIMIT ?",
                (limit,)
            ).fetchall()

            return [
                Citation(
                    cite_id=row['cite_id'],
                    canonical=row['canonical'],
                    source_hash=row['source_hash'],
                    uploaded_at=row['uploaded_at'],
                    filename=row['filename'],
                    filesize=row['filesize'],
                    content_preview=row['content_preview'],
                    metadata=json.loads(row['metadata_json']) if row['metadata_json'] else {}
                )
                for row in rows
            ]

    def get_citation_content(self, cite_id: str) -> Optional[str]:
        """Load full citation content from file."""
        cite_file = CHAT_CITATIONS_DIR / f"{cite_id}.json"
        if not cite_file.exists():
            return None

        try:
            with open(cite_file, encoding="utf-8") as _f:
                data = json.load(_f)
            return data.get("content")
        except Exception:
            return None

    # ── Map Operations ─────────────────────────────────────────

    def get_existing_map(self, cite_id: str, window_size: int = 6) -> Optional[MapRecord]:
        """Check if map already exists for citation + window size.

        Args:
            cite_id: Citation ID
            window_size: Window size

        Returns:
            Existing MapRecord or None
        """
        with self._get_conn() as conn:
            row = conn.execute(
                """SELECT * FROM maps
                   WHERE cite_id = ? AND window_size = ?
                   ORDER BY created_at DESC
                   LIMIT 1""",
                (cite_id, window_size)
            ).fetchone()

            if not row:
                return None

            return MapRecord(
                map_id=row['map_id'],
                cite_id=row['cite_id'],
                created_at=row['created_at'],
                window_size=row['window_size'],
                total_tokens=row['total_tokens'],
                unique_anchors=row['unique_anchors'],
                lexicon_coverage=row['lexicon_coverage'],
                stats=json.loads(row['stats_json']) if row['stats_json'] else {}
            )

    def create_map(
        self,
        cite_id: str,
        map_data: dict,
        window_size: int = 6,
        force: bool = False
    ) -> MapRecord:
        """Create map linked to citation (DB-enforced idempotent).

        Args:
            cite_id: Citation ID to link to
            map_data: 6-1-6 mapping result (anchors + stats)
            window_size: Window size used for mapping
            force: If True, delete old map and create new one

        Returns:
            MapRecord (existing or newly created)

        Note:
            UNIQUE INDEX on (cite_id, window_size) prevents duplicates.
            If force=False and map exists, returns existing map.
            If force=True, deletes old map first.
        """
        # Check if map already exists
        existing = self.get_existing_map(cite_id, window_size)

        if existing and not force:
            # Return existing map (idempotent)
            return existing

        if existing and force:
            # Delete old map + anchor index entries
            with self._get_conn() as conn:
                conn.execute("DELETE FROM anchor_index WHERE map_id = ?", (existing.map_id,))
                conn.execute("DELETE FROM maps WHERE map_id = ?", (existing.map_id,))
                conn.commit()

            # Delete old map file
            old_map_file = CHAT_MAPS_DIR / f"{existing.map_id}.json"
            if old_map_file.exists():
                old_map_file.unlink()

        # Verify citation exists
        citation = self.get_citation(cite_id)
        if not citation:
            raise ValueError(f"Citation not found: {cite_id}")

        if existing and force:
            try:
                from core.structural_memory.ledger import append_lifecycle_event

                append_lifecycle_event(
                    source_system="documap",
                    corpus_id=_infer_corpus_id_from_filename(citation.filename),
                    entity_kind="map",
                    entity_id=existing.map_id,
                    state="superseded",
                    metadata={"cite_id": cite_id, "replaced_by_force": True},
                )
            except Exception as exc:
                logger.warning("Structural memory supersede event failed for %s: %s", existing.map_id, exc)

        with self._lock:
            map_id = f"map_{uuid.uuid4().hex[:16]}"
            now = datetime.now(timezone.utc).isoformat()

            # Compute stats
            anchors = map_data.get("items", {})
            unique_anchors = len(anchors)

            # Contract B/D: use shared predicate — must match governed_io.py
            mapped_count = sum(
                1 for item in anchors.values()
                if isinstance(item, dict) and _is_lexicon_matched(item)
            )
            lexicon_coverage = (
                mapped_count / unique_anchors if unique_anchors > 0 else 0.0
            )

            stats = {
                "unique_anchors":   unique_anchors,
                "mapped_count":     map_data.get("mapped_count",   mapped_count),
                "unmapped_count":   map_data.get("unmapped_count", unique_anchors - mapped_count),
                "lexicon_coverage": lexicon_coverage,
                "total_tokens":     map_data.get("total_tokens", 0),
                "filename":         citation.filename,
            }

            map_record = MapRecord(
                map_id=map_id,
                cite_id=cite_id,
                created_at=now,
                window_size=window_size,
                total_tokens=stats["total_tokens"],
                unique_anchors=unique_anchors,
                lexicon_coverage=lexicon_coverage,
                stats=stats
            )

            # Store to database
            with self._get_conn() as conn:
                conn.execute(
                    """INSERT INTO maps
                       (map_id, cite_id, created_at, window_size, total_tokens,
                        unique_anchors, lexicon_coverage, stats_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        map_record.map_id,
                        map_record.cite_id,
                        map_record.created_at,
                        map_record.window_size,
                        map_record.total_tokens,
                        map_record.unique_anchors,
                        map_record.lexicon_coverage,
                        json.dumps(map_record.stats)
                    )
                )
                conn.commit()

            # Store full map data to file
            map_file = CHAT_MAPS_DIR / f"{map_id}.json"
            map_file.parent.mkdir(parents=True, exist_ok=True)
            with open(map_file, "w", encoding="utf-8") as _f:
                json.dump({
                    "map_id": map_id,
                    "cite_id": cite_id,
                    "canonical": citation.canonical,
                    "created_at": now,
                    "window_size": window_size,
                    "anchors": map_data.get("items", {}),
                    "stats": stats
                }, _f, indent=2, ensure_ascii=False)

            # Build anchor index
            self._index_anchors(map_id, cite_id, anchors)

            try:
                from core.structural_memory.ledger import record_map_snapshot

                record_map_snapshot(
                    corpus_id=_infer_corpus_id_from_filename(citation.filename),
                    map_id=map_id,
                    cite_id=cite_id,
                    canonical=citation.canonical,
                    filename=citation.filename,
                    anchors=anchors,
                    observed_at_utc=now,
                )
            except Exception as exc:
                logger.warning("Structural memory map append failed for %s: %s", map_id, exc)

            return map_record

    def _index_anchors(self, map_id: str, cite_id: str, anchors: dict):
        """Build inverted anchor index for fast search."""
        with self._get_conn() as conn:
            for anchor_word, anchor_data in anchors.items():
                # Count total window mentions
                total_count = 0
                for side in ['before', 'after']:
                    for bucket in anchor_data.get(side, {}).values():
                        for item in bucket:
                            total_count += item.get('count', 0)

                if total_count > 0:
                    conn.execute(
                        """INSERT OR REPLACE INTO anchor_index
                           (anchor, cite_id, map_id, count)
                           VALUES (?, ?, ?, ?)""",
                        (anchor_word.lower(), cite_id, map_id, total_count)
                    )
            conn.commit()

    def get_map(self, map_id: str) -> Optional[MapRecord]:
        """Get map record by ID."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM maps WHERE map_id = ?",
                (map_id,)
            ).fetchone()

            if not row:
                return None

            return MapRecord(
                map_id=row['map_id'],
                cite_id=row['cite_id'],
                created_at=row['created_at'],
                window_size=row['window_size'],
                total_tokens=row['total_tokens'],
                unique_anchors=row['unique_anchors'],
                lexicon_coverage=row['lexicon_coverage'],
                stats=json.loads(row['stats_json']) if row['stats_json'] else {}
            )

    def list_maps(self, cite_id: Optional[str] = None, limit: int = 100) -> List[MapRecord]:
        """List maps (optionally filtered by cite_id)."""
        with self._get_conn() as conn:
            if cite_id:
                rows = conn.execute(
                    "SELECT * FROM maps WHERE cite_id = ? ORDER BY created_at DESC LIMIT ?",
                    (cite_id, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM maps ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()

            return [
                MapRecord(
                    map_id=row['map_id'],
                    cite_id=row['cite_id'],
                    created_at=row['created_at'],
                    window_size=row['window_size'],
                    total_tokens=row['total_tokens'],
                    unique_anchors=row['unique_anchors'],
                    lexicon_coverage=row['lexicon_coverage'],
                    stats=json.loads(row['stats_json']) if row['stats_json'] else {}
                )
                for row in rows
            ]

    def get_map_data(self, map_id: str) -> Optional[dict]:
        """Load full map data from file."""
        map_file = CHAT_MAPS_DIR / f"{map_id}.json"
        if not map_file.exists():
            return None

        try:
            with open(map_file, encoding="utf-8") as _f:
                return json.load(_f)
        except Exception:
            return None

    # ── Query Operations ───────────────────────────────────────

    def query_maps(self, keywords: List[str], limit: int = 10) -> List[dict]:
        """Query citations by keywords, returning best map per citation.

        Args:
            keywords: List of search terms
            limit: Max results to return

        Returns:
            List of citation matches with their best map and scores
        """
        if not keywords:
            return []

        # Normalize keywords
        normalized = [kw.lower().strip() for kw in keywords if kw.strip()]
        if not normalized:
            return []

        with self._get_conn() as conn:
            # Build placeholders for IN clause
            placeholders = ','.join('?' * len(normalized))

            # Query: Aggregate directly by cite_id (unique citations only)
            query = f"""
                SELECT
                    ai.cite_id,
                    MAX(ai.map_id) AS map_id,
                    SUM(ai.count) AS total_mentions,
                    COUNT(DISTINCT ai.anchor) AS matched_count,
                    GROUP_CONCAT(DISTINCT ai.anchor) AS matched_anchors,
                    c.filename,
                    c.canonical,
                    c.uploaded_at
                FROM anchor_index ai
                JOIN citations c ON c.cite_id = ai.cite_id
                WHERE ai.anchor IN ({placeholders})
                GROUP BY ai.cite_id
                ORDER BY total_mentions DESC, matched_count DESC
                LIMIT ?
            """

            # Execute with keywords + limit
            rows = conn.execute(query, normalized + [limit]).fetchall()

            # Build results
            result = []
            for row in rows:
                matched_anchors = row['matched_anchors'].split(',') if row['matched_anchors'] else []
                keyword_coverage = row['matched_count'] / len(normalized)

                # Score: keyword coverage (weighted heavily) + total mentions
                score = keyword_coverage * 100 + row['total_mentions']

                result.append({
                    'cite_id': row['cite_id'],
                    'map_id': row['map_id'],
                    'canonical': row['canonical'],
                    'filename': row['filename'],
                    'score': score,
                    'matched_anchors': matched_anchors[:5],  # Top 5 for display
                    'total_mentions': row['total_mentions'],
                    'keyword_coverage': keyword_coverage
                })

            return result

    def get_library_summary(self) -> dict:
        """Get overview stats for the entire library with full details."""
        with self._get_conn() as conn:
            cite_count = conn.execute("SELECT COUNT(*) FROM citations").fetchone()[0]
            map_count = conn.execute("SELECT COUNT(*) FROM maps").fetchone()[0]
            anchor_count = conn.execute("SELECT COUNT(DISTINCT anchor) FROM anchor_index").fetchone()[0]

            # Get full citation list
            citations = []
            for row in conn.execute("""
                SELECT cite_id, canonical, filename, filesize, uploaded_at, content_preview
                FROM citations ORDER BY uploaded_at DESC
            """):
                citations.append({
                    "cite_id": row[0],
                    "canonical": row[1],
                    "filename": row[2],
                    "filesize": row[3],
                    "uploaded_at": row[4],
                    "content_preview": row[5],
                    "source_type": "test"  # Default for now, will be from DB after migration
                })

            # Get full map list
            maps = []
            for row in conn.execute("""
                SELECT map_id, cite_id, created_at, window_size
                FROM maps ORDER BY created_at DESC
            """):
                maps.append({
                    "map_id": row[0],
                    "cite_id": row[1],
                    "created_at": row[2],
                    "window_size": row[3]
                })

            return {
                "total_citations": cite_count,
                "total_maps": map_count,
                "unique_anchors": anchor_count,
                "citations": citations,
                "maps": maps
            }


# ── Global Instance ────────────────────────────────────────────

map_manager = MapManager()
