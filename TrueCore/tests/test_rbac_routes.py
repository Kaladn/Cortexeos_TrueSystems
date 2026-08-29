import unittest

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token

from truecore.core.db import db
from truecore.core.models import Role, User
from truecore.routes.rbac import rbac_bp


class RbacRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            {
                "JWT_SECRET_KEY": "test-secret-test-secret-test-secret",
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
                "SQLALCHEMY_TRACK_MODIFICATIONS": False,
            }
        )
        JWTManager(self.app)
        db.init_app(self.app)
        self.app.register_blueprint(rbac_bp)
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_bootstrap_status_reports_missing_admin(self):
        response = self.client.get("/api/rbac/bootstrap-status")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertFalse(payload["admin_role_exists"])
        self.assertFalse(payload["admin_user_exists"])

    def test_me_reports_role_and_permissions(self):
        with self.app.app_context():
            role = Role(name="admin")
            db.session.add(role)
            db.session.commit()
            user = User(username="admin", role_id=role.id)
            user.set_password("pw")
            db.session.add(user)
            db.session.commit()
            token = create_access_token(identity=str(user.id), additional_claims={"role": "admin"})

        response = self.client.get(
            "/api/rbac/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["role"], "admin")
        self.assertTrue(payload["permissions"]["control"])
        self.assertTrue(payload["permissions"]["rbac_admin"])


if __name__ == "__main__":
    unittest.main()
