import unittest

from truecore.sensors.wakeup import WakeupContractError, build_wake_request, validate_wake_request


class WakeupContractTests(unittest.TestCase):
    def test_wake_request_names_suggested_agents_without_launching_them(self):
        request = build_wake_request(
            request_id="wake-1",
            source_reader="windows.network.diff",
            anomaly_type="powershell_network_pair",
            observed_object={"remote_ip": "203.0.113.10"},
            changed_fields=["remote", "process"],
            confidence=0.82,
            risk_seed=4,
            suggested_wake_agents=["network_domain_agent", "process_lineage_agent"],
            evidence_refs=["evt-1", "evt-2"],
        )

        validated = validate_wake_request(request)

        self.assertEqual(validated["kind"], "wake_request")
        self.assertFalse(validated["agents_launched"])
        self.assertTrue(validated["supervisor_required"])

    def test_wake_request_rejects_empty_evidence(self):
        request = build_wake_request(
            request_id="wake-2",
            source_reader="windows.network.diff",
            anomaly_type="unknown_ip",
            observed_object={"remote_ip": "203.0.113.10"},
            changed_fields=["remote"],
            confidence=0.5,
            risk_seed=2,
            suggested_wake_agents=["network_domain_agent"],
            evidence_refs=[],
        )

        with self.assertRaisesRegex(WakeupContractError, "evidence"):
            validate_wake_request(request)

    def test_wake_request_rejects_immediate_agent_launch(self):
        request = build_wake_request(
            request_id="wake-3",
            source_reader="windows.network.diff",
            anomaly_type="unknown_ip",
            observed_object={"remote_ip": "203.0.113.10"},
            changed_fields=["remote"],
            confidence=0.5,
            risk_seed=2,
            suggested_wake_agents=["network_domain_agent"],
            evidence_refs=["evt-1"],
        )
        request["agents_launched"] = True

        with self.assertRaisesRegex(WakeupContractError, "launch"):
            validate_wake_request(request)


if __name__ == "__main__":
    unittest.main()
