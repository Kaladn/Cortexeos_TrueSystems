from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .anchors import anchorize
from .base import sha1_text, utc_now, with_protected_notice, write_json

VALUE_RE = re.compile(r"(?<!\w)(?:\d+(?:\.\d+)?\s*%|\d+(?:\.\d+)?\s+percent)(?!\w)", re.I)
CONTRADICTION_MARKERS = {"not", "no", "neither", "contradict", "contrary", "fails", "failed"}
RELATION_MARKERS = {"associated", "association", "caused", "causes", "due", "linked", "relationship", "related"}


def run_wide_deep_verification(*, packet_path: str | Path, out_dir: str | Path, expected: dict[str, Any] | None = None) -> dict[str, Any]:
    source = Path(packet_path).expanduser().resolve()
    packet = json.loads(source.read_text(encoding="utf-8"))
    result = build_wide_deep_verification(packet, expected=expected)
    out = Path(out_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    result_path = out / "WIDE_DEEP_EVIDENCE_VERIFICATION.json"
    write_json(result_path, result)
    receipt = {
        **result["receipt"],
        "source_packet_path": str(source),
        "source_packet_sha1": sha1_text(source.read_text(encoding="utf-8")),
        "result_path": str(result_path),
    }
    write_json(out / "RUN_RECEIPT.json", receipt)
    return {**result, "result_path": str(result_path)}


def build_wide_deep_verification(packet: dict[str, Any], *, expected: dict[str, Any] | None = None) -> dict[str, Any]:
    question = str(packet.get("question") or packet.get("input_question") or "")
    answer_packet = packet.get("answer_packet") if isinstance(packet.get("answer_packet"), dict) else packet
    locations = [row for row in answer_packet.get("locations") or [] if isinstance(row, dict)]
    rejected = [row for row in answer_packet.get("rejected_locations") or [] if isinstance(row, dict)]
    candidates = locations + rejected
    native = sorted(enumerate(candidates), key=lambda item: _native_sort_key(item[1], item[0]))
    question_field = build_question_field(question)
    fields = [build_candidate_field(row, question_field, candidate_rank=rank, source_lane="qualified" if row in locations else "rejected") for rank, (_index, row) in enumerate(native, 1)]
    support_ranked = sorted(fields, key=lambda row: (-row["proof_support_score"], row["candidate_rank"]))
    for rank, field in enumerate(support_ranked, 1):
        field["proof_support_rank"] = rank
    field_by_citation = {str(row.get("citation")): row for row in support_ranked}
    native_fields = [field_by_citation.get(str(row.get("citation")), row) for row in fields]
    best = support_ranked[0] if support_ranked else None
    audit = audit_expected_vs_actual(question_field, native_fields, expected)
    consequence = classify_evidence_consequence(best, audit)
    return with_protected_notice({
        "schema": "truemem_wide_deep_evidence_verification@1",
        "created_at": utc_now(),
        "question": question,
        "question_field": question_field,
        "native_rank_authority": {
            "sort_key": ["direct_hit_count desc", "density_score desc", "score desc", "block_ordinal asc"],
            "candidates": native_fields,
        },
        "proof_support_order": [{"proof_support_rank": row["proof_support_rank"], "candidate_rank": row["candidate_rank"], "citation": row.get("citation"), "proof_support_score": row["proof_support_score"]} for row in support_ranked],
        "wide_field_map": build_wide_field_map(native_fields),
        "deep_proof_burden": native_fields,
        "expected_vs_actual_audit": audit,
        "consequence": consequence,
        "answer_form": select_answer_form(consequence),
        "receipt": {
            "computed_from_existing_packet": True,
            "no_retrieval": True,
            "no_ranking_mutation": True,
            "native_rank_preserved_separately": True,
            "no_scoring_mutation": True,
            "no_citation_mutation": True,
            "no_intake": True,
            "no_dataset_mutation": True,
            "no_model_judge": True,
            "no_hardcoded_case_outcomes": True,
        },
    })


def build_question_field(question: str) -> dict[str, Any]:
    anchors = anchorize(question)
    values = _values(question)
    relation_indexes = [index for index, anchor in enumerate(anchors) if anchor in RELATION_MARKERS]
    relation_index = relation_indexes[0] if relation_indexes else None
    population_anchors = anchors[:relation_index] if relation_index is not None else []
    outcome_anchors = anchors[relation_index + 1 :] if relation_index is not None else []
    return {
        "anchors": anchors,
        "required_values": values,
        "relation_markers": sorted(set(anchors) & RELATION_MARKERS),
        "negation_markers": sorted(set(anchors) & CONTRADICTION_MARKERS),
        "requires_value": bool(values),
        "requires_relation": bool(set(anchors) & RELATION_MARKERS),
        "population_anchors": population_anchors[-4:],
        "outcome_anchors": [anchor for anchor in outcome_anchors if anchor not in values][:4],
    }


def build_candidate_field(candidate: dict[str, Any], question_field: dict[str, Any], *, candidate_rank: int, source_lane: str) -> dict[str, Any]:
    text = str(candidate.get("text") or candidate.get("passage") or candidate.get("snippet") or "")
    anchors = anchorize(text)
    q = set(question_field["anchors"])
    e = set(anchors)
    matched = sorted(q & e)
    missing = detect_missing_support(question_field, candidate, anchors)
    contradiction = bool((e & CONTRADICTION_MARKERS) ^ set(question_field["negation_markers"]))
    relation_supported = not question_field["requires_relation"] or bool(e & RELATION_MARKERS)
    exact = not any(missing.values()) and bool(matched)
    if contradiction and matched:
        status = "contradiction_candidate"
    elif exact:
        status = "exact_support_candidate"
    elif question_field["requires_value"] and missing["required_value_missing"] and matched:
        status = "related_evidence_exact_value_absent"
    elif matched:
        status = "same_subject_weak_support"
    else:
        status = "no_support"
    coverage = len(matched) / max(1, len(q))
    proof_score = round(coverage + (0.25 if relation_supported else 0.0) + (0.25 if exact else 0.0) - (0.25 if contradiction else 0.0), 6)
    return {
        "candidate_rank": candidate_rank,
        "source_candidate_lane": source_lane,
        "direct_hit_count": int(candidate.get("direct_hit_count") or 0),
        "density_score": float(candidate.get("density_score") or 0.0),
        "score": float(candidate.get("score") or 0.0),
        "block_ordinal": int(candidate.get("block_ordinal") or 0),
        "citation": candidate.get("citation"),
        "coordinates": candidate.get("coordinates") or _coordinates(candidate),
        "matched_query_anchors": matched,
        "missing_query_anchors": sorted(q - e),
        "new_relations": sorted((e & RELATION_MARKERS) - set(question_field["relation_markers"])),
        "repeated_relations": sorted((e & RELATION_MARKERS) & set(question_field["relation_markers"])),
        "drift_anchors": sorted(e - q)[:40],
        "missing_support": missing,
        "contradiction_pressure": contradiction,
        "proof_status": status,
        "proof_support_score": proof_score,
    }


def detect_missing_support(question_field: dict[str, Any], candidate: dict[str, Any], evidence_anchors: list[str]) -> dict[str, bool]:
    text = str(candidate.get("text") or candidate.get("passage") or candidate.get("snippet") or "")
    evidence_values = set(_values(text))
    return {
        "required_relation_missing": bool(question_field["requires_relation"] and not (set(evidence_anchors) & RELATION_MARKERS)),
        "required_value_missing": bool(set(question_field["required_values"]) - evidence_values),
        "required_population_missing": bool(question_field["population_anchors"] and not (set(question_field["population_anchors"]) & set(evidence_anchors))),
        "required_outcome_missing": bool(question_field["outcome_anchors"] and not (set(question_field["outcome_anchors"]) & set(evidence_anchors))),
        "required_citation_missing": not bool(candidate.get("citation")),
    }


def build_wide_field_map(fields: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "rank_slices": {str(k): [row["citation"] for row in fields[:k]] for k in (1, 3, 5, 10)},
        "strongest_direct_field": fields[0]["citation"] if fields else None,
        "nearby_support_fields": [row["citation"] for row in fields if row["proof_status"] in {"exact_support_candidate", "same_subject_weak_support"}],
        "drift_fields": [row["citation"] for row in fields if row["drift_anchors"]],
        "contradiction_candidates": [row["citation"] for row in fields if row["contradiction_pressure"]],
        "unsupported_value_fields": [row["citation"] for row in fields if row["missing_support"]["required_value_missing"]],
    }


def audit_expected_vs_actual(question_field: dict[str, Any], fields: list[dict[str, Any]], expected: dict[str, Any] | None) -> dict[str, Any]:
    if not expected:
        return {"performed": False, "classification": "not_applicable", "reason": "no_expected_field_supplied"}
    expected_field = build_candidate_field(expected, question_field, candidate_rank=0, source_lane="expected")
    actual = fields[0] if fields else None
    if actual is None:
        classification = "no support evidence found"
    elif actual["proof_status"] == "exact_support_candidate" and expected_field["proof_status"] != "exact_support_candidate":
        classification = "AW better evidence field"
    elif actual["proof_status"] != "no_support" and expected_field["proof_status"] == "no_support":
        classification = "AW better field, exact support absent"
    elif expected_field["proof_support_score"] > actual["proof_support_score"]:
        classification = "true AW miss"
    elif expected_field["proof_status"] == "no_support":
        classification = "gold/question mismatch candidate"
    else:
        classification = "unclear / human review"
    return {"performed": True, "classification": classification, "expected_field": expected_field, "actual_native_rank_1": actual}


def classify_evidence_consequence(best: dict[str, Any] | None, audit: dict[str, Any]) -> str:
    if audit.get("classification") == "gold/question mismatch candidate":
        return "benchmark mismatch"
    if best is None or best["proof_status"] == "no_support":
        return "no support refusal"
    return {"exact_support_candidate": "exact supported answer", "related_evidence_exact_value_absent": "narrow related answer", "contradiction_candidate": "contradiction report"}.get(best["proof_status"], "unclear / human review")


def select_answer_form(consequence: str) -> str:
    return {"exact supported answer": "FORM_SUPPORTED_CLAIM", "narrow related answer": "FORM_RELATED_BUT_UNSUPPORTED", "contradiction report": "FORM_EVIDENCE_SPLIT", "no support refusal": "FORM_NO_SUPPORT", "benchmark mismatch": "FORM_BENCHMARK_MISMATCH"}.get(consequence, "FORM_HUMAN_REVIEW")


def _native_sort_key(candidate: dict[str, Any], original_index: int) -> tuple[Any, ...]:
    return (-int(candidate.get("direct_hit_count") or 0), -float(candidate.get("density_score") or 0.0), -float(candidate.get("score") or 0.0), int(candidate.get("block_ordinal") or 0), original_index)


def _coordinates(candidate: dict[str, Any]) -> dict[str, Any]:
    return {key: candidate.get(key) for key in ("file_path", "line_start", "line_end", "block_ordinal") if candidate.get(key) is not None}


def _values(text: str) -> list[str]:
    return sorted({re.sub(r"\s+", " ", match.group(0).casefold()).replace(" percent", "%").replace(" ", "") for match in VALUE_RE.finditer(text)})
