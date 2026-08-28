from __future__ import annotations

import re
import sys
from collections import Counter

from .base import SYMBOL_BYTES, SYMBOL_HEX_CHARS, SYMBOL_SYSTEM, sha1_text

WORD_RE = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?|[^\sA-Za-z0-9]", re.UNICODE)
STOP_ANCHORS = {
    "a", "about", "an", "and", "are", "as", "at", "be", "by", "can", "do",
    "does", "doc", "docs", "document", "documents", "explain", "explained",
    "explains", "file", "files", "for", "from", "how", "in", "into", "is",
    "it", "of", "on", "or", "project", "say", "said", "says", "mention",
    "mentioned", "mentions", "that", "the", "this", "to", "what", "where",
    "which", "who", "why", "with",
}


def anchorize(text: str) -> list[str]:
    anchors: list[str] = []
    for match in WORD_RE.finditer(text):
        value = match.group(0).strip().casefold()
        if not value:
            continue
        if not any(ch.isalnum() for ch in value):
            continue
        if value in STOP_ANCHORS:
            continue
        if value.isalnum() and any(ch.isalpha() for ch in value) and any(ch.isdigit() for ch in value):
            anchors.extend(ch for ch in value if ch.isalnum())
        else:
            anchors.append(normalize_anchor(value))
    return anchors

def normalize_anchor(anchor: str) -> str:
    value = str(anchor or "").casefold().strip()
    if len(value) > 4 and value.endswith("ies"):
        return value[:-3] + "y"
    if len(value) > 3 and value.endswith("s") and not value.endswith("ss"):
        return value[:-1]
    return value

def expand_query_anchors(anchors: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for anchor in anchors:
        variants = [anchor, normalize_anchor(anchor)]
        if anchor.isalpha() and len(anchor) > 2:
            variants.append(anchor + "s")
        for variant in variants:
            if variant and variant not in STOP_ANCHORS and variant not in seen:
                out.append(variant)
                seen.add(variant)
    return out

def symbol_for(anchor: str) -> str:
    return "0x" + sha1_text(anchor)[:SYMBOL_HEX_CHARS].upper()

def active_symbol_for(anchor: str) -> str:
    engine_module = sys.modules.get("awrag.engine")
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
            raise ValueError(
                "symbol collision in dataset-local symbol namespace: "
                f"{existing!r} and {anchor!r} both map to {symbol}"
            )
        seen[symbol] = anchor
