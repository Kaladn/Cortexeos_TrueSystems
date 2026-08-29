from __future__ import annotations

import re
from collections import Counter
from typing import Any

from .anchors import GLUE_ANCHORS, anchor_kind, anchorize, answer_direction_anchors


def qualify_evidence(question: str, q_counter: Counter[str], candidates: list[dict[str, Any]], *, top_k: int) -> dict[str, Any]:
    question_terms = answer_direction_anchors(list(q_counter))
    required_terms = significant_question_terms(question_terms)
    path_intent = has_path_or_config_intent(question)
    unsupported_intent = len(required_terms) >= 4
    question_anchor_split = split_question_anchors_for_pressure(question, required_terms)

    receipts: list[dict[str, Any]] = []
    qualified_rows: list[tuple[float, dict[str, Any]]] = []
    rejected: list[dict[str, Any]] = []
    pressure_promoted_count = 0

    for candidate in candidates:
        receipt = qualify_candidate(candidate, required_terms, path_intent, unsupported_intent, question_anchor_split=question_anchor_split)
        receipts.append(receipt)
        enriched = dict(candidate)
        enriched["qualification"] = receipt
        if receipt["qualified"]:
            if receipt.get("pressure_decision") == "promote_to_supported":
                pressure_promoted_count += 1
            qualified_rows.append((float(receipt["qualified_score"]), enriched))
        else:
            rejected.append(enriched)

    qualified_rows.sort(key=lambda item: (-item[0], -float(item[1].get("density_score", 0)), -float(item[1].get("score", 0))))
    locations = [item[1] for item in qualified_rows[:top_k]]
    if locations and pressure_promoted_count:
        support_state = "pressure_supported_evidence"
    else:
        support_state = "qualified_evidence" if locations else "no_qualified_evidence"
    return {
        "summary": {
            "schema": "truemem_evidence_qualification_summary@1",
            "support_state": support_state,
            "raw_candidate_count": len(candidates),
            "qualified_count": len(qualified_rows),
            "rejected_count": len(rejected),
            "pressure_promoted_count": pressure_promoted_count,
            "pressure_reviewed_count": len(candidates),
            "required_terms": required_terms,
            "question_anchor_split": question_anchor_split,
            "path_or_config_intent": path_intent,
        },
        "receipts": receipts,
        "locations": locations,
        "rejected": rejected[:top_k],
    }

