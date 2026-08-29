import os
import subprocess
import sys
import unittest
from pathlib import Path

from truecore.config import load_settings, validate_settings


class ConfigLoadTests(unittest.TestCase):
    def setUp(self):
        self.env_path = Path(__file__).resolve().parents[1] / "truecore" / ".env"
        self.original_env_text = self.env_path.read_text(encoding="utf-8") if self.env_path.exists() else None
        self.original_values = {
            key: os.environ.get(key)
            for key in ("SECRET_KEY", "JWT_SECRET_KEY", "DATABASE_URL", "BIND_HOST", "BIND_PORT")
        }
        for key in self.original_values:
            os.environ.pop(key, None)

    def tearDown(self):
        if self.original_env_text is None:
            try:
                self.env_path.unlink()
            except FileNotFoundError:
                pass
        else:
            self.env_path.write_text(self.original_env_text, encoding="utf-8")

        for key, value in self.original_values.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_load_settings_reads_truecore_env_file(self):
        self.env_path.write_text(
            "\n".join(
                [
                    "SECRET_KEY=truecore-test-secret",
                    "JWT_SECRET_KEY=truecore-test-jwt-secret",
                    "DATABASE_URL=sqlite:///truecore-test.db",
                    "BIND_HOST=127.0.0.1",
                    "BIND_PORT=5057",
                ]
            ),
            encoding="utf-8",
        )

        command = (
            "from truecore.config import load_settings, validate_settings; "
            "s=load_settings(); "
            "assert s['SECRET_KEY'] == 'truecore-test-secret', s; "
            "assert s['JWT_SECRET_KEY'] == 'truecore-test-jwt-secret', s; "
            "validate_settings(s)"
        )
        env = os.environ.copy()
        for key in self.original_values:
            env.pop(key, None)

        result = subprocess.run(
            [sys.executable, "-c", command],
            cwd=str(Path(__file__).resolve().parents[1]),
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
