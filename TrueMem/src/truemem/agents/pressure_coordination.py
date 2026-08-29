from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from statistics import mean, pvariance
from typing import Any

from truemem.engine.base import safe_id, utc_now, with_protected_notice, write_json


RUN_SCHEMA = "truemem_pressure_coordination_audit_run@0"
REAL_SCHEMA = "truemem_pressure_coordination_real_system_trace@0"
REAPER_SCHEMA = "truemem_pressure_coordination_reaper_mutation_trace@0"
COMBINED_SCHEMA = "truemem_pressure_coordination_combined_strength_trace@0"

DECISION_STRENGTH = {
    "supported": 0.9,
    "pressure_inspection_needed": 0.45,
    "partially_supported": 0.65,
    "needs_bridge": 0.45,
    "unsupported": 0.1,
    "contradicted": 0.0,
}


def run_pressure_coordination_audit(*, trace_path: str | Path, out_dir: str | Path) -> dict[str, Any]:
    """Coordinate existing reverse-walk traces without mutating source evidence.

    This live side module writes three lanes:
    - the real system decision exactly as received,
    - a REAPER-inspired pressure-only mutation in its own file,
    - a combined-strength comparison that does not overwrite either source.
    """

    source = Path(trace_path).expanduser().resolve()
    out = Path(out_dir).expanduser().resolve()
    real_dir = out / "real_system_as_is"
    reaper_dir = out / "reaper_only"
    combined_dir = out / "combined_strengths"
    receipts_dir = out / "receipts"
    for directory in (real_dir, reaper_dir, combined_dir, receipts_dir):
        directory.mkdir(parents=True, exist_ok=True)

    before = _file_state(source)
    traces = _read_jsonl(source)
    real_rows: list[dict[str, Any]] = []
    reaper_rows: list[dict[str, Any]] = []
    combined_rows: list[dict[str, Any]] = []

    decision_counts: Counter[str] = Counter()
    reaper_counts: Counter[str] = Counter()
    combined_counts: Counter[str] = Counter()

    for index, trace in enumerate(traces, start=1):
        claim_id = str(trace.get("claim_id") or index)
        real = _real_system_row(trace=trace, source=source, index=index, claim_id=claim_id)
        reaper = _reaper_pressure_row(trace=trace, source=source, index=index, claim_id=claim_id)
        combined = _combined_strength_row(real, reaper, source=source, index=index, claim_id=claim_id)
        real_rows.append(real)
        reaper_rows.append(reaper)
        combined_rows.append(combined)
        decision_counts[real["real_system_decision"]] += 1
        reaper_counts[reaper["reaper_pressure_decision"]] += 1
        combined_counts[combined["combined_decision"]] += 1

    real_path = real_dir / "REAL_SYSTEM_TRACE.jsonl"
    reaper_path = reaper_dir / "REAPER_PRESSURE_MUTATION_TRACE.jsonl"
    combined_path = combined_dir / "COMBINED_STRENGTH_TRACE.jsonl"
    _write_jsonl(real_path, real_rows)
    _write_jsonl(reaper_path, reaper_rows)
    _write_jsonl(combined_path, combined_rows)

    after = _file_state(source)
    no_mutation = {
        "schema": "truemem_pressure_coordination_no_mutation_receipt@0",
        "created_at": utc_now(),
        "source_trace_path": str(source),
        "before": before,
        "after": after,
        "mutation_detected": before != after,
    }
    write_json(receipts_dir / "no_mutation_receipt.json", no_mutation)

    summary = with_protected_notice({
        "schema": RUN_SCHEMA,
        "created_at": utc_now(),
        "source_trace_path": str(source),
        "out_dir": str(out),
        "records_processed": len(traces),
        "real_system_trace_path": str(real_path),
        "reaper_pressure_trace_path": str(reaper_path),
        "combined_strength_trace_path": str(combined_path),
        "real_system_decision_counts": dict(sorted(decision_counts.items())),
        "reaper_pressure_decision_counts": dict(sorted(reaper_counts.items())),
        "combined_decision_counts": dict(sorted(combined_counts.items())),
        "input_mutation_detected": bool(no_mutation["mutation_detected"]),
        "side_module": "pressure_coordination_agent",
        "real_system_preserved_as_is": True,
        "reaper_mutation_scope": "special_file_only",
        "combined_strengths_do_not_overwrite_real_or_reaper": True,
        "retrieval_ran": False,
        "topk_ran": False,
        "intake_ran": False,
        "ranking_mutation": False,
        "dataset_mutation": False,
        "speech_mutation": False,
        "model_used": "none",
        "no_answer_generation": True,
    })
    summary_path = out / "PRESSURE_COORDINATION_SUMMARY.json"
    write_json(summary_path, summary)
    _write_summary_markdown(out / "PRESSURE_COORDINATION_SUMMARY.md", summary)
    write_json(receipts_dir / "run_receipt.json", summary)
    summary["summary_path"] = str(summary_path)
    return summary


