"""Action registry for request-time operational capabilities.

Actions are backend capabilities. They become executable only when they have a
real backend binding, validation boundary, policy gate, and receipt requirement
when writing.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def default_action_registry() -> list[dict[str, Any]]:
    return [
        {
            "action_id": "runtime.start_baseline",
            "capability_id": "runtime.baseline",
            "label": "Start Baseline",
            "description": "Run bounded USER1 baseline logging sections.",
            "backend_route": None,
            "http_method": "POST",
            "read_or_write": "write",
            "input_schema": {
                "user_id": {"type": "string", "allowed": ["USER1"]},
                "runtime_root": {"type": "string"},
                "window_seconds": {"type": "number", "min": 1, "max": 3600},
                "sections": {"type": "integer", "min": 1, "max": 480},
            },
            "output_schema": {"summary_path": "string", "section_receipts": "array"},
            "validation_route": None,
            "policy_gate": "admin_required",
            "dry_run_required": True,
            "receipt_target": "securecore_user1_baseline_section_receipt",
            "failure_state": "planned_missing_route",
            "status": "planned",
        },
        {
            "action_id": "mapping.window.update",
            "capability_id": "mapping.window",
            "label": "Update Mapping Window",
            "description": "Change a symbolic mapping window after validation, preview, dry-run, approval, and receipt.",
            "backend_route": None,
            "http_method": "POST",
            "read_or_write": "write",
            "input_schema": {
                "current": {"type": "string"},
                "target": {"type": "string", "allowed": ["6-1-6", "6x4-4-6x4"]},
                "preview_required": {"type": "boolean", "required": True},
            },
            "output_schema": {"old_settings": "object", "new_settings": "object", "impact": "object"},
            "validation_route": None,
            "policy_gate": "admin_required",
            "dry_run_required": True,
            "receipt_target": "mapping_window_update_receipt",
            "failure_state": "planned_missing_route",
            "status": "planned",
        },
        {
            "action_id": "worker.diagnostics.inspect",
            "capability_id": "worker.diagnostics",
            "label": "Inspect Worker Diagnostics",
            "description": "Read installed worker diagnostic feed status from the toolbox.",
            "backend_route": "/api/ops/toolbox",
            "http_method": "GET",
            "read_or_write": "read",
            "input_schema": {},
            "output_schema": {"workers": "array", "loggers": "array", "agents": "array"},
            "validation_route": "/api/ops/toolbox",
            "policy_gate": "admin_required",
            "dry_run_required": False,
            "receipt_target": None,
            "failure_state": "route_unavailable",
            "status": "live",
        },
    ]


def action_by_id(action_id: str) -> dict[str, Any] | None:
    for action in default_action_registry():
        if action["action_id"] == action_id:
            return deepcopy(action)
    return None
