"""Service surface for AnchorWorks calling TrueCore as a package."""

from __future__ import annotations

from pathlib import Path

from truecore.package_api.contracts import (
    TrueCorePackageError,
    TrueCoreRequest,
    TrueCoreResponse,
    validate_request,
    validate_response,
)
from truecore.package_api.policy import check_package_policy
from truecore.central.contracts import CentralContractError, build_legal_ip_trace_report, validate_legal_ip_trace_report
from truecore.package_api.reports import TextFactsReportError, build_text_facts_report


class TrueCorePackageService:
    """Small callable boundary. No server, UI, or agent launch required."""

    def __init__(self, *, fusion_store=None, receipt_root=None, runtime_manager=None):
        self.fusion_store = fusion_store
        self.receipt_root = Path(receipt_root) if receipt_root is not None else None
        self.runtime_manager = runtime_manager

    def handle(self, request: TrueCoreRequest) -> TrueCoreResponse:
        try:
            request = validate_request(request)
        except TrueCorePackageError as exc:
            return TrueCoreResponse(
                request_id=request.request_id or "invalid",
                status="rejected",
                facts=[],
                evidence_refs=[],
                warnings=[str(exc)],
            )

        if request.route == "status.summary":
            return validate_response(
                TrueCoreResponse(
                    request_id=request.request_id,
                    status="ok",
                    facts=["TrueCore package API is available."],
                    evidence_refs=["truecore:package:status"],
                    warnings=[],
                )
            )

        if request.route == "fusion.latest":
            return self._fusion_latest(request)

        if request.route == "logs.health":
            return self._logs_health(request)

        if request.route == "report.text_facts":
            return self._report_text_facts(request)

        if request.route == "report.legal_ip_trace":
            return self._report_legal_ip_trace(request)

        if request.route == "policy.check_action":
            return self._policy_check_action(request)

        if request.route == "runtime.status":
            return self._runtime_status(request)

        if request.route == "runtime.verify_latest":
            return self._runtime_verify_latest(request)

        if request.route == "runtime.watch_latest":
            return self._runtime_watch_latest(request)

        return validate_response(
            TrueCoreResponse(
                request_id=request.request_id,
                status="ok",
                facts=[],
                evidence_refs=[],
                warnings=[f"Route {request.route} is recognized but not implemented in the package service yet."],
            )
        )

    def _logs_health(self, request: TrueCoreRequest) -> TrueCoreResponse:
        if self.receipt_root is None:
            return validate_response(
                TrueCoreResponse(
                    request_id=request.request_id,
                    status="ok",
                    facts=[],
                    evidence_refs=[],
                    warnings=["Receipt root is not configured."],
                )
            )
        health_root = self.receipt_root / "health"
        receipts = sorted(health_root.glob("*.health.json")) if health_root.exists() else []
        if not receipts:
            return validate_response(
                TrueCoreResponse(
                    request_id=request.request_id,
                    status="ok",
                    facts=[],
                    evidence_refs=[],
                    warnings=["No health receipts are available."],
                )
            )
        latest = receipts[-1]
        return validate_response(
            TrueCoreResponse(
                request_id=request.request_id,
                status="ok",
                facts=[f"Latest health receipt {latest.name} is available."],
                evidence_refs=[f"retention:health:{latest.name}"],
                warnings=[],
            )
        )

    def _report_text_facts(self, request: TrueCoreRequest) -> TrueCoreResponse:
        try:
            report = build_text_facts_report(
                title=str(request.payload.get("title", "TrueCore Report")),
                facts=list(request.payload.get("facts", [])),
                evidence_refs=list(request.payload.get("evidence_refs", [])),
                warnings=list(request.payload.get("warnings", [])),
            )
        except (TextFactsReportError, TypeError) as exc:
            return validate_response(
                TrueCoreResponse(
                    request_id=request.request_id,
                    status="error",
                    facts=[],
                    evidence_refs=[],
                    warnings=[str(exc)],
                )
            )
        return validate_response(
            TrueCoreResponse(
                request_id=request.request_id,
                status="ok",
                facts=[f"Text facts report {report['title']} is ready."],
                evidence_refs=report["evidence_refs"],
                warnings=report["warnings"],
            )
        )

    def _report_legal_ip_trace(self, request: TrueCoreRequest) -> TrueCoreResponse:
        try:
            report = build_legal_ip_trace_report(
                report_id=str(request.payload.get("report_id", request.request_id)),
                title=str(request.payload.get("title", "TrueCore Legal IP Trace Report")),
                severity=str(request.payload.get("severity", "medium")),
                remote_ip=str(request.payload.get("remote_ip", "")),
                observed_endpoint=str(request.payload.get("observed_endpoint", "")),
                facts=list(request.payload.get("facts", [])),
                evidence_refs=list(request.payload.get("evidence_refs", [])),
                source_refs=list(request.payload.get("source_refs", [])),
                evidence_hashes=dict(request.payload.get("evidence_hashes", {})),
                chain_of_custody=list(request.payload.get("chain_of_custody", [])),
                containment_plan=dict(request.payload.get("containment_plan", {})),
                release_receipt_ref=str(request.payload.get("release_receipt_ref", "")),
                unknowns=list(request.payload.get("unknowns", [])),
            )
            report = validate_legal_ip_trace_report(report)
        except (CentralContractError, TypeError, ValueError) as exc:
            return validate_response(
                TrueCoreResponse(
                    request_id=request.request_id,
                    status="error",
                    facts=[],
                    evidence_refs=[],
                    warnings=[str(exc)],
                )
            )
        return validate_response(
            TrueCoreResponse(
                request_id=request.request_id,
                status="ok",
                facts=[f"Legal IP trace report {report['report_id']} is ready."],
                evidence_refs=report["evidence_refs"],
                warnings=report["unknowns"],
            )
        )

    def _policy_check_action(self, request: TrueCoreRequest) -> TrueCoreResponse:
        target_route = str(request.payload.get("route", ""))
        policy = check_package_policy(caller=request.caller, route=target_route)
        if policy["approval_required"]:
            return validate_response(
                TrueCoreResponse(
                    request_id=request.request_id,
                    status="approval_required",
                    facts=[],
                    evidence_refs=[],
                    warnings=[policy["reason"]],
                    action_required=False,
                    approval_required=True,
                )
            )
        status = "ok" if policy["allowed"] else "rejected"
        return validate_response(
            TrueCoreResponse(
                request_id=request.request_id,
                status=status,
                facts=[f"Route {target_route} is allowed."] if policy["allowed"] else [],
                evidence_refs=["truecore:policy:package"] if policy["allowed"] else [],
                warnings=[] if policy["allowed"] else [policy["reason"]],
            )
        )

    def _runtime_status(self, request: TrueCoreRequest) -> TrueCoreResponse:
        if self.runtime_manager is None:
            return validate_response(
                TrueCoreResponse(
                    request_id=request.request_id,
                    status="ok",
                    facts=[],
                    evidence_refs=[],
                    warnings=["Runtime manager is not configured."],
                )
            )
        status = self.runtime_manager.status()
        latest = status.get("latest_run_id") or "none"
        runtime_status = status.get("status", "unknown")
        return validate_response(
            TrueCoreResponse(
                request_id=request.request_id,
                status="ok",
                facts=[f"Latest runtime run {latest} status is {runtime_status}."],
                evidence_refs=["truecore:runtime:status"],
                warnings=[] if runtime_status != "missing" else [str(status.get("warning", "No runtime runs are available."))],
            )
        )

    def _runtime_verify_latest(self, request: TrueCoreRequest) -> TrueCoreResponse:
        if self.runtime_manager is None:
            return validate_response(
                TrueCoreResponse(
                    request_id=request.request_id,
                    status="ok",
                    facts=[],
                    evidence_refs=[],
                    warnings=["Runtime manager is not configured."],
                )
            )
        verify = self.runtime_manager.verify_latest()
        if verify.get("status") != "ok":
            return validate_response(
                TrueCoreResponse(
                    request_id=request.request_id,
                    status="error" if verify.get("status") == "error" else "ok",
                    facts=[],
                    evidence_refs=[],
                    warnings=[str(verify.get("warning", "Latest runtime proof pack is not available."))],
                )
            )
        run_id = str(verify.get("run_id", ""))
        return validate_response(
            TrueCoreResponse(
                request_id=request.request_id,
                status="ok",
                facts=[f"Latest runtime proof pack {run_id} verified."],
                evidence_refs=[f"truecore:runtime:proof:{run_id}"],
                warnings=[],
            )
        )

    def _runtime_watch_latest(self, request: TrueCoreRequest) -> TrueCoreResponse:
        if self.runtime_manager is None:
            return validate_response(
                TrueCoreResponse(
                    request_id=request.request_id,
                    status="ok",
                    facts=[],
                    evidence_refs=[],
                    warnings=["Runtime manager is not configured."],
                )
            )
        receipt = self.runtime_manager.watch_latest()
        if receipt.get("status") == "missing":
            return validate_response(
                TrueCoreResponse(
                    request_id=request.request_id,
                    status="ok",
                    facts=[],
                    evidence_refs=[],
                    warnings=[str(receipt.get("warning", "No runtime runs are available."))],
                )
            )
        status = str(receipt.get("status", "unknown"))
        anomaly_count = int(receipt.get("anomaly_count", 0) or 0)
        return validate_response(
            TrueCoreResponse(
                request_id=request.request_id,
                status="ok",
                facts=[f"Latest watcher receipt status is {status} with {anomaly_count} anomalies."],
                evidence_refs=["truecore:runtime:watcher"],
                warnings=[],
            )
        )

    def _fusion_latest(self, request: TrueCoreRequest) -> TrueCoreResponse:
        if self.fusion_store is None:
            return validate_response(
                TrueCoreResponse(
                    request_id=request.request_id,
                    status="ok",
                    facts=[],
                    evidence_refs=[],
                    warnings=["Fusion store is not configured."],
                )
            )
        blocks = list(self.fusion_store.iter_blocks() or [])
        if not blocks:
            return validate_response(
                TrueCoreResponse(
                    request_id=request.request_id,
                    status="ok",
                    facts=[],
                    evidence_refs=[],
                    warnings=["No fusion blocks are available."],
                )
            )
        latest = blocks[-1]
        block_id = latest["block_id"]
        return validate_response(
            TrueCoreResponse(
                request_id=request.request_id,
                status="ok",
                facts=[f"Latest fusion block {block_id} has {latest['event_count']} events."],
                evidence_refs=[f"fusion:block:{block_id}"],
                warnings=[],
            )
        )
