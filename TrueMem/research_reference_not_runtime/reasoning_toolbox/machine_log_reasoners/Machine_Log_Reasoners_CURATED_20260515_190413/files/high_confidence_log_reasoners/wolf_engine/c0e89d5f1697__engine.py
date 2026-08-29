"""
Wolf Engine — Core Engine.

Self-contained engine: Perception -> GNOME -> SQLite + Forge -> Reasoning -> Archon -> Verdicts.
Extracted from dashboard/app.py for plugin compliance.
"""

from __future__ import annotations

import os
import tempfile
import threading
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Any

from wolf_engine.archon.orchestrator import Orchestrator
from wolf_engine.archon.schemas import Verdict, VerdictStatus
from wolf_engine.archon.verdict import VerdictStore
from wolf_engine.config import DB_PATH, GENOME_VERSION, SYMBOL_GENOME_PATH
from wolf_engine.contracts import ForgeStats
from wolf_engine.evidence.session_manager import EvidenceSessionManager
from wolf_engine.evidence.workers import (
    InputLoggerWorker,
    NetworkLoggerWorker,
    ProcessLoggerWorker,
    SystemPerfWorker,
)
from wolf_engine.forge.forge_memory import ForgeMemory
from wolf_engine.gnome.gnome_service import GnomeService
from wolf_engine.pipeline import ingest_anchor
from wolf_engine.reasoning.cascade_engine import CascadeEngine
from wolf_engine.reasoning.causal_analyzer import CausalAnalyzer
from wolf_engine.reasoning.engine import ReasoningEngine
from wolf_engine.reasoning.pattern_detector import PatternDetector
from wolf_engine.services.perception_service import build_anchors, tokenize
from wolf_engine.sql.sqlite_writer import SQLiteWriter


