"""ReasoningTrace builder — constructs reasoning_trace@1 from query execution.

Collects timing, retrieval stats, reranking details, and Quality Gate verdict
into a single structured trace record for debugging and training.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from lakespeak.schemas import ReasoningTrace, REASONING_TRACE_VERSION


class TraceBuilder:
    """Fluent builder for ReasoningTrace records.

    Usage:
        tb = TraceBuilder(query_text="test", mode="grounded")
        tb.set_lexicon(present=["foo"], absent=["bar"])
        tb.set_retrieval(bm25=5, dense=3, hybrid=8)
        tb.set_rerank(anchors=["foo"], boost=True, topk=5)
        tb.set_verdict("acceptable", [], grounded=True)
        trace = tb.build()
    """

    def __init__(self, query_text: str, mode: str):
        self._query_id = f"q_{uuid.uuid4().hex[:16]}"
        self._query_text = query_text
        self._mode = mode
        self._t_start = time.perf_counter_ns()

        # Lexicon
        self._lexicon_present: List[str] = []
        self._lexicon_absent: List[str] = []

        # Retrieval
        self._bm25_hits = 0
        self._dense_hits = 0
        self._hybrid_candidates = 0
        self._t_retrieval_done: Optional[int] = None

        # Rerank
        self._anchors_used: List[str] = []
        self._anchor_boost = False
        self._final_topk = 0
        self._t_rerank_done: Optional[int] = None

        # Verdict
        self._verdict = ""
        self._verdict_reasons: List[str] = []
        self._grounded = False
        self._refusal_reason: Optional[str] = None
        self._suggested_next_mode: Optional[str] = None
        self._t_gate_done: Optional[int] = None

    @property
    def query_id(self) -> str:
        return self._query_id

    def set_lexicon(
        self,
        present: List[str],
        absent: List[str],
    ) -> TraceBuilder:
        self._lexicon_present = present
        self._lexicon_absent = absent
        return self

    def mark_retrieval_done(self) -> TraceBuilder:
        self._t_retrieval_done = time.perf_counter_ns()
        return self

    def set_retrieval(
        self,
        bm25: int = 0,
        dense: int = 0,
        hybrid: int = 0,
    ) -> TraceBuilder:
        self._bm25_hits = bm25
        self._dense_hits = dense
        self._hybrid_candidates = hybrid
        return self

    def mark_rerank_done(self) -> TraceBuilder:
        self._t_rerank_done = time.perf_counter_ns()
        return self

    def set_rerank(
        self,
        anchors: List[str],
        boost: bool,
        topk: int,
    ) -> TraceBuilder:
        self._anchors_used = anchors
        self._anchor_boost = boost
        self._final_topk = topk
        return self

    def mark_gate_done(self) -> TraceBuilder:
        self._t_gate_done = time.perf_counter_ns()
        return self

    def set_verdict(
        self,
        verdict: str,
        reasons: List[str],
        grounded: bool,
        refusal_reason: Optional[str] = None,
        suggested_next_mode: Optional[str] = None,
    ) -> TraceBuilder:
        self._verdict = verdict
        self._verdict_reasons = reasons
        self._grounded = grounded
        self._refusal_reason = refusal_reason
        self._suggested_next_mode = suggested_next_mode
        return self

    def build(self) -> ReasoningTrace:
        """Build the final ReasoningTrace record."""
        t_end = time.perf_counter_ns()

        def _ms(start: int, end: Optional[int]) -> int:
            if end is None:
                return 0
            return max(0, (end - start) // 1_000_000)

        retrieval_ms = _ms(self._t_start, self._t_retrieval_done)
        rerank_ms = _ms(self._t_retrieval_done or self._t_start, self._t_rerank_done)
        gate_ms = _ms(self._t_rerank_done or self._t_start, self._t_gate_done)
        total_ms = _ms(self._t_start, t_end)

        return ReasoningTrace(
            schema_version=REASONING_TRACE_VERSION,
            query_id=self._query_id,
            query_text=self._query_text,
            mode=self._mode,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            lexicon_present=self._lexicon_present,
            lexicon_absent=self._lexicon_absent,
            bm25_hits=self._bm25_hits,
            dense_hits=self._dense_hits,
            hybrid_candidates=self._hybrid_candidates,
            anchors_used=self._anchors_used,
            anchor_boost_applied=self._anchor_boost,
            final_topk=self._final_topk,
            verdict=self._verdict,
            verdict_reasons=self._verdict_reasons,
            grounded=self._grounded,
            refusal_reason=self._refusal_reason,
            suggested_next_mode=self._suggested_next_mode,
            retrieval_ms=retrieval_ms,
            rerank_ms=rerank_ms,
            gate_ms=gate_ms,
            total_ms=total_ms,
        )
