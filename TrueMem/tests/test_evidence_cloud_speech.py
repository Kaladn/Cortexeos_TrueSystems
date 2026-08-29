from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from truemem.engine.evidence_cloud_speech import run_evidence_cloud_speech


def _write_packet(path: Path) -> None:
    path.write_text(
        json.dumps({
            "schema": "truemem_query_result@1",
            "dataset_id": "unit",
            "question": "What supports alpha beta signal?",
            "question_anchors": ["what", "supports", "alpha", "beta", "signal"],
            "model_used": "none",
            "model_may_search": False,
            "answer_packet": {
                "qualification": {"support_state": "qualified_evidence"},
                "locations": [
                    {
                        "citation": "[TMCIT-low]",
                        "file_path": "source_a.md",
                        "line_start": 1,
                        "line_end": 4,
                        "score": 4.0,
                        "density_score": 1.0,
                        "direct_hit_count": 1,
                        "block_ordinal": 1,
                        "text": (
                            "DOC_ID: low-doc\n"
                            "TEXT: The appendix mentions signal noise. "
                            "A different sentence discusses unrelated hardware."
                        ),
                    },
                    {
                        "citation": "[TMCIT-strong]",
                        "file_path": "source_b.md",
                        "line_start": 20,
                        "line_end": 24,
                        "score": 18.0,
                        "density_score": 6.0,
                        "direct_hit_count": 4,
                        "block_ordinal": 2,
                        "text": (
                            "DOC_ID: strong-doc\n"
                            "TEXT: Alpha beta signal supports the verified local evidence cloud. "
                            "The block also includes unrelated trailing context."
                        ),
                    },
                ],
                "rejected_locations": [],
            },
            "final_answer": {
                "status": "answered_from_truemem_locations",
                "model_used": "none",
                "model_may_search": False,
                "citations": ["[TMCIT-strong]"],
            },
        }),
        encoding="utf-8",
    )


def test_evidence_cloud_speech_tightens_inside_packet_cloud(tmp_path: Path) -> None:
    packet = tmp_path / "packet.json"
    _write_packet(packet)

    out = tmp_path / "evidence_speech"
    result = run_evidence_cloud_speech(packet_path=packet, out_dir=out, max_passes=3)

    assert result["schema"] == "truemem_evidence_cloud_speech_run@0"
    assert result["retrieval_ran"] is False
    assert result["topk_ran"] is False
    assert result["intake_ran"] is False
    assert result["dataset_mutation"] is False
    assert result["input_mutation_detected"] is False
    assert result["model_used"] == "none"
    assert result["model_may_search"] is False
    assert result["support_level"] == "strong"
    assert result["operator_stepped"] is True
    assert result["next_action_required"] == "operator_decide_stop_continue_widen_or_reject"
    assert "Alpha beta signal supports" in str(result["answer"])
    assert result["citations"][0]["citation"] == "[TMCIT-strong]"

    trace = json.loads(Path(result["trace_path"]).read_text(encoding="utf-8"))
    assert trace["temporary_micro_map_only"] is True
    assert trace["mode"] == "evidence_cloud_boil_down"
    assert trace["operator_stepped"] is True
    assert trace["allowed_next_actions"] == ["stop", "continue", "widen", "reject"]
    assert trace["retrieval_ran"] is False
    assert trace["topk_ran"] is False
    assert len(trace["passes"]) == 1
    assert trace["passes"][0]["step_proved"] is True
    assert trace["step_comparison"]["note"] == "first proved step; no previous step to compare"
    assert trace["final_result"]["winner"]["citation"] == "[TMCIT-strong]"
    assert trace["final_result"]["winner"]["score_components"]["score_kind"] == "temporary_micro_map_score_not_native_topk"

    receipt = json.loads((out / "receipts" / "run_receipt.json").read_text(encoding="utf-8"))
    assert receipt["temporary_micro_map_only"] is True
    assert receipt["dataset_mutation"] is False
    assert receipt["operator_stepped"] is True
    assert receipt["requires_operator_approval_for_next_pass"] is True


def test_evidence_cloud_speech_refuses_empty_packet_cloud(tmp_path: Path) -> None:
    packet = tmp_path / "empty_packet.json"
    packet.write_text(
        json.dumps({
            "question": "What supports missing cloud?",
            "question_anchors": ["what", "supports", "missing", "cloud"],
            "answer_packet": {"locations": []},
            "model_used": "none",
            "model_may_search": False,
        }),
        encoding="utf-8",
    )

    out = tmp_path / "evidence_speech"
    result = run_evidence_cloud_speech(packet_path=packet, out_dir=out)

    assert result["support_level"] == "insufficient"
    assert result["citations"] == []
    assert "insufficient" in str(result["answer"])
    assert result["input_mutation_detected"] is False


def test_evidence_cloud_speech_cli_command(tmp_path: Path) -> None:
    packet = tmp_path / "cli_packet.json"
    _write_packet(packet)
    out = tmp_path / "cli_out"

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "truemem.cli",
            "evidence-speech",
            "--packet",
            str(packet),
            "--out",
            str(out),
            "--max-passes",
            "3",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(proc.stdout)
    assert payload["records_processed"] == 1
    assert payload["retrieval_ran"] is False
    assert payload["topk_ran"] is False
    assert payload["intake_ran"] is False
    assert payload["support_level"] == "strong"
    assert payload["operator_stepped"] is True
    assert payload["passes"] and len(payload["passes"]) == 1
    assert Path(payload["trace_path"]).is_file()
    assert Path(payload["pretty_answer_path"]).is_file()


def test_evidence_cloud_speech_auto_passes_requires_explicit_flag(tmp_path: Path) -> None:
    packet = tmp_path / "cli_packet.json"
    _write_packet(packet)
    out = tmp_path / "cli_auto_out"

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "truemem.cli",
            "evidence-speech",
            "--packet",
            str(packet),
            "--out",
            str(out),
            "--max-passes",
            "3",
            "--auto-passes",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    payload = json.loads(proc.stdout)
    trace = json.loads(Path(payload["trace_path"]).read_text(encoding="utf-8"))
    assert payload["operator_stepped"] is False
    assert len(trace["passes"]) >= 2
    assert trace["next_action_required"] in {
        "stop_or_review_stable_result",
        "stop_or_review_max_passes_reached",
        "auto_passes_complete",
    }
