import unittest

from securecore.central.contracts import (
    CentralContractError,
    build_facts_report,
    build_model_writer_report_request,
    build_reader_bundle,
    build_writer_receipt,
    build_writer_rejection,
    build_writer_request,
    validate_facts_report,
    validate_writer_rejection,
    validate_model_writer_report_request,
    validate_reader_bundle,
    validate_writer_request,
)


class CentralContractsTests(unittest.TestCase):
    def test_reader_bundle_is_read_only_context(self):
        bundle = build_reader_bundle(
            request_id="read-1",
            requested_by="agent.network",
            sources=["forge.sensor_network", "temporal.rows"],
            facts=[{"event_id": "evt-1", "summary": "process connected to ip"}],
            evidence_refs=["evt-1"],
        )

        validated = validate_reader_bundle(bundle)

        self.assertEqual(validated["authority"], "read_only")
        self.assertNotIn("message_text", validated)
        self.assertNotIn("recommended_actions", validated)

    def test_writer_request_cannot_authorize_enforcement(self):
        request = build_writer_request(
            request_id="write-1",
            requested_by_agent="agent.network",
            summary="Suspicious outbound connection observed.",
            severity="high",
            facts=["pwsh.exe connected to 203.0.113.10:443"],
            inferences=[],
            evidence_refs=["evt-1"],
            recommended_actions=[],
        )

        validated = validate_writer_request(request)

        self.assertTrue(validated["approval_required"])
        self.assertFalse(validated["enforcement_authorized"])

    def test_writer_request_rejects_enforcement_authorized_true(self):
        request = build_writer_request(
            request_id="write-2",
            requested_by_agent="agent.network",
            summary="bad",
            severity="critical",
            facts=["fact"],
            inferences=[],
            evidence_refs=["evt-1"],
            recommended_actions=[],
        )
        request["enforcement_authorized"] = True

        with self.assertRaisesRegex(CentralContractError, "enforcement"):
            validate_writer_request(request)

    def test_writer_request_rejects_inference_and_action_text(self):
        request = build_writer_request(
            request_id="write-3",
            requested_by_agent="agent.network",
            summary="Suspicious outbound connection observed.",
            severity="high",
            facts=["pwsh.exe connected to 203.0.113.10:443"],
            inferences=["connection needs operator review"],
            evidence_refs=["evt-1"],
            recommended_actions=[],
        )

        with self.assertRaisesRegex(CentralContractError, "facts-only"):
            validate_writer_request(request)

        request["inferences"] = []
        request["recommended_actions"] = ["review connection"]
        with self.assertRaisesRegex(CentralContractError, "facts-only"):
            validate_writer_request(request)

    def test_model_writer_request_requires_allowed_condition_and_facts(self):
        request = build_model_writer_report_request(
            request_id="model-write-1",
            requested_by_model="openai_session_model",
            condition="operator_requested_report",
            summary="Suspicious outbound connection observed.",
            severity="high",
            facts=["pwsh.exe connected to 203.0.113.10:443"],
            evidence_refs=["evt-1"],
            reader_bundle_refs=["read-1"],
            language_task="format_facts",
        )

        validated = validate_model_writer_report_request(request)

        self.assertEqual(validated["writer_task"], "facts_only_report")
        self.assertEqual(validated["report_format"], "securecore_facts_report_v1")
        self.assertFalse(validated["enforcement_authorized"])

    def test_model_writer_request_rejects_unknown_condition(self):
        request = build_model_writer_report_request(
            request_id="model-write-2",
            requested_by_model="openai_session_model",
            condition="model_felt_like_writing",
            summary="Suspicious outbound connection observed.",
            severity="high",
            facts=["pwsh.exe connected to 203.0.113.10:443"],
            evidence_refs=["evt-1"],
            reader_bundle_refs=["read-1"],
            language_task="format_facts",
        )

        with self.assertRaisesRegex(CentralContractError, "condition"):
            validate_model_writer_report_request(request)

    def test_facts_report_is_the_only_report_shape(self):
        report = build_facts_report(
            report_id="report-1",
            title="Suspicious outbound connection observed",
            severity="high",
            scope="local host network observation",
            facts=["pwsh.exe connected to 203.0.113.10:443"],
            evidence_refs=["evt-1"],
            source_refs=["forge:sensor_network"],
            language_notes=["Names normalized for operator readability."],
        )

        validated = validate_facts_report(report)

        self.assertEqual(validated["kind"], "securecore_facts_report")
        self.assertEqual(validated["format"], "securecore_facts_report_v1")
        self.assertNotIn("inferences", validated)
        self.assertNotIn("recommended_actions", validated)

    def test_facts_report_rejects_inference_fields(self):
        report = build_facts_report(
            report_id="report-2",
            title="Suspicious outbound connection observed",
            severity="high",
            scope="local host network observation",
            facts=["pwsh.exe connected to 203.0.113.10:443"],
            evidence_refs=["evt-1"],
            source_refs=["forge:sensor_network"],
            language_notes=[],
        )
        report["inferences"] = ["this is probably malware"]

        with self.assertRaisesRegex(CentralContractError, "inference"):
            validate_facts_report(report)

    def test_writer_receipt_links_request_without_approving_action(self):
        receipt = build_writer_receipt(
            request_id="write-1",
            receipt_id="receipt-1",
            status="rendered",
            output_ref="operator/report-1",
        )

        self.assertEqual(receipt["request_id"], "write-1")
        self.assertFalse(receipt["enforcement_authorized"])

    def test_writer_rejection_is_not_report_or_action_authority(self):
        rejection = build_writer_rejection(
            request_id="write-bad",
            receipt_id="reject-1",
            reason="writer requests are facts-only report requests",
        )

        validated = validate_writer_rejection(rejection)

        self.assertEqual(validated["status"], "rejected")
        self.assertEqual(validated["output_ref"], "")
        self.assertFalse(validated["enforcement_authorized"])
        self.assertFalse(validated["fact_authority"])


if __name__ == "__main__":
    unittest.main()
