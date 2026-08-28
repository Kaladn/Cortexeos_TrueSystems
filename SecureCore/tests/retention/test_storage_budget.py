import json
import os
import tempfile
import unittest
from pathlib import Path

from securecore.retention.budget import StorageBudgetGuard, StorageBudgetPolicy


class StorageBudgetGuardTests(unittest.TestCase):
    def test_under_budget_writes_health_receipt_without_deleting(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            logs = root / "runtime" / "logs"
            logs.mkdir(parents=True)
            log_file = logs / "window.jsonl"
            log_file.write_bytes(b"a" * 128)

            guard = StorageBudgetGuard(
                policy=StorageBudgetPolicy(max_runtime_bytes=1024),
                managed_roots=[logs],
                receipt_root=root / "receipts",
            )

            report = guard.enforce()

            self.assertEqual(report["decision"], "within_budget")
            self.assertTrue(log_file.exists())
            self.assertEqual(report["deleted_file_count"], 0)
            self.assertTrue(Path(report["health_receipt_path"]).exists())

    def test_over_budget_deletes_oldest_eligible_runtime_detail_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            logs = root / "runtime" / "logs"
            receipts = root / "receipts"
            evidence = root / "evidence"
            logs.mkdir(parents=True)
            receipts.mkdir()
            evidence.mkdir()
            old_detail = logs / "old.detail"
            new_detail = logs / "new.detail"
            receipt = receipts / "keep.json"
            evidence_file = evidence / "case.bin"
            old_detail.write_bytes(b"o" * 800)
            new_detail.write_bytes(b"n" * 300)
            receipt.write_bytes(b"r" * 800)
            evidence_file.write_bytes(b"e" * 800)
            old_time = 1_700_000_000
            new_time = old_time + 100
            os.utime(old_detail, (old_time, old_time))
            os.utime(new_detail, (new_time, new_time))

            guard = StorageBudgetGuard(
                policy=StorageBudgetPolicy(max_runtime_bytes=512),
                managed_roots=[logs],
                protected_roots=[receipts, evidence],
                receipt_root=receipts,
            )

            report = guard.enforce()

            self.assertEqual(report["decision"], "pruned_to_budget")
            self.assertFalse(old_detail.exists())
            self.assertTrue(new_detail.exists())
            self.assertTrue(receipt.exists())
            self.assertTrue(evidence_file.exists())
            self.assertEqual(report["deleted_file_count"], 1)
            deletion = json.loads(Path(report["deletion_receipt_path"]).read_text(encoding="utf-8"))
            self.assertEqual(deletion["deleted_files"][0]["path"], str(old_detail))
            self.assertEqual(deletion["deleted_files"][0]["size"], 800)
            self.assertEqual(len(deletion["deleted_files"][0]["sha256_before_delete"]), 64)

    def test_foreign_truevision_state_in_securecore_root_is_flagged_not_deleted(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            logs = root / "runtime" / "logs"
            logs.mkdir(parents=True)
            tvcells = logs / "capture.tvcells"
            tvcells.write_bytes(b"heavy truevision state")

            guard = StorageBudgetGuard(
                policy=StorageBudgetPolicy(max_runtime_bytes=1),
                managed_roots=[logs],
                receipt_root=root / "receipts",
            )

            report = guard.enforce()

            self.assertEqual(report["decision"], "blocked_foreign_heavy_state")
            self.assertEqual(report["flags"][0]["reason"], "foreign_heavy_state_in_securecore_root")
            self.assertTrue(tvcells.exists())
            self.assertEqual(report["deleted_file_count"], 0)
            self.assertTrue(Path(report["violation_receipt_path"]).exists())

    def test_active_case_marker_skips_deletion(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            logs = root / "runtime" / "logs"
            logs.mkdir(parents=True)
            detail = logs / "case-active.detail"
            marker = logs / "case-active.detail.preserve.json"
            detail.write_bytes(b"d" * 1024)
            marker.write_text('{"reason": "active_case"}', encoding="utf-8")

            guard = StorageBudgetGuard(
                policy=StorageBudgetPolicy(max_runtime_bytes=1),
                managed_roots=[logs],
                receipt_root=root / "receipts",
            )

            report = guard.enforce()

            self.assertEqual(report["decision"], "over_budget_no_eligible_files")
            self.assertTrue(detail.exists())
            self.assertEqual(report["skipped_preserved_count"], 1)


if __name__ == "__main__":
    unittest.main()
