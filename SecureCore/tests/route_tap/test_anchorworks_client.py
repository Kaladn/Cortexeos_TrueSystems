import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from securecore.route_tap.anchorworks import build_sentence_plan
from securecore.route_tap.anchorworks_client import AnchorWorksClient, anchorworks_response_to_route_object


AW_RESPONSE = {
    "query": "What is Newton's first law of motion?",
    "query_anchors": ["what", "is", "newton's", "first", "law", "of", "motion", "?"],
    "represented_anchors": ["what", "is", "newton's", "first", "law", "of", "motion", "?"],
    "missing_anchors": [],
    "speech": "Newton points toward laboratory and mothers.",
    "evidence_mode": "counts",
    "engine": "clearspeak_counts",
    "answer_assembly": {
        "inference_plan": {
            "frame": {
                "activity": "count_question",
                "frame_type": "definition",
                "subject": "newton's first law motion",
                "fact_authority": False,
            },
            "accepted_candidates": [
                {
                    "symbol": "acceleration",
                    "anchor": "acceleration",
                    "status": "accepted",
                    "reason": "candidate_passed_inference_gates",
                    "support_score": 0.5115,
                    "candidate_rank": 2,
                    "score_parts": {
                        "question_fit": 0.75,
                        "rear_fit": 0.50,
                        "answer_fit": 0.25,
                        "forward_fit": 0.40,
                        "source_support": 0.60,
                    },
                    "cloud_support": {
                        "question": ["newton's", "law", "motion"],
                        "rear": ["force"],
                        "answer": [],
                        "forward": ["mass"],
                    },
                    "support_offsets": ["+1", "-2"],
                    "lookahead_score": 0.71,
                    "future_cloud": ["force", "mass", "motion"],
                    "pattern_health": "healthy",
                    "query_field_coherence": {"coherent": True, "reason": "candidate_attached_to_query_field"},
                },
                {
                    "symbol": "mass",
                    "anchor": "mass",
                    "status": "accepted",
                    "reason": "candidate_passed_inference_gates",
                    "support_score": 0.651,
                    "candidate_rank": 1,
                    "score_parts": {
                        "question_fit": 0.80,
                        "rear_fit": 0.55,
                        "answer_fit": 0.35,
                        "forward_fit": 0.50,
                        "source_support": 0.70,
                    },
                    "cloud_support": {
                        "question": ["newton's", "law"],
                        "rear": ["motion"],
                        "answer": [],
                        "forward": ["acceleration"],
                    },
                    "support_offsets": ["+2", "-1"],
                    "lookahead_score": 0.76,
                    "future_cloud": ["force", "acceleration", "object"],
                    "pattern_health": "healthy",
                    "query_field_coherence": {"coherent": True, "reason": "candidate_attached_to_query_field"},
                },
                {
                    "symbol": "second",
                    "anchor": "second",
                    "status": "accepted",
                    "reason": "candidate_passed_inference_gates",
                    "support_score": 0.62,
                    "candidate_rank": 3,
                    "score_parts": {
                        "question_fit": 0.40,
                        "rear_fit": 0.60,
                        "answer_fit": 0.20,
                        "forward_fit": 0.30,
                        "source_support": 0.65,
                    },
                    "cloud_support": {
                        "question": ["newton's", "law"],
                        "rear": ["first"],
                        "answer": [],
                        "forward": ["force"],
                    },
                    "support_offsets": ["+3"],
                    "lookahead_score": 0.64,
                    "future_cloud": ["law", "force", "mass"],
                    "pattern_health": "healthy",
                    "query_field_coherence": {"coherent": True, "reason": "candidate_attached_to_query_field"},
                },
                {
                    "symbol": "force",
                    "anchor": "force",
                    "status": "accepted",
                    "reason": "candidate_passed_inference_gates",
                    "support_score": 0.61,
                    "candidate_rank": 4,
                    "score_parts": {
                        "question_fit": 0.82,
                        "rear_fit": 0.57,
                        "answer_fit": 0.30,
                        "forward_fit": 0.52,
                        "source_support": 0.75,
                    },
                    "cloud_support": {
                        "question": ["newton's", "law", "motion"],
                        "rear": ["mass"],
                        "answer": [],
                        "forward": ["acceleration"],
                    },
                    "support_offsets": ["+1", "-1"],
                    "lookahead_score": 0.79,
                    "future_cloud": ["mass", "acceleration", "object"],
                    "pattern_health": "healthy",
                    "query_field_coherence": {"coherent": True, "reason": "candidate_attached_to_query_field"},
                },
                {
                    "symbol": "laws",
                    "anchor": "laws",
                    "status": "accepted",
                    "reason": "candidate_passed_inference_gates",
                    "support_score": 0.59,
                    "candidate_rank": 5,
                },
            ],
            "rejected_candidates": [
                {"anchor": "mothers", "reason": "off_frame", "observations": 7},
            ],
            "inference_steps": [
                {"rule_id": "R_FRAME_FROM_INPUT_SHAPE", "decision": "build_frame"}
            ],
            "fact_authority": False,
            "render_allowed": True,
        },
        "trace": [{"step": 1}],
        "contract": {"memory_writes": False, "counts_only_no_document_claims": True},
    },
}


