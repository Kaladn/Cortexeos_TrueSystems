from __future__ import annotations

import json
from pathlib import Path

from truemem.agents.pressure_coordination import run_pressure_coordination_audit


def _write_trace(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")


def test_pressure_coordination_writes_real_reaper_and_combined_lanes(tmp_path: Path) -> None:
    trace_path = tmp_path / "reverse_trace.jsonl"
    _write_trace(
        trace_path,
        [
            {
                "schema": "truemem_answer_reasoning_reverse_walk_trace@0",
                "claim_id": "q1",
                "question": "Can the juror be excused?",
                "supplied_answer": "A juror may be excused when the rule applies.",
                "support_decision": "unsupported",
                "answer_to_candidate_coverage": 0.86,
                "candidate_to_question_coverage": 0.78,
                "bridge_needed": False,
                "candidate_citations": ["[TMCIT-1]"],
                "reverse_topK_candidates": [
                    {
                        "citation": "[TMCIT-1]",
                        "file_path": "corpus/rule.md",
                        "answer_to_candidate_coverage": 0.86,
                        "candidate_to_question_coverage": 0.78,
                        "local_neighborhood_blocks": [{"text": "nearby support"}],
                        "pressure_links": [{"anchor": "juror", "observations": 5}],
                        "missing_question_anchors": ["bob"],
                        "matched_question_anchors": ["juror", "excused"],
                    }
                ],
                "no_mutation_receipt": {"no_dataset_mutation": True},
            }
        ],
    )
    before = trace_path.read_bytes()

    result = run_pressure_coordination_audit(trace_path=trace_path, out_dir=tmp_path / "out")

    assert trace_path.read_bytes() == before
    assert result["schema"] == "truemem_pressure_coordination_audit_run@0"
    assert result["records_processed"] == 1
    assert result["input_mutation_detected"] is False

    real_rows = _read_jsonl(Path(result["real_system_trace_path"]))
    reaper_rows = _read_jsonl(Path(result["reaper_pressure_trace_path"]))
    combined_rows = _read_jsonl(Path(result["combined_strength_trace_path"]))

    assert real_rows[0]["real_system_decision"] == "unsupported"
    assert reaper_rows[0]["reaper_pressure_decision"] == "supported"
    assert reaper_rows[0]["reaper_mutation_scope"] == "special_file_only"
    assert combined_rows[0]["real_system_decision"] == "unsupported"
    assert combined_rows[0]["reaper_pressure_decision"] == "supported"
    assert combined_rows[0]["combined_decision"] in {"partially_supported", "needs_bridge"}


def test_pressure_coordination_cli(tmp_path: Path) -> None:
    from truemem.cli import main
    import sys

    trace_path = tmp_path / "trace.jsonl"
    _write_trace(
        trace_path,
        [
            {
                "claim_id": "q2",
                "question": "What rule applies?",
                "supplied_answer": "The cited rule applies.",
                "support_decision": "needs_bridge",
                "answer_to_candidate_coverage": 0.62,
                "candidate_to_question_coverage": 0.58,
                "bridge_needed": True,
                "candidate_citations": ["[TMCIT-2]"],
                "reverse_topK_candidates": [],
            }
        ],
    )
    out = tmp_path / "coordination"
    argv = [
        "truemem",
        "pressure-coordination-audit",
        "--trace",
        str(trace_path),
        "--out",
        str(out),
    ]
    old_argv = sys.argv
    try:
        sys.argv = argv
        main()
    finally:
        sys.argv = old_argv

    assert (out / "PRESSURE_COORDINATION_SUMMARY.json").exists()
    assert (out / "real_system_as_is" / "REAL_SYSTEM_TRACE.jsonl").exists()
    assert (out / "reaper_only" / "REAPER_PRESSURE_MUTATION_TRACE.jsonl").exists()
    assert (out / "combined_strengths" / "COMBINED_STRENGTH_TRACE.jsonl").exists()


def test_needs_bridge_caps_reaper_support_when_bridge_answerability_is_weak(tmp_path: Path) -> None:
    trace_path = tmp_path / "weak_bridge_trace.jsonl"
    _write_trace(
        trace_path,
        [
            {
                "claim_id": "q_bridge",
                "question": "How do two fields connect?",
                "supplied_answer": "The supplied answer needs a bridge.",
                "support_decision": "needs_bridge",
                "answer_to_candidate_coverage": 0.9,
                "candidate_to_question_coverage": 0.86,
                "bridge_needed": True,
                "candidate_citations": ["[TMCIT-B]"],
                "reverse_topK_candidates": [
                    {
                        "citation": "[TMCIT-B]",
                        "answer_to_candidate_coverage": 0.9,
                        "candidate_to_question_coverage": 0.86,
                        "local_neighborhood_blocks": [],
                        "pressure_links": [],
                        "matched_question_anchors": ["fields"],
                        "missing_question_anchors": ["connect"],
                    }
                ],
            }
        ],
    )

    result = run_pressure_coordination_audit(trace_path=trace_path, out_dir=tmp_path / "out")
    reaper_rows = _read_jsonl(Path(result["reaper_pressure_trace_path"]))

    assert reaper_rows[0]["bridge_answerability_score"] < 0.72
    assert reaper_rows[0]["reaper_pressure_decision"] == "needs_bridge"
    assert reaper_rows[0]["promotion_cap"] == "needs_bridge"


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
