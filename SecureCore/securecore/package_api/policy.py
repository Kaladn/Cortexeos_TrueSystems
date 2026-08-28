"""Policy guard for the AnchorWorks-callable SecureCore package API."""

from __future__ import annotations

from securecore.package_api.contracts import ALLOWED_CALLERS, ALLOWED_ROUTES


ACTION_ROUTE_PREFIXES = ("firewall.", "registry.", "process.", "agent.", "service.", "task.")


def check_package_policy(*, caller: str, route: str) -> dict:
    if caller not in ALLOWED_CALLERS:
        return {
            "allowed": False,
            "approval_required": False,
            "reason": f"unknown caller: {caller}",
        }
    if route in ALLOWED_ROUTES:
        return {
            "allowed": True,
            "approval_required": False,
            "reason": "route allowed",
        }
    if route.startswith(ACTION_ROUTE_PREFIXES):
        return {
            "allowed": False,
            "approval_required": True,
            "reason": f"{route} is not callable through package API without policy approval",
        }
    return {
        "allowed": False,
        "approval_required": False,
        "reason": f"unknown route: {route}",
    }
