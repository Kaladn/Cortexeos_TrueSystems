"""LakeSpeakEngine — main query orchestrator.

Pipeline:
  1. Tokenize query -> extract lexicon presence/absence
  2. BM25 sparse retrieval
  3. (Optional) Dense retrieval + hybrid merge
  4. 6-1-6 anchor reranking
  5. Quality Gate -> verdict
  6. Grounding Policy -> decision
  7. Build response with citations
  8. Compute reproducibility hashes (evidence_set, index, answer)
  9. Log frozen training_event@1
  10. Return result with trace + receipt

All heavy deps are lazy-loaded. Engine is stateless between queries
(indexes are loaded/cached internally).

Contract: lakespeak_answer@1 — base calls plugin.query(), renders result.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from lakespeak.schemas import ScoredChunk, ChunkAnchors
from lakespeak.text.normalize import tokenize as _canonical_tokenize

logger = logging.getLogger(__name__)


# ── Schema Version Constants ─────────────────────────────────

LAKESPEAK_QUERY_VERSION = "lakespeak_query@1"
LAKESPEAK_ANSWER_VERSION = "lakespeak_answer@1"


# ── Engine Result ────────────────────────────────────────────

class LakeSpeakResult:
    """Structured result from a LakeSpeak query (lakespeak_answer@1)."""

    def __init__(
        self,
        answer_text: str,
        citations: List[dict],
        trace: dict,
        verdict: str,
        verdict_reasons: List[str],
        suggested_next_mode: Optional[str],
        caveats: List[str],
        grounded: bool,
        refused: bool = False,
        refusal_reason: Optional[str] = None,
        receipt: Optional[Dict[str, str]] = None,
        confidence_tier: str = "high",
    ):
        self.answer_text = answer_text
        self.citations = citations
        self.trace = trace
        self.verdict = verdict
        self.verdict_reasons = verdict_reasons
        self.suggested_next_mode = suggested_next_mode
        self.caveats = caveats
        self.grounded = grounded
        self.refused = refused
        self.refusal_reason = refusal_reason
        self.receipt = receipt or {}
        self.confidence_tier = confidence_tier


class LakeSpeakEngine:
    """Main query engine for LakeSpeak retrieval-augmented grounding.

    Lazy-loads indexes on first query. Thread-safe for reads
    (index structures are immutable after build).
    """

    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            from lakespeak.config import load_config
            config = load_config()

        self._config = config
        self._bm25 = None      # Lazy: BM25Index
        self._dense = None      # Lazy: DenseIndex (optional)
        self._bridge = None     # Lazy: ForestLexiconBridge
        self._bridge_loaded = False
        self._training_logger = None  # Lazy: cached TrainingEventLogger

    # ── Lazy Loaders ─────────────────────────────────────────

    def _ensure_bm25(self):
        """Lazy-load BM25 index."""
        if self._bm25 is None:
            from lakespeak.index.bm25 import BM25Index
            self._bm25 = BM25Index()
        return self._bm25

    def _ensure_dense(self):
        """Lazy-load dense index (optional, graceful degradation)."""
        if self._dense is None and self._config.get("dense_enabled", True):
            try:
                from lakespeak.index.dense import DenseIndex
                if DenseIndex.is_available():
                    self._dense = DenseIndex()
            except ImportError:
                pass
        return self._dense

    def _ensure_bridge(self):
        """Lazy-load Forest lexicon bridge (best-effort)."""
        if not self._bridge_loaded:
            self._bridge_loaded = True
            try:
                from bridges.forest_bridge import load_bridge_from_config
                from security.data_paths import FOREST_CONFIG_PATH
                config_path = FOREST_CONFIG_PATH
                if config_path.exists():
                    self._bridge = load_bridge_from_config(config_path)
                    logger.info(
                        "Bridge loaded: word_index=%d entries=%d",
                        len(self._bridge.word_index),
                        len(self._bridge.entries),
                    )
            except ImportError:
                logger.debug("Forest lexicon bridge not available")
            except Exception as e:
                logger.warning("Failed to load bridge: %s", e)
        return self._bridge

    # ── Lexicon Analysis ─────────────────────────────────────

    def _analyze_lexicon(self, query: str) -> tuple:
        """Split query tokens into lexicon-present and lexicon-absent sets."""
        from lakespeak.index.anchor_reranker import STOP_TOKENS

        bridge = self._ensure_bridge()
        present: List[str] = []
        absent: List[str] = []

        for token in _canonical_tokenize(query):
            if len(token) < 3:
                continue
            if token in STOP_TOKENS:
                continue

            if bridge and hasattr(bridge, "word_index") and token in bridge.word_index:
                present.append(token)
            else:
                absent.append(token)

        return present, absent

    # ── Snippet Extraction ─────────────────────────────────────

    @staticmethod
    def _extract_snippet(
        text: str,
        query: str,
        max_chars: int = 400,
    ) -> str:
        """Extract a tight context window around the best query term match.

        Finds the first occurrence of a query token in the text,
        then extracts a window of max_chars centered on it.
        Falls back to the first max_chars if no match found.
        """
        if not text or len(text) <= max_chars:
            return text

        # Tokenize query into searchable terms (skip short tokens)
        terms = [t for t in _canonical_tokenize(query) if len(t) >= 3]

        # Find earliest match position in text
        text_lower = text.lower()
        best_pos = -1
        for term in terms:
            pos = text_lower.find(term)
            if pos >= 0 and (best_pos < 0 or pos < best_pos):
                best_pos = pos

        if best_pos < 0:
            # No term match — take first max_chars
            return text[:max_chars].rstrip() + "..."

        # Center window on match
        half = max_chars // 2
        start = max(0, best_pos - half)
        end = min(len(text), start + max_chars)
        # Adjust start if we're near the end
        if end - start < max_chars:
            start = max(0, end - max_chars)

        snippet = text[start:end]

        # Add ellipsis indicators
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(text) else ""

        return prefix + snippet.strip() + suffix

    # ── Citation Builder ─────────────────────────────────────

    def _build_citations(
        self,
        scored_chunks: List[ScoredChunk],
        chunk_data: Dict[str, dict],
        query: str = "",
    ) -> List[dict]:
        """Build citation records for top-k scored chunks.

        Each citation uses the INGEST coord format:
            INGEST:<receipt_id>#<chunk_id>

        Merges citation-intake fields with retrieval-specific fields
        so every citation is fully traceable.

        Output is deterministically sorted: score DESC, bm25 DESC,
        dense DESC, receipt_id ASC, chunk_id ASC.
        """
        citations = []
        for sc in scored_chunks:
            coord = f"INGEST:{sc.receipt_id}#{sc.chunk_id}"
            cd = chunk_data.get(sc.chunk_id, {})

            full_text = cd.get("text", "")
            snippet = self._extract_snippet(full_text, query) if query else full_text

            # Start with retrieval + provenance fields (always present)
            record = {
                "coord": coord,
                "source": "lakespeak",
                "chunk_id": sc.chunk_id,
                "receipt_id": sc.receipt_id,
                "score": round(sc.score, 6),
                "bm25_score": round(sc.bm25_score, 6),
                "dense_score": round(sc.dense_score, 6),
                "anchor_score": round(sc.anchor_score, 6),
                "text": full_text,
                "snippet": snippet,
                "span_start": cd.get("span_start"),
                "span_end": cd.get("span_end"),
                "ordinal": cd.get("ordinal"),
                "token_count": cd.get("token_count"),
            }

            # Merge citation-intake fields (cite_id, created_at_utc, etc.)
            try:
                from Conversations.citations.citation_intake import create_citation_record
                intake_record = create_citation_record(
                    coord=coord,
                    source="lakespeak",
                    note=f"Retrieval score: {sc.score:.4f}",
                )
                record.update({
                    "cite_id": intake_record["cite_id"],
                    "created_at_utc": intake_record["created_at_utc"],
                    "unresolved": intake_record["unresolved"],
                    "canonical": intake_record.get("canonical", coord),
                    "ts": intake_record.get("ts"),
                })
            except Exception:
                pass  # Retrieval fields still present even if intake fails

            citations.append(record)

        # Deterministic ordering: score DESC, then tie-break by IDs ASC
        citations.sort(key=lambda c: (
            -float(c.get("score", 0.0)),
            -float(c.get("bm25_score", 0.0)),
            -float(c.get("dense_score", 0.0)),
            str(c.get("receipt_id", "")),
            str(c.get("chunk_id", "")),
        ))

        return citations

    # ── Chunk Text Loader ────────────────────────────────────

    def _load_chunk_data(
        self,
        scored_chunks: List[ScoredChunk],
    ) -> Dict[str, dict]:
        """Load full chunk metadata for scored results.

        Returns dict of chunk_id -> {text, span_start, span_end, ordinal, token_count}.
        Reads each receipt's chunks.jsonl ONCE, builds a dict, then looks up.
        """
        data: Dict[str, dict] = {}
        try:
            from security.data_paths import LAKESPEAK_CHUNKS_DIR
        except ImportError:
            return data

        # Group needed chunk_ids by receipt_id (one file read per receipt)
        needed_by_receipt: Dict[str, Set[str]] = {}
        for sc in scored_chunks:
            if sc.chunk_id not in data:
                needed_by_receipt.setdefault(sc.receipt_id, set()).add(sc.chunk_id)

        for receipt_id, needed_ids in needed_by_receipt.items():
            chunks_file = LAKESPEAK_CHUNKS_DIR / receipt_id / "chunks.jsonl"
            if not chunks_file.exists():
                continue
            try:
                for line in chunks_file.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    cid = chunk.get("chunk_id", "")
                    if cid in needed_ids:
                        data[cid] = {
                            "text": chunk.get("text", ""),
                            "span_start": chunk.get("span_start"),
                            "span_end": chunk.get("span_end"),
                            "ordinal": chunk.get("ordinal"),
                            "token_count": chunk.get("token_count"),
                        }
                        needed_ids.discard(cid)
                        if not needed_ids:
                            break  # All found for this receipt
            except Exception as e:
                logger.warning("Failed to load chunks for receipt %s: %s", receipt_id, e)

        return data

    # ── Anchor Map Loader ────────────────────────────────────

    def _load_chunk_anchors(
        self,
        scored_chunks: List[ScoredChunk],
    ) -> Dict[str, ChunkAnchors]:
        """Load anchors for scored chunks."""
        from lakespeak.schemas import AnchorRecord

        anchors_map: Dict[str, ChunkAnchors] = {}
        try:
            from security.data_paths import LAKESPEAK_CHUNKS_DIR
        except ImportError:
            return anchors_map

        loaded_receipts: Set[str] = set()
        for sc in scored_chunks:
            if sc.receipt_id in loaded_receipts:
                continue
            loaded_receipts.add(sc.receipt_id)

            anchors_file = LAKESPEAK_CHUNKS_DIR / sc.receipt_id / "anchors.json"
            if not anchors_file.exists():
                continue
            try:
                data = json.loads(anchors_file.read_text(encoding="utf-8"))
                for item in data:
                    chunk_id = item.get("chunk_id", "")
                    anchors = [
                        AnchorRecord(**a) for a in item.get("anchors", [])
                    ]
                    anchors_map[chunk_id] = ChunkAnchors(
                        schema_version=item.get("schema_version", ""),
                        chunk_id=chunk_id,
                        receipt_id=item.get("receipt_id", ""),
                        anchor_count=item.get("anchor_count", 0),
                        anchors=anchors,
                        created_at_utc=item.get("created_at_utc", ""),
                    )
            except Exception as e:
                logger.warning("Failed to load anchors for receipt %s: %s", sc.receipt_id, e)

        return anchors_map

    # ── Answer Builder ───────────────────────────────────────

    def _build_answer(
        self,
        query: str,
        scored_chunks: List[ScoredChunk],
        chunk_data: Dict[str, dict],
    ) -> str:
        """Build answer text from top-k chunks.

        Chunks are SELECTED by score (best first), but DISPLAYED in
        narrative order (receipt_id ASC, span_start ASC) so the user
        sees contextual order instead of a score-ranked wall.
        """
        if not scored_chunks:
            return ""

        # Build (display_order_key, rank, scored_chunk) tuples
        ordered = []
        for i, sc in enumerate(scored_chunks):
            cd = chunk_data.get(sc.chunk_id, {})
            snippet = self._extract_snippet(cd.get("text", ""), query)
            if snippet:
                display_key = (
                    cd.get("receipt_id", sc.receipt_id),
                    cd.get("span_start", 0) or 0,
                )
                ordered.append((display_key, i + 1, sc, snippet))

        # Sort by narrative position for presentation
        ordered.sort(key=lambda x: x[0])

        parts = []
        for display_key, rank, sc, snippet in ordered:
            parts.append(f"[{rank}] (score: {sc.score:.3f}) {snippet}")

        if parts:
            return "\n\n".join(parts)
        return ""

    # ── Main Query ───────────────────────────────────────────

    def query(
        self,
        query: str,
        mode: str = "grounded",
        topk: int = None,
        session_id: Optional[str] = None,
        caller: str = "human",
    ) -> LakeSpeakResult:
        """Execute a full LakeSpeak query pipeline.

        Args:
            query: User query text.
            mode: "grounded" (strict) or "allow_fallback" (lenient).
            topk: Final top-k results (defaults to config.final_topk).
            session_id: Optional session identifier for training logs.
            caller: "human" | "system" | "ai"

        Returns:
            LakeSpeakResult (lakespeak_answer@1 contract).
        """
        from lakespeak.retrieval.trace import TraceBuilder
        from lakespeak.retrieval.quality_gate import evaluate
        from lakespeak.retrieval.grounding_policy import apply_policy
        from lakespeak.index.anchor_reranker import extract_query_anchors, rerank
        from lakespeak.events.hashing import (
            evidence_set_hash_from_scored,
            answer_hash as compute_answer_hash,
            compute_index_hash_from_bm25,
            lake_snapshot_id as compute_snapshot_id,
        )

        if topk is None:
            topk = self._config.get("final_topk", 5)
        min_score = self._config.get("min_score", 0.1)

        tb = TraceBuilder(query_text=query, mode=mode)

        # 1. Lexicon analysis
        lexicon_present, lexicon_absent = self._analyze_lexicon(query)
        tb.set_lexicon(present=lexicon_present, absent=lexicon_absent)

        # 2. BM25 retrieval
        bm25_index = self._ensure_bm25()
        bm25_topk = self._config.get("bm25_topk", 20)
        bm25_results = bm25_index.query(query, topk=bm25_topk)

        # 3. Dense retrieval + hybrid merge (if available)
        dense_index = self._ensure_dense()
        dense_results: List[ScoredChunk] = []
        if dense_index is not None:
            try:
                dense_topk = self._config.get("dense_topk", 20)
                dense_results = dense_index.query(query, topk=dense_topk)
            except Exception as e:
                logger.warning("Dense retrieval failed, falling back to BM25-only: %s", e)

        if dense_results:
            from lakespeak.index.hybrid import rrf_merge
            bm25_weight = self._config.get("bm25_weight", 0.4)
            dense_weight = self._config.get("dense_weight", 0.6)
            candidates = rrf_merge(
                bm25_results, dense_results,
                bm25_weight=bm25_weight,
                dense_weight=dense_weight,
            )
        else:
            candidates = bm25_results

        tb.set_retrieval(
            bm25=len(bm25_results),
            dense=len(dense_results),
            hybrid=len(candidates),
        )
        tb.mark_retrieval_done()

        # 4. Anchor reranking
        bridge = self._ensure_bridge()
        query_anchors = extract_query_anchors(query, bridge)

        anchors_map = self._load_chunk_anchors(candidates)
        anchor_weight = self._config.get("anchor_weight", 0.3)

        anchor_rerank_applied = False
        if query_anchors and anchors_map:
            reranked = rerank(
                candidates=candidates,
                query_anchors=query_anchors,
                chunk_anchors_map=anchors_map,
                bridge=bridge,
                anchor_weight=anchor_weight,
            )
            anchor_rerank_applied = True
            tb.set_rerank(
                anchors=list(query_anchors),
                boost=True,
                topk=min(topk, len(reranked)),
            )
        else:
            reranked = candidates
            tb.set_rerank(anchors=[], boost=False, topk=min(topk, len(reranked)))

        tb.mark_rerank_done()

        # Normalize scores to [0, 1] if reranking was skipped.
        # The anchor reranker normalizes internally, but when skipped,
        # raw RRF/BM25 scores pass through and can be in any range.
        # Quality gate expects scores in [0, 1].
        if not anchor_rerank_applied and reranked:
            max_s = max(c.score for c in reranked)
            if max_s > 0:
                for c in reranked:
                    c.score = c.score / max_s

        # Trim to final top-k
        final_results = reranked[:topk]

        # 5. Load chunk data, build citations and answer
        chunk_data = self._load_chunk_data(final_results)
        citations = self._build_citations(final_results, chunk_data, query=query)
        answer_text = self._build_answer(query, final_results, chunk_data)

        # Collect evidence texts for gates 6/7
        evidence_texts = [
            chunk_data[sc.chunk_id]["text"]
            for sc in final_results
            if sc.chunk_id in chunk_data and chunk_data[sc.chunk_id].get("text")
        ]

        # 6. Quality Gate
        verdict = evaluate(
            query=query,
            retrieval_hits=final_results,
            citations=citations,
            response_text=answer_text,
            mode=mode,
            lexicon_present=lexicon_present,
            lexicon_absent=lexicon_absent,
            min_score=min_score,
            evidence_texts=evidence_texts,
        )

        tb.set_verdict(
            verdict=verdict.verdict,
            reasons=verdict.reasons,
            grounded=(verdict.verdict == "acceptable"),
            refusal_reason=verdict.reasons[0] if verdict.reasons else None,
            suggested_next_mode=verdict.next_action if verdict.next_action else None,
        )
        tb.mark_gate_done()

        # 7. Grounding Policy
        decision = apply_policy(
            verdict=verdict,
            mode=mode,
            response_text=answer_text,
            citations=citations,
        )

        # 8. Build trace
        trace = tb.build()
        trace_dict = asdict(trace)

        # 9. Compute reproducibility hashes
        idx_hash = compute_index_hash_from_bm25(bm25_index)
        ev_hash = evidence_set_hash_from_scored(final_results)
        ans_hash = compute_answer_hash(decision.response_text)
        snap_id = compute_snapshot_id(idx_hash)

        receipt = {
            "lake_snapshot_id": snap_id,
            "index_hash": idx_hash,
            "evidence_set_hash": ev_hash,
        }

        # 10. Log frozen training event
        self._log_structured_event(
            query=query,
            mode=mode,
            session_id=session_id,
            user_id=caller,
            trace=trace,
            lexicon_present=lexicon_present,
            lexicon_absent=lexicon_absent,
            bm25_results=bm25_results,
            dense_results=dense_results,
            final_results=final_results,
            anchor_rerank_applied=anchor_rerank_applied,
            query_anchors=query_anchors,
            decision=decision,
            verdict=verdict,
            answer_text=decision.response_text,
            citations=citations,
            idx_hash=idx_hash,
            ev_hash=ev_hash,
            ans_hash=ans_hash,
            snap_id=snap_id,
            min_score=min_score,
            topk=topk,
        )

        return LakeSpeakResult(
            answer_text=decision.response_text,
            citations=decision.citations,
            trace=trace_dict,
            verdict=verdict.verdict,
            verdict_reasons=verdict.reasons,
            suggested_next_mode=decision.suggested_next_mode,
            caveats=decision.caveats,
            grounded=decision.action == "serve_grounded",
            refused=decision.action == "refuse",
            refusal_reason=decision.refusal_reason,
            receipt=receipt,
            confidence_tier=verdict.confidence_tier,
        )

    # ── Frozen Training Event Logging ────────────────────────

    def _log_structured_event(
        self,
        query: str,
        mode: str,
        session_id: Optional[str],
        user_id: str,
        trace: Any,
        lexicon_present: List[str],
        lexicon_absent: List[str],
        bm25_results: List[ScoredChunk],
        dense_results: List[ScoredChunk],
        final_results: List[ScoredChunk],
        anchor_rerank_applied: bool,
        query_anchors: set,
        decision: Any,
        verdict: Any,
        answer_text: str,
        citations: List[dict],
        idx_hash: str,
        ev_hash: str,
        ans_hash: str,
        snap_id: str,
        min_score: float,
        topk: int,
    ) -> None:
        """Log a frozen training_event@1 query record (best-effort)."""
        try:
            if self._training_logger is None:
                from lakespeak.events.training_logger import TrainingEventLogger
                self._training_logger = TrainingEventLogger()
            tl = self._training_logger

            # Build candidate records
            candidate_records = [
                {
                    "rank": i + 1,
                    "chunk_id": c.chunk_id,
                    "coord": f"INGEST:{c.receipt_id}#{c.chunk_id}",
                    "score": round(c.score, 6),
                    "source_type": "ingest",
                    "source_hash": "",
                }
                for i, c in enumerate(final_results)
            ]

            # Build final_topk records
            final_topk_records = [
                {
                    "rank": i + 1,
                    "chunk_id": c.chunk_id,
                    "score": round(c.score, 6),
                }
                for i, c in enumerate(final_results)
            ]

            # Build citations_emitted
            citations_emitted = []
            for c in citations:
                citations_emitted.append({
                    "cite_id": c.get("cite_id", ""),
                    "coord": c.get("coord", ""),
                    "source": c.get("source", "lakespeak"),
                    "unresolved": c.get("unresolved", True),
                    "subject": c.get("subject"),
                })

            tl.log_query_structured(
                query_id=trace.query_id,
                query_text=query,
                requested_mode=mode,
                session_id=session_id,
                user_id=user_id,
                # Grounding policy
                grounded_required=(mode == "grounded"),
                min_score=min_score,
                topk=topk,
                # Lexicon probe
                lexicon_present=lexicon_present,
                lexicon_absent=lexicon_absent,
                probe_ms=0,
                # Retrieval
                lake_snapshot_id=snap_id,
                index_hash=idx_hash,
                retrieval_ms=trace.retrieval_ms,
                bm25_enabled=True,
                bm25_hits=len(bm25_results),
                dense_enabled=bool(dense_results),
                dense_hits=len(dense_results),
                dense_model=self._config.get("dense_model") if dense_results else None,
                candidates=candidate_records,
                evidence_set_hash=ev_hash,
                # Rerank
                anchor_rerank_enabled=anchor_rerank_applied,
                anchors_used=list(query_anchors) if query_anchors else [],
                rerank_ms=trace.rerank_ms,
                final_topk=final_topk_records,
                # Decision
                grounded=(decision.action == "serve_grounded"),
                refused=(decision.action == "refuse"),
                refusal_reason=decision.refusal_reason,
                suggested_next_mode=decision.suggested_next_mode,
                # Output
                answer_text=answer_text,
                answer_hash=ans_hash,
                citations_emitted=citations_emitted,
                # Timing
                total_ms=trace.total_ms,
            )
        except Exception as e:
            logger.warning("Failed to log structured training event: %s", e)

    # ── Index Management ─────────────────────────────────────

    def reindex(self) -> Dict[str, Any]:
        """Rebuild BM25 index from all stored chunks.

        Scans LAKESPEAK_CHUNKS_DIR for all receipt directories,
        loads chunks, and builds a fresh BM25 index.
        """
        try:
            from security.data_paths import LAKESPEAK_CHUNKS_DIR
        except ImportError:
            return {"error": "data_paths not available"}

        if not LAKESPEAK_CHUNKS_DIR.exists():
            return {"error": "chunks directory does not exist", "chunks_indexed": 0}

        texts: List[str] = []
        ids: List[str] = []
        receipt_ids: List[str] = []
        receipts_processed = 0

        for receipt_dir in sorted(LAKESPEAK_CHUNKS_DIR.iterdir()):
            if not receipt_dir.is_dir():
                continue
            chunks_file = receipt_dir / "chunks.jsonl"
            if not chunks_file.exists():
                continue

            receipts_processed += 1
            for line in chunks_file.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    chunk = json.loads(line)
                    texts.append(chunk.get("text", ""))
                    ids.append(chunk.get("chunk_id", ""))
                    receipt_ids.append(chunk.get("receipt_id", ""))
                except json.JSONDecodeError:
                    continue

        if not texts:
            return {"chunks_indexed": 0, "receipts_processed": receipts_processed}

        bm25 = self._ensure_bm25()
        bm25.build(texts, ids, receipt_ids)
        bm25.save()

        # Rebuild dense index (if available)
        dense_count = 0
        try:
            from lakespeak.index.dense import DenseIndex
            if DenseIndex.is_available():
                dense = DenseIndex()
                dense.build(texts, ids, receipt_ids)
                dense.save()
                dense_count = dense.doc_count
                self._dense = dense  # Update cached reference
                logger.info("Dense index rebuilt: %d vectors", dense_count)
        except Exception as e:
            logger.warning("Dense index rebuild skipped: %s", e)

        # Log reindex event
        stats = {
            "chunks_indexed": len(texts),
            "receipts_processed": receipts_processed,
            "dense_indexed": dense_count,
        }
        try:
            if self._training_logger is None:
                from lakespeak.events.training_logger import TrainingEventLogger
                self._training_logger = TrainingEventLogger()
            self._training_logger.log_reindex(stats)
        except Exception as e:
            logger.warning("Failed to log reindex event: %s", e)

        return stats
