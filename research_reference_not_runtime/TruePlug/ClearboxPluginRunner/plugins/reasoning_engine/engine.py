"""
Reasoning Plugin - Non-LLM inference engine for 6-1-6 maps

Architecture:
- Reads existing map JSONs (read-only, no modifications to base)
- Builds derived indexes (IDF, edge scores, consensus weights)
- Provides deterministic query API (answer frames from count patterns)

Run: uvicorn plugins.reasoning_engine:app --port 5051 --reload
"""
import hashlib
import json
import logging
import math
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Ensure workspace root is on sys.path for security imports
_WORKSPACE_ROOT = str(Path(__file__).resolve().parents[2])
if _WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, _WORKSPACE_ROOT)

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Security integration
from security.data_paths import CHAT_MAPS_DIR, FOREST_DATA_ROOT
from security.secure_storage import secure_json_load

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache directory
REASONING_CACHE_DIR = FOREST_DATA_ROOT / "reasoning_cache"
REASONING_CACHE_DIR.mkdir(parents=True, exist_ok=True)

MANIFEST_DB = REASONING_CACHE_DIR / "manifest.db"
TERM_STATS_DB = REASONING_CACHE_DIR / "term_stats.db"
EDGE_SCORES_DB = REASONING_CACHE_DIR / "edge_scores.db"
ANSWER_CACHE_DB = REASONING_CACHE_DIR / "answer_cache.db"

VERSION_FILE = REASONING_CACHE_DIR / "VERSION.txt"
CURRENT_VERSION = "reasoning/1.0-mvp"

# ── Verb Lexicon (minimal, deterministic) ──────────────────────

# Common verbs for predicate gating
VERB_LEXICON = {
    "absorb", "achieve", "act", "add", "affect", "allow", "appear", "apply",
    "become", "begin", "build", "call", "capture", "carry", "cause", "change",
    "come", "compare", "contain", "continue", "contribute", "control", "convert",
    "create", "define", "depend", "develop", "differ", "do", "drive",
    "enable", "enhance", "ensure", "establish", "exceed", "exist", "expand",
    "facilitate", "find", "focus", "form", "function", "generate", "give",
    "grow", "happen", "have", "help", "hold", "impact", "implement", "improve",
    "include", "increase", "indicate", "influence", "involve", "lead", "limit",
    "maintain", "make", "manage", "measure", "mitigate", "modify", "monitor",
    "need", "occur", "offer", "operate", "perform", "play", "prevent", "produce",
    "promote", "protect", "provide", "reach", "reduce", "regulate", "relate",
    "release", "remain", "remove", "represent", "require", "result", "retain",
    "sequester", "serve", "show", "store", "suggest", "support", "sustain",
    "take", "use", "vary", "work"
}

VERB_SUFFIXES = ("ed", "ing", "ify", "ise", "ize", "ate", "en")
NOUN_SUFFIXES = ("tion", "ment", "ness", "ity", "ship", "ism", "ance", "ence")

def is_verb_like(token: str) -> bool:
    """Deterministic verb-likeness check"""
    token_lower = token.lower()

    # Check verb lexicon
    if token_lower in VERB_LEXICON:
        return True

    # Check verb suffixes
    if any(token_lower.endswith(suffix) for suffix in VERB_SUFFIXES):
        return True

    # Reject noun suffixes
    if any(token_lower.endswith(suffix) for suffix in NOUN_SUFFIXES):
        return False

    return False  # Unknown, conservative


# ── Data Models ────────────────────────────────────────────────

@dataclass
class AnswerFrame:
    """Structured answer (not text-first)"""
    subject: str
    predicates: List[Dict]
    confidence: float
    reasoning_trace: Dict
    surface_text: str


class QueryRequest(BaseModel):
    question: str
    mode: str = "what_does_x_do"  # or "definition"
    topk: int = 8


class QueryResponse(BaseModel):
    answer_frame: Dict
    surface_text: str
    reasoning_trace: Dict


# ── Reasoning Engine ───────────────────────────────────────────

