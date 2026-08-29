"""Hybrid merge — Reciprocal Rank Fusion (RRF) of sparse + dense.

Merges BM25 and dense retrieval results using weighted RRF:
    score = bm25_weight * 1/(k + bm25_rank) + dense_weight * 1/(k + dense_rank)

Where k = 60 (standard RRF constant).

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
    dense_results: List[ScoredChunk],
    bm25_weight: float = 0.4,
    dense_weight: float = 0.6,
) -> List[ScoredChunk]:
    """Merge BM25 and dense results using weighted Reciprocal Rank Fusion.

    Args:
        bm25_results: Scored chunks from BM25 (sorted by score DESC).
        dense_results: Scored chunks from dense index (sorted by score DESC).
        bm25_weight: Weight for BM25 RRF contribution (default 0.4).
        dense_weight: Weight for dense RRF contribution (default 0.6).

    Returns:
        Merged list of ScoredChunk sorted by fused score DESC, chunk_id ASC.
    """
    # Build rank maps (1-indexed)
    bm25_rank: Dict[str, int] = {}
    bm25_by_id: Dict[str, ScoredChunk] = {}
    for i, sc in enumerate(bm25_results):
        bm25_rank[sc.chunk_id] = i + 1
        bm25_by_id[sc.chunk_id] = sc

    dense_rank: Dict[str, int] = {}
    dense_by_id: Dict[str, ScoredChunk] = {}
    for i, sc in enumerate(dense_results):
        dense_rank[sc.chunk_id] = i + 1
        dense_by_id[sc.chunk_id] = sc

    # Union of all chunk IDs
    all_ids = set(bm25_rank.keys()) | set(dense_rank.keys())

    merged: List[ScoredChunk] = []
    for chunk_id in all_ids:
        # RRF scores (missing rank = large rank penalty)
        bm25_rrf = bm25_weight * (1.0 / (RRF_K + bm25_rank.get(chunk_id, 1000)))
        dense_rrf = dense_weight * (1.0 / (RRF_K + dense_rank.get(chunk_id, 1000)))
        fused = bm25_rrf + dense_rrf

        # Preserve original scores
        bm25_sc = bm25_by_id.get(chunk_id)
        dense_sc = dense_by_id.get(chunk_id)

        receipt_id = ""
        bm25_score = 0.0
        dense_score = 0.0
        if bm25_sc:
            receipt_id = bm25_sc.receipt_id
            bm25_score = bm25_sc.bm25_score
        if dense_sc:
            receipt_id = receipt_id or dense_sc.receipt_id
            dense_score = dense_sc.dense_score

        merged.append(ScoredChunk(
            chunk_id=chunk_id,
            receipt_id=receipt_id,
            score=fused,
            source="hybrid",
            bm25_score=bm25_score,
            dense_score=dense_score,
            anchor_score=0.0,
        ))

    # Sort: score DESC, chunk_id ASC (deterministic)
    merged.sort(key=lambda x: (-x.score, x.chunk_id))

    return merged
