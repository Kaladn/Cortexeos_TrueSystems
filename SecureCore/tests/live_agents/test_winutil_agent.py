import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class WinUtilAgentTests(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[2]
        self.bundle_root = self.repo_root / "securecore" / "live_agents"
        self.runner = self.bundle_root / "AGENTS" / "runner" / "securecore_agent_runner.py"
        self.script = self.bundle_root / "AGENTS" / "winutil" / "winutil_plugin_inventory.py"
        self.plugin_root = Path(r"C:\Users\mydyi\OneDrive\Documents\Desktop\plugins\winutil")

    def test_script_plan_only_classifies_winutil_tools_without_writing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"

            result = subprocess.run(
                [
                    sys.executable,
                    str(self.script),
                    "--plugin-root",
                    str(self.plugin_root),
                    "--out-dir",
                    str(out_dir),
                    "--plan-only",
                ],
                cwd=self.bundle_root,
                text=True,
                capture_output=True,
                timeout=20,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["dry_run"])
            self.assertFalse(payload["writes_performed"])
            self.assertFalse(payload["mutation_authorized"])
            self.assertGreaterEqual(payload["tool_count"], 9)
            self.assertIn("winutil_list_apps", payload["read_only_tools"])
            self.assertIn("winutil_apply_tweaks", payload["mutation_tools"])
            self.assertFalse(out_dir.exists())

    def test_runner_dry_run_exposes_winutil_inventory_command_without_execution(self):
        result = subprocess.run(
            [
                sys.executable,
                str(self.runner),
                "run",
                "winutil_plugin_inventory",
                "--dry-run",
            ],
            cwd=self.bundle_root,
            text=True,
            capture_output=True,
            timeout=20,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["agent_id"], "winutil_plugin_inventory")
        self.assertFalse(payload["approved"])
        self.assertIn("AGENTS/winutil/winutil_plugin_inventory.py", payload["would_execute"])
        self.assertIn("--plugin-root", payload["would_execute"])
        self.assertEqual(payload["risk"]["type"], "filesystem")
        self.assertTrue(payload["risk"]["confirmation"])

    def test_script_writes_metadata_manifest_and_receipt_only_when_not_plan_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"

            result = subprocess.run(
                [
                    sys.executable,
                    str(self.script),
                    "--plugin-root",
                    str(self.plugin_root),
                    "--out-dir",
                    str(out_dir),
                ],
                cwd=self.bundle_root,
                text=True,
                capture_output=True,
                timeout=20,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            manifest_path = Path(payload["manifest_path"])
            receipt_path = Path(payload["receipt_path"])
            self.assertTrue(manifest_path.exists())
            self.assertTrue(receipt_path.exists())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertFalse(manifest["raw_content_logged"])
            self.assertFalse(manifest["mutation_authorized"])
            self.assertFalse(receipt["winutil_operation_executed"])
            self.assertEqual(receipt["artifact_kind"], "winutil_inventory")


if __name__ == "__main__":
    unittest.main()
