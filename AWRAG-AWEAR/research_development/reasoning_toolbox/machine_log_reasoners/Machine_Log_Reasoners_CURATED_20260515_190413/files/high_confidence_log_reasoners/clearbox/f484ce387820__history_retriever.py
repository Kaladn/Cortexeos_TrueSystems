"""Brute-force chat history retriever with keyword scoring and recency bias.

Scans all conversations/threads/*.jsonl files, filters by branch,
scores by keyword hits + recency, returns a bounded context block
with stable citations like 2026-02-07#1.

No external dependencies. Swap search_history() backend to SQLite FTS
later without changing the public interface.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional, Tuple


# CLEARBOX_AI_PRODUCTION/
#   Conversations/threads/*.jsonl
#   Conversations/threads/history_retriever.py
ROOT = Path(__file__).resolve().parents[1]
import sys
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from security.data_paths import CHAT_THREADS_DIR
from security.secure_storage import secure_read_lines
THREADS_DIR = CHAT_THREADS_DIR

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Marker tag for meta-content (summary requests, bulk pastes, etc.)
# Any message containing this tag is skipped by the retriever.
CLEARBOX_META_TAG = "__CLEARBOX_META__"

# Messages over this length are likely conversation dumps, not real prompts.
# Skip them to prevent blob pollution in search results.
# AI messages over 2000 chars are filtered; user messages get a higher
# limit (8000) since substantive user inputs are valuable retrieval targets.
MAX_CONTENT_LEN_AI = 2000
MAX_CONTENT_LEN_USER = 8000


@dataclass(frozen=True)
class Msg:
    day: str
    msg_id: int
    sender: str
    content: str
    timestamp: Optional[str]
    branch: str


@dataclass(frozen=True)
class Hit:
    msg: Msg
    score: float


def _iter_thread_files() -> Iterable[Path]:
    if not THREADS_DIR.exists():
        return
    for fp in sorted(THREADS_DIR.glob("*.jsonl")):
        if DATE_RE.match(fp.stem):
            yield fp


def _parse_ts(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        # e.g. "2026-02-07T19:19:23.127917+00:00"
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _tokenize(q: str) -> list[str]:
    """Deterministic, no NLP: lowercase alnum-ish tokens."""
    toks = re.findall(r"[a-z0-9_]+", q.lower())
    # drop 1-char noise
    return [t for t in toks if len(t) > 1]


def _keyword_score(content_lc: str, tokens: list[str]) -> int:
    """Simple hit count; gives higher weight to repeated mentions."""
    score = 0
    for t in tokens:
        score += content_lc.count(t)
    return score


def _recency_bonus(ts: Optional[datetime]) -> float:
    """Lightweight bonus for newer messages (UTC).
    Decay: 1.0 now -> approaches 0 over ~7 days.
    """
    if not ts:
        return 0.0
    age_sec = (datetime.now(timezone.utc) - ts).total_seconds()
    if age_sec < 0:
        age_sec = 0
    return 1.0 / (1.0 + (age_sec / (7 * 24 * 3600)))


# ── Direct cite reference resolver ──────────────────────────────

# Matches patterns like 2026-02-08:L1, 2026-02-08:L3, :L5 (short form)
_DIRECT_CITE_RE = re.compile(
    r"(?:(\d{4}-\d{2}-\d{2}):)?L(\d+)",
    re.IGNORECASE,
)


def _read_jsonl_line(filepath: Path, line_number: int) -> Optional[dict]:
    """Read exactly the Nth line of a JSONL file (1-indexed)."""
    if not filepath.exists():
        return None
    try:
        lines = secure_read_lines(filepath)
        if line_number < 1 or line_number > len(lines):
            return None
        raw = lines[line_number - 1]
        return json.loads(raw) if raw.strip() else None
    except Exception:
        return None


def resolve_explicit_cites(query: str, default_day: Optional[str] = None) -> list[Hit]:
    """Extract explicit YYYY-MM-DD:L<N> references from a query and resolve
    them directly from the JSONL archive.  Returns Hit objects with high
    scores so they sort first when merged with keyword hits.

    If a cite uses short form `:L5` with no date, `default_day` is used
    (defaults to today).
    """
    if default_day is None:
        default_day = datetime.now().strftime("%Y-%m-%d")

    seen: set[Tuple[str, int]] = set()
    results: list[Hit] = []

    for m in _DIRECT_CITE_RE.finditer(query):
        day = m.group(1) or default_day
        line = int(m.group(2))
        key = (day, line)
        if key in seen:
            continue
        seen.add(key)

        fp = THREADS_DIR / f"{day}.jsonl"
        obj = _read_jsonl_line(fp, line)
        if obj is None:
            continue

        content = obj.get("content") or ""
        sender = str(obj.get("sender") or "unknown")
        msg_branch = str(obj.get("branch") or "main")
        msg_id = int(obj.get("id") or line)
        ts_raw = obj.get("timestamp")

        msg = Msg(
            day=day,
            msg_id=line,  # line number is authority
            sender=sender,
            content=content,
            timestamp=ts_raw if isinstance(ts_raw, str) else None,
            branch=msg_branch,
        )
        # Score 1000+ so explicit cites always sort first
        results.append(Hit(msg=msg, score=1000.0 + line))

    return results


def search_history(
    query: str,
    *,
    branch: str = "main",
    max_hits: int = 20,
    days_limit: Optional[int] = None,
    senders: Optional[list[str]] = None,
) -> list[Hit]:
    """Brute-force search across JSONL files.

    - branch: filter on Msg.branch (default "main")
    - days_limit: if set, only scan last N days by filename order
    - senders: if set, only include messages from these senders
              (default: ["user"] — only human messages)
    """
    if senders is None:
        senders = ["user"]  # default: only human messages, not model regurgitation
    tokens = _tokenize(query)
    if not tokens:
        return []

    files = list(_iter_thread_files())
    if days_limit is not None and days_limit > 0:
        files = files[-days_limit:]

    hits: list[Hit] = []

    for fp in files:
        day = fp.stem
        try:
            lines = secure_read_lines(fp)
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue

                msg_branch = str(obj.get("branch") or "")
                if branch and msg_branch != branch:
                    continue

                content = obj.get("content") or ""
                if not content.strip():
                    continue

                # Skip meta-tagged messages (summary inputs, bulk pastes)
                if CLEARBOX_META_TAG in content:
                    continue

                sender = str(obj.get("sender") or "unknown")

                # Filter by sender (default: user-only)
                if senders and sender not in senders:
                    continue

                # Skip blob messages — limit depends on sender
                max_len = MAX_CONTENT_LEN_USER if sender == "user" else MAX_CONTENT_LEN_AI
                if len(content) > max_len:
                    continue
                msg_id = int(obj.get("id") or 0)
                ts_raw = obj.get("timestamp")
                ts = _parse_ts(ts_raw)

                content_lc = content.lower()
                kw = _keyword_score(content_lc, tokens)
                if kw <= 0:
                    continue

                # Score: keyword hits dominate; recency breaks ties
                score = float(kw) + 0.25 * _recency_bonus(ts)

                msg = Msg(
                    day=day,
                    msg_id=msg_id,
                    sender=sender,
                    content=content,
                    timestamp=ts_raw if isinstance(ts_raw, str) else None,
                    branch=msg_branch,
                )
                hits.append(Hit(msg=msg, score=score))
        except FileNotFoundError:
            continue

    # Highest first
    hits.sort(key=lambda h: h.score, reverse=True)

    # De-dup: same message id/day shouldn't repeat
    seen: set[Tuple[str, int]] = set()
    uniq: list[Hit] = []
    for h in hits:
        key = (h.msg.day, h.msg.msg_id)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(h)
        if len(uniq) >= max_hits:
            break

    return uniq


def build_history_context(
    user_query: str,
    *,
    max_chars: int = 12000,
    per_hit_chars: int = 900,
    max_hits: int = 16,
    branch: str = "main",
    days_limit: Optional[int] = 30,
    return_hits: bool = False,
) -> "str | tuple[str, list[dict]]":
    """Build bounded HISTORY_CONTEXT block with stable citations.

    Citation format: YYYY-MM-DD:L<id>
    Skips retrieval for ultra-short queries (< 2 meaningful tokens).

    If return_hits=True, returns (context_str, structured_hits) where
    structured_hits is a list of dicts suitable for the retrieval_context
    API payload.
    """
    empty = ("", []) if return_hits else ""

    # ── Phase 1: Resolve any explicit cite references (e.g. 2026-02-08:L1) ──
    explicit_hits = resolve_explicit_cites(user_query)

    # Guard: don't scan archive for "ok", "hi", "yep", etc.
    # BUT if the user gave explicit cite refs, still proceed.
    if len(_tokenize(user_query)) < 2 and not explicit_hits:
        return empty

    # ── Phase 2: Keyword search for additional context ──
    keyword_hits = search_history(
        user_query,
        branch=branch,
        max_hits=max_hits,
        days_limit=days_limit,
    )

    # Merge: explicit cites first (score 1000+), then keyword hits.
    # De-duplicate by (day, msg_id) — explicit cites win.
    seen: set[Tuple[str, int]] = set()
    merged: list[Hit] = []
    for h in explicit_hits:
        key = (h.msg.day, h.msg.msg_id)
        if key not in seen:
            seen.add(key)
            merged.append(h)
    for h in keyword_hits:
        key = (h.msg.day, h.msg.msg_id)
        if key not in seen:
            seen.add(key)
            merged.append(h)

    if not merged:
        return empty

    header = "HISTORY_CONTEXT (retrieved from full local chat archive):\n"
    parts: list[str] = [header]
    used = len(header)
    structured: list[dict] = []

    for h in merged:
        m = h.msg
        snippet = m.content.strip().replace("\r\n", "\n")
        if len(snippet) > per_hit_chars:
            snippet = snippet[:per_hit_chars] + "…"

        cite = f"{m.day}:L{m.msg_id}"
        role = m.sender.upper()

        # Human-readable format — no confusing cite syntax for the model
        block = f"\n--- Message #{m.msg_id} from {m.day} ({role}) ---\n{snippet}\n"
        if used + len(block) > max_chars:
            break
        parts.append(block)
        used += len(block)

        structured.append({
            "canonical": cite,
            "score": round(h.score, 3),
            "sender": m.sender,
            "branch": m.branch,
            "snippet": snippet[:300],
            "day": m.day,
            "line": m.msg_id,
        })

    context_str = "".join(parts)
    if return_hits:
        return context_str, structured
    return context_str
