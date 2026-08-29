import json
import tempfile
import unittest
from pathlib import Path

from truecore.forge.sharded import ShardedForgeWriter
from truecore.sentinels.forge_verify import run as run_forge_verify
from truecore.sentinels.fusion_verify import run as run_fusion_verify
from truecore.sentinels.system_trust import run as run_system_trust
from truecore.sensors.fusion import build_temporal_fusion_block
from truecore.sensors.fusion_store import FusionBlockStore


class BasicSentinelTests(unittest.TestCase):
    def test_forge_verify_sentinel_reports_intact_sharded_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            writer = ShardedForgeWriter(root / "forge" / "sensor_process", max_records_per_shard=2)
            writer.append_dict(_forge_row(0))
            writer.append_dict(_forge_row(1))

            result = run_forge_verify({"forge_root": str(root / "forge"), "streams": ["sensor_process"]})

            self.assertEqual(result["status"], "ok")
            self.assertIn("sensor_process intact", result["facts"])
            self.assertFalse(result["engine_write_authorized"])

    def test_fusion_verify_sentinel_reports_intact_fusion_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            store = FusionBlockStore(root / "fusion")
            block = build_temporal_fusion_block(
                block_id="fusion-1",
                source_id="smoke",
                window_start_utc="2026-05-17T10:00:00.000000Z",
                window_duration_ms=1000,
                events=[],
            )
            store.append(block)

            result = run_fusion_verify({"fusion_root": str(root / "fusion")})

            self.assertEqual(result["status"], "ok")
            self.assertIn("fusion verify intact", result["facts"])
            self.assertFalse(result["engine_write_authorized"])

    def test_system_trust_sentinel_writes_trust_receipt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            result = run_system_trust(
                {
                    "receipt_root": str(root / "internal_watch"),
                    "host_id": "local",
                    "checks": [
                        {
                            "target": "watchers",
                            "status": "ok",
                            "message": "watcher heartbeat present",
                            "evidence_refs": ["watcher://heartbeat"],
                        }
                    ],
                }
            )

            self.assertEqual(result["status"], "ok")
            receipt_path = Path(result["artifacts"][0]["path"])
            self.assertTrue(receipt_path.exists())
            saved = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["kind"], "truecore_system_trust_receipt")


def _forge_row(sequence: int) -> dict:
    previous_hash = "GENESIS" if sequence == 0 else f"chain_{sequence - 1}"
    return {
        "record_id": f"rec_{sequence}",
        "substrate": "sensor_process",
        "sequence": sequence,
        "timestamp": "2026-05-17T10:00:00.000000Z",
        "cell_id": f"cell_{sequence}",
        "record_type": "sensor_event",
        "payload": {"sequence": sequence},
        "chain_hash": f"chain_{sequence}",
        "previous_hash": previous_hash,
    }


if __name__ == "__main__":
    unittest.main()
