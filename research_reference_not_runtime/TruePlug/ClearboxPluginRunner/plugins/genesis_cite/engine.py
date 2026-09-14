"""Genesis Citation Tool — citation engine (direct lookup + BM25 search).

The LLM may ONLY cite what this engine returns.
All factual claims about Clearbox AI Studio must be anchored to a G-ID.

Public API:
    engine = CitationEngine()          # lazy-loads index on first use
    engine.direct(tag)                 # → citation object dict
    engine.search(query, filters, limit, include_snippets)  # → results list
    engine.health()                    # → health dict
    engine.list_all()                  # → list of lightweight tag/title/source rows
"""

from __future__ import annotations

import re
import threading
from datetime import datetime, timezone
from typing import Any, Optional

from .config import (
    DEFAULT_SEARCH_LIMIT,
    MAX_SEARCH_LIMIT,
    SERIES_RANGES,
)
from .indexer import GenesisIndex, load_or_build_index, tokenize, _block_document
from .parser import Block

# ── Security: reject path injection attempts ──────────────────────────────────
_INJECTION_RE = re.compile(r"[/\\.]")


def _check_tag_safe(tag: str) -> None:
    if _INJECTION_RE.search(tag):
        raise ValueError(f"PATH_INJECTION: invalid characters in tag '{tag}'")
    if not re.fullmatch(r"G-\d{4}", tag):
        raise ValueError(f"INVALID_TAG: must match G-XXXX format, got '{tag}'")


# ── Citation object builder ───────────────────────────────────────────────────

def _build_citation(block: Block, source_commit: str, include_body: bool = True) -> dict:
    obj: dict[str, Any] = {
        "tag": block.tag,
        "title": block.title,
        "source": block.source,
        "scope": block.scope,
        "date_range": block.date_range,
        "write_perms": block.write_perms,
        "derived": block.derived,
        "source_commit": source_commit,
        "block_hash": block.block_hash,
        "span": block.span,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }
    if include_body:
        obj["body"] = block.body
    return obj


# ── Snippet helper ────────────────────────────────────────────────────────────

def _snippet(body: str, max_chars: int = 200) -> str:
    """Return first non-blank portion of body, truncated to max_chars."""
    text = body.strip()
    if len(text) <= max_chars:
        return text
    # Try to break at a word boundary
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > max_chars // 2:
        truncated = truncated[:last_space]
    return truncated + "…"


# ── Series filter helper ──────────────────────────────────────────────────────

def _in_series(block: Block, series_str: str) -> bool:
    lo, hi = SERIES_RANGES.get(series_str, (0, 0))
    return lo <= block.series <= hi


# ── Engine ────────────────────────────────────────────────────────────────────

class CitationEngine:
    """Thread-safe citation engine with lazy index loading."""

    def __init__(self) -> None:
        self._index: Optional[GenesisIndex] = None
        self._lock = threading.Lock()

    def _get_index(self) -> GenesisIndex:
        """Return loaded index, building it if needed."""
        if self._index is None:
            with self._lock:
                if self._index is None:
                    self._index = load_or_build_index()
        return self._index

    def reload(self) -> None:
        """Force index rebuild on next access."""
        with self._lock:
            self._index = None

    # ── Direct lookup ─────────────────────────────────────────────────────────

    def direct(self, tag: str, include_body: bool = True) -> dict:
        """Resolve a G-ID to its canonical citation object.

        Returns:
            {"ok": True, "result": {...citation object...}}
          or
            {"ok": False, "error": "NOT_FOUND", "detail": "..."}
        """
        try:
            _check_tag_safe(tag)
        except ValueError as exc:
            return {"ok": False, "error": "SPEC_VIOLATION", "detail": str(exc)}

        try:
            idx = self._get_index()
        except FileNotFoundError as exc:
            return {"ok": False, "error": "NOT_FOUND", "detail": str(exc)}
        except ValueError as exc:
            return {"ok": False, "error": "SPEC_VIOLATION", "detail": str(exc)}
        except RuntimeError as exc:
            return {"ok": False, "error": "STALE_INDEX", "detail": str(exc)}

        block = idx.tag_map.get(tag)
        if block is None:
            return {
                "ok": False,
                "error": "NOT_FOUND",
                "detail": f"Tag {tag} not in corpus",
            }

        return {
            "ok": True,
            "result": _build_citation(block, idx.meta.get("source_commit", "unknown"), include_body),
        }

    # ── Search ────────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        filters: Optional[dict] = None,
        limit: int = DEFAULT_SEARCH_LIMIT,
        include_snippets: bool = True,
    ) -> dict:
        """BM25 search over corpus.

        Args:
            query:            Plain-text query string.
            filters:          Optional dict with keys:
                                "series"          → "1"–"12"
                                "derived"         → True/False
                                "source_contains" → substring
            limit:            Max results (1–20, default 5).
            include_snippets: Include body snippet in results.

        Returns:
            {"ok": True, "query": query, "results": [...]}
        """
        # Validate query for injection
        if any(c in query for c in ["\x00"]):
            return {"ok": False, "error": "SPEC_VIOLATION", "detail": "Invalid query"}

        limit = max(1, min(limit, MAX_SEARCH_LIMIT))
        filters = filters or {}

        try:
            idx = self._get_index()
        except FileNotFoundError as exc:
            return {"ok": False, "error": "NOT_FOUND", "detail": str(exc)}
        except (ValueError, RuntimeError) as exc:
            return {"ok": False, "error": "STALE_INDEX", "detail": str(exc)}

        # BM25 scores
        query_tokens = tokenize(query)
        if not query_tokens:
            scores = [0.0] * len(idx.corpus)
        else:
            scores = list(idx.bm25.get_scores(query_tokens))

        # Tag/title boost
        query_lower = query.lower()
        for i, block in enumerate(idx.corpus):
            if block.tag.lower() in query_lower:
                scores[i] *= 2.0
            elif block.title.lower() in query_lower:
                scores[i] *= 1.5

        # Apply filters
        results: list[dict] = []
        for i, block in enumerate(idx.corpus):
            if "series" in filters and not _in_series(block, str(filters["series"])):
                continue
            if "derived" in filters and block.derived != bool(filters["derived"]):
                continue
            if "source_contains" in filters:
                if filters["source_contains"].lower() not in block.source.lower():
                    continue

            entry: dict[str, Any] = {
                "tag": block.tag,
                "title": block.title,
                "score": round(scores[i], 6),
                "block_hash": block.block_hash,
                "span": block.span,
            }
            if include_snippets:
                entry["snippet"] = _snippet(block.body)

            results.append(entry)

        # Sort: score descending, then tag ascending (deterministic tiebreaker)
        results.sort(key=lambda r: (-r["score"], r["tag"]))
        results = results[:limit]

        return {
            "ok": True,
            "query": query,
            "results": results,
        }

    # ── Health ────────────────────────────────────────────────────────────────

    def health(self) -> dict:
        """Return health/status dict."""
        try:
            idx = self._get_index()
            return {
                "ok": True,
                "blocks": len(idx.corpus),
                "index_commit": idx.meta.get("source_commit", "unknown"),
                "built_at": idx.meta.get("built_at"),
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    # ── List all ──────────────────────────────────────────────────────────────

    def list_all(self) -> list[dict]:
        """Return lightweight listing of all blocks (no bodies)."""
        idx = self._get_index()
        result = []
        for block in idx.corpus:
            from .indexer import _tag_series
            result.append({
                "tag": block.tag,
                "title": block.title,
                "source": block.source,
                "series": str(_tag_series(block.tag)),
            })
        return result
