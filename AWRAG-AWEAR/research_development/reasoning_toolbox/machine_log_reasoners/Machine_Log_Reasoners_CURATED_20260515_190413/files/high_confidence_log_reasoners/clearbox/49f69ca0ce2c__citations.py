"""Chat Citations — extract, normalize, resolve, validate.

Canonical citation coordinate: YYYY-MM-DD:L<line>
  - Line number is the authority (1-indexed, matches JSONL position).
  - The JSON `id` field is a soft cross-check, not the anchor.

Accepted input formats (backward compatible):
  [CITE 2026-02-07#15]           → 2026-02-07:L15
  [CITE 2026-02-07:L15]         → 2026-02-07:L15
  [CITE 2026-02-07#15 USER]     → 2026-02-07:L15  (role captured separately)

No external dependencies.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from security.data_paths import CHAT_THREADS_DIR
from security.secure_storage import secure_read_lines
THREADS_DIR = CHAT_THREADS_DIR

# ──────────────────────────────────────────────
# Regex: matches both legacy (#) and canonical (:L) formats
#   Group 1: day   (YYYY-MM-DD)
#   Group 2: separator  (# or :L)
#   Group 3: line number  (digits)
#   Group 4: optional role  (USER, AI, etc.)
# ──────────────────────────────────────────────
_CITE_RE = re.compile(
    r"\[CITE\s+"
    r"(\d{4}-\d{2}-\d{2})"      # group 1: day
    r"(?:#|:L)"                   # separator (# or :L)
    r"(\d+)"                      # group 2: line number
    r"(?:\s+([A-Za-z]+))?"        # group 3: optional role
    r"\s*\]"
)


# ──────────────────────────────────────────────
# Data structures
# ──────────────────────────────────────────────

@dataclass
class CitationRef:
    """A single citation extracted from text."""
    day: str                          # "2026-02-07"
    line: int                         # 1-indexed JSONL line number
    role: Optional[str] = None        # "USER" / "AI" as found in tag
    raw_tag: str = ""                 # original matched text e.g. "[CITE 2026-02-07#15]"
    canonical: str = ""               # normalized form "2026-02-07:L15"
    # Populated by resolve()
    valid: bool = False
    source_sender: Optional[str] = None
    source_content: Optional[str] = None
    source_branch: Optional[str] = None
    source_timestamp: Optional[str] = None
    source_hash: Optional[str] = None
    source_id: Optional[int] = None   # JSON `id` field — cross-check only
    id_mismatch: bool = False         # True if JSON id ≠ line number


@dataclass
class CitationReport:
    """Result of validating all citations in a piece of text."""
    citations: List[CitationRef] = field(default_factory=list)
    valid_count: int = 0
    invalid_count: int = 0
    id_mismatch_count: int = 0
    cited_days: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Serialize for JSON API response."""
        return {
            "citations": [_ref_to_dict(c) for c in self.citations],
            "valid_count": self.valid_count,
            "invalid_count": self.invalid_count,
            "id_mismatch_count": self.id_mismatch_count,
            "cited_days": self.cited_days,
        }


def _ref_to_dict(ref: CitationRef) -> dict:
    d: dict = {
        "tag": ref.raw_tag,
        "canonical": ref.canonical,
        "day": ref.day,
        "line": ref.line,
        "valid": ref.valid,
    }
    if ref.role:
        d["role"] = ref.role
    if ref.valid:
        d["source_sender"] = ref.source_sender
        d["source_branch"] = ref.source_branch
        d["source_timestamp"] = ref.source_timestamp
        d["source_hash"] = ref.source_hash
        d["source_snippet"] = (
            ref.source_content[:300] + "…"
            if ref.source_content and len(ref.source_content) > 300
            else ref.source_content
        )
    if ref.id_mismatch:
        d["id_mismatch"] = True
        d["source_id"] = ref.source_id
    return d


# ──────────────────────────────────────────────
# Phase 1 functions
# ──────────────────────────────────────────────

def extract_citations(text: str) -> List[CitationRef]:
    """Find all [CITE …] tokens in text.

    Returns CitationRef objects with valid=False (unresolved).
    Accepts both `#` and `:L` separators.
    """
    refs: List[CitationRef] = []
    for m in _CITE_RE.finditer(text):
        day = m.group(1)
        line = int(m.group(2))
        role = m.group(3).upper() if m.group(3) else None
        raw = m.group(0)

        refs.append(CitationRef(
            day=day,
            line=line,
            role=role,
            raw_tag=raw,
            canonical=f"{day}:L{line}",
        ))
    return refs


