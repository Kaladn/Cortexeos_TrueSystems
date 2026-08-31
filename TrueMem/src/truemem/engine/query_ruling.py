from __future__ import annotations

import hashlib
import json
from typing import Any

from .anchors import anchorize

SUPPORTED_OPERATIONS = {
    "all_equal",
    "attribution",
    "count_anchors",
    "earlier_date",
    "exact_constraint_match",
    "identity_intersection",
    "later_date",
    "lifespan_longer",
    "location_chain",
    "membership_chain",
    "numeric_max",
    "numeric_min",
    "set_intersection",
}


def relationship_demands(question: str) -> list[dict[str, Any]]:
    """Return signed query relationships without deleting anchor positions."""
    from .anchors import anchor_kind

    anchors = anchorize(question)
    endpoints = {
        index
        for index, anchor in enumerate(anchors)
        if anchor_kind(anchor) in {"content", "relation"}
    }
    return [
        {
            "center": anchors[left],
            "neighbor": anchors[right],
            "signed_distance": right - left,
            "query_positions": [left, right],
        }
        for left in sorted(endpoints)
        for right in sorted(endpoints)
        if left != right and -6 <= right - left <= 6
    ]


def build_anchor_structure_sheet(
    question: str,
    *,
    ruling_groups: list[dict[str, Any]],
    operation: dict[str, Any],
    required_evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build a question-local traversal sheet without supplying an answer."""
    question_anchors = anchorize(question)
    groups = validate_ruling_anchor_groups(question, ruling_groups)
    operation_name = str(operation.get("name") or "")
    if operation_name not in SUPPORTED_OPERATIONS:
        raise ValueError(f"unsupported anchor-sheet operation: {operation_name}")
    operation_anchors = [str(value) for value in operation.get("anchors") or []]
    operation_start = int(operation.get("question_anchor_start", -1))
    if not operation_anchors or operation_start < 0:
        raise ValueError("operation requires exact anchors and question_anchor_start")
    if question_anchors[operation_start : operation_start + len(operation_anchors)] != operation_anchors:
        raise ValueError("operation anchors do not match exact question coordinates")
    evidence = []
    known_group_ids = {group["group_id"] for group in groups}
    for ordinal, row in enumerate(required_evidence):
        field = str(row.get("field") or "")
        group_id = str(row.get("group_id") or "")
        if not group_id and "group_index" in row:
            group_index = int(row["group_index"])
            if 0 <= group_index < len(groups):
                group_id = groups[group_index]["group_id"]
        if not field or group_id not in known_group_ids:
            raise ValueError(f"invalid required evidence row {ordinal}")
        evidence.append({"group_id": group_id, "field": field, "required": bool(row.get("required", True))})
    question_sha256 = hashlib.sha256(question.encode("utf-8")).hexdigest()
    sheet = {
        "schema": "truemem_question_anchor_structure_sheet@1",
        "question": question,
        "question_sha256": question_sha256,
        "question_anchors": question_anchors,
        "ruling_anchor_groups": groups,
        "operation": {
            "name": operation_name,
            "anchors": operation_anchors,
            "question_anchor_start": operation_start,
            "question_anchor_end": operation_start + len(operation_anchors) - 1,
        },
        "required_evidence": evidence,
        "answer_supplied": False,
        "stored_counts_modified": False,
        "stored_relationships_modified": False,
        "temporary_query_overlay": True,
    }
    sheet["sheet_id"] = hashlib.sha256(
        json.dumps(sheet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return sheet


def validate_ruling_anchor_groups(question: str, groups: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Validate LLM-supplied ruling groups against exact question coordinates.

    This function does not detect names or infer groups. It only verifies that
    the supplied complete-word anchors occur contiguously at the declared
    question positions.
    """
    question_anchors = anchorize(question)
    question_sha256 = hashlib.sha256(question.encode("utf-8")).hexdigest()
    accepted: list[dict[str, Any]] = []
    identities: set[tuple[str, ...]] = set()
    for ordinal, raw in enumerate(groups or []):
        anchors = [str(value) for value in raw.get("anchors") or []]
        if not anchors:
            raise ValueError(f"ruling group {ordinal} has no anchors")
        if anchorize(" ".join(anchors)) != anchors:
            raise ValueError(f"ruling group {ordinal} does not contain exact complete-word anchors")
        identity = tuple(anchors)
        if identity in identities:
            raise ValueError(f"duplicate ruling group: {anchors}")
        identities.add(identity)
        positions = [
            start for start in range(len(question_anchors) - len(anchors) + 1)
            if question_anchors[start : start + len(anchors)] == anchors
        ]
        declared_start = raw.get("question_anchor_start")
        if declared_start is None:
            if len(positions) != 1:
                raise ValueError(f"ruling group {anchors} requires an unambiguous question_anchor_start")
            declared_start = positions[0]
        declared_start = int(declared_start)
        if declared_start not in positions:
            raise ValueError(f"ruling group {anchors} does not match the declared question position")
        scope = str(raw.get("match_scope") or "parent_title")
        if scope not in {"parent_title", "any_exact_position"}:
            raise ValueError(f"unsupported ruling group match_scope: {scope}")
        role = str(raw.get("role") or "ruling_identity")
        payload = {
            "anchors": anchors,
            "question_anchor_start": declared_start,
            "question_anchor_end": declared_start + len(anchors) - 1,
            "match_scope": scope,
            "role": role,
            "question_sha256": question_sha256,
            "supplied_by": str(raw.get("supplied_by") or "SITTING_LLM"),
        }
        payload["group_id"] = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        accepted.append(payload)
    return accepted
