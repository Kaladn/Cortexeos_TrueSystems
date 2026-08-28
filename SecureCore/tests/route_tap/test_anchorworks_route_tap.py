import unittest
from pathlib import Path

from securecore.central.contracts import validate_model_writer_report_request
from securecore.route_tap.anchorworks import (
    RouteTapError,
    build_sentence_plan,
    build_writer_request_from_sentence_plan,
    validate_anchorworks_route_object,
)


def _route_object(**overrides):
    row = {
        "schema_version": 1,
        "kind": "anchorworks_route_object",
        "route_id": "aw-route-001",
        "question": "why worry about laws of physics",
        "mode": "counts_only",
        "authority": "route_pressure_only",
        "represented_symbols": ["sym_laws", "sym_physics"],
        "candidate_paths": [
            {
                "path_id": "path-good",
                "status": "admitted",
                "frame": "why_causal",
                "summary": "laws of physics support prediction and safety",
                "accepted_symbols": ["sym_laws", "sym_physics", "sym_prediction", "sym_safety"],
                "rejected_symbols": [
                    {"symbol": "sym_mothers", "reason": "off_frame"},
                    {"symbol": "sym_gnp", "reason": "off_domain"},
                ],
                "evidence_refs": ["awsc://counts/sym_laws", "awsc://counts/sym_physics"],
                "support": {
                    "count_support": 0.82,
                    "lookahead_health": 0.77,
                    "frame_fit": 0.91,
                },
            }
        ],
        "final_speech": "The active path connects mothers and physics.",
    }
    row.update(overrides)
    return row


def _newton_first_law_route_object():
    return {
        "schema_version": 1,
        "kind": "anchorworks_route_object",
        "route_id": "aw-newton-first-law-001",
        "question": "What is Newton's first law of motion?",
        "mode": "count_route",
        "authority": "route_pressure_only",
        "represented_symbols": [
            "sym_newton",
            "sym_first",
            "sym_law",
            "sym_motion",
            "sym_object",
            "sym_rest",
            "sym_uniform_motion",
            "sym_external_force",
        ],
        "missing_symbols": [],
        "frame": {
            "activity": "educational_question",
            "frame_type": "definition_explanation",
            "stable_subject": "Newton's first law of motion",
        },
        "active_cloud_trace": {
            "q": ["sym_newton", "sym_first", "sym_law", "sym_motion"],
            "r": ["sym_object", "sym_rest", "sym_uniform_motion"],
            "a": [],
            "f": ["sym_external_force"],
            "top_k": 6,
        },
        "candidate_paths": [
            {
                "path_id": "path-newton-first-law",
                "status": "admitted",
                "frame": "definition_explanation",
                "summary": "Newton's first law states that an object remains at rest or in uniform motion unless acted upon by an external force.",
                "accepted_symbols": [
                    "sym_newton",
                    "sym_first",
                    "sym_law",
                    "sym_object",
                    "sym_rest",
                    "sym_uniform_motion",
                    "sym_external_force",
                ],
                "rejected_symbols": [
                    {"symbol": "sym_mothers", "reason": "off_frame"},
                    {"symbol": "sym_gnp", "reason": "off_domain"},
                    {"symbol": "sym_laboratory", "reason": "weak_subject_fit"},
                ],
                "evidence_refs": [
                    "awsc://counts/sym_newton",
                    "awsc://counts/sym_first_law_motion",
                    "aw_phrase://newtons_first_law_of_motion",
                ],
                "support": {
                    "count_support": 0.93,
                    "lookahead_health": 0.88,
                    "frame_fit": 0.96,
                    "phrase_authority": 1.0,
                    "grammar_template": "definition_explanation_v1",
                },
            }
        ],
        "final_speech": "Newton points toward laboratory and mothers.",
    }


