from __future__ import annotations

from truemem.engine.legal_anchor_typing import classify_anchor_occurrences, typed_anchor_summary


def test_classifies_same_word_by_local_legal_shape() -> None:
    text = "Section 12 means court. The court may excuse a juror unless the statute requires service."

    rows = classify_anchor_occurrences(text)
    by_anchor: dict[str, list[dict]] = {}
    for row in rows:
        by_anchor.setdefault(row["anchor"], []).append(row)

    section_rows = by_anchor["section"]
    court_rows = by_anchor["court"]
    may_rows = by_anchor["may"]
    unless_rows = by_anchor["unless"]
    requires_rows = by_anchor["requires"]

    assert section_rows[0]["anchor_type"] == "authority_anchor"
    assert court_rows[0]["anchor_type"] == "definition_anchor"
    assert may_rows[0]["anchor_type"] == "discretion_anchor"
    assert unless_rows[0]["anchor_type"] == "exception_anchor"
    assert requires_rows[0]["anchor_type"] == "duty_anchor"
    assert court_rows[0]["proof_need"] == "definition_controls_meaning"


def test_typed_anchor_summary_preserves_visible_and_typed_anchors() -> None:
    summary = typed_anchor_summary("Rule 4 shall apply unless the court orders otherwise.")

    assert summary["schema"] == "truemem_typed_anchor_summary@1"
    assert "Rule" in summary["all_anchors"]
    assert "rule" not in summary["all_anchors"]
    assert any(row["symbol"] == "shall[duty_anchor]" for row in summary["typed_anchors"])
    assert "prove_required_condition" in summary["proof_needs"]
