"""Genesis Citation Tool — corpus parser.

Parses TRAINING_CORPUS.md into a list of Block objects.
Block boundaries are defined by ━━━ separator lines (U+2501).

Structure of the corpus file:
    ━━━ (separator)
    GENESIS_BLOCK_ID: G-XXXX
    SOURCE:           ...
    DATE_RANGE:       ...
    SCOPE:            ...
    WRITE_PERMS:      READ_ONLY
    [DERIVED_SUMMARY: true]         ← optional
    [DERIVATION_BASIS: G-XXXX, ...]  ← optional
    ━━━ (separator)
    <block body text>
    ━━━ (separator — begins next block header)
    ...

The separator that closes one block's header is the same separator that
opens the next block's body terminator / next block's header opener.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .config import (
    CORPUS_PATH,
    EXPECTED_BLOCK_COUNT,
    REQUIRED_HEADER_FIELDS,
    SEPARATOR_CHAR,
    SEPARATOR_MIN_LEN,
)


# ── Block dataclass ───────────────────────────────────────────────────────────

@dataclass
class Block:
    tag: str                          # G-0001
    source: str                       # verbatim from SOURCE field
    date_range: str                   # verbatim from DATE_RANGE field
    scope: str                        # verbatim from SCOPE field
    write_perms: str                  # always READ_ONLY
    derived: bool                     # True if DERIVED_SUMMARY: true
    derivation_basis: list[str]       # e.g. ["G-0001", "G-0003"]
    body: str                         # verbatim block body (stripped)
    block_hash: str                   # sha256:<hex> of normalized body
    span: dict[str, int]              # {"start_line": N, "end_line": M}  (1-indexed)
    raw_header_lines: list[str] = field(default_factory=list, repr=False)

    @property
    def title(self) -> str:
        """Derived from SCOPE field — used as human-readable title."""
        return self.scope

    @property
    def series(self) -> int:
        """Numeric block number extracted from tag."""
        return int(self.tag.split("-")[1])


# ── Separator detection ───────────────────────────────────────────────────────

def _is_separator(line: str) -> bool:
    stripped = line.strip()
    return (
        len(stripped) >= SEPARATOR_MIN_LEN
        and all(c == SEPARATOR_CHAR for c in stripped)
    )


# ── Header parsing ────────────────────────────────────────────────────────────

_HEADER_RE = re.compile(r"^([A-Z_]+)\s*:\s*(.*?)\s*$")


def _parse_header(lines: list[str]) -> dict[str, str]:
    """Parse header lines into a key→value dict. Strips excess whitespace."""
    result: dict[str, str] = {}
    for line in lines:
        m = _HEADER_RE.match(line.rstrip())
        if m:
            result[m.group(1)] = m.group(2).strip()
    return result


# ── Body normalization + hashing ──────────────────────────────────────────────

def _normalize_body(body: str) -> str:
    """Normalize body for hashing:
    - strip leading/trailing whitespace from each line
    - collapse consecutive blank lines into a single blank line
    - strip leading/trailing blank lines from the whole body
    """
    lines = [ln.strip() for ln in body.splitlines()]
    normalized: list[str] = []
    prev_blank = False
    for ln in lines:
        if ln == "":
            if not prev_blank:
                normalized.append("")
            prev_blank = True
        else:
            normalized.append(ln)
            prev_blank = False
    # Strip leading/trailing blank lines
    while normalized and normalized[0] == "":
        normalized.pop(0)
    while normalized and normalized[-1] == "":
        normalized.pop()
    return "\n".join(normalized)


def _hash_body(body: str) -> str:
    """SHA-256 of normalized body text (UTF-8 encoded)."""
    normalized = _normalize_body(body)
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


# ── Main parser ───────────────────────────────────────────────────────────────

def parse_corpus(path: Path = CORPUS_PATH) -> list[Block]:
    """Parse TRAINING_CORPUS.md and return list of Block objects.

    Raises:
        FileNotFoundError: if corpus file doesn't exist
        ValueError: on spec violations (missing fields, duplicate tags, etc.)
    """
    if not path.exists():
        raise FileNotFoundError(f"Corpus not found: {path}")

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    blocks: list[Block] = []

    # State machine
    # States: SCAN → HEADER → BODY
    state = "SCAN"
    header_lines: list[str] = []
    body_lines: list[str] = []
    header_start_line = 0   # 1-indexed line where header started
    body_start_line = 0     # 1-indexed line where body started

    def _finish_block(body_end_line: int) -> None:
        """Build a Block from accumulated header_lines + body_lines."""
        hdr = _parse_header(header_lines)
        # Validate required fields
        for f in REQUIRED_HEADER_FIELDS:
            if f not in hdr:
                raise ValueError(
                    f"SPEC_VIOLATION: missing '{f}' in block near line {header_start_line}"
                )

        tag = hdr["GENESIS_BLOCK_ID"]
        if not re.fullmatch(r"G-\d{4}", tag):
            raise ValueError(f"SPEC_VIOLATION: invalid tag format '{tag}'")

        body_text = "\n".join(body_lines)

        derived = hdr.get("DERIVED_SUMMARY", "false").lower() == "true"
        basis_raw = hdr.get("DERIVATION_BASIS", "")
        basis = [b.strip() for b in basis_raw.split(",") if b.strip()] if basis_raw else []

        blocks.append(Block(
            tag=tag,
            source=hdr["SOURCE"],
            date_range=hdr["DATE_RANGE"],
            scope=hdr["SCOPE"],
            write_perms=hdr["WRITE_PERMS"],
            derived=derived,
            derivation_basis=basis,
            body=body_text,
            block_hash=_hash_body(body_text),
            span={
                "start_line": header_start_line,
                "end_line": body_end_line,
            },
            raw_header_lines=list(header_lines),
        ))

    for line_no, raw_line in enumerate(lines, start=1):
        if _is_separator(raw_line):
            if state == "SCAN":
                # First separator — begin collecting header
                state = "HEADER"
                header_lines = []
                header_start_line = line_no
            elif state == "HEADER":
                # Second separator — end of header, start of body
                state = "BODY"
                body_lines = []
                body_start_line = line_no
            elif state == "BODY":
                # Separator in body = end of this block, start of next header
                _finish_block(body_end_line=line_no - 1)
                state = "HEADER"
                header_lines = []
                header_start_line = line_no
        else:
            if state == "HEADER":
                header_lines.append(raw_line)
            elif state == "BODY":
                body_lines.append(raw_line)
            # SCAN: skip preamble/comment lines

    # Handle last block (no trailing separator)
    if state == "BODY" and header_lines or (state == "BODY"):
        _finish_block(body_end_line=len(lines))

    # ── Validation ────────────────────────────────────────────────────────────
    _validate_blocks(blocks)

    return blocks


def _validate_blocks(blocks: list[Block]) -> None:
    """Post-parse validation: count, uniqueness, contiguity."""
    if len(blocks) != EXPECTED_BLOCK_COUNT:
        raise ValueError(
            f"SPEC_VIOLATION: expected {EXPECTED_BLOCK_COUNT} blocks, got {len(blocks)}"
        )

    seen_tags: set[str] = set()
    for i, block in enumerate(blocks):
        if block.tag in seen_tags:
            raise ValueError(f"SPEC_VIOLATION: duplicate tag {block.tag}")
        seen_tags.add(block.tag)

        # Check contiguity (G-0001, G-0002, ...)
        expected_tag = f"G-{i + 1:04d}"
        if block.tag != expected_tag:
            raise ValueError(
                f"SPEC_VIOLATION: tag out of order — expected {expected_tag}, got {block.tag}"
            )
