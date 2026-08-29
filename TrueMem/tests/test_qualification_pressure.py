from __future__ import annotations

from collections import Counter

from truemem.engine.anchors import anchorize
from truemem.engine.qualification import qualify_evidence


def test_rejected_but_found_core_candidate_is_not_promoted_on_hot_path() -> None:
    question = (
        "Bob and Ted are close friends. Ted is on trial for drug offences, "
        "and Bob has been selected as a juror in Ted's case. Is the judge "
        "required to excuse Bob from serving on the jury?"
    )
    candidate = {
        "citation": "[TMCIT-core]",
        "file_path": "corpus/1.2-c2-s2.md",
        "score": 40.1972,
        "density_score": 5.7425,
        "direct_hit_count": 7,
        "direct_matched_anchors": ["excuse", "has", "juror", "jury", "offence", "serving", "trial"],
        "matched_anchors": ["excuse", "has", "juror", "jury", "not", "offence", "serving", "trial"],
        "text": (
            "It is not necessary to excuse a person who has had a particular life "
            "experience from serving on a jury in a trial which concerns matters "
            "to which that experience is relevant."
        ),
    }

    result = qualify_evidence(question, Counter(anchorize(question)), [candidate], top_k=5)

    assert result["summary"]["support_state"] == "no_qualified_evidence"
    assert result["summary"]["pressure_promoted_count"] == 0
    assert result["locations"] == []
    receipt = result["rejected"][0]["qualification"]
    assert receipt["qualified"] is False
    assert receipt["pressure_decision"] == "confirm_reject"
    assert receipt["candidate_status_before_pressure"] == "reject_confirmed"
    assert receipt["pressure_trigger"]["native_rank_strong"] is True
    assert receipt["pressure_trigger"]["coordinate_supported"] is True
    assert "unsupported_refusal_threshold" in receipt["reject_reasons_before_pressure"]
    assert "predicate_object_coverage_miss" in receipt["reject_reasons_before_pressure"]


def test_weak_core_candidate_stays_rejected_after_pressure_review() -> None:
    question = (
        "Bob and Ted are close friends. Ted is on trial for drug offences, "
        "and Bob has been selected as a juror in Ted's case. Is the judge "
        "required to excuse Bob from serving on the jury?"
    )
    candidate = {
        "citation": "[TMCIT-weak]",
        "file_path": "corpus/other.md",
        "score": 12.0,
        "density_score": 1.5,
        "direct_hit_count": 3,
        "direct_matched_anchors": ["judge", "jury", "trial"],
        "matched_anchors": ["judge", "jury", "trial"],
        "text": "The judge gave directions to the jury during trial.",
    }

    result = qualify_evidence(question, Counter(anchorize(question)), [candidate], top_k=5)

    assert result["summary"]["support_state"] == "no_qualified_evidence"
    assert result["summary"]["pressure_promoted_count"] == 0
    assert result["locations"] == []
    receipt = result["rejected"][0]["qualification"]
    assert receipt["pressure_decision"] == "confirm_reject"
