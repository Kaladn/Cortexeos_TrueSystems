"""Deterministic question-to-pressure planning from admitted structures only."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .anchors import anchor_kind, anchorize


SCHEMA = "truemem_generic_query_pressure_plan@1"
QUESTION_CONTROLS = frozenset({"what", "which", "who", "where", "when", "why", "how", "many", "much"})


def compile_query_pressure_plan(
    question: str,
    *,
    question_overlay: dict[str, Any],
    admitted_keys: set[str],
) -> dict[str, Any]:
    """Compile an oracle-free traversal request from question structure.

    This compiler never sees expected answers, blocks, paths, benchmark labels,
    or corpus identities.  It selects only exact question structures and exact
    admitted anchors.  Missing structure remains an explicit non-plan.
    """
    anchors = anchorize(question)
    structures = list(question_overlay.get("structures") or [])
    named = [
        row for row in structures
        if row.get("kind") == "NAMED_STRUCTURE"
        and row.get("status") != "AMBIGUOUS_STRUCTURE"
        and row.get("structure_key") in admitted_keys
        and _identity_children(row)
    ]
    # Nested candidates can describe the same question span.  Retain maximal
    # exact spans; ordering is physical question order, never corpus pressure.
    named.sort(key=lambda row: (int(row["byte_start"]), -int(row["byte_end"]), str(row["structure_key"])))
    ruling_candidates = []
    for row in named:
        if any(
            int(other["byte_start"]) <= int(row["byte_start"])
            and int(other["byte_end"]) >= int(row["byte_end"])
            and (int(other["byte_end"]) - int(other["byte_start"])) > (int(row["byte_end"]) - int(row["byte_start"]))
            for other in named
        ):
            continue
        ruling_candidates.append(row)
    # Every maximal verified identity remains a ruling center.  Discarding all
    # but the richest span erases comparison operands before traversal begins.
    date_spans = [
        (int(row["byte_start"]), int(row["byte_end"]))
        for row in structures if row.get("kind") == "DATE"
    ]
    ruling_candidates = [
        row for row in ruling_candidates
        if not any(start <= int(row["byte_start"]) and end >= int(row["byte_end"]) for start, end in date_spans)
    ]
    ruling_candidates.sort(key=lambda row: (
        int(row["byte_start"]), -int(row["byte_end"]), str(row["structure_key"]),
    ))
    ruling = list(dict.fromkeys(str(row["structure_key"]) for row in ruling_candidates))

    pressure: list[dict[str, Any]] = []
    transition_context = list(dict.fromkeys(
        anchor for anchor in anchors
        if anchor in admitted_keys and anchor_kind(anchor) in {"content", "relation"}
    ))
    question_folded = question.casefold()
    if _asks_for_alias(question_folded):
        pressure.append(_pressure("EXPLICIT_ALIAS", ruling, "alias"))

    for row in structures:
        if row.get("kind") != "DATE" or row.get("structure_key") not in admitted_keys:
            continue
        pressure.append(_pressure(
            "EXACT_STRUCTURE", ruling, f"date-{row['structure_key'][-12:]}",
            exact_structure_keys=[str(row["structure_key"])],
        ))

    if not pressure:
        for anchor in _interrogative_focus(anchors):
            if anchor not in admitted_keys:
                continue
            pressure.append(_pressure(
                "EXACT_CONTEXT_ANCHORS", ruling, f"question-focus-{hashlib.sha256(anchor.encode('utf-8')).hexdigest()[:12]}",
                context_anchor_keys=[anchor],
            ))

    for row in pressure:
        row["transition_context_anchor_keys"] = transition_context
        row["transition_context_mode"] = "ANY"

    # Pressure validation requires a ruling structure.  Refuse rather than
    # silently treating arbitrary question words as a named identity.
    status = "READY" if ruling and pressure else "INSUFFICIENT_VERIFIED_QUESTION_STRUCTURE"
    body = {
        "schema": SCHEMA,
        "question_sha256": hashlib.sha256(question.encode("utf-8")).hexdigest(),
        "question_overlay_id": question_overlay.get("compilation_id"),
        "status": status,
        "selected_question_structure_keys": sorted(set(ruling)),
        "pressure_points": pressure if status == "READY" else [],
        "derivation": {
            "question_only": True,
            "admitted_dataset_keys_only": True,
            "expected_answer_used": False,
            "expected_block_used": False,
            "expected_path_used": False,
            "benchmark_identity_used": False,
            "transition_context_supplied": False,
            "transition_context_derived_from_question": True,
        },
    }
    body["plan_sha256_without_self"] = hashlib.sha256(
        (json.dumps(body, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    ).hexdigest()
    return body


def _identity_children(row: dict[str, Any]) -> list[str]:
    values = [
        str(child.get("anchor")) for child in row.get("children") or []
        if anchor_kind(str(child.get("anchor"))) in {"content", "relation"}
    ]
    if not values or values[0].casefold() in QUESTION_CONTROLS:
        return []
    return values


def _asks_for_alias(question: str) -> bool:
    return any(phrase in question for phrase in ("other name", "also known", "known as", "called what", "what was") ) and (
        " name" in question or " known" in question or " called" in question
    )


def _interrogative_focus(anchors: list[str]) -> list[str]:
    positions = [index for index, anchor in enumerate(anchors) if anchor.casefold() in QUESTION_CONTROLS]
    if not positions:
        return []
    center = positions[-1]
    start = max(0, center - 3)
    end = min(len(anchors), center + 4)
    return list(dict.fromkeys(
        anchor for anchor in anchors[start:end]
        if anchor_kind(anchor) == "content" and anchor.casefold() not in QUESTION_CONTROLS
    ))


def _pressure(kind: str, ruling: list[str], label: str, **values: Any) -> dict[str, Any]:
    payload = {
        "pressure_id": f"question-{label}-{len(ruling)}",
        "kind": kind,
        "ruling_structure_keys": sorted(set(ruling)),
        "exact_structure_keys": [],
        "relation_field_anchor_keys": [],
        "context_anchor_keys": [],
        "mention_structure_keys": [],
        "target_structure_keys": [],
        "transition_context_anchor_keys": [],
        "transition_context_mode": "ALL",
    }
    payload.update(values)
    return payload
