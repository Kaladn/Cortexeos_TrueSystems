"""Tests for genesis_cite.parser — corpus parsing."""

import pytest
from pathlib import Path

from plugins.genesis_cite.parser import parse_corpus, _hash_body, _normalize_body
from plugins.genesis_cite.config import CORPUS_PATH, EXPECTED_BLOCK_COUNT, REQUIRED_HEADER_FIELDS


# ── Corpus parse ─────────────────────────────────────────────────────────────

def test_parse_all_blocks():
    """68 blocks parsed, no duplicates, all required fields present."""
    blocks = parse_corpus()
    assert len(blocks) == EXPECTED_BLOCK_COUNT, (
        f"Expected {EXPECTED_BLOCK_COUNT} blocks, got {len(blocks)}"
    )
    tags = [b.tag for b in blocks]
    assert len(tags) == len(set(tags)), "Duplicate tags found"
    # Map raw header field names → Block attribute names
    _field_map = {
        "GENESIS_BLOCK_ID": "tag",
        "SOURCE": "source",
        "DATE_RANGE": "date_range",
        "SCOPE": "scope",
        "WRITE_PERMS": "write_perms",
    }
    for block in blocks:
        for field in REQUIRED_HEADER_FIELDS:
            attr = _field_map.get(field, field.lower())
            val = getattr(block, attr, None)
            assert val is not None and val != "", (
                f"{block.tag}: missing required field {field} (attr={attr})"
            )


def test_block_hashes_stable():
    """Re-parsing produces identical block hashes (deterministic)."""
    blocks_a = parse_corpus()
    blocks_b = parse_corpus()
    for a, b in zip(blocks_a, blocks_b):
        assert a.block_hash == b.block_hash, (
            f"{a.tag}: hash changed between parses: {a.block_hash!r} vs {b.block_hash!r}"
        )


def test_tag_format():
    """All tags match G-XXXX format with zero-padded 4 digits."""
    import re
    blocks = parse_corpus()
    for block in blocks:
        assert re.fullmatch(r"G-\d{4}", block.tag), f"Bad tag format: {block.tag}"


def test_tags_contiguous():
    """Tags are G-0001 through G-0068 in order, no gaps."""
    blocks = parse_corpus()
    for i, block in enumerate(blocks):
        expected = f"G-{i + 1:04d}"
        assert block.tag == expected, f"Position {i}: expected {expected}, got {block.tag}"


def test_write_perms_read_only():
    """All blocks have WRITE_PERMS = READ_ONLY."""
    blocks = parse_corpus()
    for block in blocks:
        assert block.write_perms == "READ_ONLY", (
            f"{block.tag}: write_perms is {block.write_perms!r}, expected READ_ONLY"
        )


def test_span_fields():
    """Every block has start_line and end_line in span."""
    blocks = parse_corpus()
    for block in blocks:
        assert "start_line" in block.span, f"{block.tag}: missing span.start_line"
        assert "end_line" in block.span, f"{block.tag}: missing span.end_line"
        assert block.span["start_line"] > 0, f"{block.tag}: start_line must be > 0"
        assert block.span["end_line"] >= block.span["start_line"], (
            f"{block.tag}: end_line < start_line"
        )


def test_g0001_fields():
    """G-0001 has expected title/source/scope."""
    blocks = parse_corpus()
    g1 = next(b for b in blocks if b.tag == "G-0001")
    assert "README" in g1.source or "VERSION" in g1.source, (
        f"G-0001 source unexpected: {g1.source}"
    )
    assert g1.scope, "G-0001 scope is empty"
    assert g1.body, "G-0001 body is empty"


def test_body_not_empty():
    """No block has an empty body."""
    blocks = parse_corpus()
    for block in blocks:
        assert block.body.strip(), f"{block.tag}: body is empty"


def test_hash_normalization_stable():
    """_normalize_body → _hash_body is stable for known input."""
    text = "  line one  \n\nline two\n\n\nline three  \n"
    h1 = _hash_body(text)
    h2 = _hash_body(text)
    assert h1 == h2
    assert h1.startswith("sha256:")


def test_no_writes_to_corpus():
    """Attempting to write to the corpus path raises PermissionError or is blocked."""
    # The parser only reads — this test verifies we don't have any write path.
    # We can't literally test the OS-level guard here, but we verify the
    # parse_corpus function doesn't open the file in write mode.
    import builtins
    original_open = builtins.open
    write_attempts = []

    def guarded_open(file, mode="r", **kwargs):
        if "w" in str(mode) or "a" in str(mode):
            path_str = str(file)
            if "TRAINING_CORPUS" in path_str or "GENESIS_SPEC" in path_str:
                write_attempts.append(path_str)
                raise PermissionError(f"Write blocked by test guard: {path_str}")
        return original_open(file, mode, **kwargs)

    builtins.open = guarded_open
    try:
        parse_corpus()
    finally:
        builtins.open = original_open

    assert write_attempts == [], f"Parser attempted writes: {write_attempts}"
