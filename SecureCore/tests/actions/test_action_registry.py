import unittest

from securecore.actions.registry import action_by_id, default_action_registry


class ActionRegistryTests(unittest.TestCase):
    def test_first_actions_are_declared_with_policy_and_receipts(self):
        actions = {row["action_id"]: row for row in default_action_registry()}

        self.assertIn("runtime.start_baseline", actions)
        self.assertIn("mapping.window.update", actions)
        self.assertIn("worker.diagnostics.inspect", actions)
        for action_id in ("runtime.start_baseline", "mapping.window.update"):
            action = actions[action_id]
            self.assertEqual(action["read_or_write"], "write")
            self.assertEqual(action["policy_gate"], "admin_required")
            self.assertTrue(action["dry_run_required"])
            self.assertTrue(action["receipt_target"])
            self.assertEqual(action["status"], "planned")

    def test_live_read_action_has_backend_and_validation_binding(self):
        action = action_by_id("worker.diagnostics.inspect")

        self.assertEqual(action["status"], "live")
        self.assertEqual(action["read_or_write"], "read")
        self.assertEqual(action["backend_route"], "/api/ops/toolbox")
        self.assertEqual(action["validation_route"], "/api/ops/toolbox")


if __name__ == "__main__":
    unittest.main()