def _read_jsonl_line(filepath: Path, line_number: int) -> Optional[dict]:
    """Read exactly the Nth line of a JSONL file (1-indexed).

    Returns parsed dict or None if line doesn't exist / can't parse.
    """
    if not filepath.exists():
        return None
    try:
        lines = secure_read_lines(filepath)
        if line_number < 1 or line_number > len(lines):
            return None
        raw = lines[line_number - 1].strip()
        return json.loads(raw) if raw else None
    except (json.JSONDecodeError, OSError):
        return None


def resolve_citations(refs: List[CitationRef]) -> List[CitationRef]:
    """Look up each citation in the JSONL archive.

    Mutates ref objects in place:
      - valid = True if JSONL line exists and parses
      - source_* fields populated from the message
      - id_mismatch = True if JSON `id` ≠ line number (soft warning)

    Returns the same list for chaining.
    """
    # Cache: avoid re-reading the same line twice
    _cache: dict[Tuple[str, int], Optional[dict]] = {}

    for ref in refs:
        key = (ref.day, ref.line)
        if key not in _cache:
            fp = THREADS_DIR / f"{ref.day}.jsonl"
            _cache[key] = _read_jsonl_line(fp, ref.line)

        obj = _cache[key]
        if obj is None:
            ref.valid = False
            continue

        ref.valid = True
        ref.source_sender = obj.get("sender")
        ref.source_content = obj.get("content", "")
        ref.source_branch = obj.get("branch", "main")
        ref.source_timestamp = obj.get("timestamp")
        ref.source_hash = obj.get("hash")
        ref.source_id = obj.get("id")

        # Cross-check: JSON id vs line number
        json_id = obj.get("id")
        if json_id is not None and int(json_id) != ref.line:
            ref.id_mismatch = True

    return refs


def validate_response_citations(response_text: str) -> CitationReport:
    """Full pipeline: extract → resolve → report.

    Usage:
        report = validate_response_citations(ai_response)
        api_payload["citations"] = report.to_dict()
    """
    refs = extract_citations(response_text)
    if not refs:
        return CitationReport()

    resolve_citations(refs)

    valid = sum(1 for r in refs if r.valid)
    invalid = sum(1 for r in refs if not r.valid)
    mismatches = sum(1 for r in refs if r.id_mismatch)
    days = sorted(set(r.day for r in refs))

    return CitationReport(
        citations=refs,
        valid_count=valid,
        invalid_count=invalid,
        id_mismatch_count=mismatches,
        cited_days=days,
    )


# ──────────────────────────────────────────────
# Phase 3: Enforcement gate
# ──────────────────────────────────────────────

# Patterns that signal a "system-truth" question — the kind where
# the answer MUST come from archive context if context was injected.
_SYSTEM_TRUTH_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\bwhat did (i|we|you)\b",
        r"\bwhat was\b.*\b(built|decided|said|done|discussed|mentioned)\b",
        r"\bwhat('s| is) my\b",
        r"\bwhat happened\b",
        r"\bdo you remember\b",
        r"\brecall\b",
        r"\blast (time|session|conversation)\b",
        r"\bprevious(ly)?\b",
        r"\byesterday\b.*\b(we|i|you)\b",
        r"\bwhat('s| is) the status\b",
        r"\bwhat comes next\b",
        r"\bwhat role\b",
        r"\bwho (is|was)\b",
        r"\bhow far\b",
        r"\bprogress\b",
    ]
]

_ENFORCEMENT_REPLY = (
    "I looked through the available archive context but could not find "
    "a verified answer to that question. Could you give me a keyword, "
    "date, or topic so I can search more precisely?"
)


def is_system_truth_query(user_prompt: str) -> bool:
    """Return True if the user's prompt looks like it requires archive data."""
    for pat in _SYSTEM_TRUTH_PATTERNS:
        if pat.search(user_prompt):
            return True
    return False


def enforce_citations(
    user_prompt: str,
    response_text: str,
    history_was_injected: bool,
) -> Tuple[str, CitationReport]:
    """Enforcement gate: validate LLM response and fail closed if needed.

    Returns:
        (possibly_modified_response, report)

    Logic:
        1. Always extract and resolve citations from the response.
        2. If history context was injected AND the user asked a
           system-truth question AND the response has zero valid
           citations → replace response with a deterministic fallback.
        3. Otherwise pass through unchanged.
    """
    report = validate_response_citations(response_text)

    if (
        history_was_injected
        and is_system_truth_query(user_prompt)
        and report.valid_count == 0
    ):
        # Fail closed: don't let an uncited answer through
        return _ENFORCEMENT_REPLY, report

    return response_text, report
