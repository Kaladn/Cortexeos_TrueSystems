"""HID origin gate for local commands."""

from __future__ import annotations

from typing import Any


MIN_HID_COMMAND_CONFIDENCE = 0.55


def validate_hid_command_origin(
    command: str,
    attestation: dict[str, Any],
    *,
    min_confidence: float = MIN_HID_COMMAND_CONFIDENCE,
) -> dict[str, Any]:
    if not isinstance(attestation, dict) or not attestation.get("available"):
        raise ValueError("command requires active local HID attestation")
    if attestation.get("active_human") is not True:
        raise ValueError("command requires active local HID human presence")
    if bool(attestation.get("session_locked")):
        raise ValueError("command rejected because local session is locked")
    confidence = float(attestation.get("confidence", 0.0) or 0.0)
    if confidence < min_confidence:
        raise ValueError("command HID confidence is too low")
    peripheral_activity = (
        int(attestation.get("keyboard_events", 0) or 0) > 0
        or int(attestation.get("mouse_clicks", 0) or 0) > 0
        or bool(attestation.get("movement_detected"))
    )
    if not peripheral_activity:
        raise ValueError("command requires actual keyboard or mouse peripheral activity")
    return {
        "accepted": True,
        "origin": "local_hid_verified",
        "command": str(command),
        "confidence": confidence,
        "records_considered": int(attestation.get("records_considered", 0) or 0),
        "remote_or_automated_origin_allowed": False,
    }
