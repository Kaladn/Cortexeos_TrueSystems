import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class DocsFolderToPdfAgentTests(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[2]
        self.bundle_root = self.repo_root / "securecore" / "live_agents"
        self.runner = self.bundle_root / "AGENTS" / "runner" / "securecore_agent_runner.py"
        self.script = self.bundle_root / "AGENTS" / "docs-to-pdf" / "docs_folder_to_pdf.py"

    def test_script_plan_only_reports_supported_inputs_without_writing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = _make_docs_fixture(Path(tmpdir) / "docs")
            out_dir = Path(tmpdir) / "out"

            result = subprocess.run(
                [
                    sys.executable,
                    str(self.script),
                    "--source-folder",
                    str(source),
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
            self.assertEqual(payload["supported_file_count"], 3)
            self.assertFalse(payload["writes_performed"])
            self.assertFalse(out_dir.exists())

    def test_runner_dry_run_exposes_docs_folder_to_pdf_command_without_execution(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = _make_docs_fixture(Path(tmpdir) / "docs")

            result = subprocess.run(
                [
                    sys.executable,
                    str(self.runner),
                    "run",
                    "docs_folder_to_pdf",
                    "--param",
                    f"source_folder={source}",
                    "--dry-run",
                ],
                cwd=self.bundle_root,
                text=True,
                capture_output=True,
                timeout=20,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["agent_id"], "docs_folder_to_pdf")
            self.assertFalse(payload["approved"])
            self.assertIn("--source-folder", payload["would_execute"])
            self.assertIn(str(source), payload["would_execute"])
            self.assertEqual(payload["risk"]["type"], "filesystem")
            self.assertTrue(payload["risk"]["confirmation"])

    def test_runner_requires_approval_before_pdf_write(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = _make_docs_fixture(Path(tmpdir) / "docs")

            result = subprocess.run(
                [
                    sys.executable,
                    str(self.runner),
                    "run",
                    "docs_folder_to_pdf",
                    "--param",
                    f"source_folder={source}",
                ],
                cwd=self.bundle_root,
                text=True,
                capture_output=True,
                timeout=20,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("APPROVE docs_folder_to_pdf", result.stderr)

    @unittest.skipUnless(importlib.util.find_spec("PIL"), "PIL is required for PDF rendering")
    def test_script_converts_docs_folder_to_pdf_with_manifest_and_receipt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            source = _make_docs_fixture(Path(tmpdir) / "docs")
            out_dir = Path(tmpdir) / "out"

            result = subprocess.run(
                [
                    sys.executable,
                    str(self.script),
                    "--source-folder",
                    str(source),
                    "--out-dir",
                    str(out_dir),
                ],
                cwd=self.bundle_root,
                text=True,
                capture_output=True,
                timeout=30,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            pdf_path = Path(payload["pdf_path"])
            manifest_path = Path(payload["manifest_path"])
            receipt_path = Path(payload["receipt_path"])
            self.assertTrue(pdf_path.exists())
            self.assertTrue(manifest_path.exists())
            self.assertTrue(receipt_path.exists())
            self.assertGreater(pdf_path.stat().st_size, 0)
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            self.assertEqual(receipt["source_folder"], str(source.resolve()))
            self.assertFalse(receipt["raw_content_logged"])
            self.assertEqual(receipt["artifact_kind"], "generated_pdf")


def _make_docs_fixture(root: Path) -> Path:
    root.mkdir(parents=True)
    (root / "A.md").write_text("# A\n\nMarkdown body.", encoding="utf-8")
    (root / "B.txt").write_text("Plain text body.", encoding="utf-8")
    if importlib.util.find_spec("PIL"):
        from PIL import Image

        Image.new("RGB", (32, 24), (20, 80, 120)).save(root / "C.png")
    else:
        (root / "C.png").write_bytes(b"not used in plan only")
    (root / "ignored.bin").write_bytes(b"ignored")
    return root


if __name__ == "__main__":
    unittest.main()
