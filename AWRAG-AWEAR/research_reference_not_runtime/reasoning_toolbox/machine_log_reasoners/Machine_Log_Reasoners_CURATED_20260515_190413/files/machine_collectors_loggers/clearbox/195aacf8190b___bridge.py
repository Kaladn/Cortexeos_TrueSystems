"""
System Pulse Plugin — Standalone Bridge
Port: 9093

Usage:
    python plugins/system_pulse/_bridge.py [--port 9093] [--host 127.0.0.1]
"""
from __future__ import annotations

import argparse
import logging
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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
logger = logging.getLogger("system_pulse_bridge")

app = FastAPI(title="System Pulse Bridge", version="0.1.0", docs_url="/docs")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

try:
    from system_pulse.api.router import router as pulse_router
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
