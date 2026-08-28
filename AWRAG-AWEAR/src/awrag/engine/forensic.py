from __future__ import annotations

from typing import Any, Iterable

from .anchors import anchorize

FORENSIC_LADDER = [
    ("L1", "artifact_or_subject_referenced"),
    ("L2", "artifact_existence_evidenced"),
    ("L3", "artifact_contents_recovered"),
    ("L4", "artifact_modification_evidenced"),
    ("L5", "artifact_referenced_after_modification"),
    ("L6", "deletion_or_rejection_discussed"),
    ("L7", "deletion_or_rejection_evidenced"),
    ("L8", "contradictory_statements_found"),
    ("L9", "execution_or_deployment_evidenced"),
]


def build_forensic_support_receipt(
    question: str,
    answer_packet: dict[str, Any],
    final_answer: dict[str, Any],
) -> dict[str, Any]:
    """Build a conservative forensic reconstruction receipt from admitted evidence.

    The receipt never accuses. It names only what the AWEAR packet can support
    from admitted locations and explicitly lists common claims that remain
    unsupported.
    """
    locations = list(answer_packet.get("locations") or [])
    citations = [str(row.get("citation")) for row in locations if row.get("citation")]
    evidence_text = "\n".join(str(row.get("text") or "") for row in locations)
    evidence_terms = set(anchorize(evidence_text))
    question_terms = set(anchorize(question))
    text_folded = evidence_text.casefold()
    final_status = str(final_answer.get("status") or "")

    supported: list[str] = []
    ladder_hits: list[str] = []

    if locations:
        ladder_hits.append("L1")
        supported.append("artifact_or_subject_referenced")

    if locations and question_terms and len(question_terms & evidence_terms) >= min(2, len(question_terms)):
        ladder_hits.append("L2")
        supported.append("artifact_existence_evidenced")

    if _contains_any(text_folded, ("```", "def ", "class ", "function ", "import ", ".py", "module 1", "module_")):
        ladder_hits.append("L3")
        supported.append("artifact_contents_recovered")

    if _contains_any(text_folded, ("modified", "updated", "changed", "rewrote", "patched", "edited", "version")):
        ladder_hits.append("L4")
        supported.append("artifact_modification_evidenced")

    if "L4" in ladder_hits and _contains_any(text_folded, ("after", "later", "then", "again")):
        ladder_hits.append("L5")
        supported.append("artifact_referenced_after_modification")

    if _contains_any(text_folded, ("deleted", "delete", "threw it away", "thrown away", "ditched", "discarded", "rejected", "not as a build plan")):
        ladder_hits.append("L6")
        supported.append("deletion_or_rejection_discussed")

    if _contains_any(text_folded, ("deletion receipt", "delete log", "removed from disk", "file no longer exists", "not recovered")):
        ladder_hits.append("L7")
        supported.append("deletion_or_rejection_evidenced")

    if _contains_any(text_folded, ("contradiction", "contradictory", "conflict", "conflicting statement", "inconsistent")):
        ladder_hits.append("L8")
        supported.append("contradictory_statements_found")

    if _contains_any(text_folded, ("executed", "ran command", "ran script", "deployed", "launched", "installed", "in production", "production deployment")):
        ladder_hits.append("L9")
        supported.append("execution_or_deployment_evidenced")

    supported = _dedupe_preserve_order(supported)
    ladder_hits = _dedupe_preserve_order(ladder_hits)
    supported_set = set(supported)
    not_supported = [name for _, name in FORENSIC_LADDER if name not in supported_set]
    support_level = forensic_support_level(ladder_hits, final_status)

    return {
        "schema": "awrag_forensic_support_receipt@1",
        "mode": "reconstructive_not_accusatory",
        "support_level": support_level,
        "ladder": [{"level": level, "meaning": meaning} for level, meaning in FORENSIC_LADDER],
        "ladder_hits": ladder_hits,
        "supported": supported,
        "not_supported": not_supported,
        "citations": citations,
        "claim_language": "The record supports only the listed evidence states. Absence from supported means not established by admitted locations.",
        "conclusion": forensic_conclusion(support_level, supported, not_supported),
    }

def forensic_support_level(ladder_hits: list[str], final_status: str) -> str:
    if not ladder_hits or final_status == "not_enough_information":
        return "insufficient"
    if "L8" in ladder_hits:
        return "conflict"
    if "L9" in ladder_hits or "L3" in ladder_hits:
        return "strong"
    if len(ladder_hits) >= 2:
        return "partial"
    return "weak"

def forensic_conclusion(support_level: str, supported: list[str], not_supported: list[str]) -> str:
    if support_level == "insufficient":
        return "The admitted record does not provide enough evidence to support the requested forensic claim."
    supported_text = ", ".join(supported) if supported else "nothing"
    unsupported_text = ", ".join(not_supported[:4]) if not_supported else "no common unsupported states"
    return f"The record supports: {supported_text}. The record does not establish: {unsupported_text}."

def _contains_any(text: str, needles: Iterable[str]) -> bool:
    return any(needle in text for needle in needles)

def _dedupe_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out

