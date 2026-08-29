"""Sandboxed trap/block/release containment receipts.

This first build keeps containment temporary and receipt-driven. It never writes
executables, never injects into third-party traffic, and always emits a human
review requirement after the emergency sequence.
"""

from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
from pathlib import Path
from typing import Any

from truecore.time import utc_now


PROTECTED_IPS = {
    "127.0.0.1",
    "::1",
    "0.0.0.0",
}
DEFAULT_TTL_SECONDS = 300


class SandboxContainmentError(ValueError):
    """Raised when sandbox containment would violate safety rules."""


class DryRunFirewallAdapter:
    """Default adapter that records intended block/release without mutation."""

    def temporary_block(self, *, remote_ip: str, ttl_seconds: int, reason: str, evidence_refs: list[str]) -> dict[str, Any]:
        return {
            "status": "dry_run_block_recorded",
            "firewall_rule_id": f"dryrun-{_hash({'remote_ip': remote_ip, 'reason': reason})[:12]}",
            "remote_ip": remote_ip,
            "ttl_seconds": ttl_seconds,
            "evidence_refs": evidence_refs,
        }

    def release(self, *, firewall_rule_id: str, remote_ip: str) -> dict[str, Any]:
        return {"status": "dry_run_release_recorded", "firewall_rule_id": firewall_rule_id, "remote_ip": remote_ip}


def execute_sandboxed_containment(
    *,
    output_root: str | Path,
    remote_ip: str,
    observed_event_refs: list[str],
    actor_process: str,
    process_hash: str,
    remote_endpoint: str,
    fusion_block_ref: str,
    causality_chain_ref: str,
    reason_code: str,
    firewall_adapter: Any | None,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    inert_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the local trap/block/release receipt sequence."""

    payload = _validate_inert_payload(inert_payload or _default_inert_payload())
    normalized_ip = _normalize_ip(remote_ip)
    _reject_protected(normalized_ip)
    _require_refs(observed_event_refs)
    for name, value in {
        "actor_process": actor_process,
        "process_hash": process_hash,
        "remote_endpoint": remote_endpoint,
        "fusion_block_ref": fusion_block_ref,
        "causality_chain_ref": causality_chain_ref,
        "reason_code": reason_code,
    }.items():
        if not isinstance(value, str) or not value.strip():
            raise SandboxContainmentError(f"{name} is required")
    if not isinstance(ttl_seconds, int) or ttl_seconds <= 0 or ttl_seconds > 3600:
        raise SandboxContainmentError("ttl_seconds must be between 1 and 3600")

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    now = utc_now()
    evidence_refs = [*observed_event_refs, fusion_block_ref, causality_chain_ref]
    trap = {
        "schema_version": 1,
        "kind": "truecore_sandbox_trap_receipt",
        "created_at_utc": now,
        "remote_ip": normalized_ip,
        "remote_endpoint": remote_endpoint,
        "actor_process": actor_process,
        "process_hash": process_hash,
        "reason_code": reason_code,
        "inert_payload": payload,
        "evidence_refs": evidence_refs,
        "third_party_injection": False,
    }
    _write_json(root / "trap_receipt.json", trap)

    adapter = firewall_adapter or DryRunFirewallAdapter()
    block_result = adapter.temporary_block(
        remote_ip=normalized_ip,
        ttl_seconds=ttl_seconds,
        reason=reason_code,
        evidence_refs=evidence_refs,
    )
    block = {
        "schema_version": 1,
        "kind": "truecore_temporary_block_receipt",
        "created_at_utc": utc_now(),
        "remote_ip": normalized_ip,
        "ttl_seconds": ttl_seconds,
        "permanent_action_authorized": False,
        "firewall_result": block_result,
        "evidence_refs": evidence_refs,
    }
    _write_json(root / "temporary_block_receipt.json", block)

    release_result = adapter.release(
        firewall_rule_id=str(block_result.get("firewall_rule_id", "")),
        remote_ip=normalized_ip,
    )
    release = {
        "schema_version": 1,
        "kind": "truecore_release_receipt",
        "created_at_utc": utc_now(),
        "remote_ip": normalized_ip,
        "release_required": True,
        "release_result": release_result,
        "evidence_refs": evidence_refs,
    }
    _write_json(root / "release_receipt.json", release)

    report_request = {
        "schema_version": 1,
        "kind": "truecore_central_writer_forensics_request",
        "created_at_utc": utc_now(),
        "title": "TrueCore Temporary Containment Forensics",
        "facts": [
            f"Remote endpoint {remote_endpoint} was observed.",
            f"Actor process {actor_process} has hash {process_hash}.",
            f"Temporary containment for {normalized_ip} completed and released.",
        ],
        "evidence_refs": evidence_refs,
        "warnings": ["Human security review is required."],
        "action_authority": False,
        "inference_allowed": False,
    }
    _write_json(root / "central_writer_forensics_request.json", report_request)

    review = {
        "schema_version": 1,
        "kind": "truecore_human_security_review_required",
        "created_at_utc": utc_now(),
        "status": "human_review_required",
        "remote_ip": normalized_ip,
        "reason_code": reason_code,
        "receipt_refs": [
            str(root / "trap_receipt.json"),
            str(root / "temporary_block_receipt.json"),
            str(root / "release_receipt.json"),
            str(root / "central_writer_forensics_request.json"),
        ],
    }
    _write_json(root / "human_review_required.json", review)
    return review


def _default_inert_payload() -> dict[str, Any]:
    raw = b"TRUECORE-INERT-GARBLE-NOT-EXECUTABLE\x00\xff\x10garbled-garble"
    return {
        "bytes_b64": base64.b64encode(raw).decode("ascii"),
        "executable": False,
        "scope": "truecore_local_sandbox_only",
        "content_type": "application/octet-stream+inert-garble",
    }


def _validate_inert_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise SandboxContainmentError("inert payload must be an object")
    if payload.get("executable") is not False:
        raise SandboxContainmentError("inert payload must be explicitly non-executable")
    raw = str(payload.get("bytes_b64", ""))
    try:
        decoded = base64.b64decode(raw.encode("ascii"), validate=True)
    except Exception as exc:
        raise SandboxContainmentError("inert payload must be base64 bytes") from exc
    executable_markers = (b"MZ", b"#!", b"<script", b"powershell", b"cmd.exe", b"ELF")
    lowered = decoded.lower()
    if any(marker.lower() in lowered for marker in executable_markers):
        raise SandboxContainmentError("inert payload contains executable/script marker")
    cleaned = dict(payload)
    cleaned["scope"] = "truecore_local_sandbox_only"
    cleaned["executable"] = False
    cleaned["sha256"] = hashlib.sha256(decoded).hexdigest()
    return cleaned


def _reject_protected(remote_ip: str) -> None:
    address = ipaddress.ip_address(remote_ip)
    if remote_ip in PROTECTED_IPS or address.is_loopback or address.is_private or address.is_link_local:
        raise SandboxContainmentError(f"protected endpoint cannot be blocked: {remote_ip}")


def _normalize_ip(remote_ip: str) -> str:
    try:
        return str(ipaddress.ip_address(remote_ip))
    except ValueError as exc:
        raise SandboxContainmentError("remote_ip must be valid") from exc


def _require_refs(refs: list[str]) -> None:
    if not isinstance(refs, list) or not refs or not all(isinstance(ref, str) and ref.strip() for ref in refs):
        raise SandboxContainmentError("observed_event_refs are required")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).hexdigest()
