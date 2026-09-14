"""
graph_transformer.py — Converts a 6-1-6 map JSON into a Graph.

This is the ONE place where the JSON contract is read and obeyed.

Input:  raw dict (parsed JSON) or file path
Output: Graph object with all nodes and edges populated

Rules:
    1. Every anchor in items → becomes an anchor Node.
    2. Every candidate at every distance → becomes a candidate Node.
    3. Every anchor↔candidate pair at each distance/direction → becomes an Edge.
    4. If a candidate token matches an anchor token → the node is merged (is_anchor=True).
    5. We do NOT invent data. We do NOT skip data. We obey the file.
"""

import json
from pathlib import Path
from typing import Union

from graph_model import Node, Edge, Graph


def load_map(source: Union[str, Path, dict]) -> dict:
    """
    Accept a file path or an already-parsed dict.
    Returns the raw map dict.
    """
    if isinstance(source, dict):
        return source
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Map file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def transform(source: Union[str, Path, dict]) -> Graph:
    """
    The main entry point.

    Takes a 6-1-6 map (file path or dict) and returns a fully populated Graph.

    This function:
      1. Reads the top-level metadata (window, topK).
      2. Iterates every anchor in items.
      3. For each anchor, iterates before/after × distances 1..window.
      4. Creates nodes and edges for everything found.
      5. Returns the complete Graph.
    """
    raw = load_map(source)

    # ── Top-level metadata ──
    window = raw.get("window", 6)
    top_k = raw.get("topK", 10)
    map_source = raw.get("source", "unknown")

    graph = Graph(window=window, top_k=top_k, source=map_source)

    items = raw.get("items", {})

    # ── Pass 1: Create all anchor nodes ──
    for anchor_token, anchor_data in items.items():
        anchor_node = Node(
            id=anchor_token,
            token=anchor_token,
            is_anchor=True,
            in_lexicon=bool(anchor_data.get("lexicon_word")),
            symbol=anchor_data.get("symbol"),
            frequency=anchor_data.get("frequency", 0),
            count=0,
        )
        graph.add_node(anchor_node)

    # ── Pass 2: Walk every anchor's before/after clouds ──
    for anchor_token, anchor_data in items.items():
        for direction in ("before", "after"):
            cloud = anchor_data.get(direction, {})

            for distance_str, candidates in cloud.items():
                distance = int(distance_str)

                for candidate in candidates:
                    c_token = candidate["token"]
                    c_count = candidate.get("count", 1)
                    c_in_lex = candidate.get("in_lexicon", False)
                    c_symbol = candidate.get("symbol")

                    # Create candidate node (will merge if already exists as anchor or prior candidate)
                    candidate_node = Node(
                        id=c_token,
                        token=c_token,
                        is_anchor=False,        # add_node will upgrade if it's also an anchor
                        in_lexicon=c_in_lex,
                        symbol=c_symbol,
                        count=c_count,
                        anchor_distances=[distance],
                    )
                    merged = graph.add_node(candidate_node)

                    # Track which distances this candidate appears at
                    if distance not in merged.anchor_distances:
                        merged.anchor_distances.append(distance)

                    # Create the edge: anchor → candidate
                    edge = Edge(
                        source_id=anchor_token,
                        target_id=c_token,
                        direction=direction,
                        distance=distance,
                        count=c_count,
                        in_lexicon=c_in_lex,
                        symbol=c_symbol,
                    )
                    graph.add_edge(edge)

    return graph


# ─── CLI / standalone usage ────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python graph_transformer.py <path_to_map.json>")
        sys.exit(1)

    path = sys.argv[1]
    g = transform(path)
    print(g)
    print(f"Stats: {g.stats}")
    print(f"\nAnchors ({len(g.anchors)}):")
    for a in g.anchors[:10]:
        print(f"  {a.token} (freq={a.frequency}, lexicon={a.in_lexicon})")
    if len(g.anchors) > 10:
        print(f"  ... and {len(g.anchors) - 10} more")
    print(f"\nEdges ({len(g.edges)}):")
    for e in g.edges[:10]:
        print(f"  {e.source_id} --[{e.direction} d={e.distance}]--> {e.target_id} (count={e.count})")
    if len(g.edges) > 10:
        print(f"  ... and {len(g.edges) - 10} more")
