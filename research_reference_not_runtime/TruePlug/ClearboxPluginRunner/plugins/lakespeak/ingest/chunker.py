"""Deterministic text chunker for LakeSpeak.

Splits text into overlapping chunks with stable, hashable IDs.
Paragraph boundaries act as hard walls (matching bridge behavior).
Within paragraphs, applies sliding window with overlap.
"""

from __future__ import annotations

import hashlib
import re
from typing import List, Tuple

from lakespeak.schemas import ChunkRef, CHUNK_REF_VERSION


# ── Paragraph splitter (span-preserving) ────────────────────

_PARA_SPLIT_RE = re.compile(r"\n\s*\n")


def _split_paragraphs_with_spans(text: str) -> List[Tuple[int, int, str]]:
    """Split text on double-newline boundaries, preserving exact spans.

    Returns list of (start, end, stripped_text) tuples where start/end
    are character offsets into the original text.
    """
    # Find all paragraph separator positions
    separators = [(m.start(), m.end()) for m in _PARA_SPLIT_RE.finditer(text)]

    # Build paragraph spans from the gaps between separators
    paras: List[Tuple[int, int, str]] = []
    prev_end = 0

    for sep_start, sep_end in separators:
        raw = text[prev_end:sep_start]
        stripped = raw.strip()
        if stripped:
            # Find the stripped text's true start within the raw slice
            lstrip_offset = len(raw) - len(raw.lstrip())
            paras.append((prev_end + lstrip_offset, sep_start - (len(raw) - len(raw.rstrip())), stripped))
        prev_end = sep_end

    # Last paragraph (after final separator)
    raw = text[prev_end:]
    stripped = raw.strip()
    if stripped:
        lstrip_offset = len(raw) - len(raw.lstrip())
        paras.append((prev_end + lstrip_offset, len(text) - (len(raw) - len(raw.rstrip())), stripped))

    return paras


# ── Simple whitespace tokenizer (span-aware) ────────────────

def _tokenize_with_offsets(text: str) -> List[Tuple[str, int, int]]:
    """Whitespace tokenizer that returns (token, start, end) relative to text."""
    tokens: List[Tuple[str, int, int]] = []
    for m in re.finditer(r"\S+", text):
        tokens.append((m.group(), m.start(), m.end()))
    return tokens


# ── Chunk ID generation ──────────────────────────────────────

def _make_chunk_id(receipt_id: str, ordinal: int) -> str:
    """Deterministic chunk ID: ch_{sha256(receipt_id:ordinal)[:16]}"""
    raw = f"{receipt_id}:{ordinal}"
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    return f"ch_{h}"


def _text_hash(text: str) -> str:
    """SHA-256 of chunk text."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ── Public API ───────────────────────────────────────────────

def chunk_text(
    text: str,
    receipt_id: str,
    source_hash: str,
    chunk_size: int = 512,
    overlap: int = 64,
) -> List[ChunkRef]:
    """Split text into overlapping token chunks.

    Args:
        text: Raw source text
        receipt_id: Parent ingest receipt ID
        source_hash: SHA-256 of the full source text
        chunk_size: Max tokens per chunk
        overlap: Tokens of overlap between adjacent chunks

    Returns:
        List of ChunkRef records with deterministic IDs.
        span_start/span_end are exact character offsets into the original text.
    """
    paragraphs = _split_paragraphs_with_spans(text)
    chunks: List[ChunkRef] = []
    ordinal = 0

    for para_start, _para_end, para_text in paragraphs:
        token_triples = _tokenize_with_offsets(para_text)

        if not token_triples:
            continue

        # Sliding window within paragraph
        start = 0
        while start < len(token_triples):
            end = min(start + chunk_size, len(token_triples))
            window = token_triples[start:end]

            chunk_text_str = " ".join(tok for tok, _s, _e in window)

            # Exact character offsets into original text
            span_start = para_start + window[0][1]   # first token's offset within para + para offset
            span_end = para_start + window[-1][2]     # last token's end offset

            chunk = ChunkRef(
                schema_version=CHUNK_REF_VERSION,
                chunk_id=_make_chunk_id(receipt_id, ordinal),
                receipt_id=receipt_id,
                ordinal=ordinal,
                source_hash=source_hash,
                span_start=span_start,
                span_end=span_end,
                text_hash=_text_hash(chunk_text_str),
                token_count=len(window),
                text=chunk_text_str,
            )
            chunks.append(chunk)
            ordinal += 1

            # Advance by (chunk_size - overlap), but at least 1
            step = max(1, chunk_size - overlap)
            if end >= len(token_triples):
                break
            start += step

    return chunks
