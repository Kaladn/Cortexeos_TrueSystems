from __future__ import annotations

from awrag.engine.evidence_formula import build_topk_pressure_trellis, score_evidence_formula


def test_formula_rewards_bridge_and_penalizes_missing_required() -> None:
    row = {
        "question_evidence_cross_classification": {
            "matched_anchors": ["juror", "excuse"],
            "missing_question_anchors": ["judge"],
        },
        "bridge_conflict_gap_status": {"status": "bridge_possible", "conflict_count": 0},
        "local_recount": {"juror": 3, "excuse": 2},
        "citation": "rule.md",
    }

    score = score_evidence_formula(row)

    assert 0.0 <= score["support_score"] <= 1.0
    assert score["components"]["bridge_strength"] > 0
    assert score["components"]["missing_required_anchor_penalty"] > 0
    assert score["diagnostic_only"] is True


def test_formula_penalizes_conflicts_and_stays_bounded() -> None:
    row = {
        "question_evidence_cross_classification": {
            "matched_anchors": ["court"],
            "missing_question_anchors": ["exception", "duty", "authority"],
        },
        "bridge_conflict_gap_status": {"status": "gap", "conflict_count": 5},
        "local_recount": {},
        "citation": None,
    }

    score = score_evidence_formula(row)

    assert 0.0 <= score["support_score"] <= 1.0
    assert score["components"]["contradiction_pressure"] > 0
    assert score["components"]["citation_pressure"] == 0.0


def test_topk_pressure_trellis_selects_mixed_rank_path_from_pressure() -> None:
    positions = [
        [
            {"anchor": "alpha", "rank": 1, "admitted": True, "source_supported": True, "question_pressure": 0.2},
            {"anchor": "counts", "rank": 2, "admitted": True, "source_supported": True, "question_pressure": 0.9},
        ],
        [
            {"anchor": "random", "rank": 1, "admitted": True, "source_supported": True, "question_pressure": 0.1},
            {"anchor": "citations", "rank": 2, "admitted": True, "source_supported": True, "question_pressure": 0.8},
        ],
        [
            {"anchor": "retrieval", "rank": 1, "admitted": True, "source_supported": True, "question_pressure": 0.8},
            {"anchor": "noise", "rank": 2, "admitted": True, "source_supported": True, "question_pressure": 0.1},
        ],
    ]
    edge_counts = {
        ("counts", "citations", 1): 20,
        ("citations", "retrieval", 1): 20,
        ("alpha", "random", 1): 2,
        ("random", "noise", 1): 2,
    }
    total_counts = {
        "counts": 20,
        "citations": 20,
        "alpha": 20,
        "random": 20,
    }

    result = build_topk_pressure_trellis(
        positions,
        question_anchors=["counts", "citations", "retrieval"],
        edge_counts=edge_counts,
        total_counts=total_counts,
        future_window=2,
    )

    assert result["schema"] == "awear_topk_pressure_trellis@1"
    assert result["role"] == "speech_output_trellis"
    assert [step["anchor"] for step in result["chosen_path"]] == ["counts", "citations", "retrieval"]
    assert [step["rank"] for step in result["chosen_path"]] == [2, 2, 1]
    assert result["receipt"]["speech_path_selection"] is True
    assert result["receipt"]["no_answer_generation"] is False
    assert result["receipt"]["no_ranking_mutation"] is True


def test_topk_pressure_trellis_hard_rejects_unsupported_candidates() -> None:
    positions = [
        [
            {
                "anchor": "unsupported",
                "rank": 1,
                "admitted": False,
                "source_supported": False,
                "question_pressure": 1.0,
            },
            {
                "anchor": "supported",
                "rank": 2,
                "admitted": True,
                "source_supported": True,
                "question_pressure": 0.2,
            },
        ]
    ]

    result = build_topk_pressure_trellis(positions, question_anchors=["unsupported", "supported"])

    assert [step["anchor"] for step in result["chosen_path"]] == ["supported"]
    assert result["steps"][0]["rejected_candidates"][0]["anchor"] == "unsupported"
    assert "not_admitted_evidence" in result["steps"][0]["rejected_candidates"][0]["hard_reject_reasons"]
