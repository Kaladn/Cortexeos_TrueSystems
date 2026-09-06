"""Complete-word and structural-object anchors for deterministic mapping."""

from __future__ import annotations

import re
import sys
import unicodedata
from collections import Counter

from .base import SYMBOL_BYTES as SYMBOL_BYTES
from .base import SYMBOL_HEX_CHARS, SYMBOL_SYSTEM as SYMBOL_SYSTEM, sha1_text

WORD_UNIT = r"[^\W_][\u0300-\u036f]*"
WORD_BODY = rf"(?:{WORD_UNIT})+"
WORD_RE = re.compile(
    rf"{WORD_BODY}(?:['’]{WORD_BODY})*(?:[-‐‑‒–—]{WORD_BODY}(?:['’]{WORD_BODY})*)*|_|[^\s\w]",
    re.UNICODE,
)

SHA_RE = re.compile(r"(?i)(?:sha(?:1|224|256|384|512):)?[0-9a-f]{40,128}")

# Preserved, symbolized, counted, and placed like every other word. These are
# only prevented from independently steering answer direction.
GLUE_ANCHORS = frozenset({
    "a", "about", "an", "and", "are", "as", "at", "be", "because", "but",
    "by", "did", "do", "does", "for", "from", "had", "has",
    "have", "he", "her", "hers", "him", "his", "how", "if", "in", "into",
    "is", "it", "its", "me", "my", "of", "on",
    "our", "ours", "she", "so", "than", "that", "the", "their",
    "theirs", "them", "then", "there", "these", "they", "this", "those",
    "to", "under", "us", "was", "we", "were", "what",
    "where", "which", "while", "who", "why", "with", "you",
    "your", "yours",
})

# These anchors do not name the subject, but they do control the relationship
# being asserted and therefore participate in answer direction.
RELATION_ANCHORS = frozenset({
    "and", "but", "can", "cannot", "could", "if", "may", "must", "neither",
    "never", "no", "nor", "not", "or", "shall", "should", "unless", "when",
    "will", "without", "would",
})
GLUE_ANCHORS = GLUE_ANCHORS - RELATION_ANCHORS

PUNCTUATION_ROLES = {
    ".": "boundary:sentence:period",
    "!": "boundary:sentence:exclamation",
    "?": "boundary:sentence:question",
    ",": "boundary:clause:comma",
    ";": "boundary:clause:semicolon",
    ":": "boundary:relation:colon",
    "(": "boundary:group:open-parenthesis",
    ")": "boundary:group:close-parenthesis",
    "[": "boundary:group:open-bracket",
    "]": "boundary:group:close-bracket",
    "{": "boundary:group:open-brace",
    "}": "boundary:group:close-brace",
    '"': "boundary:quotation:double",
    "“": "boundary:quotation:open-double",
    "”": "boundary:quotation:close-double",
    "'": "boundary:quotation:single",
    "‘": "boundary:quotation:open-single",
    "’": "boundary:quotation:close-single",
    "/": "boundary:alternative:slash",
    "\\": "boundary:path:backslash",
    "…": "boundary:continuation:ellipsis",
    "_": "boundary:join:underscore",
    "=": "boundary:relation:equals",
    "+": "boundary:relation:plus",
    "*": "boundary:emphasis-or-multiply:asterisk",
    "#": "boundary:heading-or-reference:hash",
    "@": "boundary:address:at-sign",
    "&": "boundary:relation:ampersand",
    "%": "boundary:quantity:percent",
    "$": "boundary:currency:dollar",
}


def anchorize(text: str) -> list[str]:
    """Return every complete word and every non-whitespace structural object."""
    anchors: list[str] = []
    source = str(text)
    cursor = 0
    for sha_match in SHA_RE.finditer(source):
        anchors.extend(_anchorize_segment(source[cursor:sha_match.start()]))
        value = sha_match.group(0)
        anchors.append(f"object:sha:{normalize_anchor(value)}")
        cursor = sha_match.end()
    anchors.extend(_anchorize_segment(source[cursor:]))
    return anchors


