"""
Cascade Engine — BFS traversal on ForgeMemory co-occurrence graph.

Built from scratch (the original cascade_engine.py was a 17-line stub).

Given a starting symbol (e.g., from a pattern break), traces:
  - Forward cascade: downstream effects (what symbols tend to follow?)
  - Backward cascade: upstream causes (what symbols tend to precede?)

Uses resonance-weighted cutoff: stops expanding when co-occurrence
strength drops below a threshold relative to the strongest neighbor.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field

from wolf_engine.forge.forge_memory import ForgeMemory

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CascadeNode:
    """A node in the cascade trace."""

    symbol_id: int = 0
    depth: int = 0
    co_occurrence_strength: float = 0.0
    parent_id: int | None = None


@dataclass(slots=True)
class CascadeTrace:
    """Result of a cascade traversal from a starting symbol."""

    origin_id: int = 0
    direction: str = ""           # "forward" or "backward"
    nodes: list[CascadeNode] = field(default_factory=list)
    max_depth_reached: int = 0
    total_explored: int = 0

    def symbol_ids(self) -> list[int]:
        """Return all symbol IDs in the trace in BFS order."""
        return [n.symbol_id for n in self.nodes]


class CascadeEngine:
    """
    BFS cascade traversal on ForgeMemory's co-occurrence graph.

    Parameters:
        forge: ForgeMemory instance to read co-occurrence from.
        max_depth: Maximum BFS depth (default 4).
        min_strength_ratio: Stop expanding a branch when its co-occurrence
            is below this fraction of the origin's max co-occurrence (default 0.1).
        max_nodes: Hard cap on total nodes explored (default 100).
    """

    def __init__(
        self,
        forge: ForgeMemory,
        max_depth: int = 4,
        min_strength_ratio: float = 0.1,
        max_nodes: int = 100,
    ):
        self.forge = forge
        self.max_depth = max_depth
        self.min_strength_ratio = min_strength_ratio
        self.max_nodes = max_nodes

    def trace_forward(self, origin_id: int) -> CascadeTrace:
        """Trace downstream effects from origin_id via co-occurrence."""
        return self._bfs(origin_id, "forward")

    def trace_backward(self, origin_id: int) -> CascadeTrace:
        """Trace upstream causes leading to origin_id via co-occurrence."""
        return self._bfs(origin_id, "backward")

    def trace_both(self, origin_id: int) -> tuple[CascadeTrace, CascadeTrace]:
        """Trace both directions. Returns (forward, backward)."""
        return self.trace_forward(origin_id), self.trace_backward(origin_id)

    def _bfs(self, origin_id: int, direction: str) -> CascadeTrace:
        """
        BFS traversal on the co-occurrence graph.

        For "forward": follows co_occurrence[symbol_id] neighbors.
        For "backward": follows symbols that have origin in their co_occurrence.
        """
        # Determine the cutoff threshold from the origin's strongest connection
        origin_neighbors = self.forge.co_occurrence.get(origin_id, {})
        if not origin_neighbors:
            return CascadeTrace(
                origin_id=origin_id, direction=direction,
                nodes=[], max_depth_reached=0, total_explored=0,
            )

        max_co = max(origin_neighbors.values())
        min_strength = max_co * self.min_strength_ratio

        visited: set[int] = {origin_id}
        queue: deque[CascadeNode] = deque()
        result_nodes: list[CascadeNode] = []

        # Seed BFS with origin's neighbors
        neighbors = self._get_neighbors(origin_id, direction)
        for nid, count in neighbors.items():
            if count >= min_strength and nid not in visited:
                queue.append(CascadeNode(
                    symbol_id=nid, depth=1,
                    co_occurrence_strength=float(count), parent_id=origin_id,
                ))

        max_depth_seen = 0

        while queue and len(result_nodes) < self.max_nodes:
            node = queue.popleft()
            if node.symbol_id in visited:
                continue
            visited.add(node.symbol_id)
            result_nodes.append(node)
            max_depth_seen = max(max_depth_seen, node.depth)

            # Expand if within depth limit
            if node.depth < self.max_depth:
                child_neighbors = self._get_neighbors(node.symbol_id, direction)
                for nid, count in child_neighbors.items():
                    if nid not in visited and count >= min_strength:
                        queue.append(CascadeNode(
                            symbol_id=nid, depth=node.depth + 1,
                            co_occurrence_strength=float(count),
                            parent_id=node.symbol_id,
                        ))

        return CascadeTrace(
            origin_id=origin_id,
            direction=direction,
            nodes=result_nodes,
            max_depth_reached=max_depth_seen,
            total_explored=len(visited) - 1,  # Exclude origin
        )

    def _get_neighbors(self, symbol_id: int, direction: str) -> dict[int, int]:
        """
        Get neighbors for a symbol in the given direction.

        Forward: co_occurrence[symbol_id] — what co-occurs with this symbol.
        Backward: find all symbols that have symbol_id in their co_occurrence.
        """
        if direction == "forward":
            return dict(self.forge.co_occurrence.get(symbol_id, {}))

        # Backward: scan all co-occurrence entries for those referencing symbol_id
        # This is O(n) over all symbols — acceptable for bounded graph traversal.
        result: dict[int, int] = {}
        for sid, neighbors in self.forge.co_occurrence.items():
            if symbol_id in neighbors:
                result[sid] = neighbors[symbol_id]
        return result
