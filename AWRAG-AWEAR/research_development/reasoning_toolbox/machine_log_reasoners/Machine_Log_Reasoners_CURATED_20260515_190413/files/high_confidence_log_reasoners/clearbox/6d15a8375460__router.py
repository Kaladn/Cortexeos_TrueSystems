"""plugins/winutil/api/router.py — WinUtil FastAPI endpoints.

Mounted at /api/winutil by the plugin system.

Original WinUtil — Copyright 2022 CT Tech Group LLC (MIT License)
Plugin wrapper — Clearbox AI Studio / ForestAI team
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from winutil import config_reader as cfg
from winutil import ps_runner as ps

LOGGER = logging.getLogger("winutil")

router = APIRouter(prefix="/api/winutil", tags=["winutil"])


# ── Request models ───────────────────────────────────────────────────────────

class InstallRequest(BaseModel):
    app_id: str
    method: str = "auto"  # "winget" | "choco" | "auto"

class UninstallRequest(BaseModel):
    app_id: str

class TweakApplyRequest(BaseModel):
    tweak_ids: list[str]
    undo: bool = False

class FeatureInstallRequest(BaseModel):
    feature_ids: list[str]

class DnsSetRequest(BaseModel):
    provider: str  # provider name from dns.json, or "DHCP"

class PsRequest(BaseModel):
    script: str


# ── Health ───────────────────────────────────────────────────────────────────

@router.get("/health")
async def winutil_health():
    """Plugin health check — returns admin status and config availability."""
    status = cfg.config_status()
    status["is_admin"] = ps.is_admin()
    status["plugin"] = "winutil"
    status["version"] = "1.0.0"
    status["credit"] = "WinUtil by Chris Titus Tech (MIT) — https://github.com/ChrisTitusTech/winutil"
    return status


# ── Apps ─────────────────────────────────────────────────────────────────────

@router.get("/apps")
async def list_apps(
    category: str | None = None,
    search: str | None = None,
    foss_only: bool = False,
):
    """List available applications. Filterable by category, search term, FOSS."""
    apps = cfg.list_apps(category=category, search=search, foss_only=foss_only)
    return {"apps": apps, "count": len(apps)}


@router.get("/apps/categories")
async def list_app_categories():
    """Return all available application categories."""
    return {"categories": cfg.list_app_categories()}


@router.get("/apps/installed")
async def list_installed():
    """Return list of currently installed applications via winget."""
    result = ps.winget_list_installed()
    return {
        "ok": result["ok"],
        "packages": result.get("data", []),
        "raw": result.get("stdout", ""),
        "error": result.get("stderr", "") if not result["ok"] else "",
    }


@router.get("/apps/{app_id}")
async def get_app(app_id: str):
    """Get details for a specific application."""
    app = cfg.get_app(app_id)
    if not app:
        raise HTTPException(404, f"App '{app_id}' not found")
    return {"id": app_id, **app}


@router.post("/apps/install")
async def install_app(req: InstallRequest):
    """Install an application via winget or Chocolatey.

    method: "auto" tries winget first, falls back to choco if winget ID is missing.
    """
    app = cfg.get_app(req.app_id)
    if not app:
        raise HTTPException(404, f"App '{req.app_id}' not found in WinUtil catalog")

    winget_id: str = app.get("winget", "")
    choco_id: str = app.get("choco", "")
    app_name: str = app.get("content", req.app_id)

    method = req.method.lower()
    if method == "auto":
        method = "winget" if winget_id and winget_id != "na" else "choco"

    if method == "winget":
        if not winget_id or winget_id == "na":
            raise HTTPException(400, f"'{app_name}' has no winget ID — try method='choco'")
        result = ps.winget_install(winget_id)
    elif method == "choco":
        if not choco_id or choco_id == "na":
            raise HTTPException(400, f"'{app_name}' has no Chocolatey ID — try method='winget'")
        result = ps.choco_install(choco_id)
    else:
        raise HTTPException(400, f"Unknown method '{req.method}'. Use 'winget', 'choco', or 'auto'")

    return {
        "ok": result["ok"],
        "app": app_name,
        "app_id": req.app_id,
        "method": method,
        "output": result["stdout"],
        "error": result["stderr"],
        "admin_required": result.get("admin_required", False),
    }


@router.post("/apps/uninstall")
async def uninstall_app(req: UninstallRequest):
    """Uninstall an application via winget."""
    app = cfg.get_app(req.app_id)
    if not app:
        raise HTTPException(404, f"App '{req.app_id}' not found in WinUtil catalog")

    winget_id: str = app.get("winget", "")
    app_name: str = app.get("content", req.app_id)

    if not winget_id or winget_id == "na":
        raise HTTPException(400, f"'{app_name}' has no winget ID — cannot auto-uninstall")

    result = ps.winget_uninstall(winget_id)
    return {
        "ok": result["ok"],
        "app": app_name,
        "output": result["stdout"],
        "error": result["stderr"],
    }


# ── Tweaks ───────────────────────────────────────────────────────────────────

@router.get("/tweaks")
async def list_tweaks(category: str | None = None, search: str | None = None):
    """List available system tweaks. Filterable by category or search term."""
    tweaks = cfg.list_tweaks(category=category, search=search)
    return {"tweaks": tweaks, "count": len(tweaks)}


@router.get("/tweaks/categories")
async def list_tweak_categories():
    """Return all tweak categories."""
    return {"categories": cfg.list_tweak_categories()}


@router.get("/tweaks/{tweak_id}")
async def get_tweak(tweak_id: str):
    """Get full detail for a specific tweak."""
    tweak = cfg.get_tweak(tweak_id)
    if not tweak:
        raise HTTPException(404, f"Tweak '{tweak_id}' not found")
    return {"id": tweak_id, **tweak}


@router.post("/tweaks/apply")
async def apply_tweaks(req: TweakApplyRequest):
    """Apply (or undo) one or more tweaks.

    Returns per-tweak results. Registry changes applied via Python winreg.
    InvokeScript/UndoScript run headlessly via PowerShell.
    Admin may be required for HKLM registry paths and some scripts.
    """
    results = []
    for tweak_id in req.tweak_ids:
        tweak = cfg.get_tweak(tweak_id)
        if not tweak:
            results.append({"id": tweak_id, "ok": False, "error": "Tweak not found"})
            continue

        name = tweak.get("Content", tweak_id)
        tweak_result: dict[str, Any] = {"id": tweak_id, "name": name, "ok": True, "steps": []}

        # Step 1: Registry
        registry_entries = cfg.get_tweak_registry_entries(tweak_id)
        if registry_entries:
            reg_results = ps.apply_registry_entries(registry_entries, undo=req.undo)
            all_ok = all(r.get("ok") for r in reg_results)
            tweak_result["steps"].append({
                "step": "registry",
                "ok": all_ok,
                "entries": reg_results,
            })
            if not all_ok:
                tweak_result["ok"] = False

        # Step 2: Script
        scripts = cfg.get_tweak_undo_scripts(tweak_id) if req.undo else cfg.get_tweak_invoke_scripts(tweak_id)
        if scripts:
            script_result = ps.apply_invoke_scripts(scripts)
            tweak_result["steps"].append({
                "step": "script",
                "ok": script_result["ok"],
                "output": script_result["stdout"],
                "error": script_result["stderr"],
                "admin_required": script_result.get("admin_required", False),
            })
            if not script_result["ok"]:
                tweak_result["ok"] = False

        results.append(tweak_result)

    all_ok = all(r["ok"] for r in results)
    return {"ok": all_ok, "action": "undo" if req.undo else "apply", "results": results}


# ── Features ─────────────────────────────────────────────────────────────────

@router.get("/features")
async def list_features(search: str | None = None):
    """List available Windows optional features."""
    features = cfg.list_features(search=search)
    return {"features": features, "count": len(features)}


@router.get("/features/{feature_id}")
async def get_feature(feature_id: str):
    """Get details for a specific feature."""
    feat = cfg.get_feature(feature_id)
    if not feat:
        raise HTTPException(404, f"Feature '{feature_id}' not found")
    return {"id": feature_id, **feat}


@router.post("/features/install")
async def install_feature(req: FeatureInstallRequest):
    """Enable one or more Windows optional features. Requires admin."""
    results = []
    for feature_id in req.feature_ids:
        feat = cfg.get_feature(feature_id)
        if not feat:
            results.append({"id": feature_id, "ok": False, "error": "Feature not found"})
            continue

        feature_names = feat.get("feature", [])
        invoke_scripts = cfg.get_feature_invoke_scripts(feature_id)
        result = ps.enable_feature(feature_names, invoke_scripts=invoke_scripts or None)
        results.append({
            "id": feature_id,
            "name": feat.get("Content", feature_id),
            "ok": result["ok"],
            "output": result["stdout"],
            "error": result["stderr"],
            "admin_required": result.get("admin_required", False),
        })

    return {"ok": all(r["ok"] for r in results), "results": results}


# ── DNS ──────────────────────────────────────────────────────────────────────

@router.get("/dns")
async def list_dns():
    """List available DNS providers."""
    return {"providers": cfg.list_dns_providers()}


@router.post("/dns/set")
async def set_dns(req: DnsSetRequest):
    """Set DNS on all active adapters. Requires admin."""
    if req.provider.upper() == "DHCP":
        result = ps.reset_dns_dhcp()
        return {
            "ok": result["ok"],
            "provider": "DHCP",
            "output": result["stdout"],
            "error": result["stderr"],
            "admin_required": result.get("admin_required", False),
        }

    provider = cfg.get_dns_provider(req.provider)
    if not provider:
        raise HTTPException(404, f"DNS provider '{req.provider}' not found. Use GET /api/winutil/dns to list options.")

    result = ps.set_dns(
        provider["primary"],
        provider["secondary"],
        primary6=provider.get("primary6", ""),
        secondary6=provider.get("secondary6", ""),
    )
    return {
        "ok": result["ok"],
        "provider": provider["name"],
        "primary": provider["primary"],
        "secondary": provider["secondary"],
        "output": result["stdout"],
        "error": result["stderr"],
        "admin_required": result.get("admin_required", False),
    }


# ── Fixes / Repair ───────────────────────────────────────────────────────────

@router.post("/fixes/update")
async def fix_update():
    """Reset Windows Update components (stop services, clear cache, restart, DISM, SFC)."""
    result = ps.fix_windows_update()
    return _fix_response("windows_update", result)


@router.post("/fixes/network")
async def fix_network():
    """Reset network stack (Winsock, IP, DNS cache, ARP). Reboot recommended after."""
    result = ps.fix_network()
    return _fix_response("network", result)


@router.post("/fixes/winget")
async def fix_winget():
    """Re-register Microsoft App Installer (winget) package."""
    result = ps.fix_winget()
    return _fix_response("winget", result)


@router.post("/fixes/system")
async def fix_system():
    """Run full system repair: DISM RestoreHealth + SFC scan."""
    result = ps.fix_system_repair()
    return _fix_response("system_repair", result)


@router.post("/performance/ultimate")
async def enable_ultimate_performance():
    """Activate Windows Ultimate Performance power plan. Requires admin."""
    result = ps.enable_ultimate_performance()
    return _fix_response("ultimate_performance", result)


def _fix_response(op: str, result: dict) -> dict:
    return {
        "ok": result["ok"],
        "operation": op,
        "output": result["stdout"],
        "error": result["stderr"],
        "admin_required": result.get("admin_required", False),
        "note": "Reboot may be required for changes to take effect." if result["ok"] else "",
    }


# ── UI redirect ──────────────────────────────────────────────────────────────

@router.get("/ui")
async def winutil_ui():
    """Redirect to the WinUtil plugin UI (hosted as static page)."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/ui/winutil.html", status_code=302)
