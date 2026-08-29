import re
import unittest
import tempfile

from truecore.log_streams.schemas import health_entry
from truecore.substrates.operator import OperatorSubstrate
from truecore.time import UTC_TIMESTAMP_RE, utc_now


class TimeFormatTests(unittest.TestCase):
    def test_utc_now_uses_single_canonical_format(self):
        stamp = utc_now()

        self.assertRegex(stamp, UTC_TIMESTAMP_RE)
        self.assertRegex(stamp, re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$"))

    def test_log_schema_uses_canonical_timestamp(self):
        entry = health_entry("clock", "ok")

        self.assertRegex(entry["timestamp"], UTC_TIMESTAMP_RE)

    def test_substrate_record_uses_canonical_timestamp(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            substrate = OperatorSubstrate(tmpdir)
            record = substrate.record_action("clock_check", "time_format")

        self.assertRegex(record.timestamp, UTC_TIMESTAMP_RE)


if __name__ == "__main__":
    unittest.main()
