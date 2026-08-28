"""Hybrid merge — Reciprocal Rank Fusion (RRF) of BM25 + Census.

Merges BM25 and census (6-1-6 adjacency co-occurrence) results using weighted RRF:
    score = bm25_weight * 1/(k + bm25_rank) + census_weight * 1/(k + census_rank)

Where k = 60 (standard RRF constant).

Weights: BM25 0.40 / Census 0.60 (confirmed, locked).

If only one index provides results, its scores are normalized to [0,1] directly.
Deduplicates by chunk_id. Sorts descending by fused score, then chunk_id ASC for ties.
"""

from __future__ import annotations

import logging
from typing import Dict, List

from lakespeak.schemas import ScoredChunk

logger = logging.getLogger(__name__)

# Standard RRF constant (from Cormack et al. 2009)
RRF_K = 60


def rrf_merge(
    bm25_results: List[ScoredChunk],
    census_results: List[ScoredChunk],
    bm25_weight: float = 0.4,
    census_weight: float = 0.6,
) -> List[ScoredChunk]:
    """Merge BM25 and census results using weighted Reciprocal Rank Fusion.

    Args:
        bm25_results: Scored chunks from BM25 (sorted by score DESC).
        census_results: Scored chunks from census index (sorted by score DESC).
        bm25_weight: Weight for BM25 RRF contribution (default 0.4).
        census_weight: Weight for census RRF contribution (default 0.6).

    Returns:
        Merged list of ScoredChunk sorted by fused score DESC, chunk_id ASC.
    """
    # Build rank maps (1-indexed)
    bm25_rank: Dict[str, int] = {}
    bm25_by_id: Dict[str, ScoredChunk] = {}
    for i, sc in enumerate(bm25_results):
        bm25_rank[sc.chunk_id] = i + 1
        bm25_by_id[sc.chunk_id] = sc

    census_rank: Dict[str, int] = {}
    census_by_id: Dict[str, ScoredChunk] = {}
    for i, sc in enumerate(census_results):
        census_rank[sc.chunk_id] = i + 1
        census_by_id[sc.chunk_id] = sc

    # Union of all chunk IDs
    all_ids = set(bm25_rank.keys()) | set(census_rank.keys())

    merged: List[ScoredChunk] = []
    for chunk_id in all_ids:
        # RRF scores (missing rank = large rank penalty)
        bm25_rrf = bm25_weight * (1.0 / (RRF_K + bm25_rank.get(chunk_id, 1000)))
        census_rrf = census_weight * (1.0 / (RRF_K + census_rank.get(chunk_id, 1000)))
        fused = bm25_rrf + census_rrf

        # Preserve original scores
        bm25_sc = bm25_by_id.get(chunk_id)
        census_sc = census_by_id.get(chunk_id)

        receipt_id = ""
        bm25_score = 0.0
        census_score = 0.0
        if bm25_sc:
            receipt_id = bm25_sc.receipt_id
            bm25_score = bm25_sc.bm25_score
        if census_sc:
            receipt_id = receipt_id or census_sc.receipt_id
            census_score = census_sc.census_score

        merged.append(ScoredChunk(
            chunk_id=chunk_id,
            receipt_id=receipt_id,
            score=fused,
            source="hybrid",
            bm25_score=bm25_score,
            census_score=census_score,
            anchor_score=0.0,
        ))

    # Sort: score DESC, chunk_id ASC (deterministic)
    merged.sort(key=lambda x: (-x.score, x.chunk_id))

    return merged
