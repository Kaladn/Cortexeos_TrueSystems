"""Central Writer runtime for facts-only text report output."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from truecore.receipt_store import atomic_json, digest, read_json

from truecore.central.contracts import (
    build_facts_report,
    build_writer_receipt,
    validate_facts_report,
    validate_legal_ip_trace_report,
    validate_model_writer_report_request,
    validate_writer_request,
)


class CentralWriter:
    """Validate writer requests and emit operator-facing facts reports."""

    def __init__(self, output_root: str | Path):
        self.output_root = Path(output_root).expanduser().resolve()
        self.reports_dir = self.output_root / "reports"
        self.receipts_dir = self.output_root / "receipts"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.receipts_dir.mkdir(parents=True, exist_ok=True)

    def render_agent_request(self, request: dict[str, Any]) -> dict[str, Any]:
        validated = validate_writer_request(request)
        report = build_facts_report(
            report_id=_report_id(validated["request_id"]),
            title=validated["summary"],
            severity=validated["severity"],
            scope=f"agent:{validated['requested_by_agent']}",
            facts=validated["facts"],
            evidence_refs=validated["evidence_refs"],
            source_refs=[validated["requested_by_agent"]],
            language_notes=[],
        )
        return self._write(validated["request_id"], report)

    def render_model_request(self, request: dict[str, Any]) -> dict[str, Any]:
        validated = validate_model_writer_report_request(request)
        report = build_facts_report(
            report_id=_report_id(validated["request_id"]),
            title=validated["summary"],
            severity=validated["severity"],
            scope=f"model:{validated['requested_by_model']}",
            facts=validated["facts"],
            evidence_refs=validated["evidence_refs"],
            source_refs=validated["reader_bundle_refs"],
            language_notes=[f"language_task={validated['language_task']}"],
        )
        return self._write(validated["request_id"], report)

    def render_legal_ip_trace_report(self, report: dict[str, Any]) -> dict[str, Any]:
        validated = validate_legal_ip_trace_report(report)
        return self._write(validated["report_id"], validated)

    def _write(self, request_id: str, report: dict[str, Any]) -> dict[str, Any]:
        if report.get("kind") == "truecore_legal_ip_trace_report":
            validated_report = validate_legal_ip_trace_report(report)
        else:
            validated_report = validate_facts_report(report)
        report_path = self.reports_dir / f"{_report_id(validated_report['report_id'])}-{digest(validated_report['report_id'])[:12]}.json"
        receipt = build_writer_receipt(
            request_id=request_id,
            receipt_id=f"receipt_{validated_report['report_id']}",
            status="rendered",
            output_ref=str(report_path),
        )
        if "_publication" in validated_report:
            raise ValueError("publication metadata is writer-owned")
        publication = {**validated_report, "_publication": {
            "schema": "truecore.writer_publication@2", "receipt": receipt,
            "report_sha256": digest(validated_report),
        }}
        atomic_json(report_path, publication)
        return {
            "report": validated_report,
            "receipt": receipt,
            "report_path": str(report_path),
            "publication_schema": publication["_publication"]["schema"],
            "receipt_ref": {"path": str(report_path), "member": "_publication.receipt"},
        }

    @staticmethod
    def read_publication(path: str | Path) -> dict[str, Any]:
        publication = read_json(path)
        metadata = publication.pop("_publication", {})
        if metadata.get("schema") != "truecore.writer_publication@2":
            raise ValueError("unsupported writer publication")
        report = publication
        if report.get("kind") == "truecore_legal_ip_trace_report":
            validate_legal_ip_trace_report(report)
        else:
            validate_facts_report(report)
        if digest(report) != metadata["report_sha256"]:
            raise ValueError("report commitment mismatch")
        return {"report": report, **metadata}


def _report_id(request_id: str) -> str:
    safe = "".join(char if char.isalnum() or char in "-_" else "_" for char in request_id)
    return f"report_{safe}"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
