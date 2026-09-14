"""
graph_model.py — Data model for 6-1-6 map graph structures.

This module defines the pure data containers.
No rendering. No UI. No opinions.
Just: nodes, edges, and the graph that holds them.

Contract:
    - A Node is a token (anchor or candidate).
    - An Edge connects an anchor to a candidate at a specific distance/direction.
    - A Graph is the complete set of nodes + edges extracted from one 6-1-6 map.
"""

from dataclasses import dataclass, field
from typing import Optional


# ─── Node ──────────────────────────────────────────────────────────────────────

@dataclass
class Node:
    """A single token that exists in the graph."""

    id: str                     # unique key: the token string (or token:anchor for disambiguation)
    token: str                  # the raw token text
    is_anchor: bool             # True if this token is an anchor in the map
    in_lexicon: bool            # True if in_lexicon was True for this token
    symbol: Optional[str]       # symbol field from the map (nullable)
    frequency: int = 0          # frequency from anchor metadata (0 for candidates)
    count: int = 0              # aggregated occurrence count across all edges
    anchor_distances: list = field(default_factory=list)  # which distances this node appears at

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, Node) and self.id == other.id


# ─── Edge ──────────────────────────────────────────────────────────────────────

@dataclass
class Edge:
    """A directional relationship: anchor → candidate (or candidate → anchor)."""

    source_id: str              # node id of the anchor
    target_id: str              # node id of the candidate
    direction: str              # "before" or "after"
    distance: int               # 1-6 (how far from anchor)
    count: int                  # occurrence count from the map
    in_lexicon: bool            # candidate's lexicon status on this edge
    symbol: Optional[str]       # candidate's symbol on this edge

    @property
    def weight(self) -> int:
        """Edge weight = count. Higher count = stronger connection."""
        return self.count

    @property
    def depth(self) -> int:
        """Alias for distance — how many positions from anchor."""
        return self.distance

    def __hash__(self):
        return hash((self.source_id, self.target_id, self.direction, self.distance))

    def __eq__(self, other):
        return (isinstance(other, Edge) and
                self.source_id == other.source_id and
                self.target_id == other.target_id and
                self.direction == other.direction and
                self.distance == other.distance)


# ─── Graph ─────────────────────────────────────────────────────────────────────

class Graph:
    """
    The complete 6-1-6 graph.

    Holds all nodes and edges.
    Provides lookup, filtering, and export.
    Does NOT render. Does NOT mutate the source data.
    """

    def __init__(self, window: int = 6, top_k: int = 10, source: str = ""):
        self.window = window
        self.top_k = top_k
        self.source = source
        self._nodes: dict[str, Node] = {}      # id -> Node
        self._edges: list[Edge] = []
        self._anchor_ids: set[str] = set()

    # ── Mutation (build phase only) ──

    def add_node(self, node: Node) -> Node:
        """Add or merge a node. If it exists, merge counts."""
        if node.id in self._nodes:
            existing = self._nodes[node.id]
            existing.count += node.count
            existing.in_lexicon = existing.in_lexicon or node.in_lexicon
            if node.is_anchor:
                existing.is_anchor = True
                existing.frequency = node.frequency
            return existing
        self._nodes[node.id] = node
        if node.is_anchor:
            self._anchor_ids.add(node.id)
        return node

    def add_edge(self, edge: Edge) -> None:
        """Add an edge to the graph."""
        self._edges.append(edge)

    # ── Read access ──

    @property
    def nodes(self) -> list[Node]:
        return list(self._nodes.values())

    @property
    def edges(self) -> list[Edge]:
        return list(self._edges)

    @property
    def anchors(self) -> list[Node]:
        return [self._nodes[aid] for aid in self._anchor_ids if aid in self._nodes]

    @property
    def candidates(self) -> list[Node]:
        return [n for n in self._nodes.values() if not n.is_anchor]

    def get_node(self, node_id: str) -> Optional[Node]:
        return self._nodes.get(node_id)

    def edges_for(self, node_id: str) -> list[Edge]:
        """All edges touching a specific node (as source OR target)."""
        return [e for e in self._edges if e.source_id == node_id or e.target_id == node_id]

    def neighbors(self, node_id: str) -> list[Node]:
        """All nodes directly connected to this node."""
        neighbor_ids = set()
        for e in self.edges_for(node_id):
            other = e.target_id if e.source_id == node_id else e.source_id
            neighbor_ids.add(other)
        return [self._nodes[nid] for nid in neighbor_ids if nid in self._nodes]

    def subgraph(self, anchor_ids: list[str]) -> "Graph":
        """Extract a subgraph containing only the specified anchors and their clouds."""
        sub = Graph(window=self.window, top_k=self.top_k, source=self.source)
        relevant_edges = [e for e in self._edges if e.source_id in anchor_ids]
        relevant_node_ids = set(anchor_ids)
        for e in relevant_edges:
            relevant_node_ids.add(e.target_id)
        for nid in relevant_node_ids:
            if nid in self._nodes:
                sub.add_node(self._nodes[nid])
        for e in relevant_edges:
            sub.add_edge(e)
        return sub

    # ── Stats ──

    @property
    def stats(self) -> dict:
        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "anchors": len(self._anchor_ids),
            "candidates": len(self._nodes) - len(self._anchor_ids),
            "window": self.window,
            "top_k": self.top_k,
        }

    def __repr__(self):
        s = self.stats
        return (f"Graph(anchors={s['anchors']}, candidates={s['candidates']}, "
                f"edges={s['total_edges']}, window={s['window']})")
