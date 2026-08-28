"""Genesis Citation Tool — BM25 indexer.

Builds and persists a BM25 index over all 68 corpus blocks.

Index files (data/derived/genesis/):
    corpus.index.json  — block metadata + spans (no bodies, lightweight)
    bm25.index.pkl     — serialized BM25Okapi model
    build_meta.json    — source_commit, source_hash, built_at

Rebuild is triggered when source_commit or source_hash differs from build_meta.json.
Same corpus always produces the same index (deterministic).
"""

from __future__ import annotations

import hashlib
import json
import logging
import pickle
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from rank_bm25 import BM25Okapi

from .config import (
    BM25_INDEX_PATH,
    BUILD_META_PATH,
    CORPUS_INDEX_PATH,
    CORPUS_PATH,
    INDEX_DIR,
)
from .parser import Block, parse_corpus

logger = logging.getLogger(__name__)


# ── Tokeniser (shared by indexer and search engine) ───────────────────────────

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lower-case word tokeniser.  Filters 1-char tokens."""
    return [t for t in _TOKEN_RE.findall(text.lower()) if len(t) > 1]


def _block_document(block: Block) -> str:
    """Concatenate all searchable text for a block."""
    return " ".join([block.tag, block.title, block.source, block.scope, block.body])


# ── Source hash / commit helpers ──────────────────────────────────────────────

def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"


def _corpus_git_commit(corpus_path: Path) -> str:
    """Return git commit hash of corpus file, or 'unknown' if not in a repo."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", str(corpus_path)],
            capture_output=True,
            text=True,
            cwd=str(corpus_path.parent),
            timeout=5,
        )
        commit = result.stdout.strip()
        return commit if commit else "unknown"
    except Exception:
        return "unknown"


# ── Load / save index ─────────────────────────────────────────────────────────

def _load_build_meta() -> Optional[dict]:
    if not BUILD_META_PATH.exists():
        return None
    try:
        return json.loads(BUILD_META_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def _is_stale(source_commit: str, source_hash: str) -> bool:
    """Return True if the stored index is stale (needs rebuild)."""
    meta = _load_build_meta()
    if meta is None:
        return True
    return (
        meta.get("source_commit") != source_commit
        or meta.get("source_hash") != source_hash
    )


def _write_index(blocks: list[Block], source_commit: str, source_hash: str) -> None:
    """Serialise blocks + BM25 model to INDEX_DIR."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    # corpus.index.json — metadata only (no bodies)
    corpus_index = [
        {
            "tag": b.tag,
            "title": b.title,
            "source": b.source,
            "scope": b.scope,
            "date_range": b.date_range,
            "write_perms": b.write_perms,
            "derived": b.derived,
            "derivation_basis": b.derivation_basis,
            "block_hash": b.block_hash,
            "span": b.span,
            "series": str(_tag_series(b.tag)),
        }
        for b in blocks
    ]
    CORPUS_INDEX_PATH.write_text(
        json.dumps(corpus_index, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # bm25.index.pkl
    docs = [tokenize(_block_document(b)) for b in blocks]
    bm25 = BM25Okapi(docs)
    with open(BM25_INDEX_PATH, "wb") as fh:
        pickle.dump(bm25, fh, protocol=pickle.HIGHEST_PROTOCOL)

    # build_meta.json
    build_meta = {
        "source_commit": source_commit,
        "source_hash": source_hash,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "block_count": len(blocks),
    }
    BUILD_META_PATH.write_text(
        json.dumps(build_meta, indent=2),
        encoding="utf-8",
    )

    logger.info(
        "Genesis index built: %d blocks, commit %s", len(blocks), source_commit
    )


def _tag_series(tag: str) -> int:
    """Return series number (1–12) for a G-XXXX tag."""
    from .config import SERIES_RANGES
    num = int(tag.split("-")[1])
    for series_str, (lo, hi) in SERIES_RANGES.items():
        if lo <= num <= hi:
            return int(series_str)
    return 0


# ── Public API ────────────────────────────────────────────────────────────────

class GenesisIndex:
    """Loaded, ready-to-query index.

    Attributes:
        corpus      — list of all Block objects (in tag order)
        bm25        — BM25Okapi model
        meta        — build_meta dict
        tag_map     — {tag: Block} for O(1) direct lookup
    """

    def __init__(
        self,
        corpus: list[Block],
        bm25: BM25Okapi,
        meta: dict,
    ) -> None:
        self.corpus = corpus
        self.bm25 = bm25
        self.meta = meta
        self.tag_map: dict[str, Block] = {b.tag: b for b in corpus}


def load_or_build_index(force_rebuild: bool = False) -> GenesisIndex:
    """Return a ready-to-use GenesisIndex, rebuilding if stale.

    Raises:
        FileNotFoundError: if TRAINING_CORPUS.md is missing
        ValueError: on corpus spec violations
        RuntimeError: on STALE_INDEX after rebuild attempt failure
    """
    source_commit = _corpus_git_commit(CORPUS_PATH)
    source_hash = _file_sha256(CORPUS_PATH)

    if force_rebuild or _is_stale(source_commit, source_hash):
        blocks = parse_corpus(CORPUS_PATH)
        _write_index(blocks, source_commit, source_hash)
    else:
        # Fast path: load from disk
        blocks = _load_blocks_from_disk()
        if blocks is None:
            # Fallback: re-parse if index files are corrupt
            blocks = parse_corpus(CORPUS_PATH)
            _write_index(blocks, source_commit, source_hash)

    # Load BM25 model
    with open(BM25_INDEX_PATH, "rb") as fh:
        bm25 = pickle.load(fh)  # noqa: S301 — local file, controlled path

    meta = _load_build_meta() or {}

    # Stale check after rebuild
    if meta.get("source_commit") != source_commit or meta.get("source_hash") != source_hash:
        raise RuntimeError("STALE_INDEX: index rebuild did not update meta correctly")

    return GenesisIndex(corpus=blocks, bm25=bm25, meta=meta)


def _load_blocks_from_disk() -> Optional[list[Block]]:
    """Reconstruct Block list from corpus.index.json + re-parsing for bodies."""
    if not CORPUS_INDEX_PATH.exists():
        return None
    try:
        # We still need bodies — parse the corpus (fast, ~5ms)
        return parse_corpus(CORPUS_PATH)
    except Exception:
        return None
