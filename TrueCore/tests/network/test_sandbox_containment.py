import json
import tempfile
import unittest
from pathlib import Path

from truecore.network.sandbox_containment import (
    SandboxContainmentError,
    execute_sandboxed_containment,
)


class SandboxedContainmentTests(unittest.TestCase):
    def test_sandboxed_containment_writes_trap_block_release_review_receipts(self):
        actions = []

        class Firewall:
            def temporary_block(self, *, remote_ip, ttl_seconds, reason, evidence_refs):
                actions.append(("block", remote_ip, ttl_seconds, reason, tuple(evidence_refs)))
                return {"status": "blocked", "firewall_rule_id": "rule-1"}

            def release(self, *, firewall_rule_id, remote_ip):
                actions.append(("release", firewall_rule_id, remote_ip))
                return {"status": "released"}

        with tempfile.TemporaryDirectory() as tmpdir:
            result = execute_sandboxed_containment(
                output_root=Path(tmpdir),
                remote_ip="93.184.216.34",
                observed_event_refs=["forge:sensor_network:evt-1"],
                actor_process="browser.exe",
                process_hash="process-hash",
                remote_endpoint="93.184.216.34:443",
                fusion_block_ref="fusion:block:1",
                causality_chain_ref="causality:chain:1",
                reason_code="unknown_remote_endpoint",
                firewall_adapter=Firewall(),
                ttl_seconds=300,
            )

            self.assertEqual(result["status"], "human_review_required")
            self.assertEqual([action[0] for action in actions], ["block", "release"])
            for name in (
                "trap_receipt.json",
                "temporary_block_receipt.json",
                "release_receipt.json",
                "central_writer_forensics_request.json",
                "human_review_required.json",
            ):
                self.assertTrue((Path(tmpdir) / name).exists(), name)
            trap = json.loads((Path(tmpdir) / "trap_receipt.json").read_text(encoding="utf-8"))
            self.assertEqual(trap["inert_payload"]["executable"], False)
            self.assertEqual(trap["inert_payload"]["scope"], "truecore_local_sandbox_only")

    def test_sandboxed_containment_rejects_protected_endpoint(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(SandboxContainmentError, "protected"):
                execute_sandboxed_containment(
                    output_root=Path(tmpdir),
                    remote_ip="127.0.0.1",
                    observed_event_refs=["evt-1"],
                    actor_process="local.exe",
                    process_hash="hash",
                    remote_endpoint="127.0.0.1:5050",
                    fusion_block_ref="fusion:block:1",
                    causality_chain_ref="causality:chain:1",
                    reason_code="test",
                    firewall_adapter=None,
                )

    def test_sandboxed_containment_rejects_executable_decoy_payload(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with self.assertRaisesRegex(SandboxContainmentError, "inert"):
                execute_sandboxed_containment(
                    output_root=Path(tmpdir),
                    remote_ip="93.184.216.34",
                    observed_event_refs=["evt-1"],
                    actor_process="browser.exe",
                    process_hash="hash",
                    remote_endpoint="93.184.216.34:443",
                    fusion_block_ref="fusion:block:1",
                    causality_chain_ref="causality:chain:1",
                    reason_code="test",
                    firewall_adapter=None,
                    inert_payload={"bytes_b64": "TVqQAAMAAAAEAAAA", "executable": True},
                )


if __name__ == "__main__":
    unittest.main()
