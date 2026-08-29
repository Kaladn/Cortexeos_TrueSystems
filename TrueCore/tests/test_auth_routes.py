import unittest

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from truecore.routes.auth import auth_bp


class AuthRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["JWT_SECRET_KEY"] = "test-secret-test-secret-test-secret"
        JWTManager(self.app)
        self.app.register_blueprint(auth_bp)
        self.client = self.app.test_client()

    def test_session_requires_jwt(self):
        response = self.client.get("/api/session")
        self.assertEqual(response.status_code, 401)

    def test_session_returns_authenticated_runtime_status(self):
        with self.app.app_context():
            token = create_access_token(identity="7", additional_claims={"role": "admin"})

        response = self.client.get(
            "/api/session",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["authenticated"])
        self.assertEqual(payload["identity"], "7")
        self.assertEqual(payload["role"], "admin")
        self.assertEqual(payload["trust"]["state"], "AUTHENTICATED")
        self.assertEqual(payload["inference"]["status"], "awaiting_first_response")


if __name__ == "__main__":
    unittest.main()
