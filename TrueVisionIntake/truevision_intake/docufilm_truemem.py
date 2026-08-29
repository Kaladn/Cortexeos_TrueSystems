from __future__ import annotations

from collections.abc import Callable
from typing import Any

def build_docufilm_truemem_hierarchy(
    document_state_read: dict[str, Any],
    *,
    dataset_id: str,
    dataset_symbol_for: Callable[[str], str],
) -> dict[str, Any]:
    """Map one DocuFilm read into a dataset-native parent/contained hierarchy."""

    from truemem.engine.anchors import anchor_kind, anchorize

    if document_state_read.get("record_type") != "document_state_read":
        raise ValueError("DocuFilm requires a document_state_read record")
    read_hash = str(document_state_read.get("read_hash") or "")
    if not read_hash:
        raise ValueError("DocuFilm document_state_read has no read_hash")

    parent = f"object:docufilm:{read_hash}"
    contained: list[dict[str, Any]] = []
    position = 0

    for glyph in document_state_read.get("glyph_records") or []:
        state_hash = str(glyph.get("state_hash") or "")
        glyph_anchor = f"object:glyph:{state_hash}"
        contained.append(_dataset_item(glyph_anchor, position, dataset_symbol_for, anchor_kind, source="glyph_state"))
        position += 1

    derived_text = str(document_state_read.get("derived_text") or "")
    for anchor in anchorize(derived_text):
        contained.append(_dataset_item(anchor, position, dataset_symbol_for, anchor_kind, source="recognized_string"))
        position += 1

    parent_item = _dataset_item(parent, -1, dataset_symbol_for, anchor_kind, source="docufilm_parent")
    edges = [
        {
            "edge": "contains",
            "parent_anchor": parent,
            "child_anchor": item["anchor"],
            "child_position": item["position"],
        }
        for item in contained
    ]
    return {
        "schema": "docufilm_truemem_hierarchy@1",
        "dataset_id": str(dataset_id),
        "intake_authority": "TrueVision.DocuFilm",
        "parent": parent_item,
        "contained": contained,
        "edges": edges,
        "whitespace_symbols": 0,
        "dataset_record": {
            "parent": parent_item,
            "contained": contained,
            "edges": edges,
        },
        "model_view": {
            "parent": parent,
            "contained_strings": [item["anchor"] for item in contained],
            "derived_text": derived_text,
        },
    }


def _dataset_item(
    anchor: str,
    position: int,
    dataset_symbol_for: Callable[[str], str],
    classify_anchor: Callable[[str], str],
    *,
    source: str,
) -> dict[str, Any]:
    symbol = str(dataset_symbol_for(anchor))
    if not symbol:
        raise ValueError(f"dataset did not assign a symbol for {anchor!r}")
    return {
        "anchor": anchor,
        "anchor_kind": classify_anchor(anchor),
        "symbol": symbol,
        "position": int(position),
        "source": source,
    }
