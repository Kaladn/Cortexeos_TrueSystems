"""HTTP and WebSocket server exposing the Forest Lexicon bridge."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import threading
import time
import uuid
import sys
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, cast

import glob

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn

if __package__ is None or __package__ == "":
    BASE_DIR = Path(__file__).resolve().parent.parent
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
    from bridges.forest_bridge import ForestLexiconBridge, load_bridge_from_config
else:
    from .forest_bridge import ForestLexiconBridge, load_bridge_from_config

LOGGER = logging.getLogger("forest_bridge_server")
VERSION = "forest-bridge-1.0.0"


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
        self.config_path = config_path
        self.config = self._load_json(config_path)
        self.bridge: ForestLexiconBridge = load_bridge_from_config(config_path)
        self.lock = asyncio.Lock()
        self.jobs = JobManager()

    @staticmethod
    def _load_json(path: Path) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    async def reload(self, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        async with self.lock:
            config_data = dict(self.config)
            if overrides:
                config_data.update(overrides)
            tmp_path = self.config_path.with_suffix(".tmp")
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(config_data, handle, ensure_ascii=False, indent=2)
            tmp_path.replace(self.config_path)
            self.config = config_data
            self.bridge = load_bridge_from_config(self.config_path)
            stats = self.bridge.stats()
            stats["version"] = VERSION
            return stats

    async def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        async with self.lock:
            new_config = self.bridge.update_config(updates)
            stats = self.bridge.stats()
            stats["version"] = VERSION
            return {"config": new_config, "stats": stats, "version": VERSION}


def _normalise_path(raw: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        return (BASE_DIR / path).resolve()
    return path.resolve()


def _parse_patterns(pattern: Optional[str]) -> List[str]:
    if not pattern:
        return ["*"]
    parts = [part.strip() for part in re.split(r"[;,]", pattern) if part.strip()]
    return parts or ["*"]


def _iter_directory(path: Path, recursive: bool, patterns: List[str]) -> Iterable[Path]:
    for pattern in patterns:
        iterator = path.rglob(pattern) if recursive else path.glob(pattern)
        for candidate in iterator:
            if candidate.is_file():
                yield candidate.resolve()


def resolve_job_inputs(paths: List[str], recursive: bool, pattern: Optional[str]) -> Tuple[List[Path], List[str]]:
    patterns = _parse_patterns(pattern)
    resolved: List[Path] = []
    missing: List[str] = []
    seen: Set[Path] = set()

    for raw in paths:
        raw_clean = raw.strip()
        if not raw_clean:
            continue

        if any(ch in raw_clean for ch in "*?["):
            pattern_path = Path(raw_clean).expanduser()
            if not pattern_path.is_absolute():
                pattern_path = BASE_DIR / pattern_path
            matches = [Path(match).resolve() for match in glob.glob(str(pattern_path), recursive=True)]
            files = [candidate for candidate in matches if candidate.is_file()]
            if files:
                for candidate in files:
                    if candidate not in seen:
                        seen.add(candidate)
                        resolved.append(candidate)
            else:
                missing.append(raw_clean)
            continue

        normalised = _normalise_path(raw_clean)

        if normalised.is_dir():
            files = list(_iter_directory(normalised, recursive, patterns))
            if files:
                for candidate in files:
                    if candidate not in seen:
                        seen.add(candidate)
                        resolved.append(candidate)
            else:
                missing.append(raw_clean)
            continue

        if normalised.is_file():
            if normalised not in seen:
                seen.add(normalised)
                resolved.append(normalised)
            continue

        missing.append(raw_clean)

    return resolved, missing


class MapRequest(BaseModel):
    text: str
    source: Optional[str] = "inline"


class MapFilesRequest(BaseModel):
    paths: List[str]
    source: Optional[str] = "batch"
    recursive: Optional[bool] = True
    pattern: Optional[str] = None
    ignore_missing: Optional[bool] = False


class ConfigUpdateRequest(BaseModel):
    min_len: Optional[int]
    topK: Optional[int]
    window: Optional[int]
    alpha_only: Optional[bool]
    regex_include: Optional[str]
    regex_exclude: Optional[str]
    star_policy: Optional[str]
    batch_size: Optional[int]
    workers: Optional[int]
    rate_limit: Optional[int]
    gpu: Optional[str]


class CancelRequest(BaseModel):
    job_id: str


class SnapshotRequest(BaseModel):
    tag: Optional[str]


class RollbackRequest(BaseModel):
    path: str


class Get616Request(BaseModel):
    word: str
    topk: Optional[int]


class AnalyzeUnmappedRequest(BaseModel):
    """Request to analyze unmapped tokens from 616 reports."""
    reports_root: Optional[str] = None
    report_paths: Optional[List[str]] = None


class LexiconAppendRequest(BaseModel):
    word: str
    status: Optional[str]


class AssignSymbolRequest(BaseModel):
    word: str
    symbol: Optional[str]
    force: Optional[bool] = False


class SetStatusRequest(BaseModel):
    word: str
    status: Optional[str]


class LoadRequest(BaseModel):
    lexicon_root: Optional[str]
    reports_root: Optional[str]
    gpu: Optional[str]
    window: Optional[int]
    topK: Optional[int]
    min_len: Optional[int]


class WebSocketManager:
    def __init__(self):
        self.active: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active:
                self.active.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        payload = json.dumps(message)
        async with self._lock:
            stale = []
            for ws in self.active:
                try:
                    await ws.send_text(payload)
                except WebSocketDisconnect:
                    stale.append(ws)
            for ws in stale:
                if ws in self.active:
                    self.active.remove(ws)


def create_app(state: BridgeState) -> FastAPI:
    app = FastAPI(title="Forest Lexicon Bridge", version=VERSION)
    ws_manager = WebSocketManager()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/stats")
    async def get_stats():
        stats = state.bridge.stats()
        stats["version"] = VERSION
        return stats

    @app.post("/api/load")
    async def post_load(body: LoadRequest):
        overrides = cast(Dict[str, Any], body.dict(exclude_none=True))
        stats = await state.reload(overrides or None)
        await ws_manager.broadcast({
            "evt": "reload",
            "version": VERSION,
            "device": stats.get("device_name"),
            "entries": stats.get("entries"),
        })
        return stats

    @app.post("/api/map")
    async def post_map(body: MapRequest):
        if not body.text:
            raise HTTPException(status_code=400, detail="text is required")
        result = state.bridge.map_text(body.text, source=body.source or "inline")
        result["version"] = VERSION
        return result

    async def _map_files_job(job_id: str, paths: List[str], source: str):
        resolved = [Path(p) for p in paths]
        job = state.jobs.get(job_id)
        if not job:
            return
        loop = asyncio.get_running_loop()

        state.jobs.start(job_id, total=len(resolved), processed=0, source=source)
        await ws_manager.broadcast({
            "evt": "job-start",
            "job_id": job_id,
            "job": job.job_type,
            "count": len(resolved),
            "source": source,
            "version": VERSION,
        })

        def cancel_cb() -> bool:
            current = state.jobs.get(job_id)
            return bool(current and current.cancel_requested)

        def progress_cb(idx: int, total: int, current_path: Path, result: Dict[str, Any]):
            state.jobs.update_progress(job_id, processed=idx, total=total, current=str(current_path))
            payload = {
                "evt": "job-progress",
                "job_id": job_id,
                "job": job.job_type,
                "processed": idx,
                "total": total,
                "current": str(current_path),
                "version": VERSION,
            }
            asyncio.run_coroutine_threadsafe(ws_manager.broadcast(payload), loop)

        try:
            result = await asyncio.to_thread(
                state.bridge.map_files,
                resolved,
                progress_cb=progress_cb,
                cancel_cb=cancel_cb,
            )
            if cancel_cb():
                state.jobs.finish_cancel(job_id)
                await ws_manager.broadcast({
                    "evt": "job-cancelled",
                    "job_id": job_id,
                    "job": job.job_type,
                    "version": VERSION,
                })
                return

            output_path = state.bridge.write_report("616_map", result)
            state.jobs.complete(job_id, str(output_path))
            await ws_manager.broadcast({
                "evt": "job-complete",
                "job_id": job_id,
                "job": job.job_type,
                "result_path": str(output_path),
                "device": state.bridge.device_info.name,
                "version": VERSION,
            })
        except Exception as exc:  # pragma: no cover - surfaced to clients
            LOGGER.exception("map_files job failed")
            state.jobs.fail(job_id, str(exc))
            await ws_manager.broadcast({
                "evt": "job-error",
                "job_id": job_id,
                "job": job.job_type,
                "error": str(exc),
                "version": VERSION,
            })

    @app.post("/api/map_files")
    async def post_map_files(body: MapFilesRequest):
        if not body.paths:
            raise HTTPException(status_code=400, detail="paths is required")
        recursive = bool(body.recursive) if body.recursive is not None else True
        try:
            resolved, missing = resolve_job_inputs(body.paths, recursive, body.pattern)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if missing and not body.ignore_missing:
            raise HTTPException(status_code=404, detail={"missing": missing})

        if not resolved:
            raise HTTPException(status_code=400, detail="No files matched provided paths")

        resolved_paths = [str(path) for path in resolved]
        job_payload = {
            "paths": resolved_paths,
            "source": body.source or "batch",
            "recursive": recursive,
            "pattern": body.pattern,
            "missing": missing,
        }
        job = state.jobs.create_job("map_files", job_payload)
        asyncio.create_task(_map_files_job(job.job_id, resolved_paths, body.source or "batch"))
        response = {
            "status": "queued",
            "job_id": job.job_id,
            "files": len(resolved_paths),
            "missing": missing,
            "version": VERSION,
        }
        return response

    @app.get("/api/lookup")
    async def get_lookup(word: str):
        if not word:
            raise HTTPException(status_code=400, detail="word parameter is required")
        result = state.bridge.lookup(word)
        result["version"] = VERSION
        return result

    @app.get("/api/config")
    async def get_config():
        return {"config": state.bridge.get_config(), "version": VERSION}

    @app.patch("/api/config")
    async def patch_config(body: ConfigUpdateRequest):
        payload = cast(Dict[str, Any], body.dict(exclude_none=True))
        if not payload:
            raise HTTPException(status_code=400, detail="No config fields provided")
        result = await state.update_config(payload)
        await ws_manager.broadcast({
            "evt": "config-update",
            "config": result["config"],
            "version": VERSION,
        })
        return result

    @app.post("/api/cancel")
    async def post_cancel(body: CancelRequest):
        record = state.jobs.cancel(body.job_id)
        if not record:
            raise HTTPException(status_code=404, detail="Job not found")
        await ws_manager.broadcast({
            "evt": "job-cancel",
            "job_id": record.job_id,
            "job": record.job_type,
            "version": VERSION,
        })
        return {"status": record.status, "job_id": record.job_id, "version": VERSION}

    @app.get("/api/jobs")
    async def list_jobs():
        jobs = state.jobs.list_jobs()
        return {
            "jobs": [
                {
                    "job_id": job.job_id,
                    "job": job.job_type,
                    "status": job.status,
                    "created_at": job.created_at,
                    "updated_at": job.updated_at,
                    "progress": job.progress,
                    "result_path": job.result_path,
                    "error": job.error,
                }
                for job in jobs
            ],
            "version": VERSION,
        }

    @app.post("/api/snapshot")
    async def post_snapshot(body: SnapshotRequest):
        path = state.bridge.create_snapshot(body.tag)
        await ws_manager.broadcast({
            "evt": "snapshot",
            "path": str(path),
            "version": VERSION,
        })
        return {"path": str(path), "version": VERSION}

    @app.post("/api/rollback")
    async def post_rollback(body: RollbackRequest):
        snapshot_path = Path(body.path)
        stats = state.bridge.rollback(snapshot_path)
        stats["version"] = VERSION
        await ws_manager.broadcast({
            "evt": "rollback",
            "path": str(snapshot_path),
            "stats": stats,
            "version": VERSION,
        })
        return stats

    @app.post("/api/616")
    async def post_get_616(body: Get616Request):
        if not body.word:
            raise HTTPException(status_code=400, detail="word is required")
        payload = state.bridge.get_616(body.word, body.topk)
        payload["version"] = VERSION
        return payload

    @app.post("/api/analyze_unmapped")
    async def post_analyze_unmapped(body: AnalyzeUnmappedRequest):
        """Analyze unmapped tokens from 616 reports and return statistics."""
        if not state.bridge:
            raise HTTPException(status_code=503, detail="Bridge not loaded")
        
        import sys
        sys.path.insert(0, str(BASE_DIR / "tools"))
        try:
            from analyze_unmapped_tokens import analyze_reports, generate_review_report, discover_reports
        except ImportError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to load analysis tool: {exc}")
        
        # Determine which reports to analyze
        report_paths: List[Path] = []
        if body.report_paths:
            report_paths = [Path(p) for p in body.report_paths if Path(p).exists()]
        else:
            reports_root = Path(body.reports_root) if body.reports_root else state.bridge.reports_root
            report_paths = discover_reports(reports_root)
        
        if not report_paths:
            return {
                "error": "No reports found to analyze",
                "reports_analyzed": 0,
                "summary": {},
                "version": VERSION
            }
        
        # Analyze reports
        stats_list, unmapped = analyze_reports(report_paths)
        
        # Generate report (without writing to file)
        report = generate_review_report(stats_list, unmapped, output_path=None)
        report["version"] = VERSION
        
        return report

    @app.post("/api/lexicon/append")
    async def post_lexicon_append(body: LexiconAppendRequest):
        if not body.word:
            raise HTTPException(status_code=400, detail="word is required")
        result = state.bridge.append_word(body.word, body.status)
        result["version"] = VERSION
        await ws_manager.broadcast({
            "evt": "lexicon-append",
            "word": body.word,
            "version": VERSION,
        })
        return result

    @app.post("/api/symbol/assign")
    async def post_assign_symbol(body: AssignSymbolRequest):
        if not body.word:
            raise HTTPException(status_code=400, detail="word is required")
        try:
            result = state.bridge.assign_symbol(body.word, body.symbol, body.force or False)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        result["version"] = VERSION
        await ws_manager.broadcast({
            "evt": "symbol-assign",
            "word": body.word,
            "symbol": result.get("symbol"),
            "version": VERSION,
        })
        return result

    @app.post("/api/lexicon/status")
    async def post_lexicon_status(body: SetStatusRequest):
        if not body.word:
            raise HTTPException(status_code=400, detail="word is required")
        result = state.bridge.set_status(body.word, body.status)
        result["version"] = VERSION
        await ws_manager.broadcast({
            "evt": "lexicon-status",
            "word": body.word,
            "status": body.status,
            "version": VERSION,
        })
        return result

    @app.websocket("/ws/stream")
    async def websocket_endpoint(websocket: WebSocket):
        await ws_manager.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            await ws_manager.disconnect(websocket)

    ui_dir = BASE_DIR / "ui"
    if ui_dir.exists():
        app.mount("/ui", StaticFiles(directory=str(ui_dir), html=True), name="ui")

        @app.get("/")
        async def serve_ui_root():
            return FileResponse(ui_dir / "index.html")

        @app.get("/forest_ui.css")
        async def serve_legacy_css():
            return FileResponse(ui_dir / "forest_ui.css")

        @app.get("/forest_ui.js")
        async def serve_legacy_js():
            return FileResponse(ui_dir / "forest_ui.js")

        @app.get("/favicon.ico")
        async def serve_favicon():
            return FileResponse(ui_dir / "assets" / "logo.svg")

    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Forest Lexicon Bridge server")
    parser.add_argument("--config", type=Path, required=True, help="Path to forest.config.json")
    parser.add_argument("--host", type=str, help="Override host")
    parser.add_argument("--port", type=int, help="Override port")
    parser.add_argument("--log-level", type=str, default="info")
    return parser.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    state = BridgeState(args.config)
    config = state.config

    host = args.host or config.get("server", {}).get("host", "127.0.0.1")
    port = args.port or config.get("server", {}).get("port", 5050)

    app = create_app(state)
    uvicorn.run(app, host=host, port=port, log_level=args.log_level)


if __name__ == "__main__":
    main()
