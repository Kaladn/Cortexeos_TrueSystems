from __future__ import annotations

import math
from typing import Any


def score_evidence_formula(row: dict[str, Any]) -> dict[str, Any]:
    cross = row.get("question_evidence_cross_classification") or {}
    bridge = row.get("bridge_conflict_gap_status") or {}
    recount = row.get("local_recount") or {}
    matched = len(cross.get("matched_anchors") or [])
    missing = len(cross.get("missing_question_anchors") or [])
    conflicts = int(bridge.get("conflict_count") or 0)

    evidence_anchor_strength = min(0.35, matched * 0.08)
    citation_pressure = 0.15 if row.get("citation") else 0.0
    local_field_coherence = min(0.2, len(recount) * 0.01)
    bridge_strength = 0.15 if bridge.get("status") in {"bridge_possible", "direct_overlap"} else 0.0
    contradiction_pressure = min(0.35, conflicts * 0.12)
    missing_required_anchor_penalty = min(0.3, missing * 0.04)
    raw = (
        evidence_anchor_strength
        + citation_pressure
        + local_field_coherence
        + bridge_strength
        - contradiction_pressure
        - missing_required_anchor_penalty
    )

    return {
        "schema": "truemem_evidence_formula_score@1",
        "support_score": round(max(0.0, min(1.0, raw)), 4),
        "components": {
            "evidence_anchor_strength": round(evidence_anchor_strength, 4),
            "citation_pressure": round(citation_pressure, 4),
            "local_field_coherence": round(local_field_coherence, 4),
            "bridge_strength": round(bridge_strength, 4),
            "contradiction_pressure": round(contradiction_pressure, 4),
            "missing_required_anchor_penalty": round(missing_required_anchor_penalty, 4),
        },
        "diagnostic_only": True,
    }


