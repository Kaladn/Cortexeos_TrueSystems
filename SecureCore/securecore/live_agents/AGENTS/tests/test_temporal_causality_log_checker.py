import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
CHECKER = ROOT / "securecore" / "live_agents" / "AGENTS" / "temporal-causality" / "temporal_causality_log_checker.py"


def stable_hash(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def event_hash(record):
    material = {
        key: value
        for key, value in record.items()
        if key not in {"previous_event_hash"}
    }
    return stable_hash(material)


def make_record(event_id, sequence, previous_event_hash="GENESIS", **overrides):
    payload = overrides.pop("payload", {"message": event_id})
    record = {
        "event_id": event_id,
        "source_id": "sensor:file",
        "sensor_id": "filewatcher",
        "event_type": "file_movement",
        "observed_at_utc": f"2026-05-16T13:00:0{sequence}.000000Z",
        "sequence": sequence,
        "writer_id": "writer:file",
        "batch_id": "batch-1",
        "batch_index": sequence,
        "cursor": sequence,
        "payload_hash": stable_hash(payload),
        "previous_event_hash": previous_event_hash,
        "causal_parents": [],
        "correlation_id": "case-1",
        "lamport_counter": sequence + 1,
        "payload": payload,
    }
    record.update(overrides)
    return record


def run_checker(log_path, *extra_args):
    return subprocess.run(
        ["python", str(CHECKER), "--log-path", str(log_path), *extra_args],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


class TemporalCausalityLogCheckerTests(unittest.TestCase):
    def test_clean_log_is_replay_and_causality_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "events.jsonl"
            first = make_record("evt-1", 0)
            second = make_record(
                "evt-2",
                1,
                previous_event_hash=event_hash(first),
                causal_parents=["evt-1"],
            )
            log_path.write_text(
                "\n".join(json.dumps(row, sort_keys=True) for row in [first, second]) + "\n",
                encoding="utf-8",
            )

            result = run_checker(log_path)

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["summary"]["total_records"], 2)
            self.assertEqual(report["summary"]["violations_count"], 0)
            self.assertTrue(report["summary"]["replay_safe"])
            self.assertTrue(report["summary"]["causality_safe"])
            self.assertTrue(report["summary"]["forge_trust_safe"])

    def test_reports_hard_violations_without_repairing_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "events.jsonl"
            original = "keep-this-exact-content"
            bad_payload = {"message": "tampered"}
            bad = make_record(
                "evt-1",
                0,
                observed_at_utc="2026-05-16T13:00:00+00:00",
                payload=bad_payload,
                payload_hash="wrong",
                causal_parents=["missing-parent"],
            )
            log_path.write_text(json.dumps(bad, sort_keys=True) + "\n" + original, encoding="utf-8")

            result = run_checker(log_path)

            self.assertEqual(result.returncode, 1)
            report = json.loads(result.stdout)
            codes = {item["code"] for item in report["violations"]}
            self.assertIn("TIMESTAMP_FORMAT_INVALID", codes)
            self.assertIn("PAYLOAD_HASH_MISMATCH", codes)
            self.assertIn("MISSING_CAUSAL_PARENT", codes)
            self.assertFalse(report["summary"]["replay_safe"])
            self.assertFalse(report["summary"]["causality_safe"])
            self.assertIn(original, log_path.read_text(encoding="utf-8"))

    def test_breach_leadup_groups_preceding_events_by_correlation(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "events.jsonl"
            first = make_record("evt-process", 0, event_type="process_start")
            second = make_record(
                "evt-network",
                1,
                previous_event_hash=event_hash(first),
                event_type="network_flow",
                causal_parents=["evt-process"],
            )
            breach = make_record(
                "evt-breach",
                2,
                previous_event_hash=event_hash(second),
                event_type="approval_bypass",
                causal_parents=["evt-network"],
                payload={"severity": "emergency", "message": "approval bypass attempted"},
            )
            log_path.write_text(
                "\n".join(json.dumps(row, sort_keys=True) for row in [first, second, breach]) + "\n",
                encoding="utf-8",
            )

            result = run_checker(log_path, "--focus-event-type", "approval_bypass")

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["leadup"][0]["event_id"], "evt-breach")
            self.assertEqual(report["leadup"][0]["causal_chain"], ["evt-process", "evt-network", "evt-breach"])
            self.assertEqual(report["leadup"][0]["preceding_event_types"], ["process_start", "network_flow"])


if __name__ == "__main__":
    unittest.main()