def _real_system_row(*, trace: dict[str, Any], source: Path, index: int, claim_id: str) -> dict[str, Any]:
    return {
        "schema": REAL_SCHEMA,
        "created_at": utc_now(),
        "source_trace_path": str(source),
        "trace_index": index,
        "claim_id": claim_id,
        "question": str(trace.get("question") or ""),
        "supplied_answer": str(trace.get("supplied_answer") or ""),
        "real_system_decision": _decision(trace.get("support_decision")),
        "real_system_strength": _decision_strength(trace.get("support_decision")),
        "bridge_needed": bool(trace.get("bridge_needed")),
        "candidate_citations": _string_list(trace.get("candidate_citations")),
        "preserved_as_is": True,
    }


def _reaper_pressure_row(*, trace: dict[str, Any], source: Path, index: int, claim_id: str) -> dict[str, Any]:
    families = _pressure_families(trace)
    values = [
        value
        for key, value in families.items()
        if key != "contradiction_pressure"
    ]
    values.append(1.0 - families["contradiction_pressure"])
    variance = pvariance(values) if len(values) > 1 else 0.0
    consensus_strength = max(0.0, 1.0 - min(1.0, variance * 4.0))
    support_strength = mean(values) if values else 0.0
    bridge_answerability = bridge_answerability_score(trace)
    decision = _pressure_decision(
        trace,
        support_strength=support_strength,
        contradiction=families["contradiction_pressure"],
        bridge_answerability=bridge_answerability,
    )
    promotion_cap = _promotion_cap(trace, bridge_answerability)
    return {
        "schema": REAPER_SCHEMA,
        "created_at": utc_now(),
        "source_trace_path": str(source),
        "trace_index": index,
        "claim_id": claim_id,
        "question": str(trace.get("question") or ""),
        "pressure_families": families,
        "pressure_vector": {
            "support_strength": round(support_strength, 6),
            "consensus_strength": round(consensus_strength, 6),
            "variance": round(variance, 6),
        },
        "bridge_answerability_score": round(bridge_answerability, 6),
        "bridge_answerability_threshold": 0.72,
        "promotion_cap": promotion_cap,
        "reaper_pressure_decision": decision,
        "reaper_pressure_strength": round(_decision_strength(decision, fallback=support_strength), 6),
        "reaper_mutation_scope": "special_file_only",
        "source_system_decision_not_overwritten": True,
    }


def _combined_strength_row(real: dict[str, Any], reaper: dict[str, Any], *, source: Path, index: int, claim_id: str) -> dict[str, Any]:
    real_strength = float(real["real_system_strength"])
    reaper_strength = float(reaper["reaper_pressure_strength"])
    combined_strength = (real_strength + reaper_strength) / 2.0
    return {
        "schema": COMBINED_SCHEMA,
        "created_at": utc_now(),
        "source_trace_path": str(source),
        "trace_index": index,
        "claim_id": claim_id,
        "real_system_decision": real["real_system_decision"],
        "real_system_strength": round(real_strength, 6),
        "reaper_pressure_decision": reaper["reaper_pressure_decision"],
        "reaper_pressure_strength": round(reaper_strength, 6),
        "combined_strength": round(combined_strength, 6),
        "combined_decision": _decision_from_strength(combined_strength, bridge_needed=real["bridge_needed"]),
        "real_system_preserved": True,
        "reaper_mutation_preserved_in_special_file": True,
    }


def _pressure_families(trace: dict[str, Any]) -> dict[str, float]:
    candidates = [row for row in trace.get("reverse_topK_candidates") or [] if isinstance(row, dict)]
    top = candidates[0] if candidates else {}
    answer_coverage = _float(top.get("answer_to_candidate_coverage"), _float(trace.get("answer_to_candidate_coverage")))
    question_coverage = _float(top.get("candidate_to_question_coverage"), _float(trace.get("candidate_to_question_coverage")))
    citations = set(_string_list(trace.get("candidate_citations")))
    citations.update(str(row.get("citation")) for row in candidates if row.get("citation"))
    local_blocks = top.get("local_neighborhood_blocks") if isinstance(top.get("local_neighborhood_blocks"), list) else trace.get("local_neighborhood_blocks")
    pressure_links = top.get("pressure_links") if isinstance(top.get("pressure_links"), list) else trace.get("pressure_links")
    missing_question = top.get("missing_question_anchors") if isinstance(top.get("missing_question_anchors"), list) else []
    matched_question = top.get("matched_question_anchors") if isinstance(top.get("matched_question_anchors"), list) else []

    anchor_pressure = (answer_coverage + question_coverage) / 2.0
    citation_pressure = min(1.0, len([citation for citation in citations if citation]) / 2.0)
    field_pressure = min(1.0, (_list_len(local_blocks) * 0.25) + (_list_len(pressure_links) * 0.15))
    bridge_pressure = 0.35 if trace.get("bridge_needed") else 1.0
    scenario_gap = _scenario_gap(matched_question, missing_question)
    contradiction_pressure = 0.85 if _decision(trace.get("support_decision")) == "contradicted" else 0.0

    return {
        "anchor_pressure": round(anchor_pressure, 6),
        "citation_pressure": round(citation_pressure, 6),
        "field_pressure": round(field_pressure, 6),
        "bridge_pressure": round(bridge_pressure, 6),
        "scenario_gap_pressure": round(scenario_gap, 6),
        "contradiction_pressure": round(contradiction_pressure, 6),
    }