class ReasoningEngine:
    """Core reasoning engine - builds indexes, runs queries"""

    def __init__(self):
        self.maps_dir = CHAT_MAPS_DIR
        self.cache_dir = REASONING_CACHE_DIR
        self._ensure_schema()
        self._check_version()

    def _get_db_connection(self, db_path):
        """Create SQLite connection with custom functions registered"""
        conn = sqlite3.connect(db_path)
        # Register natural log function
        conn.create_function("ln", 1, lambda x: math.log(x) if x > 0 else 0.0)
        return conn

    def _ensure_schema(self):
        """Initialize database schemas"""
        # Manifest DB
        with self._get_db_connection(MANIFEST_DB) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS maps_manifest (
                    map_id TEXT PRIMARY KEY,
                    path TEXT,
                    mtime INTEGER,
                    size INTEGER,
                    sha256 TEXT,
                    indexed_utc TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS meta (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

        # Term stats DB
        with self._get_db_connection(TERM_STATS_DB) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS term_stats (
                    term TEXT PRIMARY KEY,
                    df INTEGER,
                    total_occurrences INTEGER,
                    idf REAL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_term_df ON term_stats(df)")

        # Edge scores DB
        with self._get_db_connection(EDGE_SCORES_DB) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS edge_scores (
                    anchor TEXT,
                    offset INTEGER,
                    neighbor TEXT,
                    raw_count INTEGER,
                    df_edge INTEGER,
                    idf REAL,
                    consensus REAL,
                    final_rank REAL,
                    PRIMARY KEY (anchor, offset, neighbor)
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_anchor_offset_rank
                ON edge_scores(anchor, offset, final_rank DESC)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_anchor_rank
                ON edge_scores(anchor, final_rank DESC)
            """)

        # Answer cache DB
        with self._get_db_connection(ANSWER_CACHE_DB) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS answer_cache (
                    query_hash TEXT PRIMARY KEY,
                    question TEXT,
                    mode TEXT,
                    created_utc TEXT,
                    response_json TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_answer_created
                ON answer_cache(created_utc)
            """)

    def _check_version(self):
        """Check/write version file, rebuild if version changed"""
        if VERSION_FILE.exists():
            current = VERSION_FILE.read_text().strip()
            if current != CURRENT_VERSION:
                logger.warning(f"Version changed ({current} -> {CURRENT_VERSION}), rebuilding indexes")
                self._rebuild_all()
        else:
            logger.info(f"First run, initializing version {CURRENT_VERSION}")

        VERSION_FILE.write_text(CURRENT_VERSION)

    def _rebuild_all(self):
        """Wipe cache and rebuild from scratch"""
        logger.info("Wiping all cached indexes")

        # Clear tables but keep schema (avoids Windows file locking issues)
        with self._get_db_connection(TERM_STATS_DB) as conn:
            conn.execute("DELETE FROM term_stats")

        with self._get_db_connection(EDGE_SCORES_DB) as conn:
            conn.execute("DELETE FROM edge_scores")

        with self._get_db_connection(ANSWER_CACHE_DB) as conn:
            conn.execute("DELETE FROM answer_cache")

        with self._get_db_connection(MANIFEST_DB) as conn:
            conn.execute("DELETE FROM maps_manifest")
            conn.execute("DELETE FROM meta")

        self._ensure_schema()

    def scan_and_update_indexes(self):
        """Incremental index rebuild - only processes new/changed maps"""
        logger.info("Scanning for new/changed maps...")

        # Get existing manifest
        with self._get_db_connection(MANIFEST_DB) as conn:
            cursor = conn.execute("SELECT map_id, mtime, size FROM maps_manifest")
            existing = {row[0]: (row[1], row[2]) for row in cursor}

        # Scan current map files
        current = {}
        for map_file in self.maps_dir.glob("*.json"):
            map_id = map_file.stem
            stat = map_file.stat()
            mtime, size = int(stat.st_mtime), stat.st_size
            current[map_id] = (mtime, size, map_file)

        # Detect changes
        new = set(current.keys()) - set(existing.keys())
        deleted = set(existing.keys()) - set(current.keys())
        modified = {
            map_id for map_id in set(current.keys()) & set(existing.keys())
            if current[map_id][:2] != existing[map_id]
        }

        # If modified or deleted, do full rebuild (correctness > efficiency)
        if modified or deleted:
            logger.warning(f"Modified ({len(modified)}) or deleted ({len(deleted)}) maps detected")
            logger.info("Performing full rebuild for correctness...")
            self._full_rebuild()
            return

        # If only new maps, safe to append
        if new:
            logger.info(f"Found {len(new)} new maps, appending to index...")
            for map_id in new:
                mtime, size, map_file = current[map_id]
                logger.info(f"Processing {map_id}...")
                self._index_map(map_id, map_file, mtime, size)

            # Recompute global IDF
            self._recompute_idf()

            # Recompute edge final_rank
            self._recompute_edge_ranks()

            logger.info("Index append complete")
        else:
            logger.info("No changes detected")

    def _full_rebuild(self):
        """Full rebuild from all maps on disk"""
        logger.info("Wiping term_stats and edge_scores for full rebuild...")

        # Clear tables but keep schema
        with self._get_db_connection(TERM_STATS_DB) as conn:
            conn.execute("DELETE FROM term_stats")

        with self._get_db_connection(EDGE_SCORES_DB) as conn:
            conn.execute("DELETE FROM edge_scores")

        with self._get_db_connection(MANIFEST_DB) as conn:
            conn.execute("DELETE FROM maps_manifest")

        # Rebuild from all maps
        logger.info("Rebuilding from all maps...")
        for map_file in self.maps_dir.glob("*.json"):
            map_id = map_file.stem
            stat = map_file.stat()
            mtime, size = int(stat.st_mtime), stat.st_size
            logger.info(f"Processing {map_id}...")
            self._index_map(map_id, map_file, mtime, size)

        # Recompute global IDF
        self._recompute_idf()

        # Recompute edge final_rank
        self._recompute_edge_ranks()

        logger.info("Full rebuild complete")

    def _index_map(self, map_id: str, map_file: Path, mtime: int, size: int):
        """Index a single map file"""
        # Load map data
        map_data = secure_json_load(map_file)

        # Compute SHA256
        sha256 = hashlib.sha256(map_file.read_bytes()).hexdigest()

        # Extract terms and edges
        doc_terms: Set[str] = set()
        doc_edges: Set[Tuple[str, int, str]] = set()
        term_occurrences: Dict[str, int] = {}
        edge_counts: Dict[Tuple[str, int, str], int] = {}

        anchors = map_data.get('anchors', {})
        for anchor, anchor_data in anchors.items():
            doc_terms.add(anchor)

            # Process before/after bins
            for side, sign in [('before', -1), ('after', 1)]:
                bins = anchor_data.get(side, {})
                for pos_str, neighbors in bins.items():
                    offset = sign * int(pos_str)

                    for neighbor in neighbors:
                        token = neighbor['token']
                        count = neighbor['count']

                        doc_terms.add(token)
                        doc_edges.add((anchor, offset, token))

                        # Track occurrences
                        term_occurrences[token] = term_occurrences.get(token, 0) + count
                        edge_counts[(anchor, offset, token)] = edge_counts.get((anchor, offset, token), 0) + count

        # Update term stats
        with self._get_db_connection(TERM_STATS_DB) as conn:
            for term in doc_terms:
                conn.execute("""
                    INSERT INTO term_stats (term, df, total_occurrences, idf)
                    VALUES (?, 1, ?, 0.0)
                    ON CONFLICT(term) DO UPDATE SET
                        df = df + 1,
                        total_occurrences = total_occurrences + ?
                """, (term, term_occurrences.get(term, 0), term_occurrences.get(term, 0)))

        # Update edge scores
        with self._get_db_connection(EDGE_SCORES_DB) as conn:
            for (anchor, offset, neighbor), count in edge_counts.items():
                conn.execute("""
                    INSERT INTO edge_scores (anchor, offset, neighbor, raw_count, df_edge, idf, consensus, final_rank)
                    VALUES (?, ?, ?, ?, 1, 0.0, 0.0, 0.0)
                    ON CONFLICT(anchor, offset, neighbor) DO UPDATE SET
                        raw_count = raw_count + ?,
                        df_edge = df_edge + 1
                """, (anchor, offset, neighbor, count, count))

        # Update manifest
        with self._get_db_connection(MANIFEST_DB) as conn:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute("""
                INSERT OR REPLACE INTO maps_manifest (map_id, path, mtime, size, sha256, indexed_utc)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (map_id, str(map_file), mtime, size, sha256, now))

    def _recompute_idf(self):
        """Recompute IDF scores for all terms"""
        with self._get_db_connection(MANIFEST_DB) as conn:
            n_docs = conn.execute("SELECT COUNT(*) FROM maps_manifest").fetchone()[0]

        if n_docs == 0:
            return

        with self._get_db_connection(TERM_STATS_DB) as conn:
            conn.execute("""
                UPDATE term_stats
                SET idf = ln((? + 1.0) / (df + 1.0)) + 1.0
            """, (n_docs,))

        # Update meta
        with self._get_db_connection(MANIFEST_DB) as conn:
            conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('n_docs', ?)", (str(n_docs),))

    def _recompute_edge_ranks(self):
        """Recompute final_rank for all edges"""
        # Formula: tf * idf * log(1 + df_edge)

        # First, load all IDF values into memory
        idf_map = {}
        with self._get_db_connection(TERM_STATS_DB) as conn:
            cursor = conn.execute("SELECT term, idf FROM term_stats")
            for term, idf in cursor:
                idf_map[term] = idf

        # Now update edge_scores using the IDF map
        with self._get_db_connection(EDGE_SCORES_DB) as conn:
            # Get all edges that need updating
            cursor = conn.execute("SELECT anchor, offset, neighbor, raw_count, df_edge FROM edge_scores")
            edges = cursor.fetchall()

            # Compute and update each edge
            for anchor, offset, neighbor, raw_count, df_edge in edges:
                idf = idf_map.get(neighbor, 1.0)  # Default IDF if not found
                consensus = math.log(1.0 + df_edge)
                final_rank = raw_count * idf * consensus

                conn.execute("""
                    UPDATE edge_scores
                    SET idf = ?, consensus = ?, final_rank = ?
                    WHERE anchor = ? AND offset = ? AND neighbor = ?
                """, (idf, consensus, final_rank, anchor, offset, neighbor))

    def query_what_does_x_do(self, subject: str, topk: int = 8) -> AnswerFrame:
        """Query: What does X do? (deterministic, no LLM)"""

        # Normalize subject (try to find in lexicon)
        anchor = self._normalize_anchor(subject)

        if not anchor:
            raise HTTPException(status_code=404, detail=f"No anchor found for '{subject}'")

        # Try to find predicates in offset +1 and +2 (slot flexibility)
        candidates_1 = self._get_top_neighbors(anchor, offset=1, limit=topk)
        candidates_2 = self._get_top_neighbors(anchor, offset=2, limit=topk // 2)

        # Score candidates by verb-likeness and rank
        predicate_candidates = []

        for neighbor, rank, count, df_edge in candidates_1:
            if is_verb_like(neighbor):
                predicate_candidates.append({
                    'token': neighbor,
                    'slot': 1,
                    'rank': rank,
                    'count': count,
                    'df_edge': df_edge,
                    'verb_score': rank  # Verb-like from +1 gets full rank
                })

        for neighbor, rank, count, df_edge in candidates_2:
            if is_verb_like(neighbor):
                predicate_candidates.append({
                    'token': neighbor,
                    'slot': 2,
                    'rank': rank,
                    'count': count,
                    'df_edge': df_edge,
                    'verb_score': rank * 0.8  # Verb from +2 gets slight penalty
                })

        # Sort by verb_score
        predicate_candidates.sort(key=lambda x: x['verb_score'], reverse=True)

        # Get best rank for confidence normalization
        best_rank = predicate_candidates[0]['rank'] if predicate_candidates else 1.0

        # Build predicate frames
        predicates = []
        for pred in predicate_candidates[:topk]:
            pred_slot = pred['slot']
            obj_slot = pred_slot + 1  # Object is relative to predicate slot

            # Get objects from relative slot
            objects = self._get_top_neighbors(anchor, offset=obj_slot, limit=3)

            if objects:
                predicates.append({
                    'verb': pred['token'],
                    'object': objects[0][0],  # Top object
                    'confidence': self._compute_confidence(pred['rank'], pred['df_edge'], best_rank),
                    'evidence': {
                        'predicate_slot': pred_slot,
                        'object_slot': obj_slot,
                        'verb_rank': pred['rank'],
                        'verb_count': pred['count'],
                        'verb_df': pred['df_edge'],
                        'object_rank': objects[0][1],
                        'object_count': objects[0][2],
                        'best_rank': best_rank  # Include for debugging
                    }
                })

        # Compute overall confidence
        overall_confidence = sum(p['confidence'] for p in predicates) / len(predicates) if predicates else 0.0

        # Generate surface text (frame-driven, not fake grammar)
        if predicates:
            # Build proper frames
            frames = []
            for p in predicates[:3]:
                frames.append(f"{p['verb']} {p['object']}")
            surface_text = f"{anchor.capitalize()}: {', '.join(frames)}."
        else:
            surface_text = f"No verb-like predicates found for {anchor}."

        return AnswerFrame(
            subject=anchor,
            predicates=predicates,
            confidence=overall_confidence,
            reasoning_trace={
                'anchors_used': [anchor],
                'predicate_candidates_found': len(predicate_candidates),
                'frames_built': len(predicates),
                'query_mode': 'what_does_x_do'
            },
            surface_text=surface_text
        )

    def _normalize_anchor(self, term: str) -> Optional[str]:
        """Find best matching anchor (case-insensitive, punctuation-safe)"""
        # Strip punctuation and clean
        term_clean = re.sub(r"[^a-z0-9_\- ]+", "", term.lower()).strip()

        # Build singular variant (remove ONE trailing 's', not all)
        singular = term_clean[:-1] if term_clean.endswith("s") and len(term_clean) > 1 else term_clean

        with self._get_db_connection(EDGE_SCORES_DB) as conn:
            # Try exact match
            result = conn.execute(
                "SELECT DISTINCT anchor FROM edge_scores WHERE LOWER(anchor) = ? LIMIT 1",
                (term_clean,)
            ).fetchone()

            if result:
                return result[0].lower()  # Enforce lowercase

            # Try variants (plural and singular)
            variants = [term_clean + "s", singular]
            for variant in variants:
                if variant == term_clean:  # Skip if same as original
                    continue
                result = conn.execute(
                    "SELECT DISTINCT anchor FROM edge_scores WHERE LOWER(anchor) = ? LIMIT 1",
                    (variant,)
                ).fetchone()
                if result:
                    logger.info(f"Normalized '{term}' -> '{result[0]}' (variant match)")
                    return result[0].lower()

            # Not found - log suggestions
            cursor = conn.execute("""
                SELECT DISTINCT anchor FROM edge_scores
                WHERE LOWER(anchor) LIKE ?
                LIMIT 5
            """, (term_clean[:3] + "%",))  # Prefix match
            suggestions = [row[0] for row in cursor.fetchall()]
            if suggestions:
                logger.warning(f"Anchor '{term}' not found. Suggestions: {suggestions}")

        return None

    def _get_top_neighbors(self, anchor: str, offset: int, limit: int = 10) -> List[Tuple[str, float, int, int]]:
        """Get top neighbors for anchor at given offset (deterministic sorting)"""
        with self._get_db_connection(EDGE_SCORES_DB) as conn:
            cursor = conn.execute("""
                SELECT neighbor, final_rank, raw_count, df_edge
                FROM edge_scores
                WHERE anchor = ? AND offset = ?
                ORDER BY final_rank DESC, raw_count DESC, df_edge DESC, neighbor ASC
                LIMIT ?
            """, (anchor, offset, limit))

            return cursor.fetchall()

    def _compute_confidence(self, rank: float, df_edge: int, best_rank: float) -> float:
        """Compute confidence score (0-1) from rank and consensus (relative to best)"""
        # Normalize rank relative to best in this query
        base = rank / best_rank if best_rank > 0 else 0.0

        # Consensus modifier (sharp penalty for df_edge=1)
        if df_edge <= 1:
            cons = 0.3  # Weak: seen in only one map
        elif df_edge == 2:
            cons = 0.6  # Moderate: seen in two maps
        else:
            cons = 1.0  # Strong: seen in 3+ maps

        # Final confidence
        confidence = base * (0.6 + 0.4 * cons)

        return min(confidence, 1.0)


# ── FastAPI App ────────────────────────────────────────────────

app = FastAPI(
    title="Forest AI Reasoning Engine",
    description="Non-LLM inference engine for 6-1-6 maps",
    version="1.0-mvp"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:8080", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global engine instance
engine = ReasoningEngine()

# ── Endpoints ──────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Scan and update indexes on startup"""
    logger.info("Reasoning Engine starting up...")
    try:
        engine.scan_and_update_indexes()
        logger.info("Reasoning Engine ready")
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok", "service": "reasoning_engine", "version": CURRENT_VERSION}


@app.post("/reasoning/rebuild")
async def rebuild_indexes():
    """Force rebuild of all indexes"""
    try:
        engine._rebuild_all()
        engine.scan_and_update_indexes()
        return {"status": "rebuilt", "message": "Indexes rebuilt successfully"}
    except Exception as e:
        logger.exception("Rebuild failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/reasoning/query", response_model=QueryResponse)
async def query(req: QueryRequest):
    """Query the reasoning engine"""
    try:
        # Parse question to extract subject
        # Simple extraction: assume question is "What does X do?" or "What is X?"
        subject = None
        question_lower = req.question.lower()

        if "what does" in question_lower or "what do" in question_lower:
            # Extract subject between "does/do" and "do"
            parts = question_lower.split()
            if "does" in parts:
                idx = parts.index("does")
                if idx + 1 < len(parts):
                    subject = parts[idx + 1]
            elif "do" in parts:
                idx = parts.index("do")
                if idx + 1 < len(parts):
                    subject = parts[idx + 1]
        elif "what is" in question_lower or "what are" in question_lower:
            parts = question_lower.split()
            if "is" in parts:
                idx = parts.index("is")
                if idx + 1 < len(parts):
                    subject = parts[idx + 1]
            elif "are" in parts:
                idx = parts.index("are")
                if idx + 1 < len(parts):
                    subject = parts[idx + 1]

        if not subject:
            # Fallback: extract last noun-like word
            words = req.question.lower().replace("?", "").split()
            if words:
                subject = words[-1]

        # Run query
        if req.mode == "what_does_x_do":
            answer_frame = engine.query_what_does_x_do(subject, topk=req.topk)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported mode: {req.mode}")

        return QueryResponse(
            answer_frame=answer_frame.__dict__,
            surface_text=answer_frame.surface_text,
            reasoning_trace=answer_frame.reasoning_trace
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Query failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/reasoning/stats")
async def get_stats():
    """Get reasoning engine statistics"""
    try:
        with engine._get_db_connection(MANIFEST_DB) as conn:
            n_docs = conn.execute("SELECT COUNT(*) FROM maps_manifest").fetchone()[0]

        with engine._get_db_connection(TERM_STATS_DB) as conn:
            n_terms = conn.execute("SELECT COUNT(*) FROM term_stats").fetchone()[0]

        with engine._get_db_connection(EDGE_SCORES_DB) as conn:
            n_edges = conn.execute("SELECT COUNT(*) FROM edge_scores").fetchone()[0]

        return {
            "indexed_maps": n_docs,
            "unique_terms": n_terms,
            "total_edges": n_edges,
            "version": CURRENT_VERSION,
            "cache_dir": str(REASONING_CACHE_DIR)
        }
    except Exception as e:
        logger.exception("Stats query failed")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5051)
