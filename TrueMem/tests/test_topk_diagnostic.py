from __future__ import annotations

import json
from pathlib import Path

from truemem.engine.topk_diagnostic import build_rank_layer_walk, build_topk_diagnostic_packet, write_topk_ladder_outputs


def test_topk_diagnostic_preserves_passages_and_refuses_nothing() -> None:
    packet = {
        "question": "What excuses a juror from serving?",
        "answer_packet": {
            "locations": [
                {
                    "rank": 1,
                    "citation": "rule-1.md",
                    "text": "A juror may be excused from serving if disqualified by law.",
                    "qualification": {"support_state": "unsupported"},
                }
            ],
            "speech": {"answer": "Existing speech attempt."},
        },
    }

    result = build_topk_diagnostic_packet(packet, max_rank=5)

    assert result["schema"] == "truemem_topk_diagnostic_packet@1"
    assert result["diagnostic_mode"] == "no_refusal"
    assert result["truth_status"] == "diagnostic_not_final_truth"
    assert result["topk_results"][0]["original_passage"] == "A juror may be excused from serving if disqualified by law."
    assert result["topk_results"][0]["rank"] == 1
    assert result["topk_results"][0]["source_support_state"] == "unsupported"
    assert result["topk_results"][0]["evidence_formula_score"]["diagnostic_only"] is True
    assert "juror" in result["question_anchor_classification"]["all_anchors"]
    assert "typed_anchors" in result["topk_results"][0]["evidence_anchor_classification"]
    assert result["receipt"]["no_refusal"] is True


def test_rank_layer_walk_runs_across_questions_by_rank() -> None:
    packets = [
        {
            "question": "Q1 juror excuse",
            "answer_packet": {"locations": [{"rank": 1, "text": "juror excuse"}, {"rank": 2, "text": "jury service"}]},
        },
        {
            "question": "Q2 court rule",
            "answer_packet": {"locations": [{"rank": 1, "text": "court rule"}, {"rank": 2, "text": "judge order"}]},
        },
    ]

    result = build_rank_layer_walk(packets, max_rank=2)

    assert [row["question_index"] for row in result["layers"][1]] == [1, 2]
    assert [row["rank"] for row in result["layers"][1]] == [1, 1]
    assert [row["question_index"] for row in result["layers"][2]] == [1, 2]
    assert [row["rank"] for row in result["layers"][2]] == [2, 2]
    assert result["layers"][1][0]["answer_starter_with_subject"].startswith("For")


def test_topk_diagnostic_walks_rejected_candidates_when_no_locations() -> None:
    packet = {
        "question": "juror judge jury excuse",
        "answer_packet": {
            "locations": [],
            "rejected_locations": [
                {
                    "citation": "reject-1.md",
                    "text": "The court must ask whether any people on the jury panel seek to be excused.",
                    "qualification": {"support_state": "rejected"},
                }
            ],
        },
    }

    result = build_topk_diagnostic_packet(packet, max_rank=5)

    assert result["topk_results"][0]["citation"] == "reject-1.md"
    assert result["topk_results"][0]["source_candidate_lane"] == "rejected_locations"
    assert result["topk_results"][0]["rank"] == 1


def test_write_topk_ladder_outputs_writes_layer_files(tmp_path: Path) -> None:
    walk = build_rank_layer_walk(
        [
            {
                "question": "Q1 juror excuse",
                "answer_packet": {"locations": [{"rank": 1, "text": "juror excuse", "citation": "a.md"}]},
            }
        ],
        max_rank=2,
    )

    result = write_topk_ladder_outputs(walk, tmp_path)

    assert Path(result["summary_path"]).exists()
    assert (tmp_path / "rank_layers" / "TOPK_LAYER_1.jsonl").exists()
    assert (tmp_path / "rank_layers" / "TOPK_LAYER_2.jsonl").exists()
    layer_rows = [
        json.loads(line)
        for line in (tmp_path / "rank_layers" / "TOPK_LAYER_1.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert layer_rows[0]["citation"] == "a.md"
