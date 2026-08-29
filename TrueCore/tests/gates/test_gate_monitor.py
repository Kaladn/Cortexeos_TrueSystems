import unittest

from truecore.gates.monitor import build_gate_monitor_snapshot


class GateMonitorTests(unittest.TestCase):
    def test_gate_monitor_declares_stack_boundary_without_claiming_kernel_control(self):
        snapshot = build_gate_monitor_snapshot()

        self.assertEqual(snapshot["kind"], "truecore_gate_monitor")
        self.assertFalse(snapshot["kernel_firewall_claimed"])
        self.assertEqual(snapshot["authority_scope"], "cortex_stack_gate_host_monitor")
        self.assertIn("canonical_chat_intake", snapshot["gates"])
        self.assertIn("tool_execution", snapshot["gates"])
        self.assertIn("command_origin", snapshot["gates"])
        self.assertIn("agent_activation", snapshot["gates"])
        self.assertIn("memory_promotion", snapshot["gates"])
        self.assertIn("host_network_observation", snapshot["monitors"])

    def test_mutation_and_export_gates_require_policy_and_receipts(self):
        snapshot = build_gate_monitor_snapshot()
        gates = {gate["gate_id"]: gate for gate in snapshot["gate_rows"]}

        for gate_id in ("command_origin", "tool_execution", "agent_activation", "memory_promotion", "cross_system_export"):
            with self.subTest(gate_id=gate_id):
                self.assertTrue(gates[gate_id]["policy_required"])
                self.assertTrue(gates[gate_id]["receipt_required"])
        self.assertEqual(gates["command_origin"]["required_origin"], "local_hid_verified")


if __name__ == "__main__":
    unittest.main()
