"""SecureCore gate monitor snapshot.

SecureCore gates the Cortex stack and monitors the host environment. This module
declares that boundary without pretending to be a kernel firewall.
"""

from __future__ import annotations

from typing import Any


def build_gate_monitor_snapshot() -> dict[str, Any]:
    gate_rows = [
        _gate("canonical_chat_intake", "cross_system_input", policy=False, receipt=True),
        _gate("command_origin", "operator_command_source", policy=True, receipt=True, required_origin="local_hid_verified"),
        _gate("tool_execution", "tool_run", policy=True, receipt=True),
        _gate("worker_creation", "worker_draft_to_install", policy=True, receipt=True),
        _gate("agent_activation", "agent_manifest_to_runtime", policy=True, receipt=True),
        _gate("file_write", "stack_file_mutation", policy=True, receipt=True),
        _gate("network_action", "host_network_mutation", policy=True, receipt=True),
        _gate("memory_promotion", "candidate_to_approved_memory", policy=True, receipt=True),
        _gate("evidence_filing", "event_to_evidence_case", policy=True, receipt=True),
        _gate("cross_system_export", "stack_output_to_external_surface", policy=True, receipt=True),
    ]
    monitors = [
        "host_network_observation",
        "process_observation",
        "window_observation",
        "eventlog_observation",
        "forge_health",
        "fusion_health",
    ]
    return {
        "schema_version": 1,
        "kind": "securecore_gate_monitor",
        "authority_scope": "cortex_stack_gate_host_monitor",
        "kernel_firewall_claimed": False,
        "law": "SecureCore gates stack authority and monitors host edges; it does not claim kernel-level interception.",
        "gates": [row["gate_id"] for row in gate_rows],
        "gate_rows": gate_rows,
        "monitors": monitors,
    }


def _gate(gate_id: str, boundary: str, *, policy: bool, receipt: bool, required_origin: str = "") -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "boundary": boundary,
        "policy_required": policy,
        "receipt_required": receipt,
        "required_origin": required_origin,
        "execution_authority": False,
        "llm_authority": False,
    }
