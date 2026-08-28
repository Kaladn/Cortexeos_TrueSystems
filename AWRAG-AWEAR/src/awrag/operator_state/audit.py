from __future__ import annotations

import json
from hashlib import sha1
from pathlib import Path
from typing import Any

from awrag.engine.base import utc_now

from .anchors import extract_anchor_groups
from .rules import build_structural_analysis, compute_anchor_scores, select_operational_routing, system_output_for_mode
from .schemas import AUDIT_SCHEMA


def audit_operator_state(raw_input: str, *, output_path: str | Path | None = None) -> dict[str, Any]:
    extracted = extract_anchor_groups(raw_input)
    scores = compute_anchor_scores(extracted)
    structural = build_structural_analysis(extracted, scores)
    routing = select_operational_routing(extracted, scores, structural)
    receipt = {
        "schema": AUDIT_SCHEMA,
        "audit_id": _audit_id(raw_input),
        "created_at": utc_now(),
        "raw_input": raw_input,
        "extracted_anchors": extracted,
        "anchor_scores": scores,
        "structural_analysis": structural,
        "operational_routing": routing,
        "system_output": system_output_for_mode(routing["selected_mode"]),
        "hard_boundaries": {
            "action_state": "AUDIT_ONLY",
            "production_command_execution": False,
            "backend_mutation": False,
            "count_mutation": False,
            "lifetime_memory_write": False,
            "model_classifier": False,
        },
    }
    if output_path is not None:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(receipt, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    return receipt


def _audit_id(raw_input: str) -> str:
    return "OSRL-" + sha1(raw_input.encode("utf-8", errors="replace")).hexdigest()[:16]
