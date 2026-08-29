import unittest

from truecore.agent_comms.handoff import (
    AgentHandoffContractError,
    build_agent_handoff_packet,
    build_agent_handoff_reply,
    validate_agent_handoff_packet,
    validate_agent_handoff_reply,
)


class AgentHandoffContractTests(unittest.TestCase):
    def test_handoff_packet_requires_typed_work_not_free_chat(self):
        packet = build_agent_handoff_packet(
            handoff_id="handoff-1",
            task_id="task-1",
            from_agent="forge_verify_sentinel",
            to_agent="fusion_verify_sentinel",
            input_refs=["forge://sensor_process/0"],
            confirmed_facts=["Forge stream verified intact."],
            open_questions=["Does fusion cover this window?"],
            requested_capability="fusion.verify",
            receipt_refs=["receipt://forge/ok"],
            timeout_ms=30000,
            allowed_reply_kind="verification_result",
        )

        validated = validate_agent_handoff_packet(packet)

        self.assertEqual(validated["kind"], "truecore_agent_handoff_packet")
        self.assertEqual(validated["allowed_reply_kind"], "verification_result")
        self.assertFalse(validated["open_conversation"])
        self.assertFalse(validated["temporal_write_authorized"])
        self.assertFalse(validated["mutation_authorized"])
        self.assertFalse(validated["policy_approval_authority"])

    def test_handoff_packet_rejects_open_conversation_and_authority(self):
        packet = build_agent_handoff_packet(
            handoff_id="handoff-2",
            task_id="task-2",
            from_agent="a",
            to_agent="b",
            input_refs=["input://one"],
            confirmed_facts=["fact"],
            open_questions=["question"],
            requested_capability="verify",
            receipt_refs=["receipt://one"],
            timeout_ms=1000,
            allowed_reply_kind="verification_result",
        )

        packet["open_conversation"] = True
        with self.assertRaises(AgentHandoffContractError):
            validate_agent_handoff_packet(packet)

        packet["open_conversation"] = False
        packet["temporal_write_authorized"] = True
        with self.assertRaises(AgentHandoffContractError):
            validate_agent_handoff_packet(packet)

    def test_handoff_reply_must_match_allowed_kind_and_stay_observer_only(self):
        packet = build_agent_handoff_packet(
            handoff_id="handoff-3",
            task_id="task-3",
            from_agent="a",
            to_agent="b",
            input_refs=["input://one"],
            confirmed_facts=["fact"],
            open_questions=["question"],
            requested_capability="verify",
            receipt_refs=["receipt://one"],
            timeout_ms=1000,
            allowed_reply_kind="verification_result",
        )
        reply = build_agent_handoff_reply(
            reply_id="reply-1",
            handoff_id="handoff-3",
            from_agent="b",
            to_agent="a",
            reply_kind="verification_result",
            facts=["verified"],
            evidence_refs=["evidence://one"],
            receipt_refs=["receipt://two"],
            unresolved_questions=[],
        )

        validated = validate_agent_handoff_reply(reply, packet)

        self.assertEqual(validated["kind"], "truecore_agent_handoff_reply")
        self.assertFalse(validated["direct_user_alert_authority"])
        self.assertFalse(validated["engine_write_authorized"])

    def test_handoff_reply_rejects_wrong_kind_and_direct_alert(self):
        packet = build_agent_handoff_packet(
            handoff_id="handoff-4",
            task_id="task-4",
            from_agent="a",
            to_agent="b",
            input_refs=["input://one"],
            confirmed_facts=["fact"],
            open_questions=["question"],
            requested_capability="verify",
            receipt_refs=["receipt://one"],
            timeout_ms=1000,
            allowed_reply_kind="verification_result",
        )
        reply = build_agent_handoff_reply(
            reply_id="reply-2",
            handoff_id="handoff-4",
            from_agent="b",
            to_agent="a",
            reply_kind="verification_result",
            facts=["verified"],
            evidence_refs=["evidence://one"],
            receipt_refs=["receipt://two"],
            unresolved_questions=[],
        )

        reply["reply_kind"] = "freeform_chat"
        with self.assertRaises(AgentHandoffContractError):
            validate_agent_handoff_reply(reply, packet)

        reply["reply_kind"] = "verification_result"
        reply["direct_user_alert_authority"] = True
        with self.assertRaises(AgentHandoffContractError):
            validate_agent_handoff_reply(reply, packet)


if __name__ == "__main__":
    unittest.main()
