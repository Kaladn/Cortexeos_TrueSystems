"""Deterministic hashing for training event reproducibility.

All hashes use SHA-256 hex. JSON normalization: sorted keys, UTF-8, no whitespace.
These hashes make it impossible to "quietly change retrieval" without a fingerprint.

Frozen invariants (Plugin #3 depends on these):
  - evidence_set_hash: sha256 of JSON array of {chunk_id, coord, score, source_hash}
    sorted by (rank asc, chunk_id asc)
  - answer_hash: sha256 of UTF-8 answer_text exactly as returned
  - index_hash: sha256 of index metadata JSON (chunk_id list + source hashes + version)
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List


def _sha256(data: str) -> str:
    """SHA-256 hex of a UTF-8 string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _normalize_json(obj: Any) -> str:
    """Deterministic JSON: sorted keys, no whitespace, UTF-8."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


# ── Evidence Set Hash ────────────────────────────────────────

def evidence_set_hash(candidates: List[Dict[str, Any]]) -> str:
    """Hash the retrieval candidate set for reproducibility.

    Input: list of dicts, each with at least:
      - chunk_id (str)
      - coord (str)
      - score (float)
      - source_hash (str)

    Candidates are sorted by (rank asc, chunk_id asc) before hashing.
    Missing fields default to empty string / 0.

    Returns: "sha256:<hex>"
    """
    # Build position lookup O(n) instead of O(n^2) index scan
    pos_by_id: Dict[str, int] = {}
    normalized = []
    for i, c in enumerate(candidates):
        cid = c.get("chunk_id", "")
        pos_by_id.setdefault(cid, i)  # first occurrence wins
        normalized.append({
            "chunk_id": cid,
            "coord": c.get("coord", ""),
            "score": c.get("score", 0),
            "source_hash": c.get("source_hash", ""),
        })

    # Sort by rank (position), then chunk_id for determinism
    normalized.sort(key=lambda x: (pos_by_id.get(x["chunk_id"], 0), x["chunk_id"]))

    payload = _normalize_json(normalized)
    return f"sha256:{_sha256(payload)}"


def evidence_set_hash_from_scored(
    scored_chunks: List[Any],
) -> str:
    """Hash evidence set from ScoredChunk objects.

    Convenience wrapper that extracts the required fields.
    """
    candidates = []
    for sc in scored_chunks:
        candidates.append({
            "chunk_id": getattr(sc, "chunk_id", ""),
            "coord": f"INGEST:{getattr(sc, 'receipt_id', '')}#{getattr(sc, 'chunk_id', '')}",
            "score": getattr(sc, "score", 0),
            "source_hash": "",  # Filled at query time if available
        })
    return evidence_set_hash(candidates)


# ── Answer Hash ──────────────────────────────────────────────

def answer_hash(answer_text: str) -> str:
    """Hash the answer text exactly as returned (before UI stripping).

    Returns: "sha256:<hex>"
    """
    return f"sha256:{_sha256(answer_text)}"


# ── Index Hash ───────────────────────────────────────────────

def index_hash(
    chunk_ids: List[str],
    source_hashes: List[str] = None,
    version: str = "bm25@1",
) -> str:
    """Hash the index metadata for reproducibility.

    Hashes the sorted list of chunk_ids + source_hashes + version.
    This fingerprints the exact state of the index used for retrieval.

    Returns: "sha256:<hex>"
    """
    payload = {
        "version": version,
        "chunk_ids": sorted(chunk_ids),
        "source_hashes": sorted(source_hashes) if source_hashes else [],
    }
    return f"sha256:{_sha256(_normalize_json(payload))}"


def compute_index_hash_from_bm25(bm25_index: Any) -> str:
    """Compute index hash from a BM25Index instance.

    Reads chunk_ids and receipt_map from the loaded index.
    """
    chunk_ids = getattr(bm25_index, "_chunk_ids", [])
    receipt_map = getattr(bm25_index, "_receipt_map", {})
    source_hashes = list(set(receipt_map.values()))
    return index_hash(chunk_ids, source_hashes, version="bm25@1")


# ── Lake Snapshot ID ─────────────────────────────────────────

def lake_snapshot_id(index_hash_str: str) -> str:
    """Generate a snapshot ID from the index hash.

    Format: snapshot_{hash_prefix}
    If no index exists, returns "snapshot_none".
    """
    if not index_hash_str or index_hash_str == "sha256:":
        return "snapshot_none"

    # Extract hex from "sha256:xxxx..."
    hex_part = index_hash_str.split(":", 1)[-1] if ":" in index_hash_str else index_hash_str
    return f"snapshot_{hex_part[:16]}"
