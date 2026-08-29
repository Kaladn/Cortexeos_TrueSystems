"""DocuMap ingestion and mapping orchestration service."""
from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List

import httpx
from fastapi import HTTPException, Request

from bridges.helpers import resolve_job_inputs, _safe_error
from bridges.models import CommitMapRequest, IntakeScanRequest, MapFilesRequest, MapRequest
from bridges.state import LOGGER


class DocuMapIngestionService:
    """Owns map staging, commit ingestion, and map_files orchestration."""

    def __init__(self, *, state: Any, ws_manager: Any, base_dir: Path, version: str) -> None:
        self.state = state
        self.ws_manager = ws_manager
        self.base_dir = base_dir
        self.version = version

    async def post_map(
        self,
        body: MapRequest,
        request: Request,
        ensure_lexicon_loaded: Callable[[str], Awaitable[None]],
    ) -> dict:
        from security.runtime_log import debug_enter, debug_exit, log_error as _rt_error

        def _trace_id(req: Request) -> str | None:
            try:
                return req.headers.get("X-Trace-Id")
            except Exception:
                return None

        _t0 = time.perf_counter()
        _tid = _trace_id(request)
        debug_enter("documap", "/api/map", trace_id=_tid, extra={"source": body.source or "inline", "text_len": len(body.text or "")})
        if not body.text:
            debug_exit("documap", "/api/map", ok=False, detail="empty_text", ms=(time.perf_counter() - _t0) * 1000, trace_id=_tid)
            raise HTTPException(status_code=400, detail="text is required")
        try:
            await ensure_lexicon_loaded("map")
            result = self.state.bridge.map_text(body.text, source=body.source or "inline", device=body.device or "cpu")
        except Exception as exc:
            _rt_error("documap", "/api/map", str(exc), level=3, trace_id=_tid)
            debug_exit("documap", "/api/map", ok=False, detail=str(exc), ms=(time.perf_counter() - _t0) * 1000, trace_id=_tid)
            raise
        result["version"] = self.version

        staging_dir = self.state.bridge.reports_root / "_staging"
        staging_dir.mkdir(parents=True, exist_ok=True)
        staging_path = staging_dir / "last_map.json"
        with open(staging_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        LOGGER.info("Staged map result to %s", staging_path)
        debug_exit("documap", "/api/map", ok=True, ms=(time.perf_counter() - _t0) * 1000, trace_id=_tid, extra={"anchors": result.get("unique_anchors")})
        return result

    async def post_map_commit(self, body: CommitMapRequest) -> dict[str, Any]:
        import concurrent.futures

        report = body.report
        if report is None:
            staging_path = self.state.bridge.reports_root / "_staging" / "last_map.json"
            if not staging_path.exists():
                raise HTTPException(status_code=404, detail="No staged map found. Run a mapping job first.")
            with open(staging_path, "r", encoding="utf-8") as f:
                report = json.load(f)
        elif not isinstance(report, dict):
            raise HTTPException(status_code=400, detail="report must be an object when provided")

        report.setdefault("version", self.version)
        output_path = self.state.bridge.write_report(body.job_name or "616_map", report)
        LOGGER.info("Committed map to data lake: %s", output_path)

        grove_receipt = None
        grove_error = None
        _cite_id = body.cite_id or report.get("cite_id") or report.get("source")
        if _cite_id:
            try:
                _llm_tls = self.state.config.get("server", {}).get("tls", False)
                _llm_base = f"{'https' if _llm_tls else 'http'}://127.0.0.1:11435"
                _verify_tls: bool | str = False
                try:
                    from security.tls import CERT_PATH as _CERT_PATH
                    if _llm_tls and _CERT_PATH.exists():
                        _verify_tls = str(_CERT_PATH)
                except ImportError:
                    pass
                async with httpx.AsyncClient(verify=_verify_tls, timeout=30.0) as _c:
                    _cr = await _c.get(f"{_llm_base}/api/library/citations/{_cite_id}/content")
                    if _cr.status_code == 200:
                        _cite_data = _cr.json()
                        _text = _cite_data.get("content") or _cite_data.get("text") or ""
                        if _text:
                            def _do_ingest():
                                sys.path.insert(0, str(self.base_dir))
                                from core.lakespeak.ingest.pipeline import ingest_text
                                return ingest_text(
                                    text=_text,
                                    source_type="documap",
                                    source_path=_cite_id,
                                    bridge=self.state.bridge,
                                    skip_mapped_guard=True,
                                )

                            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _pool:
                                grove_receipt = await asyncio.get_event_loop().run_in_executor(_pool, _do_ingest)
                            LOGGER.info("Grove ingested from citation %s: %s", _cite_id, grove_receipt.get("receipt_id", "?"))
                        else:
                            grove_error = "Citation content empty"
                    else:
                        grove_error = f"Citation fetch failed: HTTP {_cr.status_code}"
            except Exception as exc:
                LOGGER.warning("Grove ingestion failed for %s: %s", _cite_id, exc)
                grove_error = _safe_error(exc)

        result = {"status": "committed", "path": str(output_path), "version": self.version}
        if grove_receipt:
            result["grove_receipt"] = grove_receipt.get("receipt_id")
            result["grove_chunks"] = grove_receipt.get("chunk_count", 0)
        if grove_error:
            result["grove_error"] = grove_error
        return result

    async def _map_files_job(self, job_id: str, paths: List[str], source: str) -> None:
        resolved = [Path(p) for p in paths]
        job = self.state.jobs.get(job_id)
        if not job:
            return
        loop = asyncio.get_running_loop()
        self.state.jobs.start(job_id, total=len(resolved), processed=0, source=source)
        await self.ws_manager.broadcast({"evt": "job-start", "job_id": job_id, "job": job.job_type, "count": len(resolved), "source": source, "version": self.version})

        def cancel_cb() -> bool:
            current = self.state.jobs.get(job_id)
            return bool(current and current.cancel_requested)

        def progress_cb(idx: int, total: int, current_path: Path, result: Dict[str, Any]):
            self.state.jobs.update_progress(job_id, processed=idx, total=total, current=str(current_path))
            payload = {"evt": "job-progress", "job_id": job_id, "job": job.job_type, "processed": idx, "total": total, "current": str(current_path), "version": self.version}
            asyncio.run_coroutine_threadsafe(self.ws_manager.broadcast(payload), loop)

        try:
            result = await asyncio.to_thread(self.state.bridge.map_files, resolved, progress_cb=progress_cb, cancel_cb=cancel_cb)
            if cancel_cb():
                self.state.jobs.finish_cancel(job_id)
                await self.ws_manager.broadcast({"evt": "job-cancelled", "job_id": job_id, "job": job.job_type, "version": self.version})
                return
            output_path = self.state.bridge.write_report("616_map", result)
            self.state.jobs.complete(job_id, str(output_path))
            await self.ws_manager.broadcast({"evt": "job-complete", "job_id": job_id, "job": job.job_type, "result_path": str(output_path), "device": self.state.bridge.device_info.name, "version": self.version})
        except Exception as exc:
            LOGGER.exception("map_files job failed")
            self.state.jobs.fail(job_id, _safe_error(exc))
            await self.ws_manager.broadcast({"evt": "job-error", "job_id": job_id, "job": job.job_type, "error": _safe_error(exc), "version": self.version})

    async def post_intake_scan(self, body: IntakeScanRequest) -> dict[str, Any]:
        source = Path(body.source_path)
        if not source.exists():
            raise HTTPException(status_code=404, detail="Path not found")
        if not source.is_dir():
            raise HTTPException(status_code=400, detail="Path must be a directory")
        recursive = body.scan_mode == "full_directory"
        raw_files = [p for p in source.rglob("*") if p.is_file()] if recursive else [p for p in source.iterdir() if p.is_file()]
        discovered = len(raw_files)
        resolved, _ = resolve_job_inputs([str(source)], recursive=recursive, pattern=None)
        eligible = len(resolved)
        return {"source_path": str(source), "scan_mode": body.scan_mode, "discovered_paths": discovered, "eligible_paths": eligible, "skipped_paths": discovered - eligible}

    async def post_map_files(
        self,
        body: MapFilesRequest,
        ensure_lexicon_loaded: Callable[[str], Awaitable[None]],
        background_tasks_set: set,
        task_done_cb: Callable[[asyncio.Task], None],
    ) -> dict[str, Any]:
        if not body.paths:
            raise HTTPException(status_code=400, detail="paths is required")
        await ensure_lexicon_loaded("map_files")
        recursive = bool(body.recursive) if body.recursive is not None else True
        try:
            resolved, missing = resolve_job_inputs(body.paths, recursive, body.pattern)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=_safe_error(exc)) from exc
        if missing and not body.ignore_missing:
            raise HTTPException(status_code=404, detail={"missing": missing})
        if not resolved:
            raise HTTPException(status_code=400, detail="No files matched provided paths")

        resolved_paths = [str(path) for path in resolved]
        job_payload = {"paths": resolved_paths, "source": body.source or "batch", "recursive": recursive, "pattern": body.pattern, "missing": missing}
        job = self.state.jobs.create_job("map_files", job_payload)
        task = asyncio.create_task(self._map_files_job(job.job_id, resolved_paths, body.source or "batch"))
        background_tasks_set.add(task)
        task.add_done_callback(task_done_cb)
        return {"status": "queued", "job_id": job.job_id, "files": len(resolved_paths), "missing": missing, "version": self.version}
