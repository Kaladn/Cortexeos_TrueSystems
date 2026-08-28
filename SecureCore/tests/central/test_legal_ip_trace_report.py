import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from securecore.central.contracts import (
    CentralContractError,
    build_legal_ip_trace_report,
    validate_legal_ip_trace_report,
)
from securecore.central.writer import CentralWriter
from securecore.network.containment import build_trap_log_release_plan


class LegalIpTraceReportTests(unittest.TestCase):
    def test_legal_ip_trace_report_requires_evidence_hashes_and_release_receipt(self):
        containment_plan = build_trap_log_release_plan(
            remote_ip="203.0.113.10",
            observed_event_refs=["forge:sensor_network:evt-1"],
            ttl_seconds=120,
            protocol="tcp",
            remote_ports=[443],
        )
        report = build_legal_ip_trace_report(
            report_id="legal-ip-1",
            title="Bounded IP Trace Report",
            severity="high",
            remote_ip="203.0.113.10",
            observed_endpoint="203.0.113.10:443/tcp",
            facts=["Connection metadata was observed for 203.0.113.10:443/tcp."],
            evidence_refs=["forge:sensor_network:evt-1"],
            source_refs=["forge:sensor_network", "forge:fusion"],
            evidence_hashes={"forge:sensor_network:evt-1": "a" * 64},
            chain_of_custody=[
                {
                    "step": "observed",
                    "actor": "securecore.network.diff",
                    "timestamp_utc": "2026-05-17T13:00:00.000000Z",
                    "evidence_ref": "forge:sensor_network:evt-1",
                    "hash": "a" * 64,
                }
            ],
            containment_plan=containment_plan,
            release_receipt_ref="reaper:release:receipt-1",
            unknowns=["No WHOIS enrichment was attached to this report."],
        )

        validated = validate_legal_ip_trace_report(report)

        self.assertEqual(validated["kind"], "securecore_legal_ip_trace_report")
        self.assertEqual(validated["remote_ip"], "203.0.113.10")
        self.assertEqual(validated["containment"]["mode"], "trap_log_release")
        self.assertFalse(validated["enforcement_authorized"])
        self.assertFalse(validated["permanent_action_authorized"])
        self.assertEqual(validated["release_receipt_ref"], "reaper:release:receipt-1")
        self.assertNotIn("conclusion", validated)
        self.assertNotIn("verdict", validated)

    def test_legal_ip_trace_report_rejects_missing_release_receipt(self):
        containment_plan = build_trap_log_release_plan(
            remote_ip="203.0.113.10",
            observed_event_refs=["forge:sensor_network:evt-1"],
        )

        with self.assertRaisesRegex(CentralContractError, "release"):
            validate_legal_ip_trace_report(
                build_legal_ip_trace_report(
                    report_id="legal-ip-2",
                    title="Bounded IP Trace Report",
                    severity="high",
                    remote_ip="203.0.113.10",
                    observed_endpoint="203.0.113.10:443/tcp",
                    facts=["Connection metadata was observed."],
                    evidence_refs=["forge:sensor_network:evt-1"],
                    source_refs=["forge:sensor_network"],
                    evidence_hashes={"forge:sensor_network:evt-1": "a" * 64},
                    chain_of_custody=[
                        {
                            "step": "observed",
                            "actor": "securecore.network.diff",
                            "timestamp_utc": "2026-05-17T13:00:00.000000Z",
                            "evidence_ref": "forge:sensor_network:evt-1",
                            "hash": "a" * 64,
                        }
                    ],
                    containment_plan=containment_plan,
                    release_receipt_ref="",
                    unknowns=[],
                )
            )

    def test_legal_ip_trace_report_rejects_inference_and_action_fields(self):
        containment_plan = build_trap_log_release_plan(
            remote_ip="203.0.113.10",
            observed_event_refs=["forge:sensor_network:evt-1"],
        )
        report = build_legal_ip_trace_report(
            report_id="legal-ip-3",
            title="Bounded IP Trace Report",
            severity="high",
            remote_ip="203.0.113.10",
            observed_endpoint="203.0.113.10:443/tcp",
            facts=["Connection metadata was observed."],
            evidence_refs=["forge:sensor_network:evt-1"],
            source_refs=["forge:sensor_network"],
            evidence_hashes={"forge:sensor_network:evt-1": "a" * 64},
            chain_of_custody=[
                {
                    "step": "observed",
                    "actor": "securecore.network.diff",
                    "timestamp_utc": "2026-05-17T13:00:00.000000Z",
                    "evidence_ref": "forge:sensor_network:evt-1",
                    "hash": "a" * 64,
                }
            ],
            containment_plan=containment_plan,
            release_receipt_ref="reaper:release:receipt-1",
            unknowns=[],
        )
        report["recommended_actions"] = ["block the IP"]

        with self.assertRaisesRegex(CentralContractError, "inference/action"):
            validate_legal_ip_trace_report(report)

    def test_central_writer_renders_legal_ip_trace_report_and_receipt(self):
        containment_plan = build_trap_log_release_plan(
            remote_ip="203.0.113.10",
            observed_event_refs=["forge:sensor_network:evt-1"],
        )
        report = build_legal_ip_trace_report(
            report_id="legal-ip-4",
            title="Bounded IP Trace Report",
            severity="high",
            remote_ip="203.0.113.10",
            observed_endpoint="203.0.113.10:443/tcp",
            facts=["Connection metadata was observed."],
            evidence_refs=["forge:sensor_network:evt-1"],
            source_refs=["forge:sensor_network"],
            evidence_hashes={"forge:sensor_network:evt-1": "a" * 64},
            chain_of_custody=[
                {
                    "step": "observed",
                    "actor": "securecore.network.diff",
                    "timestamp_utc": "2026-05-17T13:00:00.000000Z",
                    "evidence_ref": "forge:sensor_network:evt-1",
                    "hash": "a" * 64,
                }
            ],
            containment_plan=containment_plan,
            release_receipt_ref="reaper:release:receipt-1",
            unknowns=[],
        )

        with TemporaryDirectory() as tmpdir:
            result = CentralWriter(tmpdir).render_legal_ip_trace_report(report)

            self.assertEqual(result["receipt"]["status"], "rendered")
            self.assertFalse(result["receipt"]["enforcement_authorized"])
            written = json.loads(Path(result["report_path"]).read_text(encoding="utf-8"))
            self.assertEqual(written["kind"], "securecore_legal_ip_trace_report")
            self.assertEqual(written["release_receipt_ref"], "reaper:release:receipt-1")


if __name__ == "__main__":
    unittest.main()
