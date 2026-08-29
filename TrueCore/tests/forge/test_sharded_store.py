import tempfile
import unittest

from truecore.forge.sharded import ShardedForgeReader, ShardedForgeWriter


def _row(index: int, *, substrate: str = "sensor_network") -> dict:
    previous = "GENESIS" if index == 0 else f"chain_{index - 1}"
    return {
        "record_id": f"rec_{index}",
        "substrate": substrate,
        "sequence": index,
        "timestamp": "2026-05-17T10:00:00.000000Z",
        "cell_id": f"cell_{index % 2}",
        "record_type": "network_event",
        "payload": {"index": index, "remote_ip": f"203.0.113.{index}"},
        "chain_hash": f"chain_{index}",
        "previous_hash": previous,
    }


class ShardedForgeStoreTests(unittest.TestCase):
    def test_writer_splits_records_across_shards_and_binary_index_tails(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = ShardedForgeWriter(tmpdir, max_records_per_shard=2)

            metadata = [writer.append_dict(_row(index)) for index in range(5)]

            self.assertEqual([row["shard_id"] for row in metadata], [0, 0, 1, 1, 2])
            reader = ShardedForgeReader(tmpdir)
            records = list(reader.iter_records())
            self.assertEqual([record.record_id for record in records], [f"rec_{index}" for index in range(5)])
            tail = reader.tail(2)
            self.assertEqual([record.record_id for record in tail], ["rec_3", "rec_4"])
            self.assertTrue(reader.verify()["intact"])

    def test_reader_rebuilds_binary_index_from_shards(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = ShardedForgeWriter(tmpdir, max_records_per_shard=2)
            for index in range(3):
                writer.append_dict(_row(index))

            writer.index_path.unlink()

            reader = ShardedForgeReader(tmpdir)
            rebuilt = reader.rebuild_index()

            self.assertEqual(rebuilt["records_indexed"], 3)
            self.assertTrue(writer.index_path.exists())
            self.assertEqual([record.record_id for record in reader.tail(3)], ["rec_0", "rec_1", "rec_2"])

    def test_verify_reports_sequence_regression_across_shards(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            writer = ShardedForgeWriter(tmpdir, max_records_per_shard=1)
            writer.append_dict(_row(0))
            bad = _row(0)
            bad["record_id"] = "rec_bad"
            writer.append_dict(bad)

            result = ShardedForgeReader(tmpdir).verify()

            self.assertFalse(result["intact"])
            self.assertEqual(result["error"], "sequence regression")


if __name__ == "__main__":
    unittest.main()
