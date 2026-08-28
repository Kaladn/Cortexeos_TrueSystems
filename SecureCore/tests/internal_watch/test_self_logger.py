import json
import tempfile
import unittest
from pathlib import Path

from securecore.internal_watch.self_logger import (
    InternalSelfLogger,
    build_self_audit_receipt,
    build_system_trust_receipt,
    validate_self_audit_receipt,
    validate_system_trust_receipt,
)
from securecore.time import is_canonical_utc_timestamp


class InternalSelfLoggerTests(unittest.TestCase):
    def test_self_audit_receipt_is_independent_and_non_authorizing(self):
        receipt = build_self_audit_receipt(
            host_id="local",
            observer_id="sc_internal_logger",
            checks=[
                {
                    "target": "forge",
                    "status": "ok",
                    "message": "forge chain verified",
                    "evidence_refs": ["forge://sensor_process#latest"],
                }
            ],
            human_verification={
                "signal": "hid_activity_present",
                "method": "keyboard_mouse_activity",
                "confidence": 0.72,
                "evidence_refs": ["hid://recent"],
            },
            machine_growth={
                "lesson_refs": ["lesson://self-audit/quiet-watchers"],
                "notes": ["watchers must not own recovery logic"],
            },
        )

        validated = validate_self_audit_receipt(receipt)

        self.assertEqual(validated["kind"], "securecore_internal_self_audit_receipt")
        self.assertTrue(is_canonical_utc_timestamp(validated["created_at_utc"]))
        self.assertEqual(validated["normal_logging_lane"], False)
        self.assertEqual(validated["mutation_authorized"], False)
        self.assertEqual(validated["policy_approval_authority"], False)
        self.assertEqual(validated["runtime_recovery_action_taken"], False)
        self.assertEqual(validated["retention_class"], "internal_self_audit_keep")
        self.assertEqual(validated["human_verification"]["final_security_decision"], False)
        self.assertEqual(validated["machine_growth"]["fact_authority"], False)

    def test_self_logger_writes_receipts_outside_operational_log_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            logger = InternalSelfLogger(receipt_root=root / "internal_watch")

            receipt = logger.write_receipt(
                host_id="local",
                checks=[
                    {
                        "target": "policy_gate",
                        "status": "alert",
                        "message": "policy receipt missing",
                        "evidence_refs": ["policy://missing-receipt"],
                    }
                ],
            )

            receipt_path = Path(receipt["receipt_path"])
            self.assertTrue(receipt_path.exists())
            self.assertIn("internal_watch", receipt_path.parts)
            self.assertNotIn("logs", receipt_path.parts)
            self.assertNotIn("forge", receipt_path.parts)
            saved = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], "alert")
            self.assertEqual(saved["anomaly_count"], 1)

    def test_self_audit_rejects_authority_and_normal_log_lane_pollution(self):
        receipt = build_self_audit_receipt(
            host_id="local",
            checks=[
                {
                    "target": "runner",
                    "status": "ok",
                    "message": "runner idle",
                    "evidence_refs": [],
                }
            ],
        )

        receipt["mutation_authorized"] = True
        with self.assertRaises(ValueError):
            validate_self_audit_receipt(receipt)

    def test_system_trust_receipt_compresses_posture_without_diary_logging(self):
        receipt = build_system_trust_receipt(
            host_id="local",
            checks=[
                {
                    "target": "forge",
                    "status": "ok",
                    "message": "forge sequence valid",
                    "evidence_refs": ["forge://verify/latest"],
                },
                {
                    "target": "policy",
                    "status": "alert",
                    "message": "approval receipt missing",
                    "evidence_refs": ["policy://approval/missing"],
                },
            ],
        )

        validated = validate_system_trust_receipt(receipt)

        self.assertEqual(validated["kind"], "securecore_system_trust_receipt")
        self.assertEqual(validated["status"], "yellow")
        self.assertEqual(validated["reason_count"], 1)
        self.assertEqual(validated["reasons"], ["policy: approval receipt missing"])
        self.assertEqual(validated["evidence_refs"], ["policy://approval/missing"])
        self.assertEqual(validated["full_diary"], False)
        self.assertEqual(validated["mutation_authorized"], False)
        self.assertEqual(validated["policy_approval_authority"], False)
        self.assertEqual(validated["runtime_recovery_action_taken"], False)

    def test_system_trust_receipt_rejects_unbounded_or_unknown_targets(self):
        with self.assertRaises(ValueError):
            build_system_trust_receipt(
                host_id="local",
                checks=[
                    {
                        "target": "chatty_internal_diary",
                        "status": "ok",
                        "message": "everything that happened",
                        "evidence_refs": [],
                    }
                ],
            )

        receipt = build_system_trust_receipt(
            host_id="local",
            checks=[
                {
                    "target": "watchers",
                    "status": "ok",
                    "message": "watchers quiet",
                    "evidence_refs": ["watcher://heartbeat"],
                }
            ],
        )
        receipt["full_diary"] = True
        with self.assertRaises(ValueError):
            validate_system_trust_receipt(receipt)

        receipt["mutation_authorized"] = False
        receipt["normal_logging_lane"] = True
        with self.assertRaises(ValueError):
            validate_self_audit_receipt(receipt)


if __name__ == "__main__":
    unittest.main()
