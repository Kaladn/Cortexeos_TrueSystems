"""Experimental, decomposed syntax-support measurements for 6-1-6 code clouds."""

from __future__ import annotations

from typing import Any

from truemem.engine.context_clouds import score_context_cloud_lane


def score_code_cloud_lane(
    *,
    center_anchor_kind: str,
    signed_offset: int,
    accepted_edge_count: int,
    rejected_edge_count: int,
    accepted_center_count: int,
    rejected_center_count: int,
    beta_prior: float = 1.0,
) -> dict[str, Any]:
    """Score parser-acceptance association, never behavioral correctness."""

    generic = score_context_cloud_lane(
        center_anchor_kind=center_anchor_kind,
        signed_offset=signed_offset,
        positive_edge_count=accepted_edge_count,
        negative_edge_count=rejected_edge_count,
        positive_center_count=accepted_center_count,
        negative_center_count=rejected_center_count,
        beta_prior=beta_prior,
        label_contract={
            "outcome_name": "python_parser_acceptance",
            "positive_label": "PYTHON_AST_PARSED",
            "negative_label": "PYTHON_SYNTAX_ERROR",
            "authority": "python_stdlib_ast_parser_observation",
            "correctness_authority": False,
        },
    )
    return {"schema": "truesystems_code_cloud_lane_score@1", **{key: value for key, value in generic.items() if key != "schema"}}
