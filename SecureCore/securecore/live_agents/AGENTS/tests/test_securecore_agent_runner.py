import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "AGENTS" / "runner" / "securecore_agent_runner.py"
CATALOG = ROOT / "AGENTS" / "catalog" / "agent_catalog.csv"


def run_runner(*args):
    return subprocess.run(
        ["python", str(RUNNER), "--catalog", str(CATALOG), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


class SecureCoreAgentRunnerTests(unittest.TestCase):
    def test_report_agent_requires_approval_before_disk_write(self):
        result = run_runner("run", "recovered_security_snapshot")

        self.assertEqual(result.returncode, 2)
        self.assertIn("APPROVAL REQUIRED", result.stderr)
        self.assertIn("APPROVE recovered_security_snapshot", result.stderr)

    def test_enforcement_agent_requires_exact_approval_phrase(self):
        result = run_runner(
            "run",
            "recovered_security_firewall_enforcer",
            "--approve",
            "yes",
        )

        self.assertEqual(result.returncode, 2)
        self.assertIn("APPROVAL REQUIRED", result.stderr)
        self.assertIn("APPROVE recovered_security_firewall_enforcer", result.stderr)

    def test_dry_run_outputs_command_without_execution(self):
        result = run_runner(
            "run",
            "recovered_security_snapshot",
            "--dry-run",
        )

        self.assertEqual(result.returncode, 0)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["agent_id"], "recovered_security_snapshot")
        self.assertEqual(payload["would_execute"][0], "powershell")
        self.assertIn("-File", payload["would_execute"])

    def test_dry_run_accepts_template_params(self):
        result = run_runner(
            "run",
            "temporal_causality_log_checker",
            "--param",
            "log_path=sample.jsonl",
            "--dry-run",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["agent_id"], "temporal_causality_log_checker")
        self.assertIn("sample.jsonl", payload["would_execute"])

if __name__ == "__main__":
    unittest.main()
