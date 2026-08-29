import json
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

from truecore.central.contracts import (
    CentralContractError,
    build_model_writer_report_request,
    build_writer_request,
)
from truecore.central.writer import CentralWriter


class CentralWriterRuntimeTests(unittest.TestCase):
    def test_writer_renders_agent_facts_report_and_receipt(self):
        with TemporaryDirectory() as tmpdir:
            writer = CentralWriter(tmpdir)
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

            result = writer.render_agent_request(request)

            self.assertEqual(result["receipt"]["status"], "rendered")
            self.assertEqual(result["receipt"]["request_id"], "write-1")
            self.assertFalse(result["receipt"]["enforcement_authorized"])
            report_path = Path(result["report_path"])
            self.assertTrue(report_path.exists())
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["kind"], "truecore_facts_report")
            self.assertEqual(report["facts"], ["pwsh.exe connected to 203.0.113.10:443"])
            self.assertEqual(report["evidence_refs"], ["evt-1"])
            self.assertNotIn("inferences", report)
            self.assertNotIn("recommended_actions", report)

    def test_writer_renders_model_facts_report_request(self):
        with TemporaryDirectory() as tmpdir:
            writer = CentralWriter(tmpdir)
            request = build_model_writer_report_request(
                request_id="model-write-1",
                requested_by_model="openai_session_model",
                condition="operator_requested_report",
                summary="PowerShell event observed.",
                severity="medium",
                facts=["PowerShell event 4104 appeared in the selected window."],
                evidence_refs=["evt-4104"],
                reader_bundle_refs=["reader-1"],
                language_task="format_facts",
            )

            result = writer.render_model_request(request)

            self.assertEqual(result["receipt"]["status"], "rendered")
            report = json.loads(Path(result["report_path"]).read_text(encoding="utf-8"))
            self.assertEqual(report["source_refs"], ["reader-1"])
            self.assertEqual(report["language_notes"], ["language_task=format_facts"])
            self.assertFalse(report["fact_authority"])

    def test_writer_rejects_invalid_request_without_report_file(self):
        with TemporaryDirectory() as tmpdir:
            writer = CentralWriter(tmpdir)
            request = build_writer_request(
                request_id="write-bad",
                requested_by_agent="agent.network",
                summary="Suspicious outbound connection observed.",
                severity="high",
                facts=["pwsh.exe connected to 203.0.113.10:443"],
                inferences=["probably malware"],
                evidence_refs=["evt-1"],
                recommended_actions=[],
            )

            with self.assertRaises(CentralContractError):
                writer.render_agent_request(request)

            self.assertEqual(list((Path(tmpdir) / "reports").glob("*.json")), [])


if __name__ == "__main__":
    unittest.main()
