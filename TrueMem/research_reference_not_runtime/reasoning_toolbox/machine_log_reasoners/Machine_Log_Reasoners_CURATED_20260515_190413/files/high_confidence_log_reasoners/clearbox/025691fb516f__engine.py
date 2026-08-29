"""
OpenRefine Plugin — Engine
Manages the OpenRefine subprocess, caches CSRF tokens,
and proxies all HTTP calls to the local OpenRefine server.
Thread-safe singleton; all blocking I/O offloaded to asyncio.to_thread().
"""
from __future__ import annotations

import logging
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Lazy import of requests (heavy) ──────────────────────────────────────────
_requests = None

def _req():
    global _requests
    if _requests is None:
        import requests as _r
        _requests = _r
    return _requests


class OpenRefineEngine:
    """
    Owns the OpenRefine process lifecycle and HTTP proxy layer.
    All methods are synchronous — call from asyncio.to_thread().
    """

    def __init__(self) -> None:
        from openrefine.config import CONFIG
        self._cfg = CONFIG
        self._lock = threading.RLock()
        self._proc: Optional[subprocess.Popen] = None
        self._csrf_token: Optional[str] = None
        self._csrf_fetched_at: float = 0.0
        self._csrf_ttl: float = 1700.0  # ~28 min (token valid ~30 min)
        self._override_port: Optional[int] = None
        self._override_memory: Optional[int] = None
        self._override_install_dir: Optional[Path] = None
        logger.info("OpenRefineEngine initialised (OR not yet started)")

    # ── Public config accessors ───────────────────────────────────────────────
    @property
    def port(self) -> int:
        return self._override_port or self._cfg.or_port

    @property
    def host(self) -> str:
        return self._cfg.or_host

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def install_dir(self) -> Path:
        return self._override_install_dir or self._cfg.or_install_dir

    @property
    def memory_mb(self) -> int:
        return self._override_memory or self._cfg.or_memory_mb

    # ── Status ────────────────────────────────────────────────────────────────
    def is_running(self) -> bool:
        """True if OpenRefine HTTP API is reachable."""
        try:
            r = _req().get(f"{self.base_url}/command/core/get-version", timeout=2.0)
            return r.status_code == 200
        except Exception:
            return False

    def or_version(self) -> str:
        try:
            r = _req().get(f"{self.base_url}/command/core/get-version", timeout=2.0)
            if r.ok:
                return r.json().get("full_version", r.json().get("version", ""))
        except Exception:
            pass
        return ""

    def status(self) -> Dict[str, Any]:
        running = self.is_running()
        projects: Dict = {}
        if running:
            try:
                r = _req().get(f"{self.base_url}/command/core/get-all-project-metadata", timeout=3.0)
                if r.ok:
                    projects = r.json().get("projects", {})
            except Exception:
                pass
        return {
            "ok": True,
            "running": running,
            "or_version": self.or_version() if running else "",
            "or_host": self.host,
            "or_port": self.port,
            "install_dir": str(self.install_dir),
            "workspace_dir": str(self._cfg.workspace_dir),
            "project_count": len(projects),
        }

    # ── Process management ────────────────────────────────────────────────────
    def start(self) -> Dict[str, Any]:
        with self._lock:
            if self.is_running():
                return {"ok": True, "message": "Already running", "pid": self._proc.pid if self._proc else None, "or_port": self.port}

            exe = self.install_dir / "openrefine.exe"
            bat = self.install_dir / "refine.bat"

            if exe.exists():
                cmd = [str(exe), f"-p{self.port}", f"-m{self.memory_mb}M"]
            elif bat.exists():
                cmd = ["cmd", "/c", str(bat), "-p", str(self.port), "-m", f"{self.memory_mb}M"]
            else:
                return {"ok": False, "message": f"OpenRefine not found at {self.install_dir}", "error": {"type": "not_found"}}

            t0 = time.time()
            try:
                self._proc = subprocess.Popen(
                    cmd,
                    cwd=str(self.install_dir),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
                )
            except Exception as exc:
                return {"ok": False, "message": f"Failed to launch: {exc}", "error": {"type": "launch_error", "detail": str(exc)}}

            # Poll until ready
            deadline = t0 + self._cfg.or_startup_timeout_s
            while time.time() < deadline:
                if self.is_running():
                    elapsed_ms = int((time.time() - t0) * 1000)
                    logger.info("OpenRefine ready in %dms (pid=%s)", elapsed_ms, self._proc.pid)
                    return {"ok": True, "message": "OpenRefine started", "pid": self._proc.pid, "or_port": self.port, "startup_ms": elapsed_ms}
                time.sleep(self._cfg.or_poll_interval_s)

            # Timeout
            self._proc.terminate()
            self._proc = None
            return {"ok": False, "message": f"OpenRefine did not start within {self._cfg.or_startup_timeout_s}s", "error": {"type": "timeout"}}

    def stop(self) -> Dict[str, Any]:
        with self._lock:
            pid = self._proc.pid if self._proc else None
            if self._proc is not None:
                try:
                    self._proc.terminate()
                    self._proc.wait(timeout=10)
                except Exception:
                    self._proc.kill()
                self._proc = None
                self._csrf_token = None
                return {"ok": True, "message": "OpenRefine stopped", "pid": pid}

            # If we didn't launch it, try to find and kill by port
            try:
                import psutil
                for proc in psutil.process_iter(["pid", "name", "connections"]):
                    for conn in proc.info.get("connections") or []:
                        if conn.laddr.port == self.port:
                            proc.kill()
                            return {"ok": True, "message": f"Killed process {proc.pid} on port {self.port}", "pid": proc.pid}
            except ImportError:
                pass

            return {"ok": False, "message": "OpenRefine not running (or not started by this plugin)", "pid": None}

    # ── CSRF ──────────────────────────────────────────────────────────────────
    def _get_csrf(self) -> str:
        now = time.time()
        with self._lock:
            if self._csrf_token and (now - self._csrf_fetched_at) < self._csrf_ttl:
                return self._csrf_token
        try:
            r = _req().get(f"{self.base_url}/command/core/get-csrf-token", timeout=5.0)
            token = r.json().get("token", "")
            with self._lock:
                self._csrf_token = token
                self._csrf_fetched_at = now
            return token
        except Exception as exc:
            logger.warning("CSRF fetch failed: %s", exc)
            return ""

    def _post(self, path: str, data: dict = None, files=None, timeout: float = 10.0) -> Dict[str, Any]:
        """POST to OpenRefine with CSRF token."""
        token = self._get_csrf()
        params = {"csrf_token": token} if token else {}
        try:
            r = _req().post(
                f"{self.base_url}{path}",
                params=params,
                data=data or {},
                files=files,
                timeout=timeout,
            )
            if r.headers.get("content-type", "").startswith("application/json"):
                return r.json()
            return {"code": "ok", "raw": r.text[:2000]}
        except Exception as exc:
            return {"code": "error", "message": str(exc)}

    def _get(self, path: str, params: dict = None, timeout: float = 10.0) -> Dict[str, Any]:
        try:
            r = _req().get(f"{self.base_url}{path}", params=params or {}, timeout=timeout)
            if r.headers.get("content-type", "").startswith("application/json"):
                return r.json()
            return {"code": "ok", "raw": r.text[:2000]}
        except Exception as exc:
            return {"code": "error", "message": str(exc)}

    # ── Projects ──────────────────────────────────────────────────────────────
    def list_projects(self) -> Dict[str, Any]:
        raw = self._get("/command/core/get-all-project-metadata")
        if raw.get("code") == "error":
            return {"ok": False, "message": raw.get("message", ""), "projects": []}
        projects_raw = raw.get("projects", {})
        projects = []
        for pid, meta in projects_raw.items():
            projects.append({
                "id": str(pid),
                "name": meta.get("name", ""),
                "created": meta.get("created", ""),
                "modified": meta.get("modified", ""),
                "row_count": meta.get("rowCount", 0),
                "description": meta.get("description", ""),
                "tags": meta.get("tags", []),
            })
        projects.sort(key=lambda p: p["modified"], reverse=True)
        return {"ok": True, "projects": projects}

    def get_project(self, project_id: str) -> Dict[str, Any]:
        meta_raw = self._get("/command/core/get-project-metadata", {"project": project_id})
        models_raw = self._get("/command/core/get-models", {"project": project_id})
        if meta_raw.get("code") == "error":
            return {"ok": False, "message": meta_raw.get("message", ""), "project": None}

        columns = [col.get("name", "") for col in models_raw.get("columnModel", {}).get("columns", [])]
        key_col = models_raw.get("columnModel", {}).get("keyColumnName", "")
        rows_raw = self._get("/command/core/get-rows", {"project": project_id, "start": 0, "limit": 1})
        total = rows_raw.get("total", 0)

        return {
            "ok": True,
            "project": {
                "id": project_id,
                "name": meta_raw.get("name", ""),
                "created": meta_raw.get("created", ""),
                "modified": meta_raw.get("modified", ""),
                "row_count": total,
                "description": meta_raw.get("description", ""),
                "tags": meta_raw.get("tags", []),
            },
            "columns": columns,
            "key_column": key_col,
            "total_rows": total,
        }

    def create_project_from_text(self, name: str, text_data: str, fmt: str) -> Dict[str, Any]:
        import io
        filename = name.replace(" ", "_") + (".csv" if "sv" in fmt else ".json")
        files = {"project-file": (filename, io.BytesIO(text_data.encode("utf-8")), "text/plain")}
        data = {"project-name": name, "format": fmt}
        raw = self._post("/command/core/create-project-from-upload", data=data, files=files, timeout=30.0)
        if raw.get("code") == "error":
            return {"ok": False, "message": raw.get("message", "Upload failed"), "project_id": ""}
        # OpenRefine redirects to project page — parse project ID from redirect
        # The raw response may contain a redirect URL with ?project=XXXXXX
        pid = str(raw.get("projectID", raw.get("project_id", "")))
        return {"ok": True, "message": "Project created", "project_id": pid, "project_name": name}

    def delete_project(self, project_id: str) -> Dict[str, Any]:
        raw = self._post("/command/core/delete-project", data={"project": project_id})
        ok = raw.get("code") == "ok"
        return {"ok": ok, "message": raw.get("message", ""), "project_id": project_id}

    # ── Rows ──────────────────────────────────────────────────────────────────
    def get_rows(self, project_id: str, start: int = 0, limit: int = 50) -> Dict[str, Any]:
        raw = self._get("/command/core/get-rows", {
            "project": project_id,
            "start": start,
            "limit": limit,
        })
        if raw.get("code") == "error":
            return {"ok": False, "message": raw.get("message", ""), "rows": [], "total": 0, "filtered": 0}

        rows = []
        for i, row in enumerate(raw.get("rows", [])):
            cells = []
            for cell in (row.get("cells") or []):
                if cell is None:
                    cells.append({"v": None})
                else:
                    cells.append({"v": cell.get("v"), "r": cell.get("r")})
            rows.append({"cells": cells, "starred": row.get("starred", False), "flagged": row.get("flagged", False), "i": start + i})

        return {
            "ok": True,
            "rows": rows,
            "start": start,
            "limit": limit,
            "total": raw.get("total", 0),
            "filtered": raw.get("filtered", raw.get("total", 0)),
        }

    # ── Operations ────────────────────────────────────────────────────────────
    def apply_operations(self, project_id: str, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        import json as _json
        raw = self._post("/command/core/apply-operations", data={
            "project": project_id,
            "operations": _json.dumps(operations),
        }, timeout=60.0)
        ok = raw.get("code") == "ok"
        return {
            "ok": ok,
            "message": raw.get("message", "Operations applied" if ok else "Failed"),
            "history_entry_id": raw.get("historyEntry", {}).get("id") if isinstance(raw.get("historyEntry"), dict) else None,
            "operations_applied": len(operations) if ok else 0,
        }

    def preview_expression(self, project_id: str, column_name: str, expression: str, language: str = "grel") -> Dict[str, Any]:
        raw = self._get("/command/core/preview-expression", {
            "project": project_id,
            "columnName": column_name,
            "expression": expression,
            "cellIndex": 0,
            "rowIndices": "[0,1,2,3,4]",
        })
        results = raw.get("results", raw.get("expressions", []))
        return {"ok": True, "results": results if isinstance(results, list) else [results]}

    # ── Export ────────────────────────────────────────────────────────────────
    def export_rows(self, project_id: str, fmt: str = "csv") -> Tuple[bytes, str]:
        """Returns (raw bytes, content-type)."""
        token = self._get_csrf()
        content_types = {
            "csv": "text/csv",
            "tsv": "text/tab-separated-values",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "html": "text/html",
            "json": "application/json",
        }
        ct = content_types.get(fmt, "application/octet-stream")
        try:
            r = _req().post(
                f"{self.base_url}/command/core/export-rows/{fmt}",
                params={"csrf_token": token},
                data={"project": project_id, "format": fmt},
                timeout=60.0,
            )
            return r.content, ct
        except Exception as exc:
            return f"Export failed: {exc}".encode(), "text/plain"

    # ── Clustering ────────────────────────────────────────────────────────────
    def compute_clusters(self, project_id: str, column_name: str, method: str = "binning", keyer: str = "fingerprint") -> Dict[str, Any]:
        import json as _json
        raw = self._post("/command/core/compute-clusters", data={
            "project": project_id,
            "columnName": column_name,
            "clusterer": _json.dumps({"type": method, "function": keyer}),
        })
        clusters = []
        for group in (raw if isinstance(raw, list) else []):
            clusters.append({
                "choices": group.get("choices", []),
                "value": group.get("value", ""),
                "count": group.get("count", 0),
            })
        return {"ok": True, "column_name": column_name, "method": method, "clusters": clusters}

    # ── Live config update ────────────────────────────────────────────────────
    def update_config(self, port: Optional[int] = None, memory_mb: Optional[int] = None, install_dir: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            if port is not None:
                self._override_port = port
            if memory_mb is not None:
                self._override_memory = memory_mb
            if install_dir is not None:
                self._override_install_dir = Path(install_dir)
        return {
            "ok": True,
            "config": {
                "port": self.port,
                "memory_mb": self.memory_mb,
                "install_dir": str(self.install_dir),
            }
        }
