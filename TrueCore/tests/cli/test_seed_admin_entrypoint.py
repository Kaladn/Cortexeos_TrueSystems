import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class SeedAdminEntrypointTests(unittest.TestCase):
    def test_seed_admin_direct_script_runs_from_repo_root(self):
        repo_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = os.environ.copy()
            env.update(
                {
                    "SECRET_KEY": "test-secret-key-test-secret-key-1234",
                    "JWT_SECRET_KEY": "test-jwt-secret-test-jwt-secret-1234",
                    "DATABASE_URL": f"sqlite:///{(tmp_path / 'truecore.db').as_posix()}",
                    "BIND_HOST": "127.0.0.1",
                    "BIND_PORT": "5057",
                    "HONEYPOT_ENABLED": "false",
                    "DATA_DIR": str(tmp_path / "data"),
                    "LOG_DIR": str(tmp_path / "logs"),
                    "TRUECORE_ADMIN_USER": "admin",
                    "TRUECORE_ADMIN_PASS": "test-admin-pass",
                }
            )
            env.pop("PYTHONPATH", None)

            result = subprocess.run(
                [sys.executable, "truecore/cli/seed_admin.py"],
                cwd=str(repo_root),
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
            )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("admin user", result.stdout.lower())

    def test_seed_admin_can_reset_existing_admin_password(self):
        repo_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env = os.environ.copy()
            env.update(
                {
                    "SECRET_KEY": "test-secret-key-test-secret-key-1234",
                    "JWT_SECRET_KEY": "test-jwt-secret-test-jwt-secret-1234",
                    "DATABASE_URL": f"sqlite:///{(tmp_path / 'truecore.db').as_posix()}",
                    "BIND_HOST": "127.0.0.1",
                    "BIND_PORT": "5057",
                    "HONEYPOT_ENABLED": "false",
                    "DATA_DIR": str(tmp_path / "data"),
                    "LOG_DIR": str(tmp_path / "logs"),
                    "TRUECORE_ADMIN_USER": "admin",
                    "TRUECORE_ADMIN_PASS": "first-pass",
                }
            )
            env.pop("PYTHONPATH", None)

            first = subprocess.run(
                [sys.executable, "truecore/cli/seed_admin.py"],
                cwd=str(repo_root),
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertEqual(first.returncode, 0, first.stderr or first.stdout)

            env["TRUECORE_ADMIN_PASS"] = "second-pass"
            env["TRUECORE_ADMIN_RESET"] = "true"
            second = subprocess.run(
                [sys.executable, "truecore/cli/seed_admin.py"],
                cwd=str(repo_root),
                env=env,
                capture_output=True,
                text=True,
                timeout=20,
            )

        self.assertEqual(second.returncode, 0, second.stderr or second.stdout)
        self.assertIn("reset admin user", second.stdout.lower())


if __name__ == "__main__":
    unittest.main()
