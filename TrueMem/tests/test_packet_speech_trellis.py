from __future__ import annotations

from pathlib import Path

from truemem.engine.packet_speech import build_packet_speech_record


def test_packet_speech_includes_speech_output_trellis_receipt(tmp_path: Path) -> None:
    packet = {
        "question": "how does TrueMem use counts citations and speech",
        "question_anchors": ["truemem", "count", "citation", "speech"],
        "model_used": "none",
        "answer_packet": {
            "qualification": {
                "support_state": "qualified_evidence",
                "required_terms": ["count", "citation", "speech"],
            },
            "locations": [
                {
                    "citation": "[TMCIT-1]",
                    "file_path": "source.md",
                    "line_start": 1,
                    "line_end": 3,
                    "rank": 1,
                    "direct_hit_count": 3,
                    "density_score": 4.0,
                    "score": 9.0,
                    "direct_matched_anchors": ["count", "citation"],
                    "matched_anchors": ["truemem", "count", "citation", "speech"],
                    "text": "Counts are the memory. Citations keep source authority. Speech renders packets.",
                },
                {
                    "citation": "[TMCIT-2]",
                    "file_path": "source.md",
                    "line_start": 4,
                    "line_end": 6,
                    "rank": 2,
                    "direct_hit_count": 2,
                    "density_score": 3.0,
                    "score": 8.0,
                    "direct_matched_anchors": ["speech"],
                    "matched_anchors": ["count", "speech"],
                    "text": "Speech chooses a supported path over admitted packet anchors.",
                },
            ],
            "qualification_receipts": [
                {"qualified": True, "covered_terms": ["count", "citation", "speech"]}
            ],
        },
        "final_answer": {"status": "answered_from_truemem_locations", "model_used": "none"},
    }

    record = build_packet_speech_record(packet=packet, packet_path=tmp_path / "packet.json", index=1)

    trellis = record["evidence_trace"]["speech_output_trellis"]
    assert trellis["role"] == "speech_output_trellis"
    assert trellis["receipt"]["no_retrieval"] is True
    assert trellis["receipt"]["no_citation_creation"] is True
    assert trellis["chosen_path"]
    assert "selected speech path" in record["pretty_answer"]["answer"].casefold()
    assert record["pretty_answer"]["speech_output_trellis"]["chosen_anchors"]
