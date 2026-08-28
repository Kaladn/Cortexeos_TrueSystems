"""Cloud Cascade — recursive context cloud traversal engine.

6-1-6 on the clouds themselves. Every neighbor in an evidence cell is a
potential anchor. This module walks the evidence graph, tracking provenance
at every edge, scoring with cumulative decay, and returning both discovery
(what was reached) and audit (how it got there) outputs.

The counts already exist. The traversal provenance is the only new layer.

Scoring:
    edge_weight = count * (7 - abs(position)) / 6
    path_score  = prev_score * hop_decay + edge_weight

Ranking: per-hop survivors selected by decayed_score, not raw edge weight.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from .cell_reader import BinaryCell, CellStore, BUCKET_ORDER, NeighborEntry

logger = logging.getLogger(__name__)

# Content stop words — overly broad connectors that create false bridges
STOP_ANCHORS: Set[str] = {
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had",
    "her", "was", "one", "our", "out", "has", "his", "how", "its", "may",
    "new", "now", "old", "see", "way", "who", "did", "get", "let", "say",
    "she", "too", "use", "with", "from", "this", "that", "them", "then",
    "than", "each", "make", "like", "been", "have", "into", "over", "such",
    "take", "very", "will", "more", "also", "back", "when", "only", "just",
    "some", "much", "most", "made", "well", "what", "were", "which",
}

DEFAULT_HOP_DECAY = 0.75
DEFAULT_TOP_K = 6
DEFAULT_MAX_HOPS = 2


def _position_index(bucket_name: str) -> int:
    """Convert bucket name to signed position: before_6=-6 ... after_6=+6."""
    if bucket_name.startswith("before_"):
        return -int(bucket_name.split("_")[1])
    return int(bucket_name.split("_")[1])


def edge_weight(count: int, position: int) -> float:
    """Weight formula: count * (7 - abs(position)) / 6."""
    return count * (7 - abs(position)) / 6


@dataclass
class CascadeEdge:
    """One edge in a traversal path."""
    source_word: str
    target_word: str
    source_hex: str
    target_hex: str
    position: int       # -6 to +6
    count: int
    weight: float


@dataclass
class CascadePath:
    """A complete traversal path from root to current anchor."""
    root_word: str
    root_hex: str
    current_word: str
    current_hex: str
    hop: int
    edges: List[CascadeEdge] = field(default_factory=list)
    cumulative_score: float = 0.0
    decayed_score: float = 0.0
    visited: Set[str] = field(default_factory=set)

    def extend(self, edge: CascadeEdge, hop_decay: float) -> "CascadePath":
        """Create a new path by extending this one with a new edge."""
        new_visited = set(self.visited)
        new_visited.add(edge.target_hex)
        new_score = self.cumulative_score + edge.weight
        new_decayed = self.decayed_score * hop_decay + edge.weight
        return CascadePath(
            root_word=self.root_word,
            root_hex=self.root_hex,
            current_word=edge.target_word,
            current_hex=edge.target_hex,
            hop=self.hop + 1,
            edges=self.edges + [edge],
            cumulative_score=new_score,
            decayed_score=new_decayed,
            visited=new_visited,
        )


@dataclass
class CascadeResult:
    """Output of a cloud cascade traversal."""
    root_word: str
    root_hex: str
    max_hops: int
    top_k: int
    hop_decay: float
    # Per-depth results
    paths_by_depth: Dict[int, List[CascadePath]] = field(default_factory=dict)
    reached_by_depth: Dict[int, List[dict]] = field(default_factory=dict)

    def discovery_output(self) -> Dict[int, List[dict]]:
        """Top reached anchors per depth — the discovery view."""
        return self.reached_by_depth

    def audit_output(self) -> Dict[int, List[dict]]:
        """Full path chains per depth — the audit view."""
        result = {}
        for depth, paths in self.paths_by_depth.items():
            result[depth] = [
                {
                    "root": p.root_word,
                    "reached": p.current_word,
                    "hop": p.hop,
                    "decayed_score": round(p.decayed_score, 3),
                    "cumulative_score": round(p.cumulative_score, 3),
                    "chain": [
                        {
                            "from": e.source_word,
                            "to": e.target_word,
                            "pos": e.position,
                            "count": e.count,
                            "weight": round(e.weight, 3),
                        }
                        for e in p.edges
                    ],
                }
                for p in paths
            ]
        return result


def _extract_top_neighbors(
    cell: BinaryCell,
    store: CellStore,
    top_k: int,
    stop_anchors: Set[str],
) -> List[Tuple[str, str, int, int, float]]:
    """Extract top-K content neighbors from an evidence cell.

    Returns list of (word, hex, position, count, weight) tuples,
    sorted by weight descending.
    """
    candidates = []
    for bucket_name in BUCKET_ORDER:
        pos = _position_index(bucket_name)
        neighbors = cell.get_bucket(pos)
        for ne in neighbors:
            word = ne.neighbor_word.lower()
            if not word or len(word) < 3:
                continue
            if word in stop_anchors:
                continue
            # Must exist as an anchor in evidence store
            nhex = store.resolve_word(word)
            if nhex is None:
                continue
            w = edge_weight(ne.count, pos)
            candidates.append((word, nhex, pos, ne.count, w))

    # Sort by weight desc, take top K
    candidates.sort(key=lambda x: x[4], reverse=True)
    return candidates[:top_k]


def cascade(
    store: CellStore,
    root_word: str,
    max_hops: int = DEFAULT_MAX_HOPS,
    top_k: int = DEFAULT_TOP_K,
    hop_decay: float = DEFAULT_HOP_DECAY,
    stop_anchors: Optional[Set[str]] = None,
) -> CascadeResult:
    """Run a cloud cascade traversal from a root anchor word.

    Args:
        store: Evidence CellStore (loaded, with index)
        root_word: Starting anchor word
        max_hops: Maximum traversal depth (2=practical, 3=experimental)
        top_k: Top-K neighbors to expand at each hop
        hop_decay: Decay factor for cumulative path scoring
        stop_anchors: Words to skip (broad connectors that create false bridges)

    Returns:
        CascadeResult with discovery and audit outputs per depth
    """
    if stop_anchors is None:
        stop_anchors = STOP_ANCHORS

    root_hex = store.resolve_word(root_word.lower())
    if root_hex is None:
        logger.warning("Root word '%s' not found in evidence store", root_word)
        return CascadeResult(
            root_word=root_word, root_hex="", max_hops=max_hops,
            top_k=top_k, hop_decay=hop_decay,
        )

    root_cell = store.read_cell(root_hex)
    if root_cell is None:
        logger.warning("No evidence cell for root hex %s", root_hex)
        return CascadeResult(
            root_word=root_word, root_hex=root_hex, max_hops=max_hops,
            top_k=top_k, hop_decay=hop_decay,
        )

    result = CascadeResult(
        root_word=root_word, root_hex=root_hex,
        max_hops=max_hops, top_k=top_k, hop_decay=hop_decay,
    )

    # Seed paths from root
    seed = CascadePath(
        root_word=root_word, root_hex=root_hex,
        current_word=root_word, current_hex=root_hex,
        hop=0, visited={root_hex},
    )

    active_paths = [seed]

    for depth in range(1, max_hops + 1):
        next_paths: List[CascadePath] = []

        for path in active_paths:
            cell = store.read_cell(path.current_hex)
            if cell is None:
                continue

            top_neighbors = _extract_top_neighbors(cell, store, top_k, stop_anchors)

            for word, nhex, pos, count, w in top_neighbors:
                if nhex in path.visited:
                    continue  # Cycle prevention

                edge = CascadeEdge(
                    source_word=path.current_word,
                    target_word=word,
                    source_hex=path.current_hex,
                    target_hex=nhex,
                    position=pos,
                    count=count,
                    weight=w,
                )
                new_path = path.extend(edge, hop_decay)
                next_paths.append(new_path)

        # Rank by decayed_score, keep top K*top_k survivors
        next_paths.sort(key=lambda p: p.decayed_score, reverse=True)
        survivors = next_paths[:top_k * top_k]  # beam width

        result.paths_by_depth[depth] = survivors[:top_k]

        # Discovery output: unique reached anchors at this depth
        seen_reached: Set[str] = set()
        reached = []
        for p in survivors:
            if p.current_hex not in seen_reached:
                seen_reached.add(p.current_hex)
                reached.append({
                    "word": p.current_word,
                    "hex": p.current_hex,
                    "decayed_score": round(p.decayed_score, 3),
                    "hop": p.hop,
                    "via": p.edges[-1].source_word if p.edges else root_word,
                })
                if len(reached) >= top_k:
                    break
        result.reached_by_depth[depth] = reached

        # Survivors become active paths for next hop
        active_paths = survivors

        logger.info(
            "Cascade hop %d: %d paths expanded, %d survivors, %d unique reached",
            depth, len(next_paths), len(survivors), len(reached),
        )

    return result
