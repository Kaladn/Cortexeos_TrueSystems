import unittest

from truecore.tools.capabilities import (
    CapabilityRegistryError,
    build_default_capability_registry,
    validate_capability,
)


class CapabilityRegistryTests(unittest.TestCase):
    def test_default_registry_contains_read_analyze_write_policy_boundaries(self):
        registry = build_default_capability_registry()

        self.assertIn("temporal.read", registry)
        self.assertIn("forge.relationships.trace", registry)
        self.assertIn("central_writer.report_request", registry)
        self.assertIn("firewall.block_ip", registry)
        self.assertEqual(registry["temporal.read"]["authority_class"], "read")
        self.assertEqual(registry["central_writer.report_request"]["authority_class"], "write")
        self.assertEqual(registry["firewall.block_ip"]["authority_class"], "mutate")

    def test_mutation_capability_requires_approval_and_dry_run(self):
        capability = {
            "capability_id": "firewall.block_ip",
            "description": "Block outbound traffic to an IP.",
            "authority_class": "mutate",
            "risk_tier": 5,
            "requires_approval": True,
            "dry_run_required": True,
            "dependencies": ["windows.firewall"],
            "runner_target": "adapter.firewall",
            "central_writer_required": True,
        }

        self.assertEqual(validate_capability(capability)["risk_tier"], 5)

    def test_mutation_capability_without_approval_is_rejected(self):
        capability = {
            "capability_id": "bad.mutate",
            "description": "Bad mutation.",
            "authority_class": "mutate",
            "risk_tier": 5,
            "requires_approval": False,
            "dry_run_required": True,
            "dependencies": [],
            "runner_target": "adapter.bad",
            "central_writer_required": True,
        }

        with self.assertRaisesRegex(CapabilityRegistryError, "approval"):
            validate_capability(capability)

    def test_unknown_authority_class_is_rejected(self):
        capability = {
            "capability_id": "bad.unknown",
            "description": "Bad capability.",
            "authority_class": "magic",
            "risk_tier": 1,
            "requires_approval": False,
            "dry_run_required": False,
            "dependencies": [],
            "runner_target": "agent.bad",
            "central_writer_required": False,
        }

        with self.assertRaisesRegex(CapabilityRegistryError, "authority_class"):
            validate_capability(capability)


if __name__ == "__main__":
    unittest.main()
