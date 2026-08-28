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
                       if len(t) >= 3
                       and t in bridge.word_index
                       and t not in STOP_TOKENS}

      overlap = chunk_anchor_tokens ∩ query_anchors
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Set

from lakespeak.schemas import ScoredChunk, ChunkAnchors
from lakespeak.text.normalize import tokenize as _canonical_tokenize

logger = logging.getLogger(__name__)


# ── Deterministic Stop List (~50 tokens) ─────────────────────

STOP_TOKENS: frozenset = frozenset({
    "the", "and", "is", "are", "was", "were", "that", "this",
    "with", "from", "have", "has", "been", "will", "would",
    "could", "should", "about", "into", "over", "also", "than",
    "then", "when", "where", "which", "what", "who", "how",
    "its", "their", "your", "our", "some", "most", "each",
    "every", "both", "all", "any", "but", "not", "only",
    "very", "just", "more", "other", "such", "for", "can",
    "did", "does", "had", "may", "might", "shall", "too",
})


# ── Query Anchor Extraction ──────────────────────────────────

def extract_query_anchors(
    query: str,
    bridge: Any,
) -> Set[str]:
    """Extract anchor tokens from a query using the bridge lexicon.

    Returns set of normalized tokens that pass the anchor criteria:
      - len >= 3
      - not in STOP_TOKENS
      - present in bridge.word_index
    """
    if bridge is None or not hasattr(bridge, "word_index"):
        return set()

    anchors = set()
    for token in _canonical_tokenize(query):
        if len(token) < 3:
            continue
        if token in STOP_TOKENS:
            continue
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
        bridge: ForestLexiconBridge instance (for token_boost).
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

        # Blend
        final_score = (1.0 - alpha) * hybrid_norm + alpha * anchor_rel

        reranked.append(ScoredChunk(
            chunk_id=c.chunk_id,
            receipt_id=c.receipt_id,
            score=final_score,
            source="reranked",
            bm25_score=c.bm25_score,
            census_score=c.census_score,
            anchor_score=anchor_rel,
        ))

    # Deterministic sort: score DESC, chunk_id ASC
    reranked.sort(key=lambda x: (-x.score, x.chunk_id))

    return reranked
