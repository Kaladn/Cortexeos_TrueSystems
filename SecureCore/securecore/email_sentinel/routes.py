"""Email Sentinel API routes."""

from __future__ import annotations

from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from securecore.email_sentinel.service import EmailSentinelService

email_sentinel_bp = Blueprint("email_sentinel", __name__)
_service: EmailSentinelService | None = None


def init_email_sentinel_routes(service: EmailSentinelService | None) -> None:
    global _service
    _service = service


def _require_service() -> tuple[EmailSentinelService | None, tuple | None]:
    if _service is None:
        return None, (jsonify({"ok": False, "error": "email sentinel unavailable"}), 503)
    return _service, None


@email_sentinel_bp.get("/api/email-sentinel/status")
@jwt_required()
def status():
    service, error = _require_service()
    if error is not None:
        return error
    return jsonify({"ok": True, **service.status()})


@email_sentinel_bp.get("/api/email-sentinel/patterns")
@jwt_required()
def patterns():
    service, error = _require_service()
    if error is not None:
        return error
    return jsonify({"ok": True, "patterns": service.pattern_summary()})


@email_sentinel_bp.post("/api/email-sentinel/poll-once")
@jwt_required()
def poll_once():
    service, error = _require_service()
    if error is not None:
        return error
    return jsonify({"ok": True, "result": service.poll_once()})

