import unittest

from truecore.harness.knowledge import TrueCoreHarness


class TrueCoreKnowledgeHarnessTests(unittest.TestCase):
    def test_snapshot_maps_truecore_without_authority(self):
        snapshot = TrueCoreHarness().snapshot()

        self.assertEqual(snapshot["kind"], "truecore_creator_security_harness")
        self.assertFalse(snapshot["authority"]["llm_authority"])
        self.assertFalse(snapshot["authority"]["execution_authority"])
        self.assertIn("agents", snapshot["systems"]["core"])
        self.assertIn("routes", snapshot["systems"]["core"])
        self.assertIn("logger", {row["kind"] for row in snapshot["factory_tools"]})

    def test_request_shape_selects_agent_or_logger_without_execution(self):
        harness = TrueCoreHarness()

        agent_choice = harness.choose("create an agent to review suspicious events")
        self.assertEqual(agent_choice["target_kind"], "agent")
        self.assertFalse(agent_choice["runner_executable"])
        self.assertFalse(agent_choice["llm_authority"])
        self.assertIn("temporal.read", agent_choice["needed_capabilities"])

        logger_choice = harness.choose("make a logger for window state changes")
        self.assertEqual(logger_choice["target_kind"], "logger")
        self.assertIn("temporal.read", logger_choice["needed_capabilities"])

    def test_containment_request_requires_policy_before_firewall(self):
        choice = TrueCoreHarness().choose("block a suspicious remote ip")

        self.assertEqual(choice["target_kind"], "containment")
        self.assertIn("firewall.block_ip", choice["needed_capabilities"])
        self.assertTrue(choice["policy_required_before_execution"])
        self.assertFalse(choice["runner_executable"])


if __name__ == "__main__":
    unittest.main()
