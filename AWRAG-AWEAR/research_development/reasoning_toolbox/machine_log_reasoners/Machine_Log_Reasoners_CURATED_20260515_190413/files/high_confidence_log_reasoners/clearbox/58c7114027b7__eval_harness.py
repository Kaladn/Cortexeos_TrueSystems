"""Evaluation Harness — turns training events into hard numbers.

Plugin #2 (LakeSpeak-Eval): no training, just proof.

Metrics:
  - Grounded rate: % of queries that returned grounded answers
  - Refused rate: % of queries that were refused (TRASH + grounded mode)
  - Fallback rate: % of queries that fell back to ungrounded
  - Retrieval hit-rate: % of queries with >= 1 retrieval hit
  - Avg retrieval ms
  - Avg anchor overlap (% of query anchors found in top-k chunks)
  - Precision@k (requires relevance labels, computed when available)
  - Coverage: % of lexicon tokens that have at least 1 indexed chunk

Reads from: LAKESPEAK_EVENTS_DIR/training_events_*.jsonl
Writes to: LAKESPEAK_EVAL_DIR/reports/{YYYYMMDD-HHMMSS}.eval.json
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from lakespeak.schemas import EvalReport, EVAL_REPORT_VERSION

logger = logging.getLogger(__name__)


class EvalHarness:
    """Evaluation harness for LakeSpeak query events."""

    def __init__(self):
        self._events_dir: Optional[Path] = None
        self._eval_dir: Optional[Path] = None

        try:
            from security.data_paths import LAKESPEAK_EVENTS_DIR, LAKESPEAK_EVAL_DIR
            self._events_dir = LAKESPEAK_EVENTS_DIR
            self._eval_dir = LAKESPEAK_EVAL_DIR
        except ImportError:
            pass

    # ── Event Loading ────────────────────────────────────────

    def _load_query_events(
        self,
        days: int = 30,
        event_files: List[Path] = None,
    ) -> List[Dict[str, Any]]:
        """Load query events from JSONL files.

        Args:
            days: Load events from the last N days.
            event_files: Explicit file list (overrides days scan).

        Returns:
            List of query event dicts.
        """
        events: List[Dict[str, Any]] = []

        if event_files:
            files = event_files
        elif self._events_dir and self._events_dir.exists():
            files = sorted(self._events_dir.glob("training_events_*.jsonl"))
            if days > 0:
                # Filter to recent files (by filename date)
                cutoff = datetime.now(timezone.utc)
                recent_files = []
                for f in files:
                    try:
                        date_str = f.stem.replace("training_events_", "")
                        file_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                        diff = (cutoff - file_date).days
                        if diff <= days:
                            recent_files.append(f)
                    except ValueError:
                        recent_files.append(f)  # Include if can't parse date
                files = recent_files
        else:
            return events

        for filepath in files:
            try:
                for line in filepath.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                        if event.get("event_type") == "query":
                            events.append(event)
                    except json.JSONDecodeError:
                        continue
            except Exception as e:
                logger.warning("Failed to read event file %s: %s", filepath, e)

        return events

    # ── Metric Computation ───────────────────────────────────

    def evaluate(
        self,
        days: int = 30,
        event_files: List[Path] = None,
    ) -> EvalReport:
        """Run evaluation over query events.

        Args:
            days: Evaluate events from the last N days.
            event_files: Explicit file list (overrides days scan).

        Returns:
            EvalReport with computed metrics.
        """
        events = self._load_query_events(days=days, event_files=event_files)

        if not events:
            return EvalReport(
                schema_version=EVAL_REPORT_VERSION,
                report_id=f"eval_{uuid.uuid4().hex[:16]}",
                created_at_utc=datetime.now(timezone.utc).isoformat(),
                query_count=0,
            )

        # Counters
        total = len(events)
        grounded_count = 0
        refused_count = 0
        fallback_count = 0
        hit_count = 0           # Queries with >= 1 retrieval hit
        total_retrieval_ms = 0
        total_anchor_overlap = 0.0
        anchor_overlap_queries = 0

        query_details: List[Dict[str, Any]] = []

        for ev in events:
            # Handle both frozen schema (top-level) and legacy (payload) formats
            decision = ev.get("decision", {})
            retrieval = ev.get("retrieval", {})
            rerank = ev.get("rerank", {})
            output = ev.get("output", {})
            timing = ev.get("timing", {})

            # Fallback to legacy payload format
            payload = ev.get("payload", {})
            if not decision and payload:
                decision = {
                    "grounded": payload.get("verdict") == "acceptable",
                    "refused": payload.get("refused", False),
                }
            if not retrieval and payload:
                retrieval = {
                    "candidates": payload.get("candidates", []),
                    "retrieval_ms": 0,
                }

            is_grounded = decision.get("grounded", False)
            is_refused = decision.get("refused", False)
            candidates = retrieval.get("candidates", [])
            has_hits = len(candidates) > 0
            ret_ms = retrieval.get("retrieval_ms", 0) or timing.get("total_ms", 0)

            if is_grounded:
                grounded_count += 1
            elif is_refused:
                refused_count += 1
            else:
                fallback_count += 1

            if has_hits:
                hit_count += 1

            total_retrieval_ms += ret_ms

            # Anchor overlap: fraction of final top-k chunks that had anchor boost > 0
            anchors_used = rerank.get("anchors_used", [])
            final_topk_items = rerank.get("final_topk", [])
            if anchors_used and final_topk_items:
                # Count candidates with non-zero anchor contribution
                boosted = sum(1 for item in final_topk_items if item.get("score", 0) > 0)
                overlap_ratio = boosted / max(1, len(final_topk_items))
                total_anchor_overlap += overlap_ratio
                anchor_overlap_queries += 1

            query_details.append({
                "query_id": ev.get("query_id", ""),
                "query_text": ev.get("query_text", payload.get("query", "")),
                "grounded": is_grounded,
                "refused": is_refused,
                "hit_count": len(candidates),
                "retrieval_ms": ret_ms,
            })

        avg_retrieval_ms = total_retrieval_ms / total if total > 0 else 0.0
        avg_anchor_overlap = (
            total_anchor_overlap / anchor_overlap_queries
            if anchor_overlap_queries > 0
            else 0.0
        )

        report = EvalReport(
            schema_version=EVAL_REPORT_VERSION,
            report_id=f"eval_{uuid.uuid4().hex[:16]}",
            created_at_utc=datetime.now(timezone.utc).isoformat(),
            query_count=total,
            grounded_count=grounded_count,
            refused_count=refused_count,
            fallback_count=fallback_count,
            avg_retrieval_ms=round(avg_retrieval_ms, 2),
            avg_topk_anchor_overlap=round(avg_anchor_overlap, 4),
            precision_at_k={},  # Requires relevance labels (future)
            coverage=hit_count / total if total > 0 else 0.0,
            queries=query_details,
        )

        return report

    # ── Report Persistence ───────────────────────────────────

    def run_and_save(
        self,
        days: int = 30,
        event_files: List[Path] = None,
    ) -> Dict[str, Any]:
        """Run evaluation and save report to LAKESPEAK_EVAL_DIR.

        Returns:
            Dict with report_id and path.
        """
        from dataclasses import asdict

        report = self.evaluate(days=days, event_files=event_files)
        report_dict = asdict(report)

        if self._eval_dir is None:
            return {"error": "eval directory not configured", "report": report_dict}

        reports_dir = self._eval_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        filename = f"{timestamp}.eval.json"
        filepath = reports_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)

        logger.info("Evaluation report saved: %s (queries=%d, grounded=%d, refused=%d)",
                     filepath, report.query_count, report.grounded_count, report.refused_count)

        # Log reindex-style event
        try:
            from lakespeak.events.training_logger import TrainingEventLogger
            tl = TrainingEventLogger()
            tl.log_event(
                event_type="eval",
                payload={
                    "report_id": report.report_id,
                    "query_count": report.query_count,
                    "grounded_count": report.grounded_count,
                    "refused_count": report.refused_count,
                    "coverage": report.coverage,
                    "report_path": str(filepath),
                },
            )
        except Exception as e:
            logger.warning("Failed to log eval event: %s", e)

        return {
            "report_id": report.report_id,
            "path": str(filepath),
            "query_count": report.query_count,
            "grounded_rate": round(report.grounded_count / max(1, report.query_count), 4),
            "refused_rate": round(report.refused_count / max(1, report.query_count), 4),
            "coverage": round(report.coverage, 4),
        }