def build_topk_pressure_trellis(
    positions: list[list[dict[str, Any]]],
    *,
    question_anchors: list[str] | None = None,
    open_gaps: list[str] | None = None,
    edge_counts: dict[tuple[str, str, int], int] | None = None,
    total_counts: dict[str, int] | None = None,
    lifetime_edge_counts: dict[tuple[str, str, int], int] | None = None,
    lifetime_total_counts: dict[str, int] | None = None,
    future_window: int = 6,
    local_weight: float = 0.75,
    lifetime_weight: float = 0.25,
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Choose a diagnostic path through TopK anchor choices without mutating ranking.

    This is a bounded sidecar formula. It treats each position as a choice lattice,
    rejects unsupported candidates before scoring, then chooses the path that best
    preserves rear coherence, present fit, question pressure, gap closure, and
    forward viability.
    """
    q = {str(anchor) for anchor in (question_anchors or []) if str(anchor)}
    gaps = {str(gap) for gap in (open_gaps or []) if str(gap)}
    local_edges = edge_counts or {}
    local_totals = total_counts or {}
    life_edges = lifetime_edge_counts or {}
    life_totals = lifetime_total_counts or {}
    score_weights = {
        "present": 1.0,
        "rear": 0.8,
        "forward": 0.7,
        "question": 1.0,
        "gap": 0.7,
        "drift": 0.8,
        "redundancy": 0.4,
    }
    if weights:
        score_weights.update({key: float(value) for key, value in weights.items() if key in score_weights})

    chosen: list[dict[str, Any]] = []
    steps: list[dict[str, Any]] = []
    for position_index, raw_candidates in enumerate(positions):
        candidates, rejected = _partition_trellis_candidates(raw_candidates)
        scored = [
            _score_trellis_candidate(
                candidate,
                position_index=position_index,
                history=chosen,
                future_positions=positions[position_index + 1 : position_index + 1 + max(0, int(future_window))],
                question_anchors=q,
                open_gaps=gaps,
                edge_counts=local_edges,
                total_counts=local_totals,
                lifetime_edge_counts=life_edges,
                lifetime_total_counts=life_totals,
                local_weight=local_weight,
                lifetime_weight=lifetime_weight,
                weights=score_weights,
            )
            for candidate in candidates
        ]
        scored.sort(key=lambda row: (row["score"], -int(row.get("rank") or 999999), row["anchor"]), reverse=True)
        selected = scored[0] if scored else None
        if selected:
            chosen.append(selected)
            gaps.difference_update(set(selected.get("closes_gaps") or []))
        steps.append(
            {
                "position_index": position_index,
                "candidate_count": len(raw_candidates),
                "eligible_count": len(candidates),
                "rejected_candidates": rejected,
                "scored_candidates": scored,
                "selected": selected,
            }
        )

    return {
        "schema": "truemem_topk_pressure_trellis@1",
        "role": "speech_output_trellis",
        "walk_name": "616_topk_pressure_walk",
        "choice_model": "choice_lattice_not_rank_lane",
        "chosen_path": chosen,
        "steps": steps,
        "weights": score_weights,
        "receipt": {
            "speech_path_selection": True,
            "diagnostic_only": False,
            "no_answer_generation": False,
            "no_model_reasoning": True,
            "no_retrieval": True,
            "no_citation_creation": True,
            "no_ranking_mutation": True,
            "no_dataset_mutation": True,
            "hard_gates_before_score": True,
        },
    }


def _partition_trellis_candidates(candidates: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    eligible: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for raw in candidates:
        candidate = dict(raw)
        reasons = _hard_reject_reasons(candidate)
        if reasons:
            candidate["hard_reject_reasons"] = reasons
            rejected.append(candidate)
        else:
            eligible.append(candidate)
    return eligible, rejected


def _hard_reject_reasons(candidate: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if candidate.get("admitted") is False:
        reasons.append("not_admitted_evidence")
    if candidate.get("source_supported") is False:
        reasons.append("no_source_support")
    if candidate.get("unsupported_modality_drift") is True:
        reasons.append("unsupported_modality_or_scope_drift")
    if candidate.get("contradicts_committed_support") is True and not candidate.get("repairs_contradiction"):
        reasons.append("unrepaired_contradiction")
    return reasons


def _score_trellis_candidate(
    candidate: dict[str, Any],
    *,
    position_index: int,
    history: list[dict[str, Any]],
    future_positions: list[list[dict[str, Any]]],
    question_anchors: set[str],
    open_gaps: set[str],
    edge_counts: dict[tuple[str, str, int], int],
    total_counts: dict[str, int],
    lifetime_edge_counts: dict[tuple[str, str, int], int],
    lifetime_total_counts: dict[str, int],
    local_weight: float,
    lifetime_weight: float,
    weights: dict[str, float],
) -> dict[str, Any]:
    anchor = _candidate_anchor(candidate)
    present = _present_fit(candidate)
    rear = _rear_coherence(anchor, history, edge_counts, total_counts, lifetime_edge_counts, lifetime_total_counts, local_weight, lifetime_weight)
    question = _question_pressure(candidate, anchor, question_anchors)
    gap, closes = _gap_closure(candidate, anchor, open_gaps)
    forward = _forward_viability(
        anchor,
        future_positions,
        question_anchors,
        open_gaps,
        edge_counts,
        total_counts,
        lifetime_edge_counts,
        lifetime_total_counts,
        local_weight,
        lifetime_weight,
    )
    drift = _drift_penalty(candidate, history, question, forward)
    redundancy = _redundancy_penalty(anchor, history)
    score = (
        weights["present"] * present
        + weights["rear"] * rear
        + weights["forward"] * forward
        + weights["question"] * question
        + weights["gap"] * gap
        - weights["drift"] * drift
        - weights["redundancy"] * redundancy
    )
    return {
        "anchor": anchor,
        "rank": int(candidate.get("rank") or position_index + 1),
        "position_index": position_index,
        "score": round(score, 6),
        "components": {
            "present_fit": round(present, 6),
            "rear_coherence": round(rear, 6),
            "forward_viability": round(forward, 6),
            "question_pressure": round(question, 6),
            "gap_closure": round(gap, 6),
            "drift_penalty": round(drift, 6),
            "redundancy_penalty": round(redundancy, 6),
        },
        "closes_gaps": closes,
        "source": candidate,
    }


def _candidate_anchor(candidate: dict[str, Any]) -> str:
    return str(candidate.get("anchor") or candidate.get("symbol") or candidate.get("text") or "")


def _present_fit(candidate: dict[str, Any]) -> float:
    support = _float(candidate.get("anchor_support_strength"), 0.0)
    citation = _float(candidate.get("citation_support_strength"), 0.0)
    admission = _float(candidate.get("packet_admission_strength"), 1.0 if candidate.get("admitted", True) else 0.0)
    position = _float(candidate.get("position_need_fit"), 0.0)
    source = 1.0 if candidate.get("source_supported", True) else 0.0
    return min(1.0, 0.25 * support + 0.2 * citation + 0.25 * admission + 0.2 * position + 0.1 * source)


def _rear_coherence(
    anchor: str,
    history: list[dict[str, Any]],
    edge_counts: dict[tuple[str, str, int], int],
    total_counts: dict[str, int],
    lifetime_edge_counts: dict[tuple[str, str, int], int],
    lifetime_total_counts: dict[str, int],
    local_weight: float,
    lifetime_weight: float,
) -> float:
    score = 0.0
    for distance, previous in enumerate(reversed(history[-6:]), start=1):
        previous_anchor = str(previous.get("anchor") or "")
        score += (1.0 / distance) * _blended_edge_pressure(
            previous_anchor,
            anchor,
            distance,
            edge_counts,
            total_counts,
            lifetime_edge_counts,
            lifetime_total_counts,
            local_weight,
            lifetime_weight,
        )
    return score


def _forward_viability(
    anchor: str,
    future_positions: list[list[dict[str, Any]]],
    question_anchors: set[str],
    open_gaps: set[str],
    edge_counts: dict[tuple[str, str, int], int],
    total_counts: dict[str, int],
    lifetime_edge_counts: dict[tuple[str, str, int], int],
    lifetime_total_counts: dict[str, int],
    local_weight: float,
    lifetime_weight: float,
) -> float:
    if not future_positions:
        return 0.0
    frontier = {anchor: 0.0}
    for depth, raw_candidates in enumerate(future_positions[:6], start=1):
        candidates, _ = _partition_trellis_candidates(raw_candidates)
        if not candidates:
            continue
        next_frontier: dict[str, float] = {}
        for previous_anchor, previous_score in frontier.items():
            for candidate in candidates:
                candidate_anchor = _candidate_anchor(candidate)
                transition = _blended_edge_pressure(
                    previous_anchor,
                    candidate_anchor,
                    1,
                    edge_counts,
                    total_counts,
                    lifetime_edge_counts,
                    lifetime_total_counts,
                    local_weight,
                    lifetime_weight,
                )
                q_pressure = _question_pressure(candidate, candidate_anchor, question_anchors)
                gap, _ = _gap_closure(candidate, candidate_anchor, open_gaps)
                drift = max(0.0, 0.35 - q_pressure)
                weighted = (1.0 / depth) * (transition + q_pressure + gap - drift)
                next_frontier[candidate_anchor] = max(next_frontier.get(candidate_anchor, float("-inf")), previous_score + weighted)
        frontier = next_frontier
    return max(frontier.values()) if frontier else 0.0


def _question_pressure(candidate: dict[str, Any], anchor: str, question_anchors: set[str]) -> float:
    explicit = candidate.get("question_pressure")
    if explicit is not None:
        return max(0.0, min(1.0, _float(explicit, 0.0)))
    if not question_anchors:
        return 0.0
    if anchor in question_anchors:
        return 1.0
    related = {str(value) for value in candidate.get("related_question_anchors") or []}
    return min(1.0, len(related & question_anchors) / max(1, len(question_anchors)))


def _gap_closure(candidate: dict[str, Any], anchor: str, open_gaps: set[str]) -> tuple[float, list[str]]:
    if not open_gaps:
        return 0.0, []
    closes = {str(value) for value in candidate.get("closes_gaps") or []}
    if anchor in open_gaps:
        closes.add(anchor)
    matched = sorted(closes & open_gaps)
    weights = candidate.get("gap_weights") if isinstance(candidate.get("gap_weights"), dict) else {}
    score = sum(_float(weights.get(gap), 1.0) for gap in matched)
    return min(1.0, score), matched


def _drift_penalty(candidate: dict[str, Any], history: list[dict[str, Any]], question_pressure: float, forward_viability: float) -> float:
    if candidate.get("topic_branch") is True:
        branch = 0.35
    else:
        branch = 0.0
    field_shift = _float(candidate.get("unsupported_field_shift"), 0.0)
    previous_alignment = sum(_float(row.get("components", {}).get("question_pressure"), 0.0) for row in history[-3:]) / max(1, min(3, len(history)))
    projected_alignment = (question_pressure + max(0.0, min(1.0, forward_viability))) / 2
    return max(0.0, previous_alignment - projected_alignment) + field_shift + branch


def _redundancy_penalty(anchor: str, history: list[dict[str, Any]]) -> float:
    return min(1.0, sum(1 for row in history[-6:] if str(row.get("anchor") or "") == anchor) * 0.35)


def _blended_edge_pressure(
    x: str,
    y: str,
    offset: int,
    edge_counts: dict[tuple[str, str, int], int],
    total_counts: dict[str, int],
    lifetime_edge_counts: dict[tuple[str, str, int], int],
    lifetime_total_counts: dict[str, int],
    local_weight: float,
    lifetime_weight: float,
) -> float:
    local = _edge_pressure(x, y, offset, edge_counts, total_counts)
    lifetime = _edge_pressure(x, y, offset, lifetime_edge_counts, lifetime_total_counts)
    if local == 0.0:
        return lifetime
    return local_weight * local + lifetime_weight * lifetime


def _edge_pressure(x: str, y: str, offset: int, edge_counts: dict[tuple[str, str, int], int], total_counts: dict[str, int]) -> float:
    count = edge_counts.get((x, y, offset), 0)
    total = total_counts.get(x, 0)
    if count <= 0 or total <= 0:
        return 0.0
    return math.log1p(count) / math.log1p(total)


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
