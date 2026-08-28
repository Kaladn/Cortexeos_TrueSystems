import unittest

from securecore.truevision.glyph_extender import (
    build_glyph_extender_summary,
    normalize_trim_pattern,
    pattern_hash,
)


class TrueVisionGlyphExtenderTests(unittest.TestCase):
    def test_glyph_extender_reports_known_unknown_and_anomaly_metadata_only(self):
        approved = [
            {
                "glyph_id": "glyph-exit-e",
                "trim_pattern": ["010", "111", "100", "111"],
                "promotion_status": "approved",
            }
        ]
        components = [
            {
                "component_id": "c1",
                "bounds": [0, 0, 3, 4],
                "pattern": ["010", "111", "100", "111"],
            },
            {
                "component_id": "c2",
                "bounds": [2, 0, 5, 4],
                "pattern": ["111", "001", "111"],
            },
        ]

        summary = build_glyph_extender_summary(approved, components)

        self.assertTrue(summary["enabled"])
        self.assertEqual(summary["known_pattern_count"], 1)
        self.assertEqual(summary["unknown_pattern_count"], 1)
        self.assertEqual(summary["blocking_anomaly_count"], 2)
        self.assertFalse(summary["text_reconstruction_allowed"])
        self.assertFalse(summary["raw_content_stored"])
        self.assertIn(pattern_hash(normalize_trim_pattern(["010", "111", "100", "111"])), summary["known_pattern_hashes"])
        self.assertNotIn("display", str(summary).casefold())
        self.assertNotIn("text", str(summary).casefold().replace("text_reconstruction_allowed", ""))

    def test_unapproved_patterns_are_not_known(self):
        approved = [
            {
                "glyph_id": "draft-only",
                "trim_pattern": ["1"],
                "promotion_status": "draft",
            }
        ]
        summary = build_glyph_extender_summary(
            approved,
            [{"component_id": "c1", "bounds": [0, 0, 1, 1], "pattern": ["1"]}],
        )

        self.assertEqual(summary["known_pattern_count"], 0)
        self.assertEqual(summary["unknown_pattern_count"], 1)


if __name__ == "__main__":
    unittest.main()
