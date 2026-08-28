import unittest

from securecore.package_api.policy import check_package_policy
from securecore.package_api.reports import TextFactsReportError, build_text_facts_report


class ReportsPolicyTests(unittest.TestCase):
    def test_text_facts_report_requires_evidence_for_facts(self):
        with self.assertRaises(TextFactsReportError):
            build_text_facts_report(
                title="Status",
                facts=["Fusion block is intact."],
                evidence_refs=[],
                warnings=[],
            )

    def test_text_facts_report_is_tight_and_facts_only(self):
        report = build_text_facts_report(
            title="Logger Health",
            facts=["Fusion block is intact."],
            evidence_refs=["fusion:block:abc"],
            warnings=["No eventlog source configured."],
        )

        self.assertEqual(report["kind"], "securecore_text_facts_report")
        self.assertEqual(report["facts"], ["Fusion block is intact."])
        self.assertEqual(report["evidence_refs"], ["fusion:block:abc"])
        self.assertFalse(report["action_authorized"])
        self.assertFalse(report["model_authority"])

    def test_policy_allows_anchorworks_read_routes(self):
        result = check_package_policy(caller="anchorworks", route="fusion.latest")

        self.assertTrue(result["allowed"])
        self.assertFalse(result["approval_required"])

    def test_policy_requires_approval_for_action_routes(self):
        result = check_package_policy(caller="anchorworks", route="firewall.block")

        self.assertFalse(result["allowed"])
        self.assertTrue(result["approval_required"])
        self.assertIn("not callable through package API", result["reason"])

    def test_policy_rejects_rogue_caller(self):
        result = check_package_policy(caller="rogue", route="status.summary")

        self.assertFalse(result["allowed"])
        self.assertFalse(result["approval_required"])
        self.assertIn("unknown caller", result["reason"])


if __name__ == "__main__":
    unittest.main()