def qualify_candidate(
    candidate: dict[str, Any],
    required_terms: list[str],
    path_intent: bool,
    unsupported_intent: bool,
    *,
    question_anchor_split: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    text = str(candidate.get("text", ""))
    text_anchors = set(anchorize(text))
    direct = set(candidate.get("direct_matched_anchors") or [])
    covered = sorted(anchor for anchor in required_terms if anchor in text_anchors or anchor in direct)
    missing = sorted(anchor for anchor in required_terms if anchor not in covered)
    coverage = len(covered) / max(1, len(required_terms))
    heading_only = is_heading_only(text)
    broad_heading = heading_only and is_broad_heading(text)
    slash_phrase = contains_unqualified_slash_phrase(text)

    reject_reasons: list[str] = []
    if broad_heading:
        reject_reasons.append("section_heading_ambiguity")
    if heading_only and coverage < 0.75:
        reject_reasons.append("heading_without_content")
    if path_intent and slash_phrase and not contains_true_path_or_endpoint(text):
        reject_reasons.append("path_config_classifier_miss")
    if unsupported_intent and coverage < 0.50:
        reject_reasons.append("unsupported_refusal_threshold")
    if len(required_terms) >= 3 and coverage < 0.34:
        reject_reasons.append("predicate_object_coverage_miss")

    reject_reasons_before_pressure = list(reject_reasons)
    pressure = pressure_review_candidate(
        candidate,
        covered=covered,
        missing=missing,
        coverage=coverage,
        reject_reasons=reject_reasons,
        question_anchor_split=question_anchor_split or {},
    )
    if pressure["pressure_decision"] == "promote_to_supported":
        reject_reasons = []

    qualified = not reject_reasons
    score = float(candidate.get("density_score", 0)) + 8.0 * coverage + min(4.0, float(candidate.get("direct_hit_count", 0))) - (3.0 if heading_only else 0.0)
    return {
        "schema": "truemem_candidate_qualification@1",
        "candidate": candidate.get("citation"),
        "qualified": qualified,
        "reject_reasons": reject_reasons,
        "reject_reasons_before_pressure": reject_reasons_before_pressure,
        "covered_terms": covered,
        "missing_terms": missing[:20],
        "coverage": round(coverage, 4),
        "heading_only": heading_only,
        "broad_heading": broad_heading,
        "path_or_config_candidate": contains_true_path_or_endpoint(text),
        "qualified_score": round(score, 4),
        **pressure,
    }

def pressure_review_candidate(
    candidate: dict[str, Any],
    *,
    covered: list[str],
    missing: list[str],
    coverage: float,
    reject_reasons: list[str],
    question_anchor_split: dict[str, list[str]],
) -> dict[str, Any]:
    direct_hit_count = int(candidate.get("direct_hit_count") or 0)
    score = float(candidate.get("score") or 0.0)
    density_score = float(candidate.get("density_score") or 0.0)
    matched_evidence_terms = [term for term in covered if term not in set(question_anchor_split.get("scenario_terms") or [])]
    missing_scenario_terms = [term for term in missing if term in set(question_anchor_split.get("scenario_terms") or [])]
    missing_evidence_terms = [term for term in missing if term not in set(missing_scenario_terms)]
    native_rank_strong = score >= 30.0 and density_score >= 4.0 and direct_hit_count >= 5
    strong_evidence_anchor_match = len(matched_evidence_terms) >= 5 and coverage >= 0.35
    coordinate_supported = bool(candidate.get("citation")) and bool(candidate.get("file_path"))
    scenario_gap_only = (
        "unsupported_refusal_threshold" in reject_reasons
        and "predicate_object_coverage_miss" not in reject_reasons
        and strong_evidence_anchor_match
    )
    should_promote = native_rank_strong and coordinate_supported and scenario_gap_only
    pressure_decision = "promote_to_supported" if should_promote else ("confirm_reject" if reject_reasons else "ordinary_qualified")
    support_status = "supported" if should_promote else ("unsupported" if reject_reasons else "supported")
    candidate_status = "candidate_needs_pressure" if should_promote else ("reject_confirmed" if reject_reasons else "retained")
    return {
        "candidate_status_before_pressure": candidate_status,
        "pressure_decision": pressure_decision,
        "support_status": support_status,
        "matched_evidence_terms": matched_evidence_terms,
        "missing_evidence_terms": missing_evidence_terms[:20],
        "matched_scenario_terms": [term for term in covered if term in set(question_anchor_split.get("scenario_terms") or [])],
        "missing_scenario_terms": missing_scenario_terms[:20],
        "pressure_trigger": {
            "strong_evidence_anchor_match": strong_evidence_anchor_match,
            "scenario_gap_only": scenario_gap_only,
            "coordinate_supported": coordinate_supported,
            "native_rank_strong": native_rank_strong,
            "ambiguity_present": bool(question_anchor_split.get("ambiguity_terms")),
        },
        "pressure_receipts": {
            "no_rank_mutation": True,
            "no_answer_generation": True,
            "no_raw_doc_guessing": True,
            "no_dataset_state_mutation": True,
            "citations_used": [str(candidate.get("citation"))] if candidate.get("citation") else [],
            "coordinates_used": [{
                "file_path": str(candidate.get("file_path")),
                "line_start": candidate.get("line_start"),
                "line_end": candidate.get("line_end"),
            }] if candidate.get("file_path") else [],
        },
    }

def split_question_anchors_for_pressure(question: str, required_terms: list[str]) -> dict[str, list[str]]:
    required = set(required_terms)
    proper_name_terms: list[str] = []
    for match in re.finditer(r"\b[A-Z][a-zA-Z']+\b", question):
        word = match.group(0)
        if match.start() == 0:
            continue
        anchors = [anchor for anchor in anchorize(word) if anchor in required]
        for anchor in anchors:
            if anchor not in proper_name_terms:
                proper_name_terms.append(anchor)
    ambiguity_terms = [term for term in required_terms if len(term) <= 3 and term not in proper_name_terms]
    evidence_bearing_terms = [term for term in required_terms if term not in set(proper_name_terms)]
    return {
        "scenario_terms": proper_name_terms,
        "evidence_bearing_terms": evidence_bearing_terms,
        "ambiguity_terms": ambiguity_terms,
    }

def significant_question_terms(anchors: list[str]) -> list[str]:
    low_value = GLUE_ANCHORS | {
        "answer", "ask", "asked", "claim", "data", "dataset", "describe", "described",
        "evidence", "find", "found", "give", "local", "provide", "question", "row",
        "section", "show", "staged", "under", "value", "was", "were",
    }
    out: list[str] = []
    seen: set[str] = set()
    for anchor in anchors:
        if anchor in low_value:
            continue
        if anchor_kind(anchor) not in {"content", "relation"}:
            continue
        if anchor not in seen:
            out.append(anchor)
            seen.add(anchor)
    return out

def is_heading_only(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    lines = [line.strip() for line in stripped.splitlines() if line.strip()]
    return len(lines) == 1 and (lines[0].startswith("#") or len(lines[0]) <= 80)

def is_broad_heading(text: str) -> bool:
    stripped = text.strip().strip("#*` ").casefold()
    broad = {
        "conclusion", "discussion", "implemented", "next steps", "governance",
        "overview", "summary", "background", "results", "methods", "user upload",
        "what it opens", "citation integration", "citations pane",
    }
    return stripped in broad or stripped.startswith(("implemented", "next steps"))

def has_path_or_config_intent(question: str) -> bool:
    q = question.casefold()
    return any(word in q for word in ("path", "config", "endpoint", "api", "route", "url", "file"))

def contains_unqualified_slash_phrase(text: str) -> bool:
    return bool(re.search(r"\b[a-zA-Z]{2,}/[a-zA-Z]{2,}\b", text))

def contains_true_path_or_endpoint(text: str) -> bool:
    patterns = [
        r"[A-Za-z]:\\",
        r"[/\\][A-Za-z0-9_.-]+[/\\]",
        r"\bapi/[A-Za-z0-9_./{}-]+",
        r"/api/[A-Za-z0-9_./{}-]+",
        r"\b[A-Za-z0-9_.-]+\.(json|toml|yaml|yml|py|md|txt|csv)\b",
    ]
    return any(re.search(pattern, text) for pattern in patterns)

