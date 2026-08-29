"""Grounding Policy — grounded vs fallback + refusal/miss templates.

Decides HOW to respond based on the Quality Gate verdict:
  - ACCEPTABLE + grounded → serve with citations
  - TRASH + grounded → refuse with miss template + next action
  - ACCEPTABLE + allow_fallback → serve with citations
  - TRASH + allow_fallback → serve with caveat (ungrounded label)

This module does NOT generate text. It produces structured decisions
that the query engine uses to build the final response.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

from lakespeak.retrieval.quality_gate import QualityVerdict

logger = logging.getLogger(__name__)


# ── Grounding Decision ───────────────────────────────────────

@dataclass
class GroundingDecision:
    """Structured decision from the grounding policy.

    The query engine uses this to build the final response.
    """
    action: str                         # "serve_grounded" | "refuse" | "serve_ungrounded" | "offer_alternative"
    response_text: str = ""             # What the user sees (may be safe_response for refusals)
    citations: List[dict] = field(default_factory=list)
    verdict: str = ""                   # "acceptable" | "trash" (passthrough from QualityVerdict)
    refusal_reason: Optional[str] = None  # Why we refused (if action == "refuse")
    suggested_next_mode: Optional[str] = None  # "llm" | "reasoning" | "refine_query" | "queue_mapping"
    caveats: List[str] = field(default_factory=list)  # Warnings attached to response


# ── Refusal Reasons ──────────────────────────────────────────

REFUSAL_REASONS = {
    "no_retrieval_hits": "No retrieval hits found for your query.",
    "low_confidence": "Retrieval confidence is too low to provide a grounded answer.",
    "weak_retrieval_confidence": (
        "Found related passages, but retrieval confidence is low — "
        "the question-specific terms don't appear in the matched content."
    ),
    "missing_answer_type": (
        "Found related passages, but the evidence doesn't contain the "
        "type of answer your question requires."
    ),
    "evidence_contradiction": (
        "Found related passages, but the evidence appears to contradict "
        "the premise of your question."
    ),
    "missing_provenance": "Some results cannot be traced to their source.",
}

# Map from next_action to suggested mode
_NEXT_ACTION_TO_MODE = {
    "offer_llm": "llm",
    "refine_query": "refine_query",
    "queue_mapping": "queue_mapping",
    "ask_clarify": "refine_query",
}


# ── Policy Application ──────────────────────────────────────

def apply_policy(
    verdict: QualityVerdict,
    mode: str,
    response_text: str,
    citations: List[dict],
) -> GroundingDecision:
    """Apply grounding policy based on Quality Gate verdict and mode.

    Args:
        verdict: Quality Gate result.
        mode: Query mode ("grounded" | "allow_fallback").
        response_text: The generated answer text.
        citations: Citation records for the answer.

    Returns:
        GroundingDecision describing what to do.
    """
    suggested_mode = _NEXT_ACTION_TO_MODE.get(verdict.next_action)

    # ── ACCEPTABLE ───────────────────────────────────────────
    if verdict.verdict == "acceptable":
        # HIGH confidence: fully grounded, serve with citations
        if verdict.confidence_tier == "high":
            return GroundingDecision(
                action="serve_grounded",
                response_text=response_text,
                citations=citations,
                verdict="acceptable",
                refusal_reason=None,
                suggested_next_mode=None,
                caveats=[],
            )
        # MEDIUM confidence: serve results but NOT as grounded —
        # the system found related content but can't guarantee a specific answer.
        return GroundingDecision(
            action="serve_tentative",
            response_text=response_text,
            citations=citations,
            verdict="acceptable",
            refusal_reason=None,
            suggested_next_mode="llm",
            caveats=[
                "Retrieval confidence is moderate — these passages are related "
                "to your query but may not contain the specific answer.",
            ],
        )

    # ── TRASH + grounded mode → refuse ───────────────────────
    if mode == "grounded":
        primary_reason = verdict.reasons[0] if verdict.reasons else "unknown"
        return GroundingDecision(
            action="refuse",
            response_text=verdict.safe_response,
            citations=[],
            verdict="trash",
            refusal_reason=REFUSAL_REASONS.get(primary_reason, primary_reason),
            suggested_next_mode=suggested_mode,
            caveats=[],
        )

    # ── TRASH + allow_fallback → serve ungrounded with caveats
    caveats = []
    for reason in verdict.reasons:
        if reason == "no_retrieval_hits":
            caveats.append("No grounded evidence found — this response is ungrounded.")
        elif reason == "low_confidence":
            caveats.append("Confidence is low — treat this response with caution.")
        elif reason == "weak_retrieval_confidence":
            caveats.append(
                "Retrieval confidence is low — matched passages are "
                "topically related but may not contain the specific answer."
            )
        elif reason == "missing_answer_type":
            caveats.append(
                "The evidence doesn't contain the type of answer "
                "your question requires — treat with caution."
            )
        elif reason == "evidence_contradiction":
            caveats.append(
                "The evidence appears to contradict the premise of "
                "your question — the LLM may give a more nuanced answer."
            )
        elif reason == "missing_provenance":
            caveats.append("Some claims could not be traced to their source.")
        else:
            caveats.append(f"Quality concern: {reason}")

    return GroundingDecision(
        action="serve_ungrounded",
        response_text=response_text,
        citations=citations,
        verdict="trash",
        refusal_reason=None,
        suggested_next_mode=suggested_mode,
        caveats=caveats,
    )
