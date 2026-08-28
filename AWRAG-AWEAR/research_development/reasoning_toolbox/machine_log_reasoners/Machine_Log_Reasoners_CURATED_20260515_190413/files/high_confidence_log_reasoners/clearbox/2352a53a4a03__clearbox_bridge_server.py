"""HTTP and WebSocket server — orchestrator layer.

Route handlers live in bridges/routers/. Shared types:
  bridges/state.py      — BridgeState, JobManager, JobRecord
  bridges/models.py     — Pydantic request/response models
  bridges/helpers.py    — Security, path, and ledger helpers
  bridges/services/     — Inference, reasoning, chain, lexicon stats services
  bridges/ws_manager.py — WebSocketManager
"""
from __future__ import annotations

import argparse
import asyncio
import json
import json as _json
import logging
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Set

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

if __package__ is None or __package__ == "":
    BASE_DIR = Path(__file__).resolve().parent.parent
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

from security.data_paths import CLEARBOX_CONFIG_PATH as _SEC_CONFIG, STATE_DIR  # noqa: E402

from bridges.state import BridgeState, LOGGER, VERSION  # noqa: E402
from bridges.ws_manager import WebSocketManager  # noqa: E402
from core.chat_packs.api.router import router as _r_chat_packs  # noqa: E402
from core.help_system.api.router import router as _r_help  # noqa: E402
from core.lakespeak.api.router import router as _r_lakespeak  # noqa: E402
from core.observe.router import router as _r_observe  # noqa: E402
from core.system_pulse.api.router import router as _r_system_pulse  # noqa: E402
from bridges.routers import (  # noqa: E402
    chat as _r_chat,
    documap as _r_documap,
    lexicon as _r_lexicon,
    config as _r_config,
    system as _r_system,
    analysis as _r_analysis,
    control as _r_control,
    memory as _r_memory,
)


