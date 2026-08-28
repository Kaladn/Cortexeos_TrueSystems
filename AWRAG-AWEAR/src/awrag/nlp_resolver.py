from __future__ import annotations

import re
from collections import Counter
from typing import Any


RESOLVER_ID = "awrag_deterministic_nlp_resolver@1"
ABBREVIATIONS = {
    "e.g.",
    "i.e.",
    "mr.",
    "mrs.",
    "ms.",
    "dr.",
    "prof.",
    "sr.",
    "jr.",
    "vs.",
    "v.",
}


def resolve_answer(question: str, answer_packet: dict[str, Any]) -> dict[str, Any]:
    """Convert locked AWEAR evidence locations into a cited readable answer.

    This resolver is intentionally small. It does not search, score, call a
    model, or invent citations. It only selects readable snippets from the
    locations that AWEAR already admitted into the packet.
    """
    locations = list(answer_packet.get("locations") or [])
    if not locations:
        return {
            "schema": "awrag_nlp_answer@1",
            "resolver": RESOLVER_ID,
            "status": "not_enough_information",
            "text": "Not enough information is available in the admitted dataset to answer this question.",
            "citations": [],
            "model_used": "none",
            "model_may_search": False,
            "citation_source": "awrag_locked_packet",
        }

    conversation_reply = _conversation_reply(question, locations)
    if conversation_reply:
        return conversation_reply

    question_terms = Counter(_terms(question))
    cited_sentences: list[str] = []
    citations: list[str] = []
    for location in locations[:3]:
        citation = str(location.get("citation") or "").strip()
        sentence = best_sentence(str(location.get("text") or ""), question_terms)
        if not sentence:
            continue
        if citation and citation not in sentence:
            sentence = f"{sentence} {citation}"
        cited_sentences.append(sentence)
        if citation:
            citations.append(citation)

    if not cited_sentences:
        return {
            "schema": "awrag_nlp_answer@1",
            "resolver": RESOLVER_ID,
            "status": "not_enough_information",
            "text": "AWEAR found locations, but the admitted text could not be converted into a supported answer.",
            "citations": citations,
            "model_used": "none",
            "model_may_search": False,
            "citation_source": "awrag_locked_packet",
        }

    return {
        "schema": "awrag_nlp_answer@1",
        "resolver": RESOLVER_ID,
        "status": "answered_from_awrag_locations",
        "text": " ".join(cited_sentences),
        "citations": citations,
        "model_used": "none",
        "model_may_search": False,
        "citation_source": "awrag_locked_packet",
    }


def _conversation_reply(question: str, locations: list[dict[str, Any]]) -> dict[str, Any] | None:
    input_class = _conversation_input_class(question)
    if input_class != "greeting":
        return None
    evidence = []
    for location in locations[:5]:
        citation = str(location.get("citation") or "").strip()
        text = str(location.get("text") or "")
        if not citation:
            continue
        if _contains_greeting_evidence(text):
            evidence.append({"citation": citation, "snippet": clean_sentence(text)[:240]})
    if not evidence:
        return None
    return {
        "schema": "awrag_nlp_answer@1",
        "resolver": RESOLVER_ID,
        "status": "answered_from_awrag_locations",
        "text": "Good morning.",
        "citations": [row["citation"] for row in evidence],
        "model_used": "none",
        "model_may_search": False,
        "citation_source": "awrag_locked_packet",
        "conversation_reply_receipt": {
            "schema": "awrag_conversation_reply_receipt@1",
            "input_class": input_class,
            "reply_source": "admitted_cited_evidence",
            "evidence": evidence,
            "no_model_call": True,
            "no_search_rerun": True,
            "no_new_citation": True,
        },
    }


def _conversation_input_class(question: str) -> str | None:
    normalized = " ".join(_terms(question))
    if normalized in {"good morning", "morning"}:
        return "greeting"
    return None


def _contains_greeting_evidence(text: str) -> bool:
    lowered = text.casefold()
    return "good morning" in lowered or re.search(r"\bmorning[!.]?\b", lowered) is not None


def best_sentence(text: str, question_terms: Counter[str]) -> str:
    candidates = [clean_sentence(sentence) for sentence in split_sentences(text)]
    candidates = [candidate for candidate in candidates if candidate]
    if not candidates:
        return clean_sentence(text)
    ranked = sorted(
        candidates,
        key=lambda sentence: (-sentence_score(sentence, question_terms), len(sentence), sentence),
    )
    return ranked[0]


def sentence_score(sentence: str, question_terms: Counter[str]) -> int:
    terms = Counter(_terms(sentence))
    return sum(min(count, terms.get(term, 0)) for term, count in question_terms.items())


def clean_sentence(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip(" \t\r\n")

def split_sentences(text: str) -> list[str]:
    sentences: list[str] = []
    protected_periods = _protected_period_indexes(text)
    start = 0
    index = 0
    while index < len(text):
        char = text[index]
        if char in ".!?\n" and index not in protected_periods:
            end = index + 1
            sentences.append(text[start:end])
            start = end
        index += 1
    if start < len(text):
        sentences.append(text[start:])
    return sentences

def _protected_period_indexes(text: str) -> set[int]:
    protected: set[int] = set()
    lowered = text.casefold()
    for abbreviation in ABBREVIATIONS:
        start = 0
        while True:
            found = lowered.find(abbreviation, start)
            if found < 0:
                break
            for offset, char in enumerate(abbreviation):
                if char == ".":
                    protected.add(found + offset)
            start = found + len(abbreviation)
    for match in re.finditer(r"\b(?:[A-Za-z]\.){2,}", text):
        for offset, char in enumerate(match.group(0)):
            if char == ".":
                protected.add(match.start() + offset)
    return protected


def _terms(text: str) -> list[str]:
    return [match.group(0).casefold() for match in re.finditer(r"[A-Za-z0-9]+", text)]
