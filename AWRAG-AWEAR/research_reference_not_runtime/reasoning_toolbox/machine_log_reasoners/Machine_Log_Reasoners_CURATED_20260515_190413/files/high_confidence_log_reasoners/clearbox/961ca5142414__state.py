"""BridgeState, JobManager, and JobRecord — extracted from clearbox_bridge_server.py."""
from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import json as _json

from security.data_paths import STATE_DIR
from bridges.clearbox_bridge import ClearboxLexiconBridge, load_bridge_from_config

LOGGER = logging.getLogger("clearbox_bridge_server")
VERSION = "clearbox-bridge-2.5.0"


@dataclass
class JobRecord:
    job_id: str
    job_type: str
    created_at: float
    status: str = "queued"
    progress: Dict[str, Any] = field(default_factory=dict)
    result_path: Optional[str] = None
    error: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    updated_at: float = field(default_factory=lambda: time.time())
    cancel_requested: bool = False


class JobManager:
    def __init__(self) -> None:
        self._jobs: Dict[str, JobRecord] = {}
        self._lock = threading.Lock()

    def create_job(self, job_type: str, payload: Optional[Dict[str, Any]] = None) -> JobRecord:
        job_id = uuid.uuid4().hex
        record = JobRecord(job_id=job_id, job_type=job_type, created_at=time.time(), payload=payload or {})
        with self._lock:
            self._jobs[job_id] = record
        return record

    def get(self, job_id: str) -> Optional[JobRecord]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self) -> List[JobRecord]:
        with self._lock:
            return list(self._jobs.values())

    def start(self, job_id: str, **progress: Any) -> None:
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                return
            record.status = "running"
            record.progress.update(progress)
            record.updated_at = time.time()

    def update_progress(self, job_id: str, **progress: Any) -> None:
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                return
            record.progress.update(progress)
            record.updated_at = time.time()

    def complete(self, job_id: str, result_path: Optional[str] = None) -> None:
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                return
            record.status = "completed"
            record.result_path = result_path
            record.updated_at = time.time()

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                return
            record.status = "error"
            record.error = error
            record.updated_at = time.time()

    def cancel(self, job_id: str) -> Optional[JobRecord]:
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                return None
            record.cancel_requested = True
            record.status = "cancelling" if record.status == "running" else "cancelled"
            record.updated_at = time.time()
            return record

    def finish_cancel(self, job_id: str) -> None:
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                return
            record.status = "cancelled"
            record.updated_at = time.time()


