"""System-wide exact 6-1-6 context clouds and outcome-scoring preparation."""

from __future__ import annotations

import math
from typing import Any

from .anchors import anchor_kind
from .base import sha1_text


SIGNED_LANES = (*range(-6, 0), *range(1, 7))
DEFAULT_KIND_WEIGHTS = {"content": 1.0, "relation": 0.5, "object": 0.65, "glue": 0.0, "boundary": 0.0}


def build_context_cloud(
    anchors: list[str],
    center_position: int,
    *,
    occurrence_identity: str,
    source_ref: dict[str, Any],
    radius: int = 6,
) -> dict[str, Any]:
    """Return one exact occurrence cloud without inventing semantic edges."""

    if radius != 6:
        raise ValueError("active TrueMem context clouds require radius 6")
    if not 0 <= center_position < len(anchors):
        raise IndexError(center_position)
    center = anchors[center_position]
    lanes = []
    for offset in SIGNED_LANES:
        position = center_position + offset
        if 0 <= position < len(anchors):
            neighbor = anchors[position]
            lanes.append({
                "signed_offset": offset,
                "neighbor_position": position,
                "neighbor_anchor": neighbor,
                "neighbor_anchor_kind": anchor_kind(neighbor),
                "observed_adjacency": True,
                "semantic_relation_claimed": False,
            })
    identity = sha1_text(f"{occurrence_identity}\0{center_position}\0{center}")
    return {
        "schema": "truemem_context_cloud@1",
        "cloud_id": f"TMCLOUD-{identity}",
        "occurrence_identity": occurrence_identity,
        "source_ref": dict(source_ref),
        "center_position": center_position,
        "center_anchor": center,
        "center_anchor_kind": anchor_kind(center),
        "radius": 6,
        "lanes": lanes,
        "lane_count": len(lanes),
        "all_available_lanes_retained": True,
        "measurements_collapsed": False,
        "semantic_relation_inferred": False,
    }


def score_context_cloud_lane(
    *,
    center_anchor_kind: str,
    signed_offset: int,
    positive_edge_count: int,
    negative_edge_count: int,
    positive_center_count: int,
    negative_center_count: int,
    label_contract: dict[str, Any],
    beta_prior: float = 1.0,
    kind_weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Measure association with a declared binary outcome; keep components separate."""

    if signed_offset not in SIGNED_LANES:
        raise ValueError("signed_offset must be in -6..-1 or +1..+6")
    values = (positive_edge_count, negative_edge_count, positive_center_count, negative_center_count)
    if any(int(value) < 0 for value in values) or beta_prior <= 0:
        raise ValueError("counts must be nonnegative and beta_prior positive")
    for field in ("outcome_name", "positive_label", "negative_label", "authority"):
        if not str(label_contract.get(field) or ""):
            raise ValueError(f"label contract missing {field}")
    weights = dict(DEFAULT_KIND_WEIGHTS)
    if kind_weights:
        if set(kind_weights) - set(weights):
            raise ValueError("unknown anchor-kind weight")
        weights.update({key: float(value) for key, value in kind_weights.items()})
    edge_total = positive_edge_count + negative_edge_count
    center_total = positive_center_count + negative_center_count
    outcome_support = (positive_edge_count + beta_prior) / (edge_total + 2.0 * beta_prior)
    center_support = (positive_center_count + beta_prior) / (center_total + 2.0 * beta_prior)
    contrast = outcome_support - center_support
    proximity = (7.0 - abs(signed_offset)) / 6.0
    kind_weight = weights[center_anchor_kind]
    sample_confidence = 1.0 - math.exp(-edge_total / 8.0)
    diagnostic_weight = kind_weight * proximity * sample_confidence * contrast
    correctness_authorized = bool(label_contract.get("correctness_authority"))
    return {
        "schema": "truemem_context_cloud_lane_score@1",
        "signed_offset": signed_offset,
        "label_contract": dict(label_contract),
        "counts": {
            "positive_edge": positive_edge_count, "negative_edge": negative_edge_count,
            "positive_center": positive_center_count, "negative_center": negative_center_count,
        },
        "components": {
            "outcome_support_score": round(outcome_support, 12),
            "center_baseline_support": round(center_support, 12),
            "outcome_contrast": round(contrast, 12),
            "distance_proximity": round(proximity, 12),
            "anchor_direction_weight": kind_weight,
            "sample_confidence": round(sample_confidence, 12),
        },
        "diagnostic_cloud_weight": round(diagnostic_weight, 12),
        "bounded_correctness_score": round(outcome_support, 12) if correctness_authorized else None,
        "correctness_score_status": "AUTHORIZED_BY_LABEL_CONTRACT" if correctness_authorized else "NOT_AUTHORIZED_OUTCOME_ASSOCIATION_ONLY",
        "diagnostic_only": not correctness_authorized,
        "components_preserved": True,
        "semantic_relation_inferred": False,
    }
