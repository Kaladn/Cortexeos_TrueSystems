import unittest

from securecore.network.containment import ContainmentContractError, build_trap_log_release_plan


class TrapLogReleasePlanTests(unittest.TestCase):
    def test_plan_requires_trap_log_release_without_permanent_action(self):
        plan = build_trap_log_release_plan(
            remote_ip="203.0.113.10",
            observed_event_refs=["forge:sensor_network:evt-1"],
            ttl_seconds=300,
        )

        self.assertEqual(plan["kind"], "securecore_trap_log_release_plan")
        self.assertEqual(plan["remote_ip"], "203.0.113.10")
        self.assertTrue(plan["trap_required"])
        self.assertTrue(plan["log_required"])
        self.assertTrue(plan["release_required"])
        self.assertTrue(plan["rollback_required"])
        self.assertFalse(plan["permanent_action_authorized"])
        self.assertFalse(plan["live_firewall_mutation_authorized"])
        self.assertIn("forge:sensor_network:evt-1", plan["evidence_refs"])
        self.assertIn("release_receipt", plan["required_receipts"])

    def test_plan_rejects_missing_evidence(self):
        with self.assertRaisesRegex(ContainmentContractError, "evidence"):
            build_trap_log_release_plan(remote_ip="203.0.113.10", observed_event_refs=[])

    def test_plan_rejects_invalid_ip(self):
        with self.assertRaisesRegex(ContainmentContractError, "remote_ip"):
            build_trap_log_release_plan(remote_ip="not an ip", observed_event_refs=["evt-1"])

    def test_plan_rejects_unbounded_ttl(self):
        with self.assertRaisesRegex(ContainmentContractError, "ttl"):
            build_trap_log_release_plan(remote_ip="203.0.113.10", observed_event_refs=["evt-1"], ttl_seconds=0)

        with self.assertRaisesRegex(ContainmentContractError, "ttl"):
            build_trap_log_release_plan(remote_ip="203.0.113.10", observed_event_refs=["evt-1"], ttl_seconds=86400)


if __name__ == "__main__":
    unittest.main()