class AnchorWorksRouteTapTests(unittest.TestCase):
    def test_route_tap_code_does_not_import_or_write_anchorworks(self):
        source = Path("securecore/route_tap/anchorworks.py").read_text(encoding="utf-8")
        lowered = source.lower()

        self.assertNotIn("import AnchorWorks", source)
        self.assertNotIn("from AnchorWorks", source)
        self.assertNotIn("AnchorWorks_Clean_Runtime", source)
        self.assertNotIn("anchorworks.write", lowered)
        self.assertNotIn('writes_allowed": true', lowered)
        self.assertNotIn("open(", source)
        self.assertNotIn("write_text", source)
        self.assertNotIn("write_bytes", source)

    def test_validates_route_object_as_route_pressure_not_truth_authority(self):
        validated = validate_anchorworks_route_object(_route_object())

        self.assertEqual(validated["authority"], "route_pressure_only")
        self.assertEqual(validated["candidate_paths"][0]["status"], "admitted")

    def test_rejects_anchorworks_final_speech_as_input_authority(self):
        route = _route_object(authority="final_speech_authority")

        with self.assertRaisesRegex(RouteTapError, "route_pressure_only"):
            validate_anchorworks_route_object(route)

    def test_builds_sentence_plan_from_admitted_trace_not_raw_speech(self):
        plan = build_sentence_plan(_route_object())

        self.assertEqual(plan["kind"], "securecore_sentence_plan")
        self.assertEqual(plan["source_route_id"], "aw-route-001")
        self.assertEqual(plan["sentences"], ["laws of physics support prediction and safety"])
        self.assertIn("sym_mothers: off_frame", plan["rejected_candidate_notes"])
        self.assertNotIn("mothers and physics", " ".join(plan["sentences"]))
        self.assertFalse(plan["fact_authority"])
        self.assertFalse(plan["enforcement_authorized"])

    def test_poisoned_final_speech_never_enters_sentence_plan(self):
        route = _route_object(
            final_speech="mothers, gnp, foreign, laboratory, points toward physics"
        )

        plan = build_sentence_plan(route)
        rendered = " ".join(plan["sentences"])

        self.assertEqual(rendered, "laws of physics support prediction and safety")
        for poison in ("mothers", "gnp", "foreign", "laboratory", "points toward"):
            self.assertNotIn(poison, rendered)

    def test_rejects_plan_when_no_admitted_candidate_has_evidence(self):
        route = _route_object(
            candidate_paths=[
                {
                    "path_id": "path-empty",
                    "status": "admitted",
                    "frame": "why_causal",
                    "summary": "unsupported claim",
                    "accepted_symbols": ["sym_laws"],
                    "rejected_symbols": [],
                    "evidence_refs": [],
                    "support": {"count_support": 0.1},
                }
            ]
        )

        with self.assertRaisesRegex(RouteTapError, "evidence_refs"):
            build_sentence_plan(route)

    def test_converts_sentence_plan_to_facts_only_writer_request(self):
        plan = build_sentence_plan(_route_object())
        request = build_writer_request_from_sentence_plan(
            plan,
            request_id="aw-route-report-001",
            requested_by_model="securecore.route_tap.anchorworks",
            severity="info",
        )

        validated = validate_model_writer_report_request(request)
        self.assertEqual(validated["kind"], "central_model_writer_report_request")
        self.assertEqual(validated["condition"], "chain_recipe_report_step")
        self.assertEqual(validated["language_task"], "format_facts")
        self.assertEqual(validated["facts"], ["laws of physics support prediction and safety"])
        self.assertFalse(validated["fact_authority"])
        self.assertFalse(validated["enforcement_authorized"])

    def test_newton_first_law_count_route_round_trip(self):
        plan = build_sentence_plan(_newton_first_law_route_object())

        self.assertEqual(plan["source_route_id"], "aw-newton-first-law-001")
        self.assertEqual(
            plan["sentences"],
            [
                "Newton's first law states that an object remains at rest or in uniform motion unless acted upon by an external force."
            ],
        )
        self.assertIn("sym_mothers: off_frame", plan["rejected_candidate_notes"])
        self.assertIn("sym_gnp: off_domain", plan["rejected_candidate_notes"])
        self.assertIn("awsc://counts/sym_first_law_motion", plan["evidence_refs"])
        self.assertIn("aw_phrase://newtons_first_law_of_motion", plan["evidence_refs"])
        self.assertNotIn("points toward", " ".join(plan["sentences"]))
        self.assertNotIn("laboratory", " ".join(plan["sentences"]))

        request = build_writer_request_from_sentence_plan(
            plan,
            request_id="newton-first-law-route-report",
            requested_by_model="securecore.route_tap.anchorworks",
            severity="info",
        )
        validated = validate_model_writer_report_request(request)

        self.assertEqual(validated["facts"], plan["sentences"])
        self.assertEqual(validated["reader_bundle_refs"], ["anchorworks_route:aw-newton-first-law-001"])
        self.assertFalse(validated["fact_authority"])
        self.assertFalse(validated["enforcement_authorized"])


if __name__ == "__main__":
    unittest.main()
