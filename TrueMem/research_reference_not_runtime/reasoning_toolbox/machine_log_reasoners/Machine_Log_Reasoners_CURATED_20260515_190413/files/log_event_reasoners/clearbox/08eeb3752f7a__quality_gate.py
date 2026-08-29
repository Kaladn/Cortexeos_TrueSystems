"""Quality Gate — deterministic ACCEPTABLE/TRASH verdict on every answer.

Every answer gets evaluated BEFORE the user sees it.
Rules first, no model needed. Deterministic and auditable.

Acceptable Contract v3:
  An answer is ACCEPTABLE iff ALL of:
    1. Evidence gate: has real hits (>= 1 hit AND best_score >= min_score)
       OR explicitly says "no evidence" and offers next action
    2. Provenance gate: all facts traceable (citations with valid coords)
       OR labeled as speculation/ungrounded
    3. Integrity gate: no hallucinated file access claims
    4. Policy gate: no leakage of protected data
    5. Retrieval confidence gate: multi-signal analysis of raw scores
       - dual_ratio: fraction of top-k with BOTH bm25>0 AND dense>0
       - spread: score range in top-k (clear standout vs diffuse)
       - max_dense: best raw dense cosine similarity
       Tiers: HIGH (acceptable), MEDIUM (tentative), LOW (trash)
    6. Answer-type presence gate: if the query expects a specific type
       (year, age, city, name), the evidence must contain that type
    7. Polarity/contradiction gate: if query and evidence have opposite
       polarity (survive vs died), the answer is suspect

  If ANY gate fails → TRASH (or TENTATIVE for medium confidence).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from lakespeak.schemas import ScoredChunk

logger = logging.getLogger(__name__)


# ── Configuration ────────────────────────────────────────────

MIN_SCORE_DEFAULT = 0.01     # Minimum best-hit score to pass evidence gate (scores are [0,1])
MIN_HITS_DEFAULT = 1         # Minimum number of hits to pass evidence gate


# ── Gate 6: Answer-Type Presence Patterns ─────────────────────

# Year: 4-digit year in plausible range
YEAR_RE = re.compile(r"\b(1[5-9]\d{2}|20\d{2}|21\d{2})\b")

# Age: 1-3 digit number near age hint words
AGE_RE = re.compile(r"\b(\d{1,3})\b")
AGE_HINT_RE = re.compile(r"\b(years?\s*old|aged|age\b)", re.IGNORECASE)

# Query patterns that imply an expected answer type
_ANSWER_TYPE_PATTERNS = [
    # Year/date patterns
    (re.compile(r"\bwhat\s+year\b", re.I), "year"),
    (re.compile(r"\byear\s+was\b", re.I), "year"),
    (re.compile(r"\bwhen\s+was\s+\w+\s+born\b", re.I), "year"),
    (re.compile(r"\bwhat\s+date\b", re.I), "year"),
    # Age patterns
    (re.compile(r"\bhow\s+old\b", re.I), "age"),
    (re.compile(r"\bwhat\s+age\b", re.I), "age"),
    (re.compile(r"\bwhat\s+is\s+\w+(?:'s)?\s+age\b", re.I), "age"),
    # Location/city patterns
    (re.compile(r"\bwhat\s+city\b", re.I), "city"),
    (re.compile(r"\bwhich\s+city\b", re.I), "city"),
    (re.compile(r"\bwhere\s+(?:was|is|does|did)\s+\w+\s+(?:born|live|from)\b", re.I), "city"),
    # Name-of-X patterns
    (re.compile(r"\bwhat\s+is\s+the\s+name\s+of\b", re.I), "name"),
    (re.compile(r"\bwhat\s+is\s+\w+(?:'s)?\s+(?:dog|cat|pet|wife|husband|mother|father|brother|sister|child|son|daughter)(?:'s)?\s+name\b", re.I), "name"),
]


# ── Gate 7: Polarity / Contradiction Lexicons ────────────────

SURVIVE_POS = frozenset({
    "survive", "survived", "survives", "surviving",
    "alive", "lived", "rescued", "safe", "recovered",
    "escaped", "made it", "pulled through",
})

DEATH_NEG = frozenset({
    "die", "died", "dies", "dying", "dead",
    "killed", "eaten", "devoured", "slain",
    "corpse", "perished", "drowned", "murdered",
    "deceased", "fatal", "lethal",
})


# ── Quality Verdict ──────────────────────────────────────────

@dataclass
class QualityVerdict:
    """Result of the Quality Gate evaluation."""
    verdict: str                                # "acceptable" | "trash"
    reasons: List[str] = field(default_factory=list)
    next_action: str = ""                       # "offer_llm" | "refine_query" | "queue_mapping" | "ask_clarify"
    safe_response: str = ""                     # What user sees if TRASH
    confidence_tier: str = "high"               # "high" | "medium" | "low"
    debug: Dict[str, Any] = field(default_factory=dict)


# ── Miss Templates (standardized) ────────────────────────────

MISS_TEMPLATES = {
    "lexicon_present_no_hits": (
        "No map hits for '{query}', although {tokens} appear in the lexicon. "
        "Would you like to query the LLM instead?"
    ),
    "lexicon_absent_no_hits": (
        "No map hits for '{query}'. The terms are not in the lexicon either. "
        "Try refining your query or queue a mapping request."
    ),
    "hits_present_low_confidence": (
        "Found {hit_count} potential matches for '{query}', but confidence "
        "is low ({best_score:.2f}). Showing best effort — treat with caution."
    ),
    "no_provenance": (
        "Some results for '{query}' could not be traced to their source. "
        "Showing only verifiable results."
    ),
    "weak_retrieval_confidence": (
        "Found passages related to '{query}', but retrieval confidence is low — "
        "the keyword-specific terms in your question don't appear in the "
        "retrieved content. Would you like to try the LLM or refine your query?"
    ),
    "missing_answer_type": (
        "Found passages related to '{query}', but the retrieved content "
        "doesn't contain the expected {expected_type}. "
        "Would you like to try the LLM or refine your query?"
    ),
    "evidence_contradiction": (
        "Found passages related to '{query}', but the evidence appears "
        "to contradict the premise of the question. "
        "Would you like to try the LLM for a more nuanced answer?"
    ),
    "generic_trash": (
        "Unable to provide a grounded answer for '{query}'. "
        "Would you like to try a different query or switch to LLM mode?"
    ),
}


# ── Next Action Picker ───────────────────────────────────────

def _pick_next_action(
    reasons: List[str],
    lexicon_present: List[str],
    mode: str,
) -> str:
    """Pick the best next action based on failure reasons."""
    if "no_retrieval_hits" in reasons:
        if lexicon_present:
            return "offer_llm"
        else:
            return "queue_mapping"
    if "low_confidence" in reasons:
        return "refine_query"
    if "weak_retrieval_confidence" in reasons:
        return "offer_llm"
    if "missing_answer_type" in reasons:
        return "offer_llm"
    if "evidence_contradiction" in reasons:
        return "offer_llm"
    if "missing_provenance" in reasons:
        return "ask_clarify"
    return "offer_llm"


# ── Safe Response Builder ────────────────────────────────────

def _build_safe_response(
    query: str,
    reasons: List[str],
    lexicon_present: List[str],
    lexicon_absent: List[str],
    hit_count: int = 0,
    best_score: float = 0.0,
    **kwargs,
) -> str:
    """Build a user-facing safe response for TRASH verdicts."""
    if "no_retrieval_hits" in reasons:
        if lexicon_present:
            tokens = ", ".join(f"'{t}'" for t in lexicon_present[:5])
            return MISS_TEMPLATES["lexicon_present_no_hits"].format(
                query=query, tokens=tokens,
            )
        else:
            return MISS_TEMPLATES["lexicon_absent_no_hits"].format(query=query)

    if "low_confidence" in reasons:
        return MISS_TEMPLATES["hits_present_low_confidence"].format(
            query=query, hit_count=hit_count, best_score=best_score,
        )

    if "weak_retrieval_confidence" in reasons:
        return MISS_TEMPLATES["weak_retrieval_confidence"].format(query=query)

    if "missing_answer_type" in reasons:
        return MISS_TEMPLATES["missing_answer_type"].format(
            query=query, expected_type=kwargs.get("expected_type", "answer"),
        )

    if "evidence_contradiction" in reasons:
        return MISS_TEMPLATES["evidence_contradiction"].format(query=query)

    if "missing_provenance" in reasons:
        return MISS_TEMPLATES["no_provenance"].format(query=query)

    return MISS_TEMPLATES["generic_trash"].format(query=query)


# ── Retrieval Confidence Tier ────────────────────────────────

def _compute_confidence_tier(
    retrieval_hits: List[ScoredChunk],
) -> tuple:
    """Compute confidence tier from raw retrieval signals.

    Returns (tier, signals_dict) where tier is "high"|"medium"|"low".

    Signal analysis:
      dual_ratio:  fraction of top-k with BOTH bm25>0 AND dense>0.
                   High = both retrieval methods agree on the same chunks.
      spread:      best_reranked - worst_reranked in top-k.
                   High = a clear standout answer. Low = diffuse/flat.
      max_dense:   best raw dense cosine similarity among top-k.

    Tier rules:
      HIGH:   dual_ratio >= 0.6 AND spread >= 0.10
              Both signals agree AND a clear winner exists.
      MEDIUM: (dual_ratio >= 0.6 AND spread < 0.10)
              OR (dual_ratio == 0 AND max_dense >= 0.35)
              Partial agreement, or plausible pure-semantic match.
      LOW:    0 < dual_ratio < 0.6
              Partial keyword match only — e.g. entity name matches
              but the question-specific terms don't appear in chunks.
              OR: max_dense < 0.35 with no BM25 signal.
    """
    if not retrieval_hits:
        return "low", {"dual_ratio": 0, "spread": 0, "max_dense": 0,
                        "dual_count": 0, "hit_count": 0}

    max_dense = max((h.dense_score for h in retrieval_hits), default=0.0)
    scores = [h.score for h in retrieval_hits]
    spread = max(scores) - min(scores) if len(scores) > 1 else 0.0

    dual_count = sum(
        1 for h in retrieval_hits
        if h.bm25_score > 0 and h.dense_score > 0
    )
    dual_ratio = dual_count / len(retrieval_hits)

    signals = {
        "max_dense": round(max_dense, 4),
        "dual_ratio": round(dual_ratio, 4),
        "dual_count": dual_count,
        "spread": round(spread, 4),
        "hit_count": len(retrieval_hits),
    }

    # Additional signals
    bm25_active = any(h.bm25_score > 0 for h in retrieval_hits)
    dense_active = any(h.dense_score > 0 for h in retrieval_hits)
    signals["bm25_active"] = bm25_active
    signals["dense_active"] = dense_active

    # 6-1-6 anchor signal: if anchor reranking boosted any chunks,
    # that's a third retrieval signal (lexicon-grounded overlap).
    anchor_count = sum(1 for h in retrieval_hits if h.anchor_score > 0)
    anchor_ratio = anchor_count / len(retrieval_hits)
    max_anchor = max((h.anchor_score for h in retrieval_hits), default=0.0)
    signals["anchor_ratio"] = round(anchor_ratio, 4)
    signals["anchor_count"] = anchor_count
    signals["max_anchor"] = round(max_anchor, 4)

    # HIGH: anchor reranking boosted most results with strong overlap
    # (lexicon confirms query terms appear in the retrieved chunks)
    if anchor_ratio >= 0.5 and max_anchor >= 0.3 and spread >= 0.05:
        return "high", signals

    # HIGH: strong bm25+dense agreement AND clear standout
    if dual_ratio >= 0.6 and spread >= 0.07:
        return "high", signals

    # MEDIUM: anchor reranking confirms some relevance
    if anchor_ratio >= 0.3 and max_anchor >= 0.2:
        return "medium", signals

    # MEDIUM: strong bm25+dense agreement but flat scores
    if dual_ratio >= 0.6:
        return "medium", signals

    # MEDIUM: partial agreement (dual 0.3-0.6) with a standout chunk
    if dual_ratio >= 0.3 and spread >= 0.05:
        return "medium", signals

    # MEDIUM: any anchor signal at all (lexicon-verified relevance)
    if anchor_count >= 1 and max_anchor >= 0.1:
        return "medium", signals

    # LOW: total disagreement — BM25 and dense both fired but on
    # DIFFERENT chunks with no anchor confirmation.
    if dual_ratio == 0.0 and bm25_active and dense_active and anchor_count == 0:
        return "low", signals

    # LOW: very weak agreement (dual < 0.3) and no anchor backup
    if 0 < dual_ratio < 0.3 and anchor_count == 0:
        return "low", signals

    # MEDIUM: pure semantic (no BM25 at all) with decent dense cosine
    if dual_ratio == 0.0 and max_dense >= 0.35:
        return "medium", signals

    # MEDIUM: any non-zero anchor (conservative — at least the lexicon sees overlap)
    if anchor_count > 0:
        return "medium", signals

    # LOW: everything else (weak signals all around)
    return "low", signals


# ── Gate 6: Answer-Type Presence ─────────────────────────────

def _expected_answer_type(query: str) -> Optional[str]:
    """Infer the expected answer type from a query.

    Returns "year"|"age"|"city"|"name" or None if no specific type expected.
    """
    for pattern, ans_type in _ANSWER_TYPE_PATTERNS:
        if pattern.search(query):
            return ans_type
    return None


def _evidence_has_answer_type(ans_type: str, evidence_texts: List[str]) -> bool:
    """Check if ANY evidence text contains the expected answer type.

    Conservative: only blocks when we're confident the type is missing.
    """
    combined = " ".join(evidence_texts)

    if ans_type == "year":
        return bool(YEAR_RE.search(combined))

    if ans_type == "age":
        # Need both a number AND an age hint word nearby
        return bool(AGE_RE.search(combined)) and bool(AGE_HINT_RE.search(combined))

    if ans_type == "city":
        # Check for preposition + capitalized word pattern (simple heuristic)
        # e.g. "in Seattle", "from Portland", "at Denver"
        city_pattern = re.compile(
            r"\b(?:in|at|near|from|of)\s+[A-Z][a-z]{2,}",
        )
        return bool(city_pattern.search(combined))

    if ans_type == "name":
        # Check for "named X" / "called X" / capitalized proper noun
        name_pattern = re.compile(
            r"\b(?:named|called|name\s+(?:is|was))\s+[A-Z][a-z]+",
        )
        return bool(name_pattern.search(combined))

    return True  # Unknown type — don't block


# ── Gate 7: Polarity / Contradiction Heuristic ──────────────

def _contradiction_heuristic(query: str, evidence_texts: List[str]) -> bool:
    """Detect polarity contradiction between query and evidence.

    Returns True if query implies one polarity (survive/alive)
    but evidence contains the opposite (died/killed), or vice versa.
    """
    q_tokens = set(re.findall(r"[a-z']+", query.lower()))
    e_tokens = set(re.findall(r"[a-z']+", " ".join(evidence_texts).lower()))

    q_has_survive = bool(q_tokens & SURVIVE_POS)
    q_has_death = bool(q_tokens & DEATH_NEG)
    e_has_survive = bool(e_tokens & SURVIVE_POS)
    e_has_death = bool(e_tokens & DEATH_NEG)

    # Query asks about survival, evidence says death
    if q_has_survive and e_has_death and not e_has_survive:
        return True

    # Query asks about death, evidence says survival
    if q_has_death and e_has_survive and not e_has_death:
        return True

    return False


# ── Main Evaluator ───────────────────────────────────────────

def evaluate(
    query: str,
    retrieval_hits: List[ScoredChunk],
    citations: List[dict],
    response_text: str,
    mode: str,
    lexicon_present: List[str],
    lexicon_absent: List[str],
    min_score: float = MIN_SCORE_DEFAULT,
    min_hits: int = MIN_HITS_DEFAULT,
    evidence_texts: Optional[List[str]] = None,
) -> QualityVerdict:
    """Deterministic Quality Gate. Rules first, no model needed.

    Args:
        query: Original query text.
        retrieval_hits: Scored retrieval candidates (already ranked).
        citations: Citation records attached to the response.
        response_text: Generated response text.
        mode: Query mode ("grounded" | "allow_fallback").
        lexicon_present: Query tokens found in lexicon.
        lexicon_absent: Query tokens NOT in lexicon.
        min_score: Minimum score threshold for evidence gate.
        min_hits: Minimum hit count for evidence gate.
        evidence_texts: Raw text from top-k evidence chunks (for gates 6/7).

    Returns:
        QualityVerdict with verdict, reasons, next_action, safe_response.
    """
    reasons: List[str] = []
    hit_count = len(retrieval_hits)
    best_score = max((h.score for h in retrieval_hits), default=0.0)
    if evidence_texts is None:
        evidence_texts = []

    # ── Gate 1: Evidence ─────────────────────────────────────
    if hit_count < min_hits:
        reasons.append("no_retrieval_hits")
    elif best_score < min_score:
        reasons.append("low_confidence")

    # ── Gate 2: Provenance ───────────────────────────────────
    for c in citations:
        if not c.get("coord"):
            reasons.append("missing_provenance")
            break

    # ── Gate 3: Integrity (reserved, expandable) ─────────────
    # Future: check for hallucinated file paths, disk access claims, etc.

    # ── Gate 4: Policy (reserved, expandable) ────────────────
    # Future: check for protected data leakage

    # ── Gate 5: Retrieval Confidence (multi-signal) ──────────
    confidence_tier, confidence_signals = _compute_confidence_tier(retrieval_hits)

    if confidence_tier == "low" and not reasons:
        if mode == "grounded":
            reasons.append("weak_retrieval_confidence")

    # ── Gate 6: Answer-Type Presence ─────────────────────────
    # Only check when we have evidence texts AND haven't already failed
    expected_type = _expected_answer_type(query)
    if expected_type and evidence_texts and not reasons:
        if not _evidence_has_answer_type(expected_type, evidence_texts):
            reasons.append("missing_answer_type")
            logger.info(
                "Gate 6 tripped: query expects '%s' but evidence lacks it | query='%s'",
                expected_type, query,
            )

    # ── Gate 7: Polarity / Contradiction ─────────────────────
    # Only check when we have evidence texts AND haven't already failed
    if evidence_texts and not reasons:
        if _contradiction_heuristic(query, evidence_texts):
            reasons.append("evidence_contradiction")
            logger.info(
                "Gate 7 tripped: polarity contradiction detected | query='%s'",
                query,
            )

    # ── Build verdict ────────────────────────────────────────
    if reasons:
        return QualityVerdict(
            verdict="trash",
            reasons=reasons,
            next_action=_pick_next_action(reasons, lexicon_present, mode),
            safe_response=_build_safe_response(
                query=query,
                reasons=reasons,
                lexicon_present=lexicon_present,
                lexicon_absent=lexicon_absent,
                hit_count=hit_count,
                best_score=best_score,
                expected_type=expected_type or "answer",
            ),
            confidence_tier=confidence_tier,
            debug={
                "hit_count": hit_count,
                "best_score": best_score,
                "min_score": min_score,
                "min_hits": min_hits,
                "confidence_signals": confidence_signals,
                "expected_answer_type": expected_type,
            },
        )
    else:
        return QualityVerdict(
            verdict="acceptable",
            reasons=[],
            next_action="",
            safe_response="",
            confidence_tier=confidence_tier,
            debug={
                "hit_count": hit_count,
                "best_score": best_score,
                "confidence_signals": confidence_signals,
                "expected_answer_type": expected_type,
            },
        )