def bridge_answerability_score(trace: dict[str, Any]) -> float:
    candidates = [row for row in trace.get("reverse_topK_candidates") or [] if isinstance(row, dict)]
    top = candidates[0] if candidates else {}
    citations = set(_string_list(trace.get("candidate_citations")))
    citations.update(str(row.get("citation")) for row in candidates if row.get("citation"))
    local_blocks = top.get("local_neighborhood_blocks") if isinstance(top.get("local_neighborhood_blocks"), list) else trace.get("local_neighborhood_blocks")
    pressure_links = top.get("pressure_links") if isinstance(top.get("pressure_links"), list) else trace.get("pressure_links")
    matched_question = top.get("matched_question_anchors") if isinstance(top.get("matched_question_anchors"), list) else []
    missing_question = top.get("missing_question_anchors") if isinstance(top.get("missing_question_anchors"), list) else []

    citation_component = min(1.0, len([citation for citation in citations if citation]) / 2.0)
    local_component = min(1.0, _list_len(local_blocks) / 2.0)
    link_component = min(1.0, _list_len(pressure_links) / 2.0)
    matched = len([item for item in matched_question if str(item).strip()])
    missing = len([item for item in missing_question if str(item).strip()])
    anchor_component = matched / (matched + missing) if matched + missing else 0.5

    return max(0.0, min(1.0, (
        citation_component * 0.25
        + local_component * 0.25
        + link_component * 0.25
        + anchor_component * 0.25
    )))


def _pressure_decision(trace: dict[str, Any], *, support_strength: float, contradiction: float, bridge_answerability: float) -> str:
    if contradiction >= 0.75:
        return "contradicted"
    if _promotion_cap(trace, bridge_answerability) == "needs_bridge":
        return "needs_bridge"
    if trace.get("bridge_needed") and support_strength < 0.72:
        return "needs_bridge"
    return _decision_from_strength(support_strength, bridge_needed=bool(trace.get("bridge_needed")))


def _promotion_cap(trace: dict[str, Any], bridge_answerability: float) -> str | None:
    if _decision(trace.get("support_decision")) == "needs_bridge" and bridge_answerability < 0.72:
        return "needs_bridge"
    return None


def _decision_from_strength(strength: float, *, bridge_needed: bool) -> str:
    if strength >= 0.72:
        return "supported"
    if bridge_needed and strength >= 0.38:
        return "needs_bridge"
    if strength >= 0.45:
        return "partially_supported"
    return "unsupported"


def _scenario_gap(matched_question: list[Any], missing_question: list[Any]) -> float:
    matched = len([item for item in matched_question if str(item).strip()])
    missing = len([item for item in missing_question if str(item).strip()])
    if matched == 0 and missing == 0:
        return 0.5
    if matched > 0 and missing > 0:
        return 0.75
    if matched > 0:
        return 1.0
    return 0.25


def _decision(value: Any) -> str:
    text = str(value or "unsupported").strip() or "unsupported"
    return safe_id(text)


def _decision_strength(value: Any, *, fallback: float | None = None) -> float:
    decision = _decision(value)
    if decision in DECISION_STRENGTH:
        return DECISION_STRENGTH[decision]
    return float(fallback if fallback is not None else 0.1)


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _list_len(value: Any) -> int:
    return len(value) if isinstance(value, list) else 0


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"trace row {line_number} is not a JSON object")
            rows.append(row)
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(with_protected_notice(row), ensure_ascii=True) + "\n")


def _file_state(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    stat = path.stat()
    return {
        "path": str(path),
        "exists": True,
        "size": stat.st_size,
        "modified_ns": stat.st_mtime_ns,
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _write_summary_markdown(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Pressure Coordination Audit",
        "",
        f"Records processed: {summary['records_processed']}",
        f"Real system trace: `{summary['real_system_trace_path']}`",
        f"REAPER-only mutation trace: `{summary['reaper_pressure_trace_path']}`",
        f"Combined strength trace: `{summary['combined_strength_trace_path']}`",
        "",
        "## Decision Counts",
        "",
        f"Real system: `{summary['real_system_decision_counts']}`",
        f"REAPER-only: `{summary['reaper_pressure_decision_counts']}`",
        f"Combined: `{summary['combined_decision_counts']}`",
        "",
        "## Boundaries",
        "",
        "- Real system output is preserved as-is.",
        "- REAPER pressure mutation is written only to the special REAPER file.",
        "- Combined strengths do not overwrite either lane.",
        "- No retrieval, topK, intake, ranking mutation, dataset mutation, speech mutation, model call, or answer generation ran.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