def create_app(state: BridgeState) -> FastAPI:
    app = FastAPI(title="Clearbox AI Studio Bridge", version=VERSION)

    # ── Shared objects (passed to routers as closure dependencies) ──────────
    ws_manager = WebSocketManager()
    _background_tasks: Set[asyncio.Task] = set()

    def _task_done(task: asyncio.Task) -> None:
        """Discard from tracking set + log unhandled exceptions."""
        _background_tasks.discard(task)
        if not task.cancelled() and task.exception():
            LOGGER.error(
                "Background task %s failed: %s",
                task.get_name(), task.exception(),
                exc_info=task.exception(),
            )

    async def _ensure_lexicon_loaded(reason: str) -> None:
        await state.ensure_bridge_loaded(reason)

    # ── Shutdown ─────────────────────────────────────────────────────────────
    @app.on_event("shutdown")
    async def _on_shutdown():
        await state.close()

    # ── CORS ─────────────────────────────────────────────────────────────────
    _cors_origins = [
        "http://localhost:8080", "http://127.0.0.1:8080",
        "https://localhost:8080", "https://127.0.0.1:8080",
    ]
    try:
        from security.tls import get_cert_san_ips, get_cert_san_hostnames
        for ip in get_cert_san_ips():
            if ip != "127.0.0.1":
                _cors_origins.append(f"https://{ip}:8080")
        for hostname in get_cert_san_hostnames():
            _cors_origins.append(f"https://{hostname}:8080")
    except Exception:
        pass
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "X-Clearbox-CSRF", "X-Trace-Id"],
    )

    # ── Security headers ──────────────────────────────────────────────────────
    @app.middleware("http")
    async def _security_headers(request: Request, call_next):
        response = await call_next(request)
        path = request.url.path or ""
        allow_same_origin_frame = (
            path.startswith("/api/")
            and (
                path.endswith("/ui")
                or path.endswith("/preview")
                or path.endswith("/dashboard")
            )
        )
        frame_ancestors = "'self'" if allow_same_origin_frame else "'none'"
        xfo = "SAMEORIGIN" if allow_same_origin_frame else "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self' ws: wss:; "
            "object-src 'none'; "
            f"frame-ancestors {frame_ancestors}"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = xfo
        return response

    # ── Rate limiter ──────────────────────────────────────────────────────────
    import time as _rl_time
    from collections import defaultdict as _rl_defaultdict

    _RATE_LIMITS = {
        "general": (120, 60),
        "chat":    (30, 60),
        "ingest":  (10, 60),
    }
    _rl_buckets: dict = _rl_defaultdict(list)

    def _rl_check(bucket: str, client_ip: str) -> bool:
        max_req, window = _RATE_LIMITS.get(bucket, (120, 60))
        key = f"{bucket}:{client_ip}"
        now = _rl_time.time()
        _rl_buckets[key] = [t for t in _rl_buckets[key] if t > now - window]
        if len(_rl_buckets[key]) >= max_req:
            return False
        _rl_buckets[key].append(now)
        return True

    @app.middleware("http")
    async def _rate_limit_middleware(request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        if path.startswith("/api/chat/send"):
            bucket = "chat"
        elif path.startswith("/api/") and path.endswith("/ingest"):
            bucket = "ingest"
        else:
            bucket = "general"
        if not _rl_check(bucket, client_ip):
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "code": "RATE_LIMITED"},
            )
        return await call_next(request)

    # ── Request metrics ───────────────────────────────────────────────────────
    import time as _time

    _METRICS: dict = {
        "started_at": _time.time(),
        "by_path": defaultdict(lambda: {"count": 0, "errors": 0, "latency_ms_sum": 0.0}),
    }

    @app.middleware("http")
    async def _metrics_middleware(request: Request, call_next):
        t0 = _time.perf_counter()
        path = request.url.path
        status = 200
        try:
            resp = await call_next(request)
            status = getattr(resp, "status_code", 200)
            return resp
        except Exception:
            status = 500
            raise
        finally:
            dt_ms = (_time.perf_counter() - t0) * 1000.0
            row = _METRICS["by_path"][path]
            row["count"] += 1
            if status >= 400:
                row["errors"] += 1
            row["latency_ms_sum"] += dt_ms

    # ── Validation error handler ──────────────────────────────────────────────
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        LOGGER.warning(
            "422 Validation Error on %s %s: %s",
            request.method, request.url.path, exc.errors(),
        )
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    # ── Mount core routers ────────────────────────────────────────────────────
    app.include_router(_r_chat.make_router(state, ws_manager))
    app.include_router(_r_documap.make_router(
        state, ws_manager, _ensure_lexicon_loaded,
        _background_tasks, _task_done,
    ))
    app.include_router(_r_lexicon.make_router(state, ws_manager, _ensure_lexicon_loaded))
    app.include_router(_r_chat_packs)
    app.include_router(_r_config.make_router(state, ws_manager))
    app.include_router(_r_help)
    app.include_router(_r_lakespeak)
    app.include_router(_r_observe)
    app.include_router(_r_system_pulse)
    app.include_router(_r_system.make_router(
        state, ws_manager, _METRICS,
        _background_tasks, _task_done, BASE_DIR,
    ))
    app.include_router(_r_analysis.make_router(state))
    app.include_router(_r_memory.make_router(state))
    app.include_router(_r_control.make_router(state=state))

    # ── Static files ──────────────────────────────────────────────────────────
    ui_dir = BASE_DIR / "ui"
    if ui_dir.exists():
        app.mount("/ui", StaticFiles(directory=str(ui_dir), html=True), name="ui")
        art_dir = BASE_DIR / "ART"
        if art_dir.exists():
            app.mount("/ART", StaticFiles(directory=str(art_dir), html=False), name="art")

        _ui_html = ui_dir / "clearbox_ai_production.html"

        @app.get("/")
        async def serve_ui_root():
            if _ui_html.exists():
                return FileResponse(_ui_html)
            raise HTTPException(status_code=404, detail="UI entry point not found")

        @app.get("/favicon.ico")
        async def serve_favicon():
            for candidate in (ui_dir / "favicon.ico", ui_dir / "assets" / "logo.svg"):
                if candidate.exists():
                    return FileResponse(candidate)
            raise HTTPException(status_code=404, detail="No favicon available")

    return app


# ── Startup helpers ───────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clearbox Lexicon Bridge server")
    parser.add_argument("--config", type=Path, default=None,
                        help="Path to clearbox.config.json (defaults to secure location)")
    parser.add_argument("--host", type=str, help="Override host")
    parser.add_argument("--port", type=int, help="Override port")
    parser.add_argument("--log-level", type=str, default="info")
    return parser.parse_args()


def _resolve_runtime_path(raw_path: str | Path) -> Path:
    try:
        from security.data_paths import SOURCE_ROOT as _SOURCE_ROOT
    except Exception:
        _SOURCE_ROOT = BASE_DIR
    p = Path(raw_path).expanduser()
    if p.is_absolute():
        return p
    return (_SOURCE_ROOT / p).resolve()


def _critical_config_fields(cfg: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "lexicon_root": cfg.get("lexicon_root"),
        "reports_root": cfg.get("reports_root"),
    }


