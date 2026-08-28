from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from awrag.engine.pressure_probe import clean_pressure_hypothesis_question, run_pressure_probe


def test_clean_pressure_hypothesis_question_strips_probe_meta_terms() -> None:
    question = "What nearby cited passage clarifies excuse, has, juror around [AWCIT-3db1fffb7b]?"

    cleaned = clean_pressure_hypothesis_question(question)

    assert cleaned == "excuse has juror"
    for meta in ("nearby", "cited", "passage", "clarifies", "around", "AWCIT"):
        assert meta.casefold() not in cleaned.casefold()


def _write_packet(path: Path, *, question: str = "Can a judge excuse a juror?") -> None:
    path.write_text(
        json.dumps({
            "schema": "awrag_query_result@1",
            "dataset_id": "unit",
            "question": question,
            "question_anchors": ["judge", "excuse", "juror"],
            "model_used": "none",
            "model_may_search": False,
            "answer_packet": {
                "qualification": {"support_state": "qualified_evidence"},
                "locations": [
                    {
                        "citation": "[AWCIT-1]",
                        "file_path": "1.2-c2-s2.md",
                        "line_start": 10,
                        "line_end": 12,
                        "block_ordinal": 7,
                        "score": 42.0,
                        "density_score": 6.0,
                        "direct_hit_count": 6,
                        "text": "TEXT: The court may excuse a juror from serving on a jury in a trial.",
                        "qualification": {
                            "matched_evidence_terms": ["court", "excuse", "juror", "serving", "jury", "trial"],
                            "missing_evidence_terms": ["judge"],
                            "missing_scenario_terms": ["bob", "ted"],
                            "pressure_decision": "ordinary_qualified",
                        },
                    }
                ],
                "rejected_locations": [
                    {
                        "citation": "[AWCIT-R]",
                        "text": "TEXT: A different candidate mentions jury service.",
                        "qualification": {
                            "candidate_status_before_pressure": "candidate_needs_pressure",
                            "pressure_decision": "pressure_inspection_needed",
                            "matched_evidence_terms": ["jury", "service"],
                        },
                    }
                ],
            },
            "final_answer": {
                "status": "answered_from_awrag_locations",
                "text": "The court may excuse a juror. [AWCIT-1]",
                "citations": ["[AWCIT-1]"],
                "model_used": "none",
                "model_may_search": False,
            },
        }),
        encoding="utf-8",
    )


def test_pressure_probe_builds_bounded_followups_from_admitted_evidence(tmp_path: Path) -> None:
    packet = tmp_path / "query.json"
    _write_packet(packet)

    out = tmp_path / "pressure_probe"
    result = run_pressure_probe(packet_paths=[packet], out_dir=out, max_questions_per_packet=4)

    assert result["schema"] == "awrag_pressure_probe_run@0"
    assert result["records_processed"] == 1
    assert result["probe_question_count"] == 4
    assert result["hypotheses_jsonl_path"].endswith("PRESSURE_HYPOTHESES.jsonl")
    assert result["retrieval_ran"] is False
    assert result["topk_ran"] is False
    assert result["intake_ran"] is False
    assert result["ranking_mutation"] is False
    assert result["dataset_mutation"] is False
    assert result["model_used"] == "none"
    assert result["input_mutation_detected"] is False

    questions = [
        json.loads(line)
        for line in Path(result["questions_jsonl_path"]).read_text(encoding="utf-8").splitlines()
    ]
    hypotheses = [
        json.loads(line)
        for line in Path(result["hypotheses_jsonl_path"]).read_text(encoding="utf-8").splitlines()
    ]
    assert hypotheses == questions
    assert [row["probe_index"] for row in questions] == [1, 2, 3, 4]
    assert all(row["source_citation"] == "[AWCIT-1]" for row in questions)
    assert all(row["source_packet_path"] == str(packet.resolve()) for row in questions)
    assert any("court, excuse, juror" in row["question"] for row in questions)
    assert any("judge" in row["question"] for row in questions)
    assert any(row["probe_type"] == "scenario_gap_pressure" for row in questions)
    assert all(row["clean_question"] for row in questions)
    assert all("[AWCIT-" not in row["clean_question"] for row in questions)
    bridge = next(row for row in questions if row["probe_type"] == "missing_evidence_bridge")
    assert bridge["question"] == "Does the cited evidence connect court, excuse, juror to judge?"
    assert bridge["clean_question"] == "court excuse juror serving jury"
    assert "judge" not in bridge["clean_question"]
    assert bridge["missing_evidence_terms"] == ["judge"]
    assert all(row["bounded_depth"] == 1 for row in questions)

    receipt = json.loads((out / "receipts" / "run_receipt.json").read_text(encoding="utf-8"))
    assert receipt["source"] == "existing_awrag_query_packets"
    assert receipt["no_answer_generation"] is True
    assert receipt["no_answer_key_leakage"] is True


def test_pressure_probe_can_load_packets_from_batch_summary(tmp_path: Path) -> None:
    packet = tmp_path / "query.json"
    _write_packet(packet, question="What is the jury service rule?")
    batch = tmp_path / "batch_run_summary.json"
    batch.write_text(
        json.dumps({
            "schema": "awrag_batch_run_summary@1",
            "output_paths": [str(packet)],
            "question_results": [{"status": "completed", "output_path": str(packet)}],
        }),
        encoding="utf-8",
    )

    result = run_pressure_probe(batch_summary_path=batch, out_dir=tmp_path / "probe", max_questions_per_packet=2)

    assert result["records_processed"] == 1
    assert result["probe_question_count"] == 2
    assert result["batch_summary_path"] == str(batch.resolve())


def test_pressure_probe_cli_command(tmp_path: Path) -> None:
    packet = tmp_path / "query.json"
    _write_packet(packet)
    out = tmp_path / "cli_probe"

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "awrag.cli",
            "pressure-probe",
            "--packet",
            str(packet),
            "--out",
            str(out),
            "--max-questions-per-packet",
            "3",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(proc.stdout)
    assert payload["records_processed"] == 1
    assert payload["probe_question_count"] == 3
    assert Path(payload["summary_path"]).is_file()
    assert Path(payload["questions_jsonl_path"]).is_file()
