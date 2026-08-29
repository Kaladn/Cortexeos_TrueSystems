import json
import unittest

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from truecore.openai_session import OpenAIKeyVault
from truecore.routes.openai_session import openai_session_bp


class OpenAISessionRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["JWT_SECRET_KEY"] = "test-secret-test-secret-test-secret"
        JWTManager(self.app)
        self.app.openai_key_vault = OpenAIKeyVault(default_model="gpt-test")
        self.app.register_blueprint(openai_session_bp)
        self.client = self.app.test_client()

        with self.app.app_context():
            self.token = create_access_token(identity="USER1", additional_claims={"role": "admin"})

    def test_login_status_and_logout_never_return_api_key(self):
        login = self.client.post(
            "/api/openai/session/login",
            json={"api_key": "sk-test-secret", "model": "gpt-operator"},
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(login.status_code, 200)
        login_payload = login.get_json()
        self.assertTrue(login_payload["ok"])
        self.assertTrue(login_payload["openai_session"]["active"])
        self.assertNotIn("api_key", login_payload["openai_session"])
        self.assertNotIn("sk-test-secret", json.dumps(login_payload))

        status = self.client.get(
            "/api/openai/session/status",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(status.status_code, 200)
        self.assertTrue(status.get_json()["openai_session"]["active"])
        self.assertNotIn("sk-test-secret", json.dumps(status.get_json()))

        logout = self.client.post(
            "/api/openai/session/logout",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(logout.status_code, 200)
        self.assertFalse(logout.get_json()["openai_session"]["active"])
        self.assertIsNone(self.app.openai_key_vault.get_api_key("USER1"))

    def test_login_requires_api_key(self):
        resp = self.client.post(
            "/api/openai/session/login",
            json={"api_key": ""},
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(resp.status_code, 400)
        self.assertIn("api key", resp.get_json()["error"].lower())


if __name__ == "__main__":
    unittest.main()
