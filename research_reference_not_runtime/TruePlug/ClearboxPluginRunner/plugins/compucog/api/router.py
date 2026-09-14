"""CompuCog plugin router for Clearbox Plugin Runner."""

from __future__ import annotations

import os
from typing import Any, Dict

import httpx
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="/api/compucog", tags=["compucog"])


def _backend_base() -> str:
    return os.getenv("COMPUCOG_API_BASE", "http://127.0.0.1:5000").rstrip("/")


def _plugin_version() -> str:
    try:
        from compucog import VERSION

        return VERSION
    except Exception:
        return "0.0.0"


def _safe_get_json(path: str, timeout: float = 2.0) -> Dict[str, Any] | None:
    url = f"{_backend_base()}{path}"
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url)
        if resp.status_code >= 400:
            return None
        data = resp.json()
        return data if isinstance(data, dict) else {"raw": data}
    except Exception:
        return None


@router.get("/status")
async def compucog_status() -> Dict[str, Any]:
    status = _safe_get_json("/api/status")
    return {
        "ok": True,
        "plugin": "compucog",
        "version": _plugin_version(),
        "backend_base_url": _backend_base(),
        "backend_reachable": status is not None,
        "backend_status": status,
    }


@router.get("/health")
async def compucog_health() -> Dict[str, Any]:
    status = _safe_get_json("/api/status")
    return {
        "ok": status is not None,
        "plugin": "compucog",
        "backend_reachable": status is not None,
    }


@router.get("/system/overview")
async def compucog_system_overview() -> Dict[str, Any]:
    overview = _safe_get_json("/api/system/overview")
    return {
        "ok": overview is not None,
        "backend_base_url": _backend_base(),
        "overview": overview,
    }


@router.get("/ui")
async def compucog_ui() -> RedirectResponse:
    base = _backend_base()
    return RedirectResponse(url=f"{base}/ui/compucog", status_code=307)


@router.get("/ui/info")
async def compucog_ui_info() -> Dict[str, Any]:
    base = _backend_base()
    return {"ok": True, "ui_url": f"{base}/ui/compucog", "api_base_url": base}
