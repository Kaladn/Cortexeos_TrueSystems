import unittest

from securecore.tools.capabilities import build_default_capability_registry
from securecore.tools.picker import PickerDecisionError, pick_tool_chain


class SituationalToolPickerTests(unittest.TestCase):
    def setUp(self):
        self.registry = build_default_capability_registry()

    def test_unknown_capability_is_rejected(self):
        with self.assertRaisesRegex(PickerDecisionError, "unknown capability"):
            pick_tool_chain(
                interpreter_packet={"needed_capabilities": ["does.not.exist"]},
                registry=self.registry,
                available_dependencies=set(),
                approvals=set(),
            )

    def test_missing_dependency_blocks_chain(self):
        with self.assertRaisesRegex(PickerDecisionError, "missing dependency"):
            pick_tool_chain(
                interpreter_packet={"needed_capabilities": ["temporal.read"]},
                registry=self.registry,
                available_dependencies=set(),
                approvals=set(),
            )

    def test_interpreter_suggested_firewall_action_requires_policy_approval(self):
        with self.assertRaisesRegex(PickerDecisionError, "approval"):
            pick_tool_chain(
                interpreter_packet={"needed_capabilities": ["firewall.block_ip"]},
                registry=self.registry,
                available_dependencies={"windows.firewall"},
                approvals=set(),
            )

    def test_reader_and_writer_chain_is_selected_when_requirements_are_met(self):
        decision = pick_tool_chain(
            interpreter_packet={
                "needed_capabilities": [
                    "temporal.read",
                    "forge.relationships.trace",
                    "central_writer.report_request",
                ]
            },
            registry=self.registry,
            available_dependencies={"forge", "temporal_rows", "central_writer"},
            approvals=set(),
        )

        self.assertEqual(
            [step["capability_id"] for step in decision["chain"]],
            ["temporal.read", "forge.relationships.trace", "central_writer.report_request"],
        )
        self.assertFalse(decision["runner_executable"])
        self.assertTrue(decision["central_writer_required"])
        self.assertTrue(decision["interpreter_advisory_only"])


if __name__ == "__main__":
    unittest.main()
