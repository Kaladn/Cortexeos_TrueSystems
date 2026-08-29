"""Read-only anomaly wake-up rules."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def evaluate_wakeup_rules(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    findings.extend(_powershell_network_pair(rows))
    return findings


def _powershell_network_pair(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    process_rows = []
    network_rows = []
    for row in rows:
        payload = row.get("payload", {})
        if not isinstance(payload, dict):
            continue
        process = payload.get("process", {})
        if isinstance(process, dict) and _looks_like_powershell(process):
            process_rows.append(row)
        connection = payload.get("connection", {})
        if isinstance(connection, dict) and connection.get("remote"):
            network_rows.append(row)

    findings = []
    for proc in process_rows:
        proc_time = _parse_utc(str(proc.get("observed_at_utc", "")))
        if proc_time is None:
            continue
        for net in network_rows:
            net_time = _parse_utc(str(net.get("observed_at_utc", "")))
            if net_time is None:
                continue
            delta = abs((net_time - proc_time).total_seconds())
            if delta <= 60:
                findings.append(
                    {
                        "rule_id": "powershell_network_pair",
                        "severity": "high",
                        "reason": "PowerShell activity paired with a network connection within 60 seconds.",
                        "evidence_event_ids": [str(proc.get("event_id", "")), str(net.get("event_id", ""))],
                        "operator_decision_required": True,
                    }
                )
                return findings
    return findings


def _looks_like_powershell(process: dict[str, Any]) -> bool:
    material = " ".join(
        [
            str(process.get("name", "")),
            " ".join(str(item) for item in process.get("cmdline", []) if item is not None),
        ]
    ).lower()
    return "powershell" in material or "pwsh" in material


def _parse_utc(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return None
