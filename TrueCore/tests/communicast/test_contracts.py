import unittest

from truecore.communicast.contracts import (
    CommunicastContractError,
    build_communicast_message,
    validate_communicast_message,
)


class CommunicastContractTests(unittest.TestCase):
    def test_anchorworks_can_publish_user_facing_speech(self):
        message = build_communicast_message(
            message_id="msg-aw-face-1",
            source_system="anchorworks",
            source_component="clearspeak.renderer",
            target_system="operator",
            topic="anchorworks.face.rendered",
            authority="aw_face",
            payload_schema="anchorworks.rendered_answer.v1",
            payload={"text": "Newton's first law describes inertia."},
            evidence_refs=["aw:count_route:newton-first-law"],
            trace_refs=["aw:trace:answer-path-1"],
        )

        validated = validate_communicast_message(message)

        self.assertEqual(validated["source_system"], "anchorworks")
        self.assertEqual(validated["authority"], "aw_face")

    def test_truecore_toolbox_result_can_target_anchorworks(self):
        message = build_communicast_message(
            message_id="msg-sc-toolbox-1",
            source_system="truecore",
            source_component="temporal_logger",
            target_system="anchorworks",
            topic="truecore.toolbox.result",
            authority="truecore_support",
            payload_schema="truecore.logger.summary.v1",
            payload={"healthy_loggers": 4, "written_streams": 4},
            evidence_refs=["forge:batch:logger-smoke-1"],
            trace_refs=["truecore:reader:logger-status-1"],
        )

        validated = validate_communicast_message(message)

        self.assertEqual(validated["target_system"], "anchorworks")
        self.assertFalse(validated["user_facing"])

    def test_truecore_cannot_claim_anchorworks_face_authority(self):
        message = build_communicast_message(
            message_id="msg-bad-face-1",
            source_system="truecore",
            source_component="central_writer",
            target_system="operator",
            topic="anchorworks.face.rendered",
            authority="aw_face",
            payload_schema="truecore.report.v1",
            payload={"text": "I am the face now."},
            evidence_refs=["forge:batch:1"],
            trace_refs=["truecore:writer:1"],
        )

        with self.assertRaises(CommunicastContractError):
            validate_communicast_message(message)

    def test_messages_need_receipts(self):
        message = build_communicast_message(
            message_id="msg-no-receipts-1",
            source_system="truecore",
            source_component="agent_runner",
            target_system="anchorworks",
            topic="truecore.agent.finding",
            authority="truecore_support",
            payload_schema="truecore.agent.finding.v1",
            payload={"finding": "no anomaly"},
            evidence_refs=[],
            trace_refs=[],
        )

        with self.assertRaises(CommunicastContractError):
            validate_communicast_message(message)


if __name__ == "__main__":
    unittest.main()
