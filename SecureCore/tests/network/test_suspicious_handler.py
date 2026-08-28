import json
import tempfile
import unittest
from pathlib import Path

from securecore.network.suspicious_handler import handle_suspicious_activity


class SuspiciousActivityHandlerTests(unittest.TestCase):
    def test_handler_builds_causality_before_sandbox_containment(self):
        events = [
            {
                "event_id": "evt-1",
                "observed_at_utc": "2026-05-23T10:00:00.000000Z",
                "sequence": 1,
                "cursor": {"sample": 1},
                "payload_hash": "hash-1",
                "previous_event_hash": "GENESIS",
                "confidence": "observed",
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            result = handle_suspicious_activity(
                output_root=Path(tmpdir),
                chain_id="chain-1",
                trigger_event_id="evt-1",
                fusion_block_id="fusion-1",
                events=events,
                remote_ip="93.184.216.34",
                actor_process="browser.exe",
                process_hash="process-hash",
                remote_endpoint="93.184.216.34:443",
                reason_code="unknown_remote_endpoint",
                firewall_adapter=None,
            )

            self.assertEqual(result["status"], "human_review_required")
            self.assertTrue((Path(tmpdir) / "causality_chain.json").exists())
            chain = json.loads((Path(tmpdir) / "causality_chain.json").read_text(encoding="utf-8"))
            self.assertEqual(chain["confidence"], "observed")
            review = json.loads((Path(tmpdir) / "human_review_required.json").read_text(encoding="utf-8"))
            self.assertEqual(review["status"], "human_review_required")


if __name__ == "__main__":
    unittest.main()
