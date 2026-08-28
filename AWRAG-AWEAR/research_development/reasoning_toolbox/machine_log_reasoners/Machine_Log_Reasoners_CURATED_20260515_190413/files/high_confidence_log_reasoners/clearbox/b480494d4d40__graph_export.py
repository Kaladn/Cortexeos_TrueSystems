"""
graph_export.py — Export a Graph to renderer-ready formats.

Takes a Graph object and emits clean, portable structures
that any renderer (3D, 2D, terminal, web) can consume.

Output formats:
    1. render_dict()  → Python dict (for in-process use)
    2. render_json()  → JSON string (for file/API transport)
    3. render_file()  → writes JSON to disk

The renderer format spec:

{
    "meta": {
        "window": int,
        "topK": int,
        "source": str,
        "total_nodes": int,
        "total_edges": int,
        "anchors": int,
        "candidates": int
    },
    "nodes": [
        {
            "id": str,
            "token": str,
            "type": "anchor" | "candidate",
            "in_lexicon": bool,
            "symbol": str | null,
            "frequency": int,
            "count": int,
            "degree": int            ← number of edges touching this node
        }
    ],
    "edges": [
        {
            "source": str,          ← node id (always the anchor)
            "target": str,          ← node id (always the candidate)
            "direction": "before" | "after",
            "distance": int,        ← 1-6
            "count": int,           ← weight
            "in_lexicon": bool,
            "symbol": str | null
        }
    ]
}

This format is designed so that:
    - Any graph library (D3, Three.js, networkx, vis.js) can consume it directly.
    - Nodes have enough metadata for coloring, sizing, labeling.
    - Edges have enough metadata for coloring, weighting, filtering by distance/direction.
    - The structure is flat and JSON-serializable. No nested nightmares.
"""

import json
from pathlib import Path
from typing import Optional

from graph_model import Graph


def render_dict(graph: Graph, anchor_filter: Optional[list[str]] = None) -> dict:
    """
    Convert a Graph to the renderer-ready dict format.

    Args:
        graph: The full Graph object.
        anchor_filter: Optional list of anchor IDs to include.
                       If None, all anchors and their clouds are included.
                       This is the "focus mode" — isolate specific anchors.
    """
    # If filtering, extract subgraph first
    if anchor_filter:
        graph = graph.subgraph(anchor_filter)

    # Build node list
    nodes = []
    edge_counts: dict[str, int] = {}
    for e in graph.edges:
        edge_counts[e.source_id] = edge_counts.get(e.source_id, 0) + 1
        edge_counts[e.target_id] = edge_counts.get(e.target_id, 0) + 1

    for node in graph.nodes:
        nodes.append({
            "id": node.id,
            "token": node.token,
            "type": "anchor" if node.is_anchor else "candidate",
            "in_lexicon": node.in_lexicon,
            "symbol": node.symbol,
            "frequency": node.frequency,
            "count": node.count,
            "degree": edge_counts.get(node.id, 0),
        })

    # Build edge list
    edges = []
    for edge in graph.edges:
        edges.append({
            "source": edge.source_id,
            "target": edge.target_id,
            "direction": edge.direction,
            "distance": edge.distance,
            "count": edge.count,
            "in_lexicon": edge.in_lexicon,
            "symbol": edge.symbol,
        })

    return {
        "meta": graph.stats,
        "nodes": nodes,
        "edges": edges,
    }


def render_json(graph: Graph, anchor_filter: Optional[list[str]] = None, indent: int = 2) -> str:
    """Convert a Graph to a JSON string."""
    return json.dumps(render_dict(graph, anchor_filter), indent=indent, ensure_ascii=False)


def render_file(graph: Graph, output_path: str, anchor_filter: Optional[list[str]] = None) -> Path:
    """Write the renderer-ready JSON to a file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(render_json(graph, anchor_filter))
    return path


# ─── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    from graph_transformer import transform

    if len(sys.argv) < 2:
        print("Usage: python graph_export.py <map.json> [output.json] [anchor1,anchor2,...]")
        sys.exit(1)

    map_path = sys.argv[1]
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    anchor_filter = sys.argv[3].split(",") if len(sys.argv) > 3 else None

    g = transform(map_path)

    if out_path:
        p = render_file(g, out_path, anchor_filter)
        print(f"Wrote renderer JSON to: {p}")
    else:
        print(render_json(g, anchor_filter))
