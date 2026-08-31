"""Exact evidence-obligation contract for occurrence traversal v2."""

from __future__ import annotations

import hashlib
import json
from typing import Any


SCHEMA = "truemem_pressure_point@1"
KINDS = frozenset({
    "EXACT_STRUCTURE",
    "EXACT_RELATION_FIELD",
    "EXACT_CONTEXT_ANCHORS",
    "EXACT_PARENT_TRANSITION",
})


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def validate_pressure_points(
    pressure_points: list[dict[str, Any]],
    *,
    verified_question_structure_keys: set[str],
    admitted_keys: set[str],
) -> list[dict[str, Any]]:
    """Validate exact obligations without inferring fields or authority."""
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for ordinal, raw in enumerate(pressure_points):
        row = dict(raw)
        pressure_id = str(row.get("pressure_id") or f"pressure-{ordinal + 1}")
        if pressure_id in seen:
            raise ValueError("DUPLICATE_PRESSURE_ID")
        seen.add(pressure_id)
        kind = str(row.get("kind") or "")
        if kind not in KINDS:
            raise ValueError("INVALID_PRESSURE_KIND")
        ruling = tuple(sorted(set(map(str, row.get("ruling_structure_keys") or []))))
        if not ruling or any(value not in verified_question_structure_keys for value in ruling):
            raise ValueError("UNVERIFIED_RULING_STRUCTURE")
        if any(value not in admitted_keys for value in ruling):
            raise ValueError("UNADMITTED_RULING_STRUCTURE")
        exact_structures = tuple(sorted(set(map(str, row.get("exact_structure_keys") or []))))
        relation_fields = tuple(map(str, row.get("relation_field_anchor_keys") or []))
        context_anchors = tuple(map(str, row.get("context_anchor_keys") or []))
        mention_structures = tuple(sorted(set(map(str, row.get("mention_structure_keys") or []))))
        target_structures = tuple(sorted(set(map(str, row.get("target_structure_keys") or []))))
        transition_context = tuple(map(str, row.get("transition_context_anchor_keys") or []))
        if any(value not in admitted_keys for value in exact_structures + mention_structures + target_structures):
            raise ValueError("UNADMITTED_PRESSURE_STRUCTURE")
        if any(value not in admitted_keys for value in relation_fields + context_anchors + transition_context):
            raise ValueError("UNADMITTED_PRESSURE_ANCHOR")
        if kind == "EXACT_STRUCTURE" and not exact_structures:
            raise ValueError("MISSING_EXACT_STRUCTURE_OBLIGATION")
        if kind == "EXACT_RELATION_FIELD" and not relation_fields:
            raise ValueError("MISSING_RELATION_FIELD_OBLIGATION")
        if kind == "EXACT_CONTEXT_ANCHORS" and not context_anchors:
            raise ValueError("MISSING_CONTEXT_ANCHOR_OBLIGATION")
        if kind == "EXACT_PARENT_TRANSITION" and (not mention_structures or not target_structures):
            raise ValueError("MISSING_PARENT_TRANSITION_OBLIGATION")
        normalized = {
            "schema": SCHEMA,
            "pressure_id": pressure_id,
            "kind": kind,
            "ruling_structure_keys": list(ruling),
            "exact_structure_keys": list(exact_structures),
            "relation_field_anchor_keys": list(relation_fields),
            "context_anchor_keys": list(context_anchors),
            "mention_structure_keys": list(mention_structures),
            "target_structure_keys": list(target_structures),
            "transition_context_anchor_keys": list(transition_context),
        }
        normalized["pressure_hash"] = hashlib.sha256(canonical_bytes(normalized)).hexdigest()
        rows.append(normalized)
    return rows