def _anchorize_segment(text: str) -> list[str]:
    anchors: list[str] = []
    for match in WORD_RE.finditer(text):
        value = match.group(0)
        if any(char.isalnum() or char == "_" for char in value):
            anchors.append(normalize_anchor(value))
        else:
            anchors.append(structural_anchor(value))
    return anchors


def normalize_anchor(anchor: str) -> str:
    """Return source identity unchanged; TrueMem performs zero normalization."""
    return str(anchor or "")


def structural_anchor(value: str) -> str:
    source = str(value)
    known = PUNCTUATION_ROLES.get(source)
    if known:
        return known
    codepoints = "-".join(f"u+{ord(char):04x}" for char in source)
    names = "+".join(unicodedata.name(char, "unknown").casefold().replace(" ", "-") for char in source)
    return f"object:{codepoints}:{names}"


def anchor_kind(anchor: str) -> str:
    if anchor.startswith("boundary:"):
        return "boundary"
    if anchor.startswith("object:"):
        return "object"
    identity = anchor.casefold()
    if identity in RELATION_ANCHORS:
        return "relation"
    if identity in GLUE_ANCHORS:
        return "glue"
    return "content"


def answer_direction_anchors(anchors: list[str]) -> list[str]:
    """Choose answer-direction anchors without deleting anchors from the map."""
    out: list[str] = []
    seen: set[str] = set()
    for anchor in anchors:
        if anchor_kind(anchor) not in {"content", "relation"} or anchor in seen:
            continue
        out.append(anchor)
        seen.add(anchor)
    return out


def direction_weight(anchor: str) -> float:
    return {"content": 1.0, "relation": 0.5, "object": 0.65, "glue": 0.0, "boundary": 0.0}[anchor_kind(anchor)]


def anchor_surface(anchor: str) -> str:
    """Return the visible mark for a known structural anchor."""
    for mark, role in PUNCTUATION_ROLES.items():
        if role == anchor:
            return mark
    return anchor


def anchors_to_text(anchors: list[str]) -> str:
    """Render an anchor path without exposing structural-anchor names."""
    closing = {".", "!", "?", ",", ";", ":", ")", "]", "}", "%", "…"}
    opening = {"(", "[", "{"}
    out = ""
    previous = ""
    for anchor in anchors:
        value = anchor_surface(anchor)
        if not out:
            out = value
        elif value in closing:
            out += value
        elif previous in opening:
            out += value
        else:
            out += " " + value
        previous = value
    return out


def expand_query_anchors(anchors: list[str]) -> list[str]:
    """Preserve query anchors exactly; intake owns exact source identity."""
    return list(dict.fromkeys(anchor for anchor in anchors if anchor))


def symbol_for(anchor: str) -> str:
    return "0x" + sha1_text(anchor)[:SYMBOL_HEX_CHARS].upper()


def active_symbol_for(anchor: str) -> str:
    engine_module = sys.modules.get("truemem.engine")
    dataset_symbol_for = getattr(engine_module, "symbol_for", None) if engine_module is not None else None
    if dataset_symbol_for is not None and dataset_symbol_for is not symbol_for:
        return dataset_symbol_for(anchor)
    return symbol_for(anchor)


def symbol_bytes(anchor: str) -> bytes:
    return bytes.fromhex(active_symbol_for(anchor)[2:])


def symbol_hex(raw: bytes) -> str:
    return "0x" + raw.hex().upper()


def assert_no_symbol_collisions(anchors: Counter[str]) -> None:
    seen: dict[str, str] = {}
    for anchor in sorted(anchors):
        symbol = active_symbol_for(anchor)
        existing = seen.get(symbol)
        if existing is not None and existing != anchor:
            raise ValueError(f"symbol collision in dataset-local symbol namespace: {existing!r} and {anchor!r} both map to {symbol}")
        seen[symbol] = anchor
