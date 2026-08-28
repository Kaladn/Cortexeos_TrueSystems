import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class RecoveredSecurityBundleTests(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[2]
        self.bundle_root = self.repo_root / "securecore" / "live_agents"
        self.runner = self.bundle_root / "AGENTS" / "runner" / "securecore_agent_runner.py"

    def run_runner(self, *args):
        return subprocess.run(
            [sys.executable, str(self.runner), *args],
            cwd=str(self.bundle_root),
            capture_output=True,
            text=True,
            timeout=20,
        )

    def test_recovered_security_agents_are_listable(self):
        result = self.run_runner("list")

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        self.assertIn("recovered_security_snapshot", result.stdout)
        self.assertIn("recovered_security_firewall_enforcer", result.stdout)

    def test_agents_are_dry_run_callable_or_report_required_params(self):
        expectations = {
            "recovered_security_snapshot": 0,
            "recovered_security_firewall_enforcer": 0,
            "temporal_causality_log_checker": 3,
        }
        for agent_id, expected_code in expectations.items():
            with self.subTest(agent_id=agent_id):
                result = self.run_runner("run", agent_id, "--dry-run")
                self.assertEqual(result.returncode, expected_code, result.stderr or result.stdout)
                if expected_code == 3:
                    self.assertIn("Missing required agent parameters", result.stderr)

    def test_restricted_firewall_agent_is_dry_run_only_without_approval(self):
        result = self.run_runner("run", "recovered_security_firewall_enforcer", "--dry-run")

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["approved"])
        self.assertEqual(payload["risk"]["type"], "network_control")
        self.assertIn("-BlockEgyptIP", payload["would_execute"])
        self.assertIn("-BlockMeta", payload["would_execute"])

    def test_snapshot_agent_requires_exact_human_approval(self):
        result = self.run_runner("run", "recovered_security_snapshot")

        self.assertEqual(result.returncode, 2)
        self.assertIn("APPROVAL REQUIRED", result.stderr)
        self.assertIn("APPROVE recovered_security_snapshot", result.stderr)

    def test_runner_rejects_prompt_only_manifest(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            catalog = root / "agent_catalog.csv"
            agent_dir = root / "agents"
            agent_dir.mkdir()
            catalog.write_text(
                "operator_id,name,category,agent_tier,definition,input_shape,output_shape,"
                "assumptions_in,assumptions_out,side_effects,dependencies,statefulness,"
                "sync_mode,destruction_score,risk_type,risk_reason,requires_confirmation,"
                "sandbox_required,promotion_ready,contract_status,category_confidence,source_file\n"
                "bad_prompt,Bad Prompt,test,standalone,x,x,x,x,x,none,none,STATELESS,SYNC,"
                "0,test,forbidden,NO,NO,NO,BAD,LOW,bad\n",
                encoding="utf-8",
            )
            (agent_dir / "bad_prompt.agent.json").write_text(
                json.dumps(
                    {
                        "agent_id": "bad_prompt",
                        "id": "bad_prompt",
                        "catalog_id": "bad_prompt",
                        "name": "Bad Prompt",
                        "version": "1.0.0",
                        "runtime_language": "prompt",
                        "entrypoint": "none",
                        "entrypoint_hash": "sha256:" + ("a" * 64),
                        "allowed_reads": [],
                        "allowed_writes": [],
                        "requires_approval": False,
                        "approval_phrase": "",
                        "mutation_class": "read_only",
                        "dry_run_supported": False,
                        "log_stream": "agent_decision",
                        "test_command": ["none"],
                        "risk_tier": 0,
                        "prompt_only_allowed": True,
                        "required_params": [],
                        "default_out_dir": "runtime",
                        "command": ["echo", "bad"],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_runner(
                "--catalog",
                str(catalog),
                "--agent-dir",
                str(agent_dir),
                "run",
                "bad_prompt",
                "--dry-run",
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn("prompt-only", result.stderr)


if __name__ == "__main__":
    unittest.main()
