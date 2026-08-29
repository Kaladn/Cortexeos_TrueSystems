from flask import Blueprint, jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from truecore.core.models import Role, User

rbac_bp = Blueprint("rbac", __name__)


@rbac_bp.get("/api/rbac/bootstrap-status")
def bootstrap_status():
    admin_role = Role.query.filter_by(name="admin").first()
    admin_count = 0
    if admin_role is not None:
        admin_count = User.query.filter_by(role_id=admin_role.id).count()
    return jsonify({
        "ok": True,
        "admin_role_exists": admin_role is not None,
        "admin_user_exists": admin_count > 0,
        "admin_user_count": admin_count,
        "bootstrap_command": "TRUECORE_ADMIN_USER=<user> TRUECORE_ADMIN_PASS=<pass> python truecore\\cli\\seed_admin.py",
        "reset_command": "TRUECORE_ADMIN_RESET=true TRUECORE_ADMIN_USER=<user> TRUECORE_ADMIN_PASS=<pass> python truecore\\cli\\seed_admin.py",
    })


@rbac_bp.get("/api/rbac/me")
@jwt_required()
def me():
    claims = get_jwt()
    return jsonify({
        "ok": True,
        "identity": str(get_jwt_identity()),
        "role": claims.get("role", "unknown"),
        "permissions": {
            "chat": True,
            "control": claims.get("role") == "admin",
            "rbac_admin": claims.get("role") == "admin",
        },
    })
