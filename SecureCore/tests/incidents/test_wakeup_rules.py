import unittest

from securecore.incidents.wakeup_rules import evaluate_wakeup_rules


class WakeupRulesTests(unittest.TestCase):
    def test_powershell_network_pair_wakes_investigation(self):
        rows = [
            {
                "event_id": "proc",
                "event_type": "diff",
                "observed_at_utc": "2026-05-16T19:00:00.000000Z",
                "payload": {"state": "started", "process": {"name": "pwsh.exe", "cmdline": ["pwsh", "-enc"]}},
            },
            {
                "event_id": "net",
                "event_type": "diff",
                "observed_at_utc": "2026-05-16T19:00:05.000000Z",
                "payload": {"state": "opened", "connection": {"remote": "57.144.174.141:443"}},
            },
        ]

        findings = evaluate_wakeup_rules(rows)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["rule_id"], "powershell_network_pair")
        self.assertTrue(findings[0]["operator_decision_required"])
        self.assertEqual(findings[0]["evidence_event_ids"], ["proc", "net"])


if __name__ == "__main__":
    unittest.main()
