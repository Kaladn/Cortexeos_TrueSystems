import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "AGENTS" / "runner" / "truecore_agent_runner.py"
CATALOG = ROOT / "AGENTS" / "catalog" / "agent_catalog.csv"


def run_runner(*args):
    return subprocess.run(
        ["python", str(RUNNER), "--catalog", str(CATALOG), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


class TrueCoreAgentRunnerTests(unittest.TestCase):
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

    def test_creator_generated_worker_binds_source_and_runtime_separately(self):
        result = run_runner(
            "run",
            "repo_process_execution",
            "--param",
            'input_json={"kwargs":{"map_dir":"/tmp/map"}}',
            "--dry-run",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["agent_id"], "repo_process_execution")
        self.assertIn("truecore.live_agents.generated_runtime", payload["would_execute"])

if __name__ == "__main__":
    unittest.main()
