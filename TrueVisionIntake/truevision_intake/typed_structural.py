"""Bounded structural routing after deterministic TrueVision source typing."""

from __future__ import annotations

import hashlib
from typing import Any

from .structural_binding import compile_text_structures, stable_hash


BOUNDED_TYPES = {"source_code", "capability_catalog", "provenance_record", "structured_document", "structured_records"}


def compile_typed_structures(
    text: str,
    *,
    source_identity: str,
    source_profile: dict[str, Any],
    block_ordinal: int = 0,
    tabular: bool = False,
) -> dict[str, Any]:
    source_type = str(source_profile.get("source_type") or "unclassified_text")
    if source_type not in BOUNDED_TYPES:
        return compile_text_structures(
            text,
            source_identity=source_identity,
            block_ordinal=block_ordinal,
            temporary_query_overlay=False,
        )
    parent_object_id = stable_hash({
        "source_identity": source_identity,
        "block_ordinal": block_ordinal,
        "kind": "PARENT_OBJECT",
    })
    body = {
        "schema": "truevision_typed_structural_binding@1",
        "compiler": "truevision_bounded_typed_structure_router@1",
        "source_identity": source_identity,
        "source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "block_ordinal": block_ordinal,
        "source_type": source_type,
        "tabular_grid_present": bool(tabular),
        "source_text_modified": False,
        "normalization_performed": False,
        "model_used": False,
        "statistical_nlp_used": False,
        "parent_object_id": parent_object_id,
        "native_identity_byte_start": 0,
        "native_identity_byte_end": len(text.encode("utf-8")),
        "structures": [],
        "relations": [],
        "bounded_reason": "typed source uses exact anchors, relations, citations, and typed/grid metadata instead of prose entity expansion",
    }
    body["compilation_id"] = stable_hash(body)
    return body
