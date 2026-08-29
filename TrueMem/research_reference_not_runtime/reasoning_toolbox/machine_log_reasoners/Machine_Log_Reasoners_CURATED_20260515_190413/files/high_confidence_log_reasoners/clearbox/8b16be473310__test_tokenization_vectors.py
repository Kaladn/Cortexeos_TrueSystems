"""Golden test vectors for canonical tokenization.

This file is the drift detector. If someone tweaks normalization,
these tests fail immediately instead of "mysterious retrieval regression".

Run:  python -m pytest tests/test_tokenization_vectors.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "plugins"))

from lakespeak.text.normalize import normalize_text, tokenize, TOKENIZER_VERSION


# ── Version Pin ────────────────────────────────────────────────

def test_tokenizer_version():
    assert TOKENIZER_VERSION == "v1"


# ── normalize_text() ──────────────────────────────────────────

NORMALIZE_VECTORS = [
    # (input, expected_output)
    ("Hello World", "hello world"),
    ("  extra   spaces  ", "extra spaces"),
    ("Clearbox—Fire!!", "clearbox fire"),
    ("fire-resistant", "fire resistant"),
    ("don't", "don't"),
    ("it's a tree's bark", "it's a tree's bark"),
    ("'quoted'", "'quoted'"),  # Apostrophe stripping happens in tokenize(), not here
    ("C:\\Users\\Name\\file.txt", "c users name file txt"),
    ("6-1-6 mapping", "6 1 6 mapping"),
    ("ALL CAPS CLEARBOX", "all caps clearbox"),
    ("", ""),
    ("   ", ""),
    # Unicode: NFKC normalizes fullwidth chars
    ("\uff26\uff4f\uff52\uff45\uff53\uff54", "clearbox"),  # Fullwidth CLEARBOX
    # Em-dash, en-dash, hyphen all become spaces
    ("old\u2014growth\u2013clearbox-fire", "old growth clearbox fire"),
    # Digits preserved
    ("plot42 tree99", "plot42 tree99"),
    # Punctuation soup
    ("why avoid fire in the clearbox?", "why avoid fire in the clearbox"),
    ("...leading...dots...", "leading dots"),
    # Tabs and newlines collapse
    ("line\tone\nline\ttwo", "line one line two"),
]


def test_normalize_text():
    for raw, expected in NORMALIZE_VECTORS:
        result = normalize_text(raw)
        assert result == expected, (
            f"normalize_text({raw!r})\n"
            f"  expected: {expected!r}\n"
            f"  got:      {result!r}"
        )


# ── tokenize() ────────────────────────────────────────────────

TOKENIZE_VECTORS = [
    # (input, expected_tokens)
    ("why avoid fire in the clearbox?", ["why", "avoid", "fire", "in", "the", "clearbox"]),
    ("Clearbox—Fire!!", ["clearbox", "fire"]),
    ("fire-resistant", ["fire", "resistant"]),
    ("don't stop", ["don't", "stop"]),
    ("6-1-6 mapping", ["6", "1", "6", "mapping"]),
    ("C:\\Users\\Name\\file.txt", ["c", "users", "name", "file", "txt"]),
    ("", []),
    ("   ", []),
    ("'hello' 'world'", ["hello", "world"]),
    ("old-growth clearbox—fire!!", ["old", "growth", "clearbox", "fire"]),
    # Single characters preserved (callers filter by min_length, not tokenizer)
    ("a b c", ["a", "b", "c"]),
    # Digits
    ("plot42", ["plot42"]),
    ("42", ["42"]),
    # Apostrophe edge cases
    ("'twas the night", ["twas", "the", "night"]),
    ("trees'''", ["trees"]),
    ("it's", ["it's"]),
]


def test_tokenize():
    for raw, expected in TOKENIZE_VECTORS:
        result = tokenize(raw)
        assert result == expected, (
            f"tokenize({raw!r})\n"
            f"  expected: {expected!r}\n"
            f"  got:      {result!r}"
        )


# ── Consistency: tokenize == normalize_text.split (modulo apostrophe strip) ──

def test_tokenize_consistency():
    """tokenize() should always produce the same tokens as
    splitting normalize_text() output (with boundary apostrophe cleanup)."""
    cases = [
        "Clearbox fire prevention 101",
        "what's the fire-resistant species?",
        "6-1-6 mapping results",
        "old\u2014growth\u2013canopy",
    ]
    for text in cases:
        tokens = tokenize(text)
        # Every token must appear in normalized text
        normalized = normalize_text(text)
        for t in tokens:
            assert t in normalized or t.replace("'", "") in normalized, (
                f"Token {t!r} from tokenize({text!r}) "
                f"not found in normalize_text output {normalized!r}"
            )


# ── Idempotency ────────────────────────────────────────────────

def test_normalize_idempotent():
    """Normalizing already-normalized text should be a no-op."""
    cases = ["hello world", "fire resistant", "don't stop", "6 1 6 mapping"]
    for text in cases:
        assert normalize_text(text) == text
        assert normalize_text(normalize_text(text)) == text


# ── Punctuation → Space (NOT deletion) ────────────────────────

def test_punctuation_becomes_space_not_deletion():
    """Critical invariant: punctuation replacement must never
    concatenate adjacent words."""
    # The bug this prevents: "fire-resistant" → "fireresistant"
    assert "fireresistant" not in normalize_text("fire-resistant")
    assert normalize_text("fire-resistant") == "fire resistant"

    # Em-dash must not concatenate
    assert "clearboxfire" not in normalize_text("clearbox—fire")
    assert normalize_text("clearbox—fire") == "clearbox fire"


if __name__ == "__main__":
    print(f"Tokenizer version: {TOKENIZER_VERSION}")
    print()

    print("=== normalize_text vectors ===")
    for raw, expected in NORMALIZE_VECTORS:
        result = normalize_text(raw)
        status = "PASS" if result == expected else "FAIL"
        print(f"  [{status}] {raw!r} -> {result!r}")

    print()
    print("=== tokenize vectors ===")
    for raw, expected in TOKENIZE_VECTORS:
        result = tokenize(raw)
        status = "PASS" if result == expected else "FAIL"
        print(f"  [{status}] {raw!r} -> {result!r}")