class _Handler(BaseHTTPRequestHandler):
    request_body = {}

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        _Handler.request_body = json.loads(self.rfile.read(length).decode("utf-8"))
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(AW_RESPONSE).encode("utf-8"))

    def log_message(self, *_args):
        return


class AnchorWorksClientTests(unittest.TestCase):
    def test_converts_live_response_shape_to_route_pressure_object(self):
        route = anchorworks_response_to_route_object(AW_RESPONSE)

        self.assertEqual(route["kind"], "anchorworks_route_object")
        self.assertEqual(route["authority"], "route_pressure_only")
        self.assertEqual(route["mode"], "count_route")
        self.assertEqual(route["frame"]["frame_type"], "definition")
        self.assertEqual(route["candidate_paths"][0]["status"], "admitted")
        self.assertEqual(
            route["candidate_paths"][0]["summary"],
            "Newton's first law of motion is assembled through force, mass, and acceleration.",
        )
        self.assertEqual(route["candidate_paths"][0]["accepted_symbols"], ["mass", "acceleration", "force", "laws"])
        self.assertIn({"symbol": "second", "reason": "conflicting_ordinal_for_first_law_frame"}, route["candidate_paths"][0]["rejected_symbols"])
        self.assertIn({"symbol": "mothers", "reason": "off_frame"}, route["candidate_paths"][0]["rejected_symbols"])
        self.assertEqual(route["final_speech"], "Newton points toward laboratory and mothers.")
        self.assertEqual(
            route["candidate_paths"][0]["support"]["aw_accepted_symbols"],
            ["mass", "acceleration", "second", "force", "laws"],
        )
        self.assertEqual(
            route["candidate_paths"][0]["support"]["candidate_clouds"]["mass"]["cloud_support"]["question"],
            ["newton's", "law"],
        )
        self.assertEqual(
            route["candidate_paths"][0]["support"]["candidate_clouds"]["force"]["lookahead_score"],
            0.79,
        )
        self.assertIn("contract", route["active_cloud_trace"])

        plan = build_sentence_plan(route)
        self.assertEqual(
            plan["sentences"],
            ["Newton's first law of motion is assembled through force, mass, and acceleration."],
        )
        self.assertNotIn("second", " ".join(plan["sentences"]))
        self.assertNotIn("laboratory", " ".join(plan["sentences"]))
        self.assertNotIn("mothers", " ".join(plan["sentences"]))

    def test_client_posts_counts_query_and_returns_route_object(self):
        server = HTTPServer(("127.0.0.1", 0), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = AnchorWorksClient(f"http://127.0.0.1:{server.server_port}")
            route = client.query_count_route("What is Newton's first law of motion?", limit=6)
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

        self.assertEqual(_Handler.request_body["query"], "What is Newton's first law of motion?")
        self.assertEqual(_Handler.request_body["limit"], 6)
        self.assertEqual(_Handler.request_body["evidence_mode"], "counts")
        self.assertEqual(route["authority"], "route_pressure_only")
        self.assertEqual(route["candidate_paths"][0]["accepted_symbols"], ["mass", "acceleration", "force", "laws"])


if __name__ == "__main__":
    unittest.main()
