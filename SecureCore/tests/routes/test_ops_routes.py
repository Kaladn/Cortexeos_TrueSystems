import unittest

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from securecore.routes.ops import ops_bp


class _FakeAgent:
    stats = {"running": True, "ticks": 2}


class _FakeLogRouter:
    def stats(self):
        return {"health": {"records": 3}}


class OpsRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["JWT_SECRET_KEY"] = "test-secret-test-secret-test-secret"
        JWTManager(self.app)
        self.app.agents = {"watcher": _FakeAgent()}
        self.app.substrates = {}
        self.app.log_router = _FakeLogRouter()
        self.app.register_blueprint(ops_bp)
        self.client = self.app.test_client()
        with self.app.app_context():
            self.admin_token = create_access_token(identity="1", additional_claims={"role": "admin"})
            self.user_token = create_access_token(identity="2", additional_claims={"role": "user"})

    def test_ops_routes_require_admin(self):
        missing = self.client.get("/api/ops/dashboard")
        self.assertEqual(missing.status_code, 401)

        forbidden = self.client.get(
            "/api/ops/dashboard",
            headers={"Authorization": f"Bearer {self.user_token}"},
        )
        self.assertEqual(forbidden.status_code, 403)

    def test_dashboard_reports_state_without_authorizing_mutation(self):
        response = self.client.get(
            "/api/ops/dashboard",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["mutation_authorized"])
        self.assertFalse(payload["activation_authorized"])
        self.assertIn("watcher", payload["agents"])
        self.assertIn("health", payload["log_streams"])

    def test_catalog_exposes_factories_capabilities_and_agents(self):
        response = self.client.get(
            "/api/ops/catalog",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["activation_authorized"])
        self.assertIn("temporal.read", {row["capability_id"] for row in payload["capabilities"]})
        self.assertIn("logger", {row["kind"] for row in payload["factory_tools"]})
        self.assertIn("worker", {row["kind"] for row in payload["factory_tools"]})
        self.assertIn("agent", {row["kind"] for row in payload["factory_tools"]})
        self.assertTrue(all(row["forbidden"] for row in payload["factory_tools"]))

    def test_toolbox_exposes_workers_loggers_and_routes_without_activation(self):
        response = self.client.get(
            "/api/ops/toolbox",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["activation_authorized"])
        self.assertFalse(payload["mutation_authorized"])
        self.assertEqual(payload["ui_runtime"], "not_installed")
        self.assertEqual(payload["chat_runtime"], "not_installed")
        self.assertEqual(payload["memory_runtime"], "not_installed")
        self.assertTrue(payload["future_port"])
        self.assertIn("worker_heartbeat", {row["worker_id"] for row in payload["workers"]})
        self.assertIn("process_diff", {row["logger_id"] for row in payload["loggers"]})
        self.assertIn("AnchorWorks", {row["source_system"] for row in payload["loggers"]})
        self.assertIn("SecureCore", {row["source_system"] for row in payload["loggers"]})
        self.assertIn("TrueVision", {row["source_system"] for row in payload["loggers"]})
        self.assertIn("user_aura_shape", {row["logger_id"] for row in payload["loggers"]})
        self.assertTrue(all("user_logging_default" in row for row in payload["loggers"]))
        self.assertIn("runtime.start_baseline", {row["action_id"] for row in payload["actions"]})
        self.assertIn("/api/ops/toolbox", {row["path"] for row in payload["system_routes"]})
        self.assertNotIn("available_surfaces", payload)
        self.assertNotIn("surface_recipes", payload)

    def test_truevision_ops_tab_reports_sc_edition_without_capture_or_activation(self):
        response = self.client.get(
            "/api/ops/truevision",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["edition"], "truevision_sc_edition")
        self.assertFalse(payload["capture_authorized"])
        self.assertFalse(payload["activation_authorized"])
        self.assertFalse(payload["mutation_authorized"])
        self.assertIn("gpu_pre_render", payload["approved_capture_surfaces"])
        self.assertIn("raw_frames", payload["forbidden_source_truth"])
        self.assertIn("truevision.state_change", {row["sensor_id"] for row in payload["lanes"]})

    def test_warmup_route_runs_read_only_startup_checks(self):
        response = self.client.get(
            "/api/ops/warmup",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        report = payload["warmup"]
        self.assertEqual(report["kind"], "securecore_system_warmup_report")
        self.assertFalse(report["writes_performed"])
        self.assertFalse(report["agents_started"])
        self.assertFalse(report["loggers_started"])
        self.assertIn("test_inventory", report)

    def test_runtime_latest_handles_missing_runtime(self):
        response = self.client.get(
            "/api/ops/runtime/latest",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertIn("status", payload)
        self.assertIn("verify", payload)
        self.assertIn("watch", payload)
        self.assertFalse(payload["mutation_authorized"])

    def test_harness_routes_expose_snapshot_and_choice_without_execution(self):
        snapshot = self.client.get(
            "/api/ops/harness",
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(snapshot.status_code, 200)
        snapshot_payload = snapshot.get_json()
        self.assertFalse(snapshot_payload["harness"]["authority"]["llm_authority"])
        self.assertIn("capabilities", snapshot_payload["harness"])

        choice = self.client.post(
            "/api/ops/harness/choose",
            json={"request": "create a worker for incident review"},
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(choice.status_code, 200)
        choice_payload = choice.get_json()["choice"]
        self.assertEqual(choice_payload["target_kind"], "worker")
        self.assertFalse(choice_payload["runner_executable"])
        self.assertFalse(choice_payload["llm_authority"])


if __name__ == "__main__":
    unittest.main()
