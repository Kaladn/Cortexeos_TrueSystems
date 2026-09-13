"""Production manifest contract for TrueCore live agents."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


ALLOWED_RUNTIME_LANGUAGES = {
    "rust",
    "cpp",
    "python",
    "typescript",
    "javascript",
}

REQUIRED_FIELDS = {
    "agent_id",
    "name",
    "version",
    "runtime_language",
    "entrypoint",
    "entrypoint_hash",
    "allowed_reads",
    "allowed_writes",
    "requires_approval",
    "approval_phrase",
    "mutation_class",
    "dry_run_supported",
    "log_stream",
    "test_command",
    "risk_tier",
    "prompt_only_allowed",
    "required_params",
    "worker_result_schema",
}

HASH_RE = re.compile(r"^sha256:[0-9a-fA-F]{64}$")


class AgentManifestError(ValueError):
    """Raised when a live-agent manifest violates TrueCore contract."""


def load_agent_manifest(path: str | Path) -> dict[str, Any]:
    manifest_path = Path(path)
    with manifest_path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    return validate_agent_manifest(manifest)


def validate_agent_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise AgentManifestError("manifest must be a JSON object")

    missing = sorted(REQUIRED_FIELDS.difference(manifest))
    if missing:
        raise AgentManifestError(f"missing required field: {missing[0]}")

    runtime = str(manifest["runtime_language"]).lower()
    if runtime == "prompt" or manifest.get("prompt_only_allowed") is True:
        raise AgentManifestError("prompt-only production agents are forbidden")
    if runtime not in ALLOWED_RUNTIME_LANGUAGES:
        raise AgentManifestError(f"unsupported runtime_language: {runtime}")

    if not str(manifest["agent_id"]).strip():
        raise AgentManifestError("agent_id must not be empty")
    if manifest.get("id") and manifest["id"] != manifest["agent_id"]:
        raise AgentManifestError("id must match agent_id when present")
    if manifest.get("catalog_id") and manifest["catalog_id"] != manifest["agent_id"]:
        raise AgentManifestError("catalog_id must match agent_id when present")
    if not str(manifest["entrypoint"]).strip():
        raise AgentManifestError("entrypoint must not be empty")
    if not HASH_RE.match(str(manifest["entrypoint_hash"])):
        raise AgentManifestError("entrypoint_hash must be sha256:<64 hex chars>")

    _require_bool(manifest, "requires_approval")
    _require_bool(manifest, "dry_run_supported")
    _require_bool(manifest, "prompt_only_allowed")
    _require_string_list(manifest, "allowed_reads")
    _require_string_list(manifest, "allowed_writes")
    _require_string_list(manifest, "test_command")
    _require_string_list(manifest, "required_params")
    if "command" in manifest:
        _require_string_list(manifest, "command")
    if "write_params" in manifest:
        _require_string_list(manifest, "write_params")
        unknown_write_params = sorted(set(manifest["write_params"]) - set(manifest["required_params"]))
        if unknown_write_params:
            raise AgentManifestError(f"write_params names unknown parameter: {unknown_write_params[0]}")

    if not isinstance(manifest["risk_tier"], int) or manifest["risk_tier"] < 0:
        raise AgentManifestError("risk_tier must be a non-negative integer")
    if manifest["requires_approval"] and not str(manifest["approval_phrase"]).strip():
        raise AgentManifestError("approval_phrase required when requires_approval is true")
    if not str(manifest["mutation_class"]).strip():
        raise AgentManifestError("mutation_class must not be empty")
    if not str(manifest["log_stream"]).strip():
        raise AgentManifestError("log_stream must not be empty")
    if manifest["worker_result_schema"] != "truecore.worker_result@1":
        raise AgentManifestError("worker_result_schema must be truecore.worker_result@1")
    if "default_out_dir" in manifest and not str(manifest["default_out_dir"]).strip():
        raise AgentManifestError("default_out_dir must not be empty")
    if manifest["mutation_class"] == "read_only" and manifest["allowed_writes"]:
        raise AgentManifestError("read_only agents must not declare allowed_writes")

    validated = dict(manifest)
    if manifest.get("entrypoint") == "truecore.live_agents.generated_runtime" or "usage" in manifest:
        from truecore.help.agent_usage import validate_usage
        try:
            validate_usage(manifest)
        except ValueError as exc:
            raise AgentManifestError(str(exc)) from exc
    validated["runtime_language"] = runtime
    return validated


def _require_bool(manifest: dict[str, Any], field: str) -> None:
    if not isinstance(manifest[field], bool):
        raise AgentManifestError(f"{field} must be boolean")


def _require_string_list(manifest: dict[str, Any], field: str) -> None:
    value = manifest[field]
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise AgentManifestError(f"{field} must be a list of non-empty strings")
