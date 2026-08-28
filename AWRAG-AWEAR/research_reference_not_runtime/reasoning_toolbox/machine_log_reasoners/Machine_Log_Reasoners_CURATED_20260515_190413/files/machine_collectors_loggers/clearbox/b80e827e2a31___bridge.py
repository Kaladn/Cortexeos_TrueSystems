"""
System Pulse Plugin — Standalone Bridge
Port: 9093

Usage:
    python -m core.system_pulse._bridge [--port 9093] [--host 127.0.0.1]
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PLUGINS_DIR = ROOT / "plugins"
if str(PLUGINS_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGINS_DIR))

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
logger = logging.getLogger("system_pulse_bridge")
_DEV_MODE = os.environ.get("SYSTEM_PULSE_DEV", "").strip() == "1"

app = FastAPI(
    title="System Pulse Bridge",
    version="0.1.0",
    docs_url="/docs" if _DEV_MODE else None,
    openapi_url="/openapi.json" if _DEV_MODE else None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5050",
        "http://localhost:5050",
        "https://127.0.0.1:5050",
        "https://localhost:5050",
        "http://127.0.0.1:8080",
        "http://localhost:8080",
        "https://127.0.0.1:8080",
        "https://localhost:8080",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Clearbox-CSRF", "X-Trace-Id"],
    allow_credentials=False,
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["127.0.0.1", "localhost", "::1"],
)


@app.middleware("http")
async def _security_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path or ""
    allow_frame = path.endswith("/ui") or path == "/"
    frame_ancestors = "'self'" if allow_frame else "'none'"
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
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "SAMEORIGIN" if allow_frame else "DENY"
    return response

try:
    from .api.router import router as pulse_router
    app.include_router(pulse_router)
    logger.info("System Pulse router mounted at /api/system-pulse")
except Exception as exc:
    logger.error("Failed to mount System Pulse router: %s", exc)
    sys.exit(1)


@app.get("/health", include_in_schema=False)
async def health():
    return {"ok": True, "plugin": "system_pulse", "version": "0.1.0"}


@app.get("/", include_in_schema=False)
async def root():
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/api/system-pulse/ui")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=9093)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    logger.info("System Pulse bridge at http://%s:%d", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
