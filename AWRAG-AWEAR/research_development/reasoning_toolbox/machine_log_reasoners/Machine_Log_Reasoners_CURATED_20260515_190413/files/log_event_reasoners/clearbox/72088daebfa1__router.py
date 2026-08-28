"""av_security FastAPI router — mounts at /api/av_security on bridge port 5050."""

from __future__ import annotations
from typing import Any

from fastapi import APIRouter
from av_security.api.models import CorrelateRequest
from av_security.core.analyzer import correlate_sessions

router = APIRouter(prefix="/api/av_security", tags=["av_security"])

_last_findings: list[dict] = []


@router.get("/status")
async def av_security_status() -> dict[str, Any]:
    return {
        "ok": True,
        "plugin": "av_security",
        "version": "0.1.0",
        "last_finding_count": len(_last_findings),
    }


@router.get("/health")
async def av_security_health() -> dict[str, Any]:
    return {"ok": True, "plugin": "av_security"}


@router.post("/correlate")
async def correlate(req: CorrelateRequest) -> dict[str, Any]:
    """
    Run full AV correlation analysis on two session directories.
    Pass the session_dir from visual_io and audio_io sessions.
    """
    global _last_findings
    try:
        findings = correlate_sessions(req.visual_session_dir, req.audio_session_dir)
        _last_findings = findings
        return {
            "ok": True,
            "total_findings": len(findings),
            "findings": findings,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "findings": []}


@router.get("/findings")
async def get_findings(limit: int = 100) -> dict[str, Any]:
    """Return cached findings from last correlation run."""
    return {
        "ok": True,
        "total": len(_last_findings),
        "findings": _last_findings[-limit:],
    }


@router.get("/findings/summary")
async def findings_summary() -> dict[str, Any]:
    """Counts by anomaly type."""
    counts: dict[str, int] = {}
    for f in _last_findings:
        atype = f.get("anomaly", "UNKNOWN")
        counts[atype] = counts.get(atype, 0) + 1
    return {"ok": True, "total": len(_last_findings), "by_type": counts}


@router.get("/help")
async def help_schema() -> dict[str, Any]:
    """Machine-readable API schema — usable by both AI and human."""
    return {
        "ok": True,
        "plugin": "av_security",
        "version": "0.1.0",
        "mount_prefix": "/api/av_security",
        "endpoints": {
            "GET /status": {
                "description": "Plugin status and last finding count",
                "params": {},
                "returns": "ok, plugin, version, last_finding_count",
            },
            "GET /health": {
                "description": "Health check",
                "params": {},
                "returns": "ok, plugin",
            },
            "POST /correlate": {
                "description": "Run AV correlation on visual + audio session dirs",
                "params": {"visual_session_dir": "str (path)", "audio_session_dir": "str (path)"},
                "returns": "ok, total_findings, findings[]",
            },
            "GET /findings": {
                "description": "Cached findings from last correlation run",
                "params": {"limit": "int (default 100)"},
                "returns": "ok, total, findings[]",
            },
            "GET /findings/summary": {
                "description": "Anomaly type counts",
                "params": {},
                "returns": "ok, total, by_type{anomaly_name: count}",
            },
            "GET /help": {
                "description": "This endpoint — machine-readable API schema",
                "params": {},
                "returns": "this object",
            },
        },
        "hooks": {
            "plugin_pre": "Injects high-confidence findings (>=0.75) into LLM context (max 5)",
            "plugin_post": "Adds finding count to chat contributions",
        },
        "anomaly_types": [
            "PHANTOM_AUDIO",
            "SILENT_VISUAL",
            "DELAYED_CORRELATION",
            "DIRECTION_MISMATCH",
        ],
        "requires": ["visual_io", "audio_io"],
    }


# ── plugin_pre hook — inject AV security summary into chat context ────────────
async def plugin_pre(ctx: dict) -> dict:
    """If there are recent high-confidence findings, surface them to the LLM."""
    if not _last_findings:
        return ctx
    high = [f for f in _last_findings if f.get("confidence", 0) >= 0.75]
    if high:
        extra = ctx.setdefault("extra", {})
        extra["av_security_alerts"] = high[-5:]  # last 5 high-confidence findings
    return ctx


# ── plugin_post hook ────────────────────────────────────────────────────────
async def plugin_post(ctx: dict) -> dict:
    """Add finding count to contributions."""
    if _last_findings:
        contributions = ctx.setdefault("contributions", [])
        contributions.append({
            "source": "av_security",
            "type": "av_analysis",
            "finding_count": len(_last_findings),
        })
    return ctx
