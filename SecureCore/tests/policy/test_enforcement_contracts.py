import unittest

from securecore.policy.contracts import (
    PolicyContractError,
    build_action_request,
    build_password_verified_action_decision,
    build_policy_decision,
    validate_action_request,
    validate_password_verified_action_decision,
    validate_policy_decision,
)


class PolicyEnforcementContractTests(unittest.TestCase):
    def test_action_request_requires_user_approval_before_adapter(self):
        request = build_action_request(
            request_id="act-1",
            requested_by="central_writer",
            action_type="firewall.block_ip",
            target={"ip": "203.0.113.10"},
            evidence_refs=["evt-1"],
            reason="Suspicious connection.",
            dry_run=True,
        )

        validated = validate_action_request(request)

        self.assertTrue(validated["requires_user_approval"])
        self.assertFalse(validated["adapter_execution_authorized"])
        self.assertTrue(validated["dry_run"])

    def test_action_request_rejects_pre_authorized_adapter_execution(self):
        request = build_action_request(
            request_id="act-2",
            requested_by="agent.network",
            action_type="process.kill",
            target={"pid": 123},
            evidence_refs=["evt-1"],
            reason="bad",
            dry_run=False,
        )
        request["adapter_execution_authorized"] = True

        with self.assertRaisesRegex(PolicyContractError, "adapter"):
            validate_action_request(request)

    def test_policy_decision_approval_requires_user_identity_and_phrase(self):
        decision = build_policy_decision(
            decision_id="dec-1",
            request_id="act-1",
            decided_by_user="lee",
            decision="approved",
            approval_phrase="APPROVE firewall.block_ip act-1",
        )

        validated = validate_policy_decision(decision)

        self.assertEqual(validated["decision"], "approved")
        self.assertTrue(validated["adapter_execution_authorized"])

    def test_policy_decision_rejects_ai_only_approval(self):
        with self.assertRaisesRegex(PolicyContractError, "user"):
            build_policy_decision(
                decision_id="dec-2",
                request_id="act-1",
                decided_by_user="",
                decision="approved",
                approval_phrase="APPROVE",
            )

    def test_password_verified_action_decision_requires_verification_and_cooldown(self):
        decision = build_password_verified_action_decision(
            decision_id="dec-3",
            request_id="act-3",
            decided_by_user="lee",
            action_type="firewall.block_ip",
            target={"ip": "203.0.113.10"},
            evidence_refs=["evt-1"],
            password_verified=True,
            password_verification_ref="auth:password:verified:dec-3",
            cooldown_seconds=10,
        )

        validated = validate_password_verified_action_decision(decision)

        self.assertEqual(validated["decision"], "approved")
        self.assertTrue(validated["adapter_execution_authorized"])
        self.assertTrue(validated["password_verified"])
        self.assertEqual(validated["cooldown_seconds"], 10)
        self.assertFalse(validated["permanent_action_authorized"])

    def test_password_verified_action_decision_rejects_missing_password_ref(self):
        with self.assertRaisesRegex(PolicyContractError, "password"):
            build_password_verified_action_decision(
                decision_id="dec-4",
                request_id="act-4",
                decided_by_user="lee",
                action_type="firewall.block_ip",
                target={"ip": "203.0.113.10"},
                evidence_refs=["evt-1"],
                password_verified=True,
                password_verification_ref="",
                cooldown_seconds=10,
            )

    def test_password_verified_action_decision_rejects_cooldown_below_ten_seconds(self):
        with self.assertRaisesRegex(PolicyContractError, "cooldown"):
            build_password_verified_action_decision(
                decision_id="dec-5",
                request_id="act-5",
                decided_by_user="lee",
                action_type="firewall.block_ip",
                target={"ip": "203.0.113.10"},
                evidence_refs=["evt-1"],
                password_verified=True,
                password_verification_ref="auth:password:verified:dec-5",
                cooldown_seconds=9,
            )


if __name__ == "__main__":
    unittest.main()
