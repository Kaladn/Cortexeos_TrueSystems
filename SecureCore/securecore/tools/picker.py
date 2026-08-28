"""Situational tool picker.

External assistants or local system classifiers may suggest needed capabilities,
but this picker independently validates requirements before anything can become
runnable.
"""

from __future__ import annotations

from typing import Any


class PickerDecisionError(ValueError):
    """Raised when a requested tool chain is not allowed or not ready."""


def pick_tool_chain(
    *,
    interpreter_packet: dict[str, Any],
    registry: dict[str, dict[str, Any]],
    available_dependencies: set[str],
    approvals: set[str],
) -> dict[str, Any]:
    requested = interpreter_packet.get("needed_capabilities", [])
    if not isinstance(requested, list) or not requested:
        raise PickerDecisionError("needed_capabilities must be a non-empty list")

    chain = []
    central_writer_required = False
    for capability_id in requested:
        if capability_id not in registry:
            raise PickerDecisionError(f"unknown capability: {capability_id}")
        capability = registry[capability_id]
        missing = sorted(set(capability["dependencies"]) - available_dependencies)
        if missing:
            raise PickerDecisionError(f"missing dependency for {capability_id}: {missing[0]}")
        if capability["requires_approval"] and capability_id not in approvals:
            raise PickerDecisionError(f"approval required for {capability_id}")
        central_writer_required = central_writer_required or bool(capability.get("central_writer_required"))
        chain.append(
            {
                "capability_id": capability_id,
                "runner_target": capability["runner_target"],
                "authority_class": capability["authority_class"],
                "risk_tier": capability["risk_tier"],
                "dry_run_required": capability["dry_run_required"],
            }
        )

    return {
        "schema_version": 1,
        "kind": "situational_tool_chain",
        "chain": chain,
        "runner_executable": False,
        "central_writer_required": central_writer_required,
        "interpreter_advisory_only": True,
    }
