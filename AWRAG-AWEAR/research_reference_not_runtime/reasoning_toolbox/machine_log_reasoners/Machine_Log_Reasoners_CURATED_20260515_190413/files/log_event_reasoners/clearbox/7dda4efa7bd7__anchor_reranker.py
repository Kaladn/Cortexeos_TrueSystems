"""6-1-6 Anchor-Aware Reranker — bounded, deterministic.

Boosts retrieval candidates that share anchor tokens with the query.
All scores normalized to [0, 1]. Deterministic tie-break: (score DESC, chunk_id ASC).

Formula:
    final_score = (1 - α) * hybrid_score_norm + α * anchor_relevance_norm

    Where:
      α = anchor_weight (default 0.3)
      hybrid_score_norm = hybrid_score / max(hybrid_scores)          [0, 1]
      anchor_relevance_norm = clamp(raw_relevance, 0.0, 1.0)        [0, 1]

      raw_relevance = sum(token_boost(t) for t in overlap) / max(1, len(query_anchors))

      token_boost(t) = (1.0 + 0.2 * has_symbol) * (1.0 + clamp(log(freq+1)/10, 0, 1))
                       # max possible per token = 1.2 * 2.0 = 2.4

      query_anchors = {t for t in normalized_query_tokens
                       if t in bridge.word_index}

      overlap = chunk_anchor_tokens ∩ query_anchors
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Set

from ..schemas import ScoredChunk, ChunkAnchors
from ..text.normalize import extract_anchors as _extract_anchors

logger = logging.getLogger(__name__)


# ── Query Anchor Extraction ──────────────────────────────────

def extract_query_anchors(
    query: str,
    bridge: Any,
) -> Set[str]:
    """Extract anchor tokens from a query using the bridge lexicon.

    Returns set of normalized tokens that exist in bridge.word_index.
    """
    if bridge is None or not hasattr(bridge, "word_index"):
        return set()

    anchors = set()
    for token in _extract_anchors(query):
        if token in bridge.word_index:
            anchors.add(token)

    return anchors


# ── Token Boost Calculation ──────────────────────────────────

def _token_boost(
    token: str,
    bridge: Any,
) -> float:
    """Calculate boost for a single anchor token.

    boost = (1.0 + 0.2 * has_symbol) * (1.0 + clamp(log(freq+1)/10, 0, 1))
    Max possible: 1.2 * 2.0 = 2.4
    """
    has_symbol = False
    freq = 0

    if hasattr(bridge, "word_index") and token in bridge.word_index:
        hex_addr = bridge.word_index[token]
        entry = bridge.entries.get(hex_addr) if hasattr(bridge, "entries") else None
        if entry is not None:
            has_symbol = bool(entry.payload.get("font_symbol")) if hasattr(entry, "payload") else False
        if hasattr(bridge, "frequency"):
            freq = bridge.frequency.get(token, 0)

    symbol_factor = 1.0 + (0.2 if has_symbol else 0.0)
    freq_factor = 1.0 + min(max(math.log(freq + 1) / 10.0, 0.0), 1.0)

    return symbol_factor * freq_factor


# ── Anchor Relevance Calculation ─────────────────────────────

def _anchor_relevance(
    query_anchors: Set[str],
    chunk_anchor_tokens: Set[str],
    bridge: Any,
) -> float:
    """Calculate normalized anchor relevance for a chunk.

    raw = sum(token_boost(t) for t in overlap) / max(1, len(query_anchors))
    Returns: clamp(raw, 0.0, 1.0)
    """
    if not query_anchors:
        return 0.0

    overlap = query_anchors & chunk_anchor_tokens
    if not overlap:
        return 0.0

    raw = sum(_token_boost(t, bridge) for t in overlap) / max(1, len(query_anchors))
    return min(max(raw, 0.0), 1.0)


# ── Evidence Structural Relevance ───────────────────────────

def _evidence_relevance(
    query_anchors: Set[str],
    chunk_anchor_tokens: Set[str],
    bridge: Any,
) -> float:
    """Score how well chunk anchors match evidence cell neighbors.

    For each query anchor, reads its evidence cell. Checks how many of
    the chunk's anchor tokens appear as positional neighbors anywhere
    in the cell's 12 buckets. Weighted by count.

    Returns: normalized score [0, 1].
    """
    if not query_anchors or not chunk_anchor_tokens or bridge is None:
        return 0.0

    try:
        from bridges.evidence_store import get_evidence_store
        store = get_evidence_store()
    except Exception:
        return 0.0

    if store.count() == 0:
        return 0.0

    total_weight = 0.0
    hit_weight = 0.0

    for token in query_anchors:
        hex_addr = bridge.word_index.get(token) if hasattr(bridge, "word_index") else None
        if not hex_addr:
            continue
        cell = store.read_cell(hex_addr)
        if cell is None:
            continue

        # Build set of neighbor hex addresses with their total counts
        for offset, entries in cell.buckets.items():
            for entry in entries:
                total_weight += entry.count
                # Check if this neighbor is one of the chunk's anchors
                # Need to reverse-lookup hex → word
                neighbor_word = None
                if hasattr(bridge, "entries") and entry.hex_addr in bridge.entries:
                    e = bridge.entries[entry.hex_addr]
                    neighbor_word = e.word if hasattr(e, "word") else None
                if neighbor_word and neighbor_word in chunk_anchor_tokens:
                    hit_weight += entry.count

    if total_weight == 0:
        return 0.0
    return min(hit_weight / total_weight, 1.0)


# ── Main Reranker ────────────────────────────────────────────

def rerank(
    candidates: List[ScoredChunk],
    query_anchors: Set[str],
    chunk_anchors_map: Dict[str, ChunkAnchors],
    bridge: Any = None,
    anchor_weight: float = 0.3,
) -> List[ScoredChunk]:
    """Rerank candidates using 6-1-6 anchor boosting.

    Args:
        candidates: Retrieval candidates with hybrid scores.
        query_anchors: Anchor tokens extracted from the query.
        chunk_anchors_map: {chunk_id: ChunkAnchors} for all chunks.
        bridge: ClearboxLexiconBridge instance (for token_boost).
        anchor_weight: α — blending weight for anchor score (default 0.3).

    Returns:
        Reranked list of ScoredChunk with updated scores,
        sorted by (score DESC, chunk_id ASC).
    """
    if not candidates:
        return []

    alpha = min(max(anchor_weight, 0.0), 1.0)

    # If no chunk has any anchors, set alpha=0 to avoid penalizing
    # chunks ingested without bridge. The reranker still normalizes
    # hybrid scores to [0,1], but the anchor component contributes 0.
    any_has_anchors = any(
        c.chunk_id in chunk_anchors_map
        and chunk_anchors_map[c.chunk_id].anchor_count > 0
        for c in candidates
    )
    if not any_has_anchors:
        alpha = 0.0

    # Normalize hybrid scores to [0, 1]
    max_score = max(c.score for c in candidates)
    if max_score <= 0:
        max_score = 1.0  # Avoid division by zero

    reranked: List[ScoredChunk] = []
    for c in candidates:
        hybrid_norm = c.score / max_score

        # Get chunk's anchor tokens
        chunk_anchor_tokens: Set[str] = set()
        if c.chunk_id in chunk_anchors_map:
            chunk_anchor_tokens = {
                a.token for a in chunk_anchors_map[c.chunk_id].anchors
            }

        anchor_rel = _anchor_relevance(query_anchors, chunk_anchor_tokens, bridge)

        # Evidence structural score: do the chunk's anchors appear as
        # positional neighbors in the evidence cells of the query's anchors?
        evidence_score = _evidence_relevance(query_anchors, chunk_anchor_tokens, bridge)

        # Blend: hybrid + anchor overlap + evidence structure
        # Split anchor_weight between word overlap and structural evidence
        alpha_word = alpha * 0.5
        alpha_evidence = alpha * 0.5
        final_score = (1.0 - alpha) * hybrid_norm + alpha_word * anchor_rel + alpha_evidence * evidence_score

        reranked.append(ScoredChunk(
            chunk_id=c.chunk_id,
            receipt_id=c.receipt_id,
            corpus_id=c.corpus_id,
            score=final_score,
            source="reranked",
            bm25_score=c.bm25_score,
            dense_score=c.dense_score,
            anchor_score=anchor_rel,
        ))

    # Deterministic sort: score DESC, chunk_id ASC
    reranked.sort(key=lambda x: (-x.score, x.chunk_id))

    return reranked
