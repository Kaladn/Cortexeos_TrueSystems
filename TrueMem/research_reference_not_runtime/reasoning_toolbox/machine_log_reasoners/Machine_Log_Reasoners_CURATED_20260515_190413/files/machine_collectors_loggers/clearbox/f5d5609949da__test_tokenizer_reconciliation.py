"""Golden vectors: canonical tokenizer reconciliation.

Step 6 — verifies that the relation extraction path now uses the same
canonical tokenizer as anchor extraction.  Every vector here represents
a case where the OLD bridge.tokenize() and the canonical tokenize()
would produce different tokens.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure plugins/ is importable
_root = Path(__file__).resolve().parents[1]
if str(_root / "plugins") not in sys.path:
    sys.path.insert(0, str(_root / "plugins"))
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from lakespeak.text.normalize import tokenize as _canonical_tokenize
from core.services.compute import ComputeService


# ── Vectors: (input, expected_canonical_tokens) ──────────────────────
# Each vector exercises a divergence that bridge.tokenize would get wrong.

RECONCILIATION_VECTORS = [
    # Accented chars: canonical keeps é (NFKC preserves composed accents;
    # \w includes them). Bridge [^A-Za-z0-9']+ would SPLIT on é → ["caf"].
    ("caf\u00e9\u2013resistant", ["caf\u00e9", "resistant"]),
    # Multiple accented chars preserved as word characters
    ("na\u00efve r\u00e9sum\u00e9", ["na\u00efve", "r\u00e9sum\u00e9"]),
    # Boundary apostrophes stripped by canonical; bridge keeps them
    ("'hello' world", ["hello", "world"]),
    # En-dash (U+2013) and em-dash (U+2014) are Unicode punct → space
    ("pre\u2013process em\u2014dash", ["pre", "process", "em", "dash"]),
    # Curly quotes (U+2018, U+2019) are punct, not word chars
    ("\u2018quoted\u2019 text", ["quoted", "text"]),
    # Mixed: accent + Unicode punct + boundary apostrophe + case folding
    ("'caf\u00e9's' recipe\u2014Pro\u2013Tip", ["caf\u00e9's", "recipe", "pro", "tip"]),
    # Fullwidth characters (NFKC normalizes ＡＢＣ → ABC → abc)
    ("\uff21\uff22\uff23 test", ["abc", "test"]),
    # Superscript (NFKC: ² → 2, merges with adjacent letter)
    ("x\u00b2 + y\u00b2", ["x2", "y2"]),
    # Plain ASCII — identical on both paths
    ("the cat sat on a mat", ["the", "cat", "sat", "on", "a", "mat"]),
    # Numbers and internal apostrophes preserved
    ("don't stop 42 times", ["don't", "stop", "42", "times"]),
]


def test_seam_matches_canonical():
    """ComputeService.tokenize() == _canonical_tokenize() on every vector."""
    for text, expected in RECONCILIATION_VECTORS:
        seam = ComputeService.tokenize(text)
        canonical = _canonical_tokenize(text)
        assert seam == canonical, (
            f"Seam/canonical mismatch on {text!r}: "
            f"seam={seam}, canonical={canonical}"
        )
        assert seam == expected, (
            f"Unexpected tokens for {text!r}: got {seam}, expected {expected}"
        )


def test_canonical_tokens_are_lowercase():
    """Every token from the canonical path is lowercase."""
    for text, _ in RECONCILIATION_VECTORS:
        tokens = ComputeService.tokenize(text)
        for tok in tokens:
            assert tok == tok.lower(), (
                f"Non-lowercase token {tok!r} from {text!r}"
            )


def test_no_empty_tokens():
    """Canonical tokenizer never produces empty strings."""
    for text, _ in RECONCILIATION_VECTORS:
        tokens = ComputeService.tokenize(text)
        assert all(len(t) > 0 for t in tokens), (
            f"Empty token in output for {text!r}: {tokens}"
        )


def test_encode_decode_roundtrip_preserves_canonical():
    """Round-trip through bridge._encode_tokens → _decode_index
    preserves canonical token form (no normalization drift)."""
    # Minimal mock of bridge encode/decode (same logic as ClearboxLexiconBridge)
    vocab_index: dict[str, int] = {}
    index_vocab: list[str] = []

    def encode(tokens):
        ids = []
        for tok in tokens:
            norm = tok.lower()  # bridge.normalise_token
            if norm not in vocab_index:
                vocab_index[norm] = len(index_vocab)
                index_vocab.append(norm)
            ids.append(vocab_index[norm])
        return ids

    def decode(idx):
        return index_vocab[idx]

    for text, expected in RECONCILIATION_VECTORS:
        tokens = ComputeService.tokenize(text)
        ids = encode(tokens)
        roundtripped = [decode(i) for i in ids]
        assert roundtripped == tokens, (
            f"Round-trip drift on {text!r}: "
            f"tokens={tokens}, roundtripped={roundtripped}"
        )
