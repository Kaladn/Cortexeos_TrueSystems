import json
import os
import tempfile
import unittest
from pathlib import Path

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from securecore.routes.ops import ops_bp


class AwayWatchReportRouteTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.runtime_root = Path(self.temp_dir.name) / "away_watch"
        reports_root = self.runtime_root / "reports" / "start"
        reports_root.mkdir(parents=True)
        self.report_path = reports_root / "away_watch_start_cycle_0001.json"
        self.report_path.write_text(
            json.dumps(
                {
                    "kind": "securecore_away_watch_start_snapshot",
                    "created_at_utc": "2026-06-03T11:27:49Z",
                    "metadata_only": True,
                    "no_actions": True,
                    "resources": {"cpu_percent": 7.0, "memory_percent": 31.9},
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        self.old_root = os.environ.get("SECURECORE_AWAY_WATCH_ROOT")
        os.environ["SECURECORE_AWAY_WATCH_ROOT"] = str(self.runtime_root)
        self.addCleanup(self._restore_env)

        self.app = Flask(__name__)
        self.app.config["JWT_SECRET_KEY"] = "test-secret-test-secret-test-secret"
        JWTManager(self.app)
        self.app.register_blueprint(ops_bp)
        self.client = self.app.test_client()
        with self.app.app_context():
            self.admin_token = create_access_token(identity="1", additional_claims={"role": "admin"})
            self.user_token = create_access_token(identity="2", additional_claims={"role": "user"})

    def _restore_env(self):
        if self.old_root is None:
            os.environ.pop("SECURECORE_AWAY_WATCH_ROOT", None)
        else:
            os.environ["SECURECORE_AWAY_WATCH_ROOT"] = self.old_root

    def _auth(self, token=None):
        return {"Authorization": f"Bearer {token or self.admin_token}"}

    def test_reports_list_requires_admin_and_returns_read_only_rows(self):
        missing = self.client.get("/api/ops/away-watch/reports")
        self.assertEqual(missing.status_code, 401)

        forbidden = self.client.get("/api/ops/away-watch/reports", headers=self._auth(self.user_token))
        self.assertEqual(forbidden.status_code, 403)

        response = self.client.get("/api/ops/away-watch/reports", headers=self._auth())

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["mutation_authorized"])
        self.assertEqual(payload["runtime_root"], str(self.runtime_root))
        self.assertIn("start/away_watch_start_cycle_0001.json", {row["report_id"] for row in payload["reports"]})
        row = payload["reports"][0]
        self.assertEqual(row["report_kind"], "start")
        self.assertEqual(row["content_type"], "application/json")

    def test_report_read_returns_text_without_mutation(self):
        response = self.client.get(
            "/api/ops/away-watch/report?report_id=start/away_watch_start_cycle_0001.json",
            headers=self._auth(),
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["mutation_authorized"])
        self.assertEqual(payload["report_id"], "start/away_watch_start_cycle_0001.json")
        self.assertEqual(payload["parsed"]["kind"], "securecore_away_watch_start_snapshot")
        self.assertIn('"metadata_only": true', payload["text"].lower())
        self.assertNotIn("discussion_prompt", payload)

    def test_report_read_rejects_path_traversal(self):
        response = self.client.get(
            "/api/ops/away-watch/report?report_id=../secrets.json",
            headers=self._auth(),
        )

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertIn("invalid report_id", payload["error"])


if __name__ == "__main__":
    unittest.main()
