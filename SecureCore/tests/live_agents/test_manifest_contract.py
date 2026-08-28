import json
import tempfile
import unittest
from pathlib import Path

from securecore.live_agents.manifest import (
    AgentManifestError,
    load_agent_manifest,
    validate_agent_manifest,
)


class AgentManifestContractTests(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[2]
        self.agent_dir = self.repo_root / "securecore" / "live_agents" / "AGENTS" / "agents"

    def test_valid_manifest_declares_executable_contract(self):
        manifest = _valid_manifest()

        validated = validate_agent_manifest(manifest)

        self.assertEqual(validated["agent_id"], "sample_agent")
        self.assertEqual(validated["runtime_language"], "python")

    def test_prompt_only_production_agent_is_rejected(self):
        manifest = _valid_manifest()
        manifest["runtime_language"] = "prompt"
        manifest["prompt_only_allowed"] = True

        with self.assertRaisesRegex(AgentManifestError, "prompt-only"):
            validate_agent_manifest(manifest)

    def test_unknown_runtime_language_is_rejected(self):
        manifest = _valid_manifest()
        manifest["runtime_language"] = "brainwave"

        with self.assertRaisesRegex(AgentManifestError, "runtime_language"):
            validate_agent_manifest(manifest)

    def test_all_repo_agent_specs_validate(self):
        for spec_path in self.agent_dir.glob("*.agent.json"):
            with self.subTest(spec_path=spec_path.name):
                manifest = load_agent_manifest(spec_path)
                validate_agent_manifest(manifest)

    def test_all_repo_agent_specs_declare_required_params(self):
        for spec_path in self.agent_dir.glob("*.agent.json"):
            with self.subTest(spec_path=spec_path.name):
                manifest = load_agent_manifest(spec_path)
                self.assertIn("required_params", manifest)
                self.assertIsInstance(manifest["required_params"], list)

    def test_load_manifest_rejects_missing_required_field(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad.agent.json"
            payload = _valid_manifest()
            payload.pop("entrypoint_hash")
            path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(AgentManifestError, "entrypoint_hash"):
                load_agent_manifest(path)


def _valid_manifest():
    return {
        "agent_id": "sample_agent",
        "id": "sample_agent",
        "catalog_id": "sample_agent",
        "name": "Sample Agent",
        "version": "1.0.0",
        "runtime_language": "python",
        "entrypoint": "AGENTS/sample/sample.py",
        "entrypoint_hash": "sha256:" + ("a" * 64),
        "allowed_reads": ["AGENTS/sample"],
        "allowed_writes": ["AGENTS/sample/runtime"],
        "requires_approval": False,
        "approval_phrase": "",
        "mutation_class": "read_only",
        "dry_run_supported": True,
        "log_stream": "agent_decision",
        "test_command": ["python", "-m", "unittest", "tests.live_agents.test_manifest_contract"],
        "risk_tier": 1,
        "prompt_only_allowed": False,
        "required_params": [],
        "default_out_dir": "AGENTS/sample/runtime",
        "command": ["python", "AGENTS/sample/sample.py"],
    }


if __name__ == "__main__":
    unittest.main()