class WolfEngine:
    """
    Self-contained Wolf Engine instance. Everything runs in one process.

    Wires: Perception -> GNOME -> SQLite + Forge -> Reasoning -> Archon -> Verdicts.
    """

    def __init__(self, db_dir: str | None = None):
        if db_dir is None:
            try:
                from security.data_paths import WOLF_ENGINE_DIR
                db_dir = str(WOLF_ENGINE_DIR)
            except Exception:
                configured_parent = Path(DB_PATH).expanduser().resolve().parent
                db_dir = str(configured_parent) if str(configured_parent) else os.path.join(
                    tempfile.gettempdir(), "wolf_engine"
                )
        self._db_dir = db_dir
        os.makedirs(self._db_dir, exist_ok=True)

        # Core components
        self.forge = ForgeMemory(window_size=10000)
        self.gnome = GnomeService(SYMBOL_GENOME_PATH)
        self.sql_writer = SQLiteWriter(os.path.join(self._db_dir, "wolf.db"))

        # Reasoning
        self.reasoning = ReasoningEngine()
        self.detector = PatternDetector()
        self.cascade = CascadeEngine(self.forge)

        # Archon
        verdict_db = os.path.join(self._db_dir, "verdicts.db")
        self.orchestrator = Orchestrator(self.forge, verdict_db)

        # Evidence
        self._evidence_dir = os.path.join(self._db_dir, "evidence")
        os.makedirs(self._evidence_dir, exist_ok=True)
        self.evidence_mgr = EvidenceSessionManager(self._evidence_dir, node_id="local")
        self._evidence_workers: dict[str, object] = {}
        self._recording_session_id: str = ""

        # Counters
        self._lock = threading.Lock()
        self.total_ingested = 0
        self.total_analyses = 0
        self.total_tokens = 0
        self._start_time = time.time()
        self._activity_log: list[dict] = []

    @property
    def verdict_store(self) -> VerdictStore:
        """Single VerdictStore — owned by the Orchestrator, shared here."""
        return self.orchestrator.verdict_store

    def perceive_and_ingest(self, text: str, session_id: str = "") -> dict:
        """Full pipeline: text -> tokenize -> symbolize -> forge -> return stats."""
        session_id = session_id or str(uuid.uuid4())[:8]
        tokens = tokenize(text)
        anchors = build_anchors(tokens, session_id)

        # Ensure session exists in SQLite (foreign key requirement)
        try:
            self.sql_writer.create_session(session_id, GENOME_VERSION, "dashboard")
        except Exception:
            pass  # Session may already exist

        ingested = 0
        errors = []
        for anchor in anchors:
            try:
                ingest_anchor(anchor, self.gnome, self.sql_writer, self.forge)
                ingested += 1
            except Exception as exc:
                errors.append(str(exc))

        with self._lock:
            self.total_ingested += ingested
            self.total_tokens += len(tokens)

        self.forge.build_chains()
        stats = self.forge.stats()

        result = {
            "session_id": session_id,
            "tokens": len(tokens),
            "anchors_ingested": ingested,
            "errors": errors[:5],
            "forge": asdict(stats),
        }
        self._log_activity("ingest", f"{len(tokens)} tokens -> {ingested} symbols", session_id)
        return result

    def analyze(self, session_id: str = "", text: str = "") -> dict:
        """Run full governed analysis. Optionally ingest text first."""
        session_id = session_id or str(uuid.uuid4())[:8]

        ingest_result = None
        if text:
            ingest_result = self.perceive_and_ingest(text, session_id)

        # Archon governed analysis
        verdict = self.orchestrator.analyze(session_id=session_id)

        with self._lock:
            self.total_analyses += 1

        # Reasoning details
        result = self.reasoning.analyze_from_forge(self.forge)
        engine_stats = self.reasoning.get_statistics(result)

        # Pattern detection
        causal = CausalAnalyzer(self.forge)
        causal_results = causal.analyze_all(result.windows)
        detection = self.detector.detect(result, causal_results)

        output: dict[str, Any] = {
            "verdict": verdict.to_dict(),
            "engine": engine_stats,
            "patterns": {
                "breaks": len(detection.pattern_breaks),
                "chains": len(detection.causal_chains),
                "anomalies": len(detection.anomalies),
                "break_details": [
                    {"anchor_id": b.anchor_id, "severity": round(b.severity, 3),
                     "anchor_index": b.anchor_index, "break_type": b.break_type}
                    for b in detection.pattern_breaks[:10]
                ],
                "chain_details": [
                    {"start": c.start_index, "length": c.length,
                     "avg_consistency": round(c.avg_consistency, 3)}
                    for c in detection.causal_chains[:10]
                ],
                "anomaly_details": [
                    {"anchor_id": a.anchor_id, "reason": a.reason,
                     "consistency": round(a.consistency, 3)}
                    for a in detection.anomalies[:10]
                ],
            },
            "session_id": session_id,
        }

        if ingest_result:
            output["ingest"] = ingest_result

        self._log_activity(
            "analyze",
            f"verdict={verdict.status.value} conf={verdict.adjusted_confidence:.3f}",
            session_id,
        )
        return output

    def query_symbol(self, symbol_id: int) -> dict | None:
        """Query forge for a symbol."""
        result = self.forge.query(symbol_id)
        if result is None:
            return None
        return {
            "symbol_id": result.symbol_id,
            "resonance": result.resonance,
            "neighbors": dict(result.neighbors),
            "chains": result.chains,
            "event": asdict(result.symbol_event) if result.symbol_event else None,
        }

    def trace_cascade(self, symbol_id: int, direction: str = "both",
                      max_depth: int = 5) -> dict:
        """Run cascade trace from a symbol."""
        engine = CascadeEngine(self.forge, max_depth=max_depth)

        if direction == "forward":
            trace = engine.trace_forward(symbol_id)
        elif direction == "backward":
            trace = engine.trace_backward(symbol_id)
        else:
            fwd, bwd = engine.trace_both(symbol_id)
            all_nodes = bwd.nodes + fwd.nodes
            return {
                "root": symbol_id,
                "direction": "both",
                "depth": max(fwd.max_depth_reached, bwd.max_depth_reached),
                "total_nodes": len(all_nodes),
                "nodes": [
                    {"symbol_id": n.symbol_id, "depth": n.depth,
                     "strength": round(n.co_occurrence_strength, 3),
                     "parent": n.parent_id}
                    for n in all_nodes[:50]
                ],
                "symbol_ids": [n.symbol_id for n in all_nodes[:50]],
            }

        return {
            "root": trace.origin_id,
            "direction": trace.direction,
            "depth": trace.max_depth_reached,
            "total_nodes": len(trace.nodes),
            "nodes": [
                {"symbol_id": n.symbol_id, "depth": n.depth,
                 "strength": round(n.co_occurrence_strength, 3),
                 "parent": n.parent_id}
                for n in trace.nodes[:50]
            ],
            "symbol_ids": trace.symbol_ids()[:50],
        }

    def get_top_symbols(self, limit: int = 20) -> list[dict]:
        """Get top symbols by resonance."""
        sorted_res = sorted(
            self.forge.resonance.items(), key=lambda x: x[1], reverse=True
        )[:limit]
        results = []
        for sid, res in sorted_res:
            neighbors = dict(self.forge.co_occurrence.get(sid, {}))
            top_neighbors = sorted(
                neighbors.items(), key=lambda x: x[1], reverse=True
            )[:5]
            results.append({
                "symbol_id": sid,
                "resonance": round(res, 2),
                "co_occurrence_count": len(neighbors),
                "top_neighbors": [{"id": n, "count": c} for n, c in top_neighbors],
            })
        return results

    def get_forge_stats(self) -> ForgeStats:
        return self.forge.stats()

    def get_system_snapshot(self) -> dict:
        """Full system state."""
        stats = self.forge.stats()
        verdict_counts = self.verdict_store.count_by_status()
        with self._lock:
            activity = list(reversed(self._activity_log[-20:]))
        return {
            "forge": asdict(stats),
            "verdicts": verdict_counts,
            "counters": {
                "total_ingested": self.total_ingested,
                "total_analyses": self.total_analyses,
                "total_tokens": self.total_tokens,
                "uptime_sec": round(time.time() - self._start_time, 1),
            },
            "activity": activity,
        }

    def _log_activity(self, action: str, detail: str, session_id: str = "") -> None:
        entry = {
            "time": time.strftime("%H:%M:%S"),
            "action": action,
            "detail": detail,
            "session_id": session_id,
        }
        with self._lock:
            self._activity_log.append(entry)
            if len(self._activity_log) > 100:
                self._activity_log = self._activity_log[-100:]

    # --- Debug ---

    def debug_push(self) -> dict:
        """Inject a synthetic metric tick + verdict. For self-test / proving liveness."""
        session_id = f"debug-{uuid.uuid4().hex[:6]}"

        verdict = Verdict(
            request_id=f"debug-req-{uuid.uuid4().hex[:6]}",
            session_id=session_id,
            status=VerdictStatus.APPROVED,
            original_confidence=0.85,
            adjusted_confidence=0.85,
        )
        self.verdict_store.record(verdict)

        self._log_activity("debug", "Synthetic metric+verdict injected", session_id)
        return {
            "status": "ok",
            "session_id": session_id,
            "verdict_id": verdict.verdict_id,
            "message": "Synthetic metric tick + verdict injected",
        }

    # --- Session Recording ---

    def start_recording(self, label: str = "") -> dict:
        """Start an evidence recording session."""
        if self.evidence_mgr.active_session is not None:
            return {"error": "Recording already active", "session": self.evidence_mgr.active_session.to_dict()}

        info = self.evidence_mgr.start(label=label)
        self._recording_session_id = info.session_id
        self._log_activity("record_start", f"Session: {info.label}", info.session_id)
        return {"status": "started", "session": info.to_dict()}

    def stop_recording(self) -> dict:
        """Stop the active evidence recording session."""
        if self.evidence_mgr.active_session is None:
            return {"error": "No active recording session"}

        self.stop_evidence_workers()

        info = self.evidence_mgr.stop()
        sid = self._recording_session_id
        self._recording_session_id = ""
        self._log_activity("record_stop", f"Events: {info.event_count}", sid)
        return {"status": "stopped", "session": info.to_dict()}

    def get_recording_status(self) -> dict:
        """Get current recording status."""
        session = self.evidence_mgr.active_session
        if session is None:
            return {"recording": False}
        return {
            "recording": True,
            "session": session.to_dict(),
            "workers": list(self._evidence_workers.keys()),
        }

    # --- Evidence Workers ---

    _WORKER_CLASSES = {
        "system_perf": SystemPerfWorker,
        "network_logger": NetworkLoggerWorker,
        "process_logger": ProcessLoggerWorker,
        "input_logger": InputLoggerWorker,
    }

    def start_evidence_workers(self, worker_names: list[str] | None = None) -> dict:
        """Start evidence workers. Requires an active recording session."""
        if self.evidence_mgr.active_session is None:
            return {"error": "No active recording session. Call /api/session/start first."}

        if worker_names is None:
            worker_names = list(self._WORKER_CLASSES.keys())

        started = []
        errors = []
        for name in worker_names:
            if name in self._evidence_workers:
                errors.append(f"{name}: already running")
                continue
            cls = self._WORKER_CLASSES.get(name)
            if cls is None:
                errors.append(f"{name}: unknown worker")
                continue
            try:
                worker = cls(session_mgr=self.evidence_mgr, interval_sec=5.0)
                worker.start()
                self._evidence_workers[name] = worker
                started.append(name)
            except Exception as exc:
                errors.append(f"{name}: {exc}")

        self._log_activity("workers_start", f"Started: {started}", self._recording_session_id)
        return {"started": started, "errors": errors, "running": list(self._evidence_workers.keys())}

    def stop_evidence_workers(self) -> dict:
        """Stop all running evidence workers."""
        stopped = []
        for name, worker in list(self._evidence_workers.items()):
            try:
                worker.stop()
                stopped.append(name)
            except Exception:
                pass
        self._evidence_workers.clear()
        if stopped:
            self._log_activity("workers_stop", f"Stopped: {stopped}", self._recording_session_id)
        return {"stopped": stopped, "running": []}

    def get_evidence_status(self) -> dict:
        """Get evidence worker status."""
        running = {}
        for name, worker in self._evidence_workers.items():
            running[name] = {
                "events": worker.event_count,
                "running": worker.is_running,
            }
        return {
            "available": list(self._WORKER_CLASSES.keys()),
            "running": running,
            "recording": self.evidence_mgr.active_session is not None,
        }

    # --- Export ---

    def export_data(self, what: str = "verdicts", fmt: str = "json") -> list[dict] | dict:
        """Export data for download."""
        if what == "verdicts":
            return self.verdict_store.get_recent(limit=10000)
        elif what == "sessions":
            return self.evidence_mgr.list_sessions()
        elif what == "forge":
            symbols = []
            for sid, res in sorted(self.forge.resonance.items(), key=lambda x: x[1], reverse=True):
                neighbors = dict(self.forge.co_occurrence.get(sid, {}))
                symbols.append({"symbol_id": sid, "resonance": round(res, 4),
                                "neighbors": len(neighbors)})
            return symbols
        elif what == "snapshot":
            return self.get_system_snapshot()
        else:
            return {"error": f"Unknown export type: {what}"}

    # --- Reset ---

    def reset_state(self) -> dict:
        """Reset forge memory and counters. Verdicts are preserved (audit trail)."""
        self.forge = ForgeMemory(window_size=10000)
        self.reasoning = ReasoningEngine()
        self.detector = PatternDetector()
        self.cascade = CascadeEngine(self.forge)
        with self._lock:
            self.total_ingested = 0
            self.total_analyses = 0
            self.total_tokens = 0
            self._activity_log.clear()
        self._log_activity("reset", "Forge memory and counters cleared")
        return {"status": "ok", "message": "Forge memory and counters reset. Verdict audit trail preserved."}

    def close(self) -> None:
        self.stop_evidence_workers()
        if self.evidence_mgr.active_session:
            self.evidence_mgr.stop()
        self.orchestrator.close()
        self.sql_writer.close()
