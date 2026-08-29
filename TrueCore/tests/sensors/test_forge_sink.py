import tempfile
import unittest
from pathlib import Path

from truecore.forge.reader import ForgeReader
from truecore.sensors.contracts import build_sensor_event
from truecore.sensors.forge_sink import SensorForgeSink


class SensorForgeSinkTests(unittest.TestCase):
    def test_sink_writes_sensor_events_to_forge_destination(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            event = build_sensor_event(
                sensor_id="windows.eventlog.Security",
                sensor_class="eventlog",
                host_id="local",
                event_type="snapshot",
                sequence=0,
                cursor={"record_id": 1},
                subject={"event_id": 4625},
                payload={"event_id": 4625},
                previous_event_hash="GENESIS",
                confidence="observed",
                privacy_level="metadata",
                writer_id="forge.sensor.eventlog",
                batch_id="batch",
                batch_index=0,
            )
            sink = SensorForgeSink(Path(tmpdir))
            count = sink.write_events("sensor_eventlog", [event])

            verify = ForgeReader(Path(tmpdir) / "sensor_eventlog").verify()
            self.assertEqual(count, 1)
            self.assertTrue(verify["intact"])
            self.assertEqual(verify["total_records"], 1)

    def test_sink_resumes_sequence_and_hash_chain_across_calls(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            sink = SensorForgeSink(Path(tmpdir))
            for index in range(2):
                event = build_sensor_event(
                    sensor_id="windows.eventlog.Security",
                    sensor_class="eventlog",
                    host_id="local",
                    event_type="snapshot",
                    sequence=index,
                    cursor={"record_id": index},
                    subject={"event_id": 4625},
                    payload={"event_id": 4625, "index": index},
                    previous_event_hash="GENESIS",
                    confidence="observed",
                    privacy_level="metadata",
                    writer_id="forge.sensor.eventlog",
                    batch_id="batch",
                    batch_index=index,
                )
                self.assertEqual(sink.write_events("sensor_eventlog", [event]), 1)

            reader = ForgeReader(Path(tmpdir) / "sensor_eventlog")
            verify = reader.verify()
            self.assertTrue(verify["intact"])
            self.assertEqual(verify["total_records"], 2)
            self.assertEqual(verify["last_sequence"], 1)


if __name__ == "__main__":
    unittest.main()
