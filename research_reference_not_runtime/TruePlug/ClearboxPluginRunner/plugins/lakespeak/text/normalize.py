"""Canonical text normalization for LakeSpeak.

ONE definition of tokenization, used everywhere:
  - lakespeak/index/bm25.py          (sparse retrieval)
  - lakespeak/retrieval/query.py     (query analysis + snippet extraction)
  - lakespeak/index/anchor_reranker.py (anchor extraction from queries)
  - lakespeak/ingest/pipeline.py     (anchor extraction from chunks)

Rules (frozen for TOKENIZER_VERSION = "v1"):
  1. Unicode NFKC normalization
  2. Lowercase
  3. Replace punctuation with spaces (never delete — avoids token concatenation)
  4. Collapse whitespace
  5. Split on whitespace
  6. Keep digits
  7. Strip empty tokens

Punctuation = everything that is NOT alphanumeric, apostrophe, or whitespace.
Apostrophes are kept internal to tokens (don't → don't, not dont).
Hyphens become spaces (fire-resistant → fire resistant → ["fire", "resistant"]).
"""

import re
import unicodedata

TOKENIZER_VERSION = "v1"

# Everything that isn't a letter, digit, apostrophe, or whitespace → space
_PUNCT_RE = re.compile(r"[^\w']+", re.UNICODE)

# Apostrophes at token boundaries (leading/trailing)
_BOUNDARY_APOS_RE = re.compile(r"(^'+|'+$)")


def normalize_text(text: str) -> str:
    """Normalize raw text to a canonical lowercase string.

    Steps: NFKC → lowercase → punctuation→space → collapse whitespace → strip.
    """
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    text = _PUNCT_RE.sub(" ", text)
    text = text.strip()
    # Collapse internal whitespace
    text = re.sub(r"\s+", " ", text)
    return text


def tokenize(text: str) -> list[str]:
    """Normalize text and split into tokens.

    Returns a list of non-empty lowercase tokens with punctuation removed.
    Internal apostrophes are preserved (e.g. "don't" stays as one token).
    """
    normalized = normalize_text(text)
    tokens = []
    for raw in normalized.split():
        # Strip leading/trailing apostrophes (but keep internal ones)
        token = _BOUNDARY_APOS_RE.sub("", raw)
        if token:
            tokens.append(token)
    return tokens
