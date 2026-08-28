"""OpenAI API key session routes.

The key is accepted only for the active process session. Responses never echo
the key, and logout clears the in-memory vault entry.
"""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required


openai_session_bp = Blueprint("openai_session", __name__)


@openai_session_bp.post("/api/openai/session/login")
@jwt_required()
def openai_session_login():
    vault = getattr(current_app, "openai_key_vault", None)
    if vault is None:
        return jsonify({"ok": False, "error": "OpenAI session vault unavailable"}), 503

    data = request.get_json(silent=True) or {}
    api_key = str(data.get("api_key", ""))
    model = str(data.get("model", ""))
    try:
        status = vault.login(user_id=str(get_jwt_identity()), api_key=api_key, model=model)
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    finally:
        api_key = ""
        data.pop("api_key", None)
    return jsonify({"ok": True, "openai_session": status})


@openai_session_bp.get("/api/openai/session/status")
@jwt_required()
def openai_session_status():
    vault = getattr(current_app, "openai_key_vault", None)
    if vault is None:
        return jsonify({"ok": False, "error": "OpenAI session vault unavailable"}), 503
    return jsonify({"ok": True, "openai_session": vault.status(str(get_jwt_identity()))})


@openai_session_bp.post("/api/openai/session/logout")
@jwt_required()
def openai_session_logout():
    vault = getattr(current_app, "openai_key_vault", None)
    if vault is None:
        return jsonify({"ok": False, "error": "OpenAI session vault unavailable"}), 503
    return jsonify({"ok": True, "openai_session": vault.logout(str(get_jwt_identity()))})
