import unittest

from truecore.sentinels.contracts import (
    SentinelContractError,
    build_sentinel_result,
    validate_sentinel_manifest,
    validate_sentinel_result,
)


class SentinelContractTests(unittest.TestCase):
    def test_manifest_requires_observer_only_boundaries(self):
        manifest = {
            "sentinel_id": "forge_verify_sentinel",
            "version": "1.0",
            "entrypoint": "truecore.sentinels.forge_verify:run",
            "allowed_reads": ["forge://sensor_process"],
            "allowed_writes": ["receipt://sentinel/forge_verify"],
            "mutation_authority": False,
            "policy_approval_authority": False,
            "temporal_write_authority": False,
            "direct_user_alert_authority": False,
        }

        validated = validate_sentinel_manifest(manifest)

        self.assertEqual(validated["sentinel_id"], "forge_verify_sentinel")
        self.assertFalse(validated["mutation_authority"])

    def test_manifest_rejects_temporal_write_or_policy_authority(self):
        manifest = {
            "sentinel_id": "bad_sentinel",
            "version": "1.0",
            "entrypoint": "bad:run",
            "allowed_reads": [],
            "allowed_writes": [],
            "mutation_authority": False,
            "policy_approval_authority": False,
            "temporal_write_authority": True,
            "direct_user_alert_authority": False,
        }

        with self.assertRaises(SentinelContractError):
            validate_sentinel_manifest(manifest)

    def test_result_can_request_backend_engine_without_claiming_write_authority(self):
        result = build_sentinel_result(
            sentinel_id="system_trust_sentinel",
            status="alert",
            facts=["system trust is yellow"],
            evidence_refs=["internal_watch://trust/latest"],
            warnings=["policy check should run"],
            wake_requests=[
                {
                    "requested_engine": "policy_check_engine",
                    "reason": "policy receipt missing",
                    "evidence_refs": ["policy://missing"],
                }
            ],
        )

        validated = validate_sentinel_result(result)

        self.assertEqual(validated["status"], "alert")
        self.assertEqual(validated["engine_write_authorized"], False)
        self.assertEqual(validated["wake_requests"][0]["requested_engine"], "policy_check_engine")


if __name__ == "__main__":
    unittest.main()
