import json
import tempfile
import unittest
from pathlib import Path

from truecore.forge.reader import ForgeReader
from truecore.worker_feeds.heartbeat_worker import HeartbeatWorker
from truecore.worker_feeds.policy import WorkerFeedValidationError, validate_worker_packet
from truecore.worker_feeds.recorder import WorkerDiagnosticRecorder
from truecore.worker_feeds.registry import default_worker_registry


class WorkerDiagnosticFeedTests(unittest.TestCase):
    def test_heartbeat_worker_emits_valid_diagnostic_packet(self):
        packet = HeartbeatWorker().packet(state="running", progress=0.4, queue_depth=2)

        validate_worker_packet(packet)
        self.assertEqual(packet["worker_id"], "worker_heartbeat")
        self.assertEqual(packet["state"], "running")
        self.assertNotIn("keystrokes", packet)
        self.assertNotIn("screen", packet)

    def test_policy_rejects_user_replay_or_execution_fields(self):
        packet = HeartbeatWorker().packet()
        packet["screen"] = "raw replay data"

        with self.assertRaises(WorkerFeedValidationError):
            validate_worker_packet(packet)

        packet = HeartbeatWorker().packet()
        packet["command"] = "netsh advfirewall set allprofiles state off"
        with self.assertRaises(WorkerFeedValidationError):
            validate_worker_packet(packet)

    def test_recorder_writes_forge_record_and_receipt_without_security_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            recorder = WorkerDiagnosticRecorder(tmp)
            packet = HeartbeatWorker().packet(job_id="job_test", state="complete", progress=1.0)

            result = recorder.record(packet)

            self.assertTrue(result["ok"])
            receipt_path = Path(result["receipt_path"])
            self.assertTrue(receipt_path.exists())
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertFalse(receipt["raw_user_content_stored"])
            self.assertFalse(receipt["security_action_authorized"])

            reader = ForgeReader(Path(tmp) / "forge" / "worker_diagnostics")
            records = list(reader.iter_records())
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].record_type, "worker_diagnostic_packet")
            self.assertTrue(reader.verify()["intact"])

    def test_registry_installs_heartbeat_as_coded_worker_not_prompt_agent(self):
        workers = default_worker_registry()
        heartbeat = next(row for row in workers if row["worker_id"] == "worker_heartbeat")

        self.assertEqual(heartbeat["status"], "installed")
        self.assertFalse(heartbeat["prompt_only"])
        self.assertTrue(heartbeat["no_user_replay"])
        self.assertTrue(heartbeat["no_security_enforcement"])


if __name__ == "__main__":
    unittest.main()
