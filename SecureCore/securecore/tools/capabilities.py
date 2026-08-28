"""SecureCore capability registry."""

from __future__ import annotations

from typing import Any


AUTHORITY_CLASSES = {"read", "analyze", "write", "mutate"}


class CapabilityRegistryError(ValueError):
    """Raised when a capability definition is unsafe or malformed."""


def build_default_capability_registry() -> dict[str, dict[str, Any]]:
    registry = {
        "temporal.read": {
            "capability_id": "temporal.read",
            "description": "Read temporal rows for investigation context.",
            "authority_class": "read",
            "risk_tier": 1,
            "requires_approval": False,
            "dry_run_required": False,
            "dependencies": ["temporal_rows"],
            "runner_target": "central_reader.temporal",
            "central_writer_required": False,
        },
        "forge.relationships.trace": {
            "capability_id": "forge.relationships.trace",
            "description": "Trace Forge-derived relationships for a case.",
            "authority_class": "analyze",
            "risk_tier": 2,
            "requires_approval": False,
            "dry_run_required": False,
            "dependencies": ["forge"],
            "runner_target": "forge_relational_engine",
            "central_writer_required": False,
        },
        "central_writer.report_request": {
            "capability_id": "central_writer.report_request",
            "description": "Request a Central Writer operator report.",
            "authority_class": "write",
            "risk_tier": 2,
            "requires_approval": False,
            "dry_run_required": False,
            "dependencies": ["central_writer"],
            "runner_target": "central_writer",
            "central_writer_required": True,
        },
        "firewall.block_ip": {
            "capability_id": "firewall.block_ip",
            "description": "Request an approval-gated firewall block for an IP.",
            "authority_class": "mutate",
            "risk_tier": 5,
            "requires_approval": True,
            "dry_run_required": True,
            "dependencies": ["windows.firewall"],
            "runner_target": "adapter.firewall",
            "central_writer_required": True,
        },
    }
    for capability in registry.values():
        validate_capability(capability)
    return registry


def validate_capability(capability: dict[str, Any]) -> dict[str, Any]:
    for field in (
        "capability_id",
        "description",
        "authority_class",
        "risk_tier",
        "requires_approval",
        "dry_run_required",
        "dependencies",
        "runner_target",
        "central_writer_required",
    ):
        if field not in capability:
            raise CapabilityRegistryError(f"missing field: {field}")

    if not isinstance(capability["capability_id"], str) or not capability["capability_id"].strip():
        raise CapabilityRegistryError("capability_id must be a non-empty string")
    if capability["authority_class"] not in AUTHORITY_CLASSES:
        raise CapabilityRegistryError(f"invalid authority_class: {capability['authority_class']}")
    if not isinstance(capability["risk_tier"], int) or not 0 <= capability["risk_tier"] <= 5:
        raise CapabilityRegistryError("risk_tier must be an integer from 0 to 5")
    for field in ("requires_approval", "dry_run_required", "central_writer_required"):
        if not isinstance(capability[field], bool):
            raise CapabilityRegistryError(f"{field} must be boolean")
    if not isinstance(capability["dependencies"], list) or not all(
        isinstance(item, str) and item.strip() for item in capability["dependencies"]
    ):
        raise CapabilityRegistryError("dependencies must be a list of non-empty strings")
    if capability["authority_class"] == "mutate":
        if capability["requires_approval"] is not True:
            raise CapabilityRegistryError("mutation capability requires approval")
        if capability["dry_run_required"] is not True:
            raise CapabilityRegistryError("mutation capability requires dry-run")
        if capability["central_writer_required"] is not True:
            raise CapabilityRegistryError("mutation capability requires Central Writer boundary")
    return dict(capability)