class BridgeState:
    def __init__(self, config_path: Path):
        from bridges.services.inference import InferenceService
        from bridges.services.lakespeak_service import LakeSpeakService
        from bridges.services.lexicon_stats import LexiconStatsService
        from bridges.services.reasoning_service import ReasoningService

        self.config_path = config_path
        self.config = self._load_json(config_path)
        self.bridge: ClearboxLexiconBridge = load_bridge_from_config(config_path, load_lexicon=False)
        self.lock = asyncio.Lock()
        self._config_write_lock = asyncio.Lock()
        self.jobs = JobManager()
        self.ollama_client: Optional[httpx.AsyncClient] = None
        self.reasoning_service = ReasoningService()
        self.lakespeak_service = LakeSpeakService()
        self.inference_service = InferenceService(
            state=self,
            reasoning_service=self.reasoning_service,
            lakespeak_service=self.lakespeak_service,
        )
        self.lexicon_stats_service = LexiconStatsService()
        # Spell-check components (lazy-init)
        self._spellchecker: Optional[object] = None
        self._alias_map: Optional[object] = None
        self._correction_queue: Optional[object] = None

    async def get_ollama_client(self) -> httpx.AsyncClient:
        if self.ollama_client is None or self.ollama_client.is_closed:
            self.ollama_client = httpx.AsyncClient(timeout=120.0)
        return self.ollama_client

    def get_ollama_base_url(self) -> str:
        inference_cfg = self.config.get("inference", {})
        ollama_cfg = self.config.get("ollama", {})
        raw = (
            inference_cfg.get("ollama_base_url")
            or ollama_cfg.get("base_url")
            or self.config.get("ollama_base_url")
            or "http://127.0.0.1:11434"
        )
        return str(raw).rstrip("/")

    async def close(self):
        if self.ollama_client and not self.ollama_client.is_closed:
            await self.ollama_client.close()

    def get_spellchecker(self):
        if self._spellchecker is None:
            self._spellchecker = self.lakespeak_service.create_spellchecker(
                lexicon_dir=self.bridge.lexicon_root
            )
        return self._spellchecker

    def get_alias_map(self):
        if self._alias_map is None:
            self._alias_map = self.lakespeak_service.create_alias_map(
                data_dir=STATE_DIR / "spellcheck"
            )
        return self._alias_map

    def get_correction_queue(self):
        if self._correction_queue is None:
            self._correction_queue = self.lakespeak_service.create_correction_queue(
                data_dir=STATE_DIR / "spellcheck"
            )
        return self._correction_queue

    @staticmethod
    def _load_json(path: Path) -> Dict[str, Any]:
        with open(path, encoding="utf-8") as _f:
            return _json.load(_f)

    @staticmethod
    def _deep_merge(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(base)
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = BridgeState._deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged

    async def write_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        async with self._config_write_lock:
            tmp_path: Optional[Path] = None
            try:
                current = self._load_json(self.config_path)
            except (FileNotFoundError, _json.JSONDecodeError, ValueError):
                current = dict(self.config)
            merged = self._deep_merge(current, updates)
            try:
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                tmp_path = self.config_path.with_suffix(f"{self.config_path.suffix}.{uuid.uuid4().hex}.tmp")
                with open(tmp_path, "w", encoding="utf-8") as _cf:
                    _json.dump(merged, _cf, indent=2, ensure_ascii=False)
                tmp_path.replace(self.config_path)
                self.config = merged
                return dict(self.config)
            except Exception:
                if tmp_path and tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except OSError:
                        pass
                raise

    async def ensure_bridge_loaded(self, reason: str = "on-demand") -> None:
        if self.bridge.loaded:
            return
        async with self.lock:
            if self.bridge.loaded:
                return
            t0 = time.perf_counter()
            await asyncio.to_thread(self.bridge.load)
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            LOGGER.info(
                "Lexicon lazy-loaded: entries=%s in %sms [reason=%s]",
                len(self.bridge.entries),
                elapsed_ms,
                reason,
            )

    def compute_pack_inventory(self) -> Dict[str, Any]:
        return self.lexicon_stats_service.compute_pack_inventory(self.bridge)

    async def stats_snapshot(self) -> Dict[str, Any]:
        stats = self.bridge.stats()
        if self.bridge.loaded:
            return stats
        disk_stats = await asyncio.to_thread(self.lexicon_stats_service.compute_disk_stats, self.bridge)
        stats.update(disk_stats)
        return stats

    async def reload(self, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        async with self.lock:
            if overrides:
                await self.write_config(overrides)
            else:
                self.config = self._load_json(self.config_path)
            self.bridge = load_bridge_from_config(self.config_path)
            self._spellchecker = None
            stats = self.bridge.stats()
            stats["version"] = VERSION
            return stats

    async def rollback_snapshot(self, snapshot_path: Path) -> Dict[str, Any]:
        async with self.lock:
            stats = self.bridge.rollback(snapshot_path, persist=False)
            await self.write_config(self.bridge.get_config())
            stats["version"] = VERSION
            return stats

    async def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        async with self.lock:
            normalized: Dict[str, Any] = {}
            for key in ["min_len", "topK", "window", "alpha_only", "regex_include", "regex_exclude", "gpu"]:
                if key in updates and updates[key] is not None:
                    value = updates[key]
                    if key in {"min_len", "topK", "window"}:
                        value = int(value)
                    normalized[key] = value
            if not normalized:
                stats = self.bridge.stats()
                stats["version"] = VERSION
                return {"config": dict(self.config), "stats": stats, "version": VERSION}

            new_config = self.bridge.update_config(normalized, persist=False)
            await self.write_config(new_config)
            stats = self.bridge.stats()
            stats["version"] = VERSION
            return {"config": dict(self.config), "stats": stats, "version": VERSION}
