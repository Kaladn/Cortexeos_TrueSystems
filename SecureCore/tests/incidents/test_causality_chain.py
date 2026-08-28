import unittest

from securecore.incidents.causality import CausalityError, build_causality_chain


class CausalityChainTests(unittest.TestCase):
    def test_causality_chain_preserves_sequence_hash_cursor_and_gap(self):
        events = [
            {
                "event_id": "evt-1",
                "observed_at_utc": "2026-05-23T10:00:00.000000Z",
                "sequence": 1,
                "cursor": {"record_id": 10},
                "payload_hash": "hash-1",
                "previous_event_hash": "GENESIS",
                "confidence": "observed",
            },
            {
                "event_id": "evt-2",
                "observed_at_utc": "2026-05-23T10:00:01.000000Z",
                "sequence": 2,
                "cursor": {"record_id": 11},
                "payload_hash": "hash-2",
                "previous_event_hash": "hash-1",
                "confidence": "observed",
                "parent_event_refs": ["evt-missing"],
            },
        ]

        chain = build_causality_chain(
            chain_id="chain-1",
            trigger_event_id="evt-2",
            fusion_block_id="fusion-1",
            events=events,
        )

        self.assertEqual(chain["trigger_event_id"], "evt-2")
        self.assertEqual(chain["fusion_block_id"], "fusion-1")
        self.assertEqual(chain["event_refs"], ["evt-1", "evt-2"])
        self.assertEqual(chain["sequence_range"], {"first": 1, "last": 2})
        self.assertEqual(chain["unresolved_gaps"], [{"missing_event_ref": "evt-missing", "referenced_by": "evt-2"}])
        self.assertEqual(chain["confidence"], "gap")

    def test_causality_chain_rejects_sequence_regression(self):
        with self.assertRaisesRegex(CausalityError, "monotonic"):
            build_causality_chain(
                chain_id="chain-1",
                trigger_event_id="evt-2",
                fusion_block_id="fusion-1",
                events=[
                    {
                        "event_id": "evt-1",
                        "observed_at_utc": "2026-05-23T10:00:00.000000Z",
                        "sequence": 2,
                        "cursor": {},
                        "payload_hash": "hash-1",
                        "previous_event_hash": "GENESIS",
                        "confidence": "observed",
                    },
                    {
                        "event_id": "evt-2",
                        "observed_at_utc": "2026-05-23T10:00:01.000000Z",
                        "sequence": 1,
                        "cursor": {},
                        "payload_hash": "hash-2",
                        "previous_event_hash": "hash-1",
                        "confidence": "observed",
                    },
                ],
            )


if __name__ == "__main__":
    unittest.main()
