import unittest

from truecore.policy.command_origin import validate_hid_command_origin


class HIDCommandOriginTests(unittest.TestCase):
    def test_command_origin_requires_recent_active_human_peripheral_activity(self):
        attestation = {
            "available": True,
            "active_human": True,
            "confidence": 0.72,
            "records_considered": 3,
            "keyboard_events": 4,
            "mouse_clicks": 1,
            "movement_detected": True,
            "session_locked": False,
            "foreground_app": "TrueCore",
        }

        result = validate_hid_command_origin("reaper_pause", attestation)

        self.assertTrue(result["accepted"])
        self.assertEqual(result["origin"], "local_hid_verified")
        self.assertFalse(result["remote_or_automated_origin_allowed"])

    def test_command_origin_rejects_missing_or_low_confidence_hid(self):
        with self.assertRaisesRegex(ValueError, "active local HID"):
            validate_hid_command_origin(
                "reaper_pause",
                {"available": False, "active_human": False, "confidence": 0.0, "records_considered": 0},
            )

        with self.assertRaisesRegex(ValueError, "confidence"):
            validate_hid_command_origin(
                "reaper_pause",
                {
                    "available": True,
                    "active_human": True,
                    "confidence": 0.2,
                    "records_considered": 1,
                    "keyboard_events": 1,
                    "session_locked": False,
                },
            )

    def test_command_origin_rejects_no_peripheral_activity_or_locked_session(self):
        base = {
            "available": True,
            "active_human": True,
            "confidence": 0.8,
            "records_considered": 2,
            "keyboard_events": 0,
            "mouse_clicks": 0,
            "movement_detected": False,
            "voice_detected": True,
            "session_locked": False,
        }
        with self.assertRaisesRegex(ValueError, "peripheral"):
            validate_hid_command_origin("reaper_pause", base)

        locked = dict(base, keyboard_events=2, session_locked=True)
        with self.assertRaisesRegex(ValueError, "locked"):
            validate_hid_command_origin("reaper_pause", locked)


if __name__ == "__main__":
    unittest.main()
