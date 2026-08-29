#!/usr/bin/env python3
"""Read-only temporal causality and integrity checker for JSONL event logs."""

from __future__ import annotations

import argparse
import json
import hashlib
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")

REQUIRED_FIELDS = {
    "event_id",
    "source_id",
    "sensor_id",
    "event_type",
    "observed_at_utc",
    "sequence",
    "writer_id",
    "batch_id",
    "batch_index",
    "cursor",
    "payload_hash",
    "previous_event_hash",
    "causal_parents",
    "correlation_id",
    "payload",
}


def stable_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def parse_time(value: str) -> datetime | None:
    if not isinstance(value, str) or not TIMESTAMP_RE.match(value):
        return None
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)


def compute_event_hash(record: dict[str, Any]) -> str:
    material = {
        key: value
        for key, value in record.items()
        if key not in {"previous_event_hash"}
    }
    return stable_hash(material)


@dataclass
class Finding:
    code: str
    severity: str
    record_ref: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "record_ref": self.record_ref,
            "message": self.message,
            "details": self.details,
        }


class TemporalCausalityLogChecker:
    def __init__(
        self,
        *,
        allowed_clock_skew_ms: int = 1000,
        require_monotonic_sequence: bool = True,
        require_hash_chain: bool = True,
        require_cursor_progression: bool = True,
        require_causal_parent_presence: bool = True,
        fail_on_mixed_timestamp_format: bool = True,
        focus_event_type: str = "",
    ):
        self.allowed_clock_skew_ms = allowed_clock_skew_ms
        self.require_monotonic_sequence = require_monotonic_sequence
        self.require_hash_chain = require_hash_chain
        self.require_cursor_progression = require_cursor_progression
        self.require_causal_parent_presence = require_causal_parent_presence
        self.fail_on_mixed_timestamp_format = fail_on_mixed_timestamp_format
        self.focus_event_type = focus_event_type

        self.seen_event_ids: set[str] = set()
        self.last_sequence_by_writer: dict[str, int] = {}
        self.last_cursor_by_sensor: dict[str, Any] = {}
        self.last_timestamp_by_source: dict[str, datetime] = {}
        self.event_hash_index: dict[str, str] = {}
        self.event_time_index: dict[str, datetime] = {}
        self.event_record_index: dict[str, dict[str, Any]] = {}
        self.event_order: list[str] = []
        self.lamport_by_source: dict[str, int] = {}
        self.previous_hash_by_writer: dict[str, str] = {}
        self.batch_index_seen: dict[str, set[int]] = {}
        self.batch_last_index: dict[str, int] = {}
        self.violations: list[Finding] = []
        self.warnings: list[Finding] = []

    def check_path(self, log_path: Path) -> dict[str, Any]:
        total = 0
        clean = 0

        with log_path.open("r", encoding="utf-8", errors="replace") as handle:
            for line_number, line in enumerate(handle, start=1):
                raw = line.strip()
                if not raw:
                    continue
                total += 1
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError as exc:
                    self._violation(
                        "JSON_PARSE_ERROR",
                        f"line:{line_number}",
                        "record is not valid JSON",
                        {"error": str(exc)},
                    )
                    continue
                before = len(self.violations)
                self._validate_record(record, line_number)
                if len(self.violations) == before:
                    clean += 1

        leadup = self._build_leadup()
        hard_violation = bool(self.violations)
        grouped = self._group_findings(self.violations)

        return {
            "summary": {
                "total_records": total,
                "clean_records": clean,
                "violations_count": len(self.violations),
                "warnings_count": len(self.warnings),
                "first_failure": self.violations[0].to_dict() if self.violations else None,
                "highest_severity": "hard" if hard_violation else ("warning" if self.warnings else "none"),
                "replay_safe": not hard_violation,
                "causality_safe": not any(
                    item.code in {"MISSING_CAUSAL_PARENT", "PARENT_AFTER_CHILD", "CAUSAL_LAMPORT_INVERSION"}
                    for item in self.violations
                ),
                "forge_trust_safe": not any(
                    item.code in {"HASH_CHAIN_BREAK", "PAYLOAD_HASH_MISMATCH", "DUPLICATE_EVENT_ID"}
                    for item in self.violations
                ),
            },
            "violations": [item.to_dict() for item in self.violations],
            "warnings": [item.to_dict() for item in self.warnings],
            "groups": grouped,
            "leadup": leadup,
        }

    def _validate_record(self, record: dict[str, Any], line_number: int) -> None:
        record_ref = str(record.get("event_id") or f"line:{line_number}")
        if not isinstance(record, dict):
            self._violation("SCHEMA_INVALID_RECORD", record_ref, "record must be a JSON object")
            return

        self._validate_schema(record, record_ref)
        self._validate_timestamp_format(record, record_ref)
        self._validate_unique_event_id(record, record_ref)
        self._validate_sequence(record, record_ref)
        self._validate_batch_order(record, record_ref)
        self._validate_cursor(record, record_ref)
        self._validate_hash_chain(record, record_ref)
        self._validate_payload_hash(record, record_ref)
        self._validate_wall_clock_order(record, record_ref)
        self._validate_lamport_order(record, record_ref)
        self._validate_causal_parents(record, record_ref)
        self._update_state(record)

    def _validate_schema(self, record: dict[str, Any], record_ref: str) -> None:
        missing = sorted(REQUIRED_FIELDS.difference(record))
        for field_name in missing:
            self._violation(
                "SCHEMA_MISSING_FIELD",
                record_ref,
                f"missing required field: {field_name}",
                {"field": field_name},
            )

    def _validate_timestamp_format(self, record: dict[str, Any], record_ref: str) -> None:
        timestamp = record.get("observed_at_utc")
        if parse_time(timestamp) is None:
            self._violation(
                "TIMESTAMP_FORMAT_INVALID",
                record_ref,
                "observed_at_utc must use YYYY-MM-DDTHH:MM:SS.ffffffZ",
                {"observed_at_utc": timestamp},
            )

    def _validate_unique_event_id(self, record: dict[str, Any], record_ref: str) -> None:
        event_id = record.get("event_id")
        if not event_id:
            return
        if event_id in self.seen_event_ids:
            self._violation("DUPLICATE_EVENT_ID", record_ref, "event_id already seen", {"event_id": event_id})

    def _validate_sequence(self, record: dict[str, Any], record_ref: str) -> None:
        if not self.require_monotonic_sequence:
            return
        key = str(record.get("writer_id") or record.get("source_id") or "")
        sequence = record.get("sequence")
        if not key or not isinstance(sequence, int):
            return
        previous = self.last_sequence_by_writer.get(key)
        if previous is not None:
            if sequence == previous:
                self._violation("REPEATED_SEQUENCE", record_ref, "sequence repeated", {"key": key, "sequence": sequence})
            elif sequence < previous:
                self._violation(
                    "SEQUENCE_REGRESSION",
                    record_ref,
                    "sequence regressed",
                    {"key": key, "previous": previous, "current": sequence},
                )
            elif sequence > previous + 1:
                self._warning(
                    "SEQUENCE_GAP",
                    record_ref,
                    "sequence gap detected",
                    {"key": key, "previous": previous, "current": sequence},
                )

    def _validate_batch_order(self, record: dict[str, Any], record_ref: str) -> None:
        batch_id = record.get("batch_id")
        batch_index = record.get("batch_index")
        if not batch_id or not isinstance(batch_index, int):
            return
        seen = self.batch_index_seen.setdefault(str(batch_id), set())
        if batch_index in seen:
            self._violation("REPEATED_BATCH_INDEX", record_ref, "batch_index repeated", {"batch_id": batch_id})
        previous = self.batch_last_index.get(str(batch_id))
        if previous is not None:
            if batch_index < previous:
                self._violation(
                    "BATCH_INDEX_REGRESSION",
                    record_ref,
                    "batch_index regressed",
                    {"batch_id": batch_id, "previous": previous, "current": batch_index},
                )
            elif batch_index > previous + 1:
                self._warning(
                    "BATCH_INDEX_GAP",
                    record_ref,
                    "batch_index gap detected",
                    {"batch_id": batch_id, "previous": previous, "current": batch_index},
                )

    def _validate_cursor(self, record: dict[str, Any], record_ref: str) -> None:
        if not self.require_cursor_progression:
            return
        key = str(record.get("sensor_id") or "")
        cursor = record.get("cursor")
        if not key or cursor is None:
            return
        previous = self.last_cursor_by_sensor.get(key)
        if previous is None:
            return
        try:
            if cursor == previous:
                self._warning("CURSOR_STALLED", record_ref, "sensor cursor did not advance", {"sensor_id": key})
            elif cursor < previous:
                self._violation(
                    "CURSOR_REGRESSION",
                    record_ref,
                    "sensor cursor regressed",
                    {"sensor_id": key, "previous": previous, "current": cursor},
                )
        except TypeError:
            self._warning("CURSOR_UNORDERED", record_ref, "sensor cursor cannot be ordered", {"sensor_id": key})

    def _validate_hash_chain(self, record: dict[str, Any], record_ref: str) -> None:
        if not self.require_hash_chain:
            return
        writer_id = str(record.get("writer_id") or "")
        if not writer_id:
            return
        expected = self.previous_hash_by_writer.get(writer_id, "GENESIS")
        actual = record.get("previous_event_hash")
        if actual != expected:
            self._violation(
                "HASH_CHAIN_BREAK",
                record_ref,
                "previous_event_hash does not match expected writer chain",
                {"writer_id": writer_id, "expected": expected, "actual": actual},
            )

    def _validate_payload_hash(self, record: dict[str, Any], record_ref: str) -> None:
        if "payload" not in record:
            return
        computed = stable_hash(record.get("payload"))
        if computed != record.get("payload_hash"):
            self._violation(
                "PAYLOAD_HASH_MISMATCH",
                record_ref,
                "payload_hash does not match canonical payload hash",
                {"expected": computed, "actual": record.get("payload_hash")},
            )

    def _validate_wall_clock_order(self, record: dict[str, Any], record_ref: str) -> None:
        source_id = str(record.get("source_id") or "")
        current_time = parse_time(record.get("observed_at_utc"))
        if not source_id or current_time is None:
            return
        previous_time = self.last_timestamp_by_source.get(source_id)
        if previous_time is not None and current_time < previous_time:
            delta_ms = (previous_time - current_time).total_seconds() * 1000
            if delta_ms > self.allowed_clock_skew_ms:
                self._violation(
                    "TIMESTAMP_REGRESSION",
                    record_ref,
                    "observed_at_utc regressed beyond allowed clock skew",
                    {"source_id": source_id, "delta_ms": delta_ms},
                )
            else:
                self._warning(
                    "SMALL_CLOCK_SKEW",
                    record_ref,
                    "small timestamp regression within allowed skew",
                    {"source_id": source_id, "delta_ms": delta_ms},
                )

    def _validate_lamport_order(self, record: dict[str, Any], record_ref: str) -> None:
        lamport = record.get("lamport_counter")
        source_id = str(record.get("source_id") or "")
        if lamport is None or not isinstance(lamport, int) or not source_id:
            return
        previous = self.lamport_by_source.get(source_id)
        if previous is not None and lamport <= previous:
            self._violation(
                "LAMPORT_REGRESSION",
                record_ref,
                "lamport_counter did not increase for source",
                {"source_id": source_id, "previous": previous, "current": lamport},
            )

    def _validate_causal_parents(self, record: dict[str, Any], record_ref: str) -> None:
        if not self.require_causal_parent_presence:
            return
        parents = record.get("causal_parents") or []
        if not isinstance(parents, list):
            self._violation("CAUSAL_PARENTS_INVALID", record_ref, "causal_parents must be a list")
            return
        current_time = parse_time(record.get("observed_at_utc"))
        current_lamport = record.get("lamport_counter")
        for parent_id in parents:
            if parent_id not in self.event_hash_index:
                self._violation(
                    "MISSING_CAUSAL_PARENT",
                    record_ref,
                    "causal parent was not seen before child",
                    {"parent_id": parent_id},
                )
                continue
            parent_time = self.event_time_index.get(parent_id)
            if current_time is not None and parent_time is not None:
                delta_ms = (parent_time - current_time).total_seconds() * 1000
                if delta_ms > self.allowed_clock_skew_ms:
                    self._violation(
                        "PARENT_AFTER_CHILD",
                        record_ref,
                        "causal parent timestamp is after child",
                        {"parent_id": parent_id, "delta_ms": delta_ms},
                    )
            parent_lamport = self.event_record_index.get(parent_id, {}).get("lamport_counter")
            if isinstance(parent_lamport, int) and isinstance(current_lamport, int):
                if parent_lamport >= current_lamport:
                    self._violation(
                        "CAUSAL_LAMPORT_INVERSION",
                        record_ref,
                        "parent lamport counter is not before child",
                        {"parent_id": parent_id, "parent": parent_lamport, "current": current_lamport},
                    )

    def _update_state(self, record: dict[str, Any]) -> None:
        event_id = record.get("event_id")
        if not event_id:
            return
        writer_id = str(record.get("writer_id") or "")
        source_id = str(record.get("source_id") or "")
        sensor_id = str(record.get("sensor_id") or "")
        batch_id = record.get("batch_id")
        batch_index = record.get("batch_index")
        sequence = record.get("sequence")
        cursor = record.get("cursor")
        lamport = record.get("lamport_counter")
        event_time = parse_time(record.get("observed_at_utc"))
        hashed = compute_event_hash(record)

        self.seen_event_ids.add(str(event_id))
        self.event_hash_index[str(event_id)] = hashed
        self.event_record_index[str(event_id)] = dict(record)
        self.event_order.append(str(event_id))
        if event_time is not None:
            self.event_time_index[str(event_id)] = event_time
            if source_id:
                self.last_timestamp_by_source[source_id] = event_time
        if writer_id:
            self.previous_hash_by_writer[writer_id] = hashed
        if writer_id and isinstance(sequence, int):
            self.last_sequence_by_writer[writer_id] = sequence
        if sensor_id and cursor is not None:
            self.last_cursor_by_sensor[sensor_id] = cursor
        if source_id and isinstance(lamport, int):
            self.lamport_by_source[source_id] = lamport
        if batch_id and isinstance(batch_index, int):
            key = str(batch_id)
            self.batch_index_seen.setdefault(key, set()).add(batch_index)
            self.batch_last_index[key] = batch_index

    def _build_leadup(self) -> list[dict[str, Any]]:
        focused = []
        for event_id in self.event_order:
            record = self.event_record_index[event_id]
            if self.focus_event_type and record.get("event_type") != self.focus_event_type:
                continue
            if not self.focus_event_type:
                payload = record.get("payload", {})
                severity = payload.get("severity") if isinstance(payload, dict) else ""
                if severity not in {"high", "critical", "emergency"} and "error" not in str(record.get("event_type", "")):
                    continue
            chain = self._causal_chain(event_id)
            preceding = chain[:-1]
            focused.append({
                "event_id": event_id,
                "event_type": record.get("event_type", ""),
                "correlation_id": record.get("correlation_id", ""),
                "causal_chain": chain,
                "preceding_event_types": [
                    self.event_record_index[item].get("event_type", "")
                    for item in preceding
                    if item in self.event_record_index
                ],
                "leadup_count": len(preceding),
            })
        return focused

    def _causal_chain(self, event_id: str) -> list[str]:
        visited: set[str] = set()
        ordered: list[str] = []

        def visit(current: str) -> None:
            if current in visited:
                return
            visited.add(current)
            record = self.event_record_index.get(current, {})
            for parent in record.get("causal_parents") or []:
                if parent in self.event_record_index:
                    visit(parent)
            ordered.append(current)

        visit(event_id)
        return ordered

    def _group_findings(self, findings: list[Finding]) -> dict[str, list[dict[str, Any]]]:
        groups = {
            "schema": [],
            "timestamp": [],
            "sequence": [],
            "batch": [],
            "cursor": [],
            "hash_chain": [],
            "payload": [],
            "causality": [],
            "clock_skew": [],
            "parse": [],
        }
        mapping = {
            "SCHEMA": "schema",
            "TIMESTAMP": "timestamp",
            "SEQUENCE": "sequence",
            "BATCH": "batch",
            "CURSOR": "cursor",
            "HASH": "hash_chain",
            "PAYLOAD": "payload",
            "MISSING_CAUSAL": "causality",
            "PARENT_AFTER": "causality",
            "CAUSAL": "causality",
            "LAMPORT": "causality",
            "JSON": "parse",
        }
        for finding in findings:
            target = "schema"
            for prefix, group in mapping.items():
                if finding.code.startswith(prefix):
                    target = group
                    break
            groups[target].append(finding.to_dict())
        return groups

    def _violation(self, code: str, record_ref: str, message: str, details: dict[str, Any] | None = None) -> None:
        self.violations.append(Finding(code, "hard", record_ref, message, details or {}))

    def _warning(self, code: str, record_ref: str, message: str, details: dict[str, Any] | None = None) -> None:
        self.warnings.append(Finding(code, "warning", record_ref, message, details or {}))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only temporal causality log checker.")
    parser.add_argument("--log-path", required=True, type=Path)
    parser.add_argument("--report-path", type=Path)
    parser.add_argument("--allowed-clock-skew-ms", type=int, default=1000)
    parser.add_argument("--focus-event-type", default="")
    parser.add_argument("--no-hash-chain", action="store_true")
    parser.add_argument("--no-cursor-progression", action="store_true")
    parser.add_argument("--no-causal-parent-presence", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    checker = TemporalCausalityLogChecker(
        allowed_clock_skew_ms=args.allowed_clock_skew_ms,
        require_hash_chain=not args.no_hash_chain,
        require_cursor_progression=not args.no_cursor_progression,
        require_causal_parent_presence=not args.no_causal_parent_presence,
        focus_event_type=args.focus_event_type,
    )
    report = checker.check_path(args.log_path)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.report_path:
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        args.report_path.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 1 if report["summary"]["violations_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