def _load_json_object(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _deep_merge_dicts(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dicts(current, value)
        else:
            merged[key] = value
    return merged


def _normalize_runtime_roots(cfg: Dict[str, Any]) -> Dict[str, Any]:
    from security.data_paths import CHAT_MAPS_DIR, LEGACY_WINDOWS_DATA_ROOT

    normalized = dict(cfg)
    if not normalized.get("lexicon_root"):
        normalized["lexicon_root"] = "./Lexical Data/Canonical"

    raw_reports = normalized.get("reports_root")
    normalized_reports = str(CHAT_MAPS_DIR).replace("\\", "/")
    try:
        legacy_reports_abs = (LEGACY_WINDOWS_DATA_ROOT / "data" / "maps").resolve()
    except OSError:
        legacy_reports_abs = None  # Drive locked (e.g. BitLocker) — skip legacy migration

    if not raw_reports:
        normalized["reports_root"] = normalized_reports
        return normalized

    try:
        reports_abs = _resolve_runtime_path(str(raw_reports)).resolve()
    except OSError:
        reports_abs = None

    if legacy_reports_abs and reports_abs == legacy_reports_abs and CHAT_MAPS_DIR.resolve() != legacy_reports_abs:
        normalized["reports_root"] = normalized_reports
    else:
        normalized["reports_root"] = str(raw_reports).replace("\\", "/")

    return normalized


def _write_runtime_config(path: Path, cfg: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(cfg, handle, indent=2)
        handle.write("\n")


def _startup_preflight(config_path: Path, *, explicit_config: bool) -> Dict[str, Any]:
    from security.data_paths import SOURCE_ROOT, CLEARBOX_CONFIG_PATH
    workspace_cfg_path = SOURCE_ROOT / "clearbox.config.json"
    workspace_cfg = _load_json_object(workspace_cfg_path)
    secure_cfg = _load_json_object(config_path)

    # Fresh installs often have an empty secure config; hydrate it from the
    # workspace config and normalize any legacy path roots into the chosen data root.
    cfg = _normalize_runtime_roots(_deep_merge_dicts(workspace_cfg, secure_cfg))
    critical_secure = _critical_config_fields(cfg)

    if (not explicit_config) and cfg != secure_cfg:
        _write_runtime_config(config_path, cfg)

    lexicon_abs = _resolve_runtime_path(str(critical_secure.get("lexicon_root") or ""))
    reports_abs = _resolve_runtime_path(str(critical_secure.get("reports_root") or ""))

    if (not explicit_config) and workspace_cfg_path.exists():
        try:
            critical_workspace = _critical_config_fields(_normalize_runtime_roots(workspace_cfg))
            mismatches = []
            for key, secure_val in critical_secure.items():
                ws_val = critical_workspace.get(key)
                if ws_val != secure_val:
                    mismatches.append((key, secure_val, ws_val))
            if mismatches:
                details = "; ".join(
                    [f"{k}: secure={sv!r} workspace={wv!r}" for k, sv, wv in mismatches]
                )
                raise RuntimeError(
                    "Split-brain config detected between secure and workspace "
                    f"clearbox.config.json. Mismatches: {details}"
                )
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"Workspace config unreadable at {workspace_cfg_path}: {exc}"
            ) from exc

    if not lexicon_abs.exists():
        raise RuntimeError(f"Configured lexicon_root does not exist: {lexicon_abs}")

    LOGGER.info(
        "Preflight roots: config=%s secure_default=%s source=%s lexicon=%s reports=%s state=%s",
        config_path, CLEARBOX_CONFIG_PATH, SOURCE_ROOT, lexicon_abs, reports_abs, STATE_DIR,
    )
    return cfg


def main():
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    config_path = args.config if args.config else _SEC_CONFIG
    config = _startup_preflight(config_path, explicit_config=bool(args.config))
    state = BridgeState(config_path)

    host = args.host or config.get("server", {}).get("host", "127.0.0.1")
    port = args.port or config.get("server", {}).get("port", 5050)

    app = create_app(state)

    ssl_kw = {}
    if config.get("server", {}).get("tls", False):
        try:
            from security.tls import ensure_tls
            tls_result = ensure_tls()
            if tls_result:
                ssl_kw["ssl_certfile"] = tls_result[0]
                ssl_kw["ssl_keyfile"] = tls_result[1]
                LOGGER.info("TLS enabled: %s", tls_result[0])
        except Exception as e:
            LOGGER.warning("TLS setup failed, serving plain HTTP: %s", e)

    uvicorn.run(app, host=host, port=port, log_level=args.log_level, **ssl_kw)


if __name__ == "__main__":
    main()
