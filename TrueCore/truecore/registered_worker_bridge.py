"""Host-bound bridge from model requests to registered read-only TrueCore workers.

The model selects only a host-granted worker identity, resource identity, and
typed arguments.  Filesystem paths, modules, commands, manifests, and grants
remain outside the model request.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from types import MappingProxyType
from typing import Any

from .live_agents.manifest import load_agent_manifest
from .live_agents.worker_result import validate_result


RESOURCE_KIND = "TRUEMACHINE_REPOSITORY_MAP"
SOURCE_MODULE = "truecore.agents.repository_graph_workers"
AGENT_ROOT = Path(__file__).resolve().parent / "live_agents" / "AGENTS"
AGENT_DIR = AGENT_ROOT / "agents"
CATALOG = AGENT_ROOT / "catalog" / "agent_catalog.csv"
RUNNER = AGENT_ROOT / "runner" / "truecore_agent_runner.py"


class RegisteredWorkerBridgeError(ValueError):
    """Raised when a model request cannot enter the registered worker path."""


def _sha256_file(path: Path) -> str:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(descriptor, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def _validate_resource(resource_id: str, binding: dict[str, Any]) -> dict[str, str]:
    if not isinstance(resource_id, str) or not resource_id:
        raise RegisteredWorkerBridgeError("INVALID_RESOURCE_ID")
    if not isinstance(binding, dict) or set(binding) != {"kind", "path", "manifest_sha256"}:
        raise RegisteredWorkerBridgeError("INVALID_HOST_RESOURCE_BINDING")
    if binding["kind"] != RESOURCE_KIND:
        raise RegisteredWorkerBridgeError("UNSUPPORTED_RESOURCE_KIND")
    path = Path(binding["path"])
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        raise RegisteredWorkerBridgeError("INVALID_HOST_RESOURCE_PATH")
    manifest_path = path / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise RegisteredWorkerBridgeError("RESOURCE_MANIFEST_NOT_FOUND")
    actual = _sha256_file(manifest_path)
    if actual != binding["manifest_sha256"]:
        raise RegisteredWorkerBridgeError("STALE_OR_CHANGED_RESOURCE")
    manifest = json.loads(manifest_path.read_bytes())
    if not isinstance(manifest, dict) or manifest.get("persistent_symbols") is not False:
        raise RegisteredWorkerBridgeError("UNSUPPORTED_RESOURCE_MANIFEST")
    contract = manifest.get("n_n_n_contract")
    if not isinstance(contract, dict) or contract.get("meaning") != "ownership-source_order-dependency":
        raise RegisteredWorkerBridgeError("UNSUPPORTED_RESOURCE_CONTRACT")
    snapshot_id = manifest.get("snapshot_id")
    if not isinstance(snapshot_id, str) or not snapshot_id:
        raise RegisteredWorkerBridgeError("RESOURCE_SNAPSHOT_ID_MISSING")
    return {
        "path": str(path),
        "manifest_path": str(manifest_path),
        "manifest_sha256": actual,
        "snapshot_id": snapshot_id,
    }


def _validate_worker(worker_id: str) -> dict[str, Any]:
    if not isinstance(worker_id, str) or not worker_id:
        raise RegisteredWorkerBridgeError("INVALID_WORKER_ID")
    manifest_path = AGENT_DIR / f"{worker_id}.agent.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise RegisteredWorkerBridgeError("WORKER_NOT_REGISTERED")
    manifest = load_agent_manifest(manifest_path)
    source_entrypoint = manifest.get("source_entrypoint", "")
    if source_entrypoint.split(":", 1)[0] != SOURCE_MODULE:
        raise RegisteredWorkerBridgeError("WORKER_OUTSIDE_REPOSITORY_GRAPH_FAMILY")
    if (
        manifest["requires_approval"]
        or manifest["allowed_writes"]
        or manifest["worker_result_schema"] != "truecore.worker_result@1"
        or manifest.get("required_params") != ["input_json"]
    ):
        raise RegisteredWorkerBridgeError("WORKER_NOT_READ_ONLY_MODEL_ELIGIBLE")
    return manifest


class RegisteredWorkerBridge:
    """Execute only host-granted repository workers against host-bound maps."""

    def __init__(self, *, worker_grants=(), resources=None, timeout_seconds: int = 120):
        if not isinstance(worker_grants, (list, tuple, set, frozenset)):
            raise ValueError("INVALID_WORKER_GRANTS")
        grants = frozenset(worker_grants)
        for worker_id in grants:
            _validate_worker(worker_id)
        if not isinstance(resources or {}, dict):
            raise ValueError("INVALID_RESOURCE_BINDINGS")
        checked_resources = {
            resource_id: MappingProxyType(_validate_resource(resource_id, dict(binding)))
            for resource_id, binding in (resources or {}).items()
        }
        if type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 600:
            raise ValueError("INVALID_WORKER_TIMEOUT")
        self.worker_grants = grants
        self.resources = MappingProxyType(checked_resources)
        self.timeout_seconds = timeout_seconds

    def public_contract(self) -> dict[str, Any]:
        return {
            "worker_grants": sorted(self.worker_grants),
            "resource_ids": sorted(self.resources),
            "arguments": {
                "worker_id": "host-granted registered worker identity",
                "resource_id": "host-bound TrueMachine repository-map identity",
                "parameters": {"limit": "integer from 1 through 100000"},
            },
            "model_supplied_paths": False,
            "model_supplied_commands": False,
            "model_supplied_modules": False,
            "result_schema": "truecore.worker_result@1",
        }

    def invoke(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(arguments, dict) or set(arguments) != {"worker_id", "resource_id", "parameters"}:
            raise RegisteredWorkerBridgeError("INVALID_WORKER_ARGUMENTS")
        worker_id = arguments["worker_id"]
        resource_id = arguments["resource_id"]
        if worker_id not in self.worker_grants:
            raise RegisteredWorkerBridgeError("WORKER_PERMISSION_DENIED")
        _validate_worker(worker_id)
        resource = self.resources.get(resource_id)
        if resource is None:
            raise RegisteredWorkerBridgeError("MISSING_WORKER_RESOURCE")
        parameters = arguments["parameters"]
        if not isinstance(parameters, dict) or set(parameters) != {"limit"}:
            raise RegisteredWorkerBridgeError("INVALID_WORKER_PARAMETERS")
        limit = parameters["limit"]
        if type(limit) is not int or not 1 <= limit <= 100_000:
            raise RegisteredWorkerBridgeError("INVALID_WORKER_LIMIT")

        before_hash = _sha256_file(Path(resource["manifest_path"]))
        payload = json.dumps(
            {"kwargs": {"map_dir": resource["path"], "limit": limit}},
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        command = [
            sys.executable,
            "-B",
            str(RUNNER),
            "--catalog",
            str(CATALOG),
            "--agent-dir",
            str(AGENT_DIR),
            "run",
            worker_id,
            "--param",
            f"input_json={payload}",
        ]
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        import_roots = [
            str(Path(__file__).resolve().parents[1]),
            str(Path(__file__).resolve().parents[2] / "TrueMachine" / "src"),
        ]
        inherited_pythonpath = environment.get("PYTHONPATH")
        if inherited_pythonpath:
            import_roots.append(inherited_pythonpath)
        environment["PYTHONPATH"] = os.pathsep.join(import_roots)
        try:
            completed = subprocess.run(
                command,
                cwd=AGENT_ROOT,
                capture_output=True,
                env=environment,
                timeout=self.timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise RegisteredWorkerBridgeError("REGISTERED_WORKER_TIMEOUT") from exc
        except OSError as exc:
            raise RegisteredWorkerBridgeError("REGISTERED_WORKER_START_FAILED") from exc
        after_hash = _sha256_file(Path(resource["manifest_path"]))
        if before_hash != resource["manifest_sha256"] or after_hash != before_hash:
            raise RegisteredWorkerBridgeError("RESOURCE_CHANGED_DURING_EXECUTION")
        if completed.returncode != 0:
            raise RegisteredWorkerBridgeError("REGISTERED_WORKER_PROCESS_FAILED")
        try:
            packet = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise RegisteredWorkerBridgeError("INVALID_REGISTERED_WORKER_OUTPUT") from exc
        validate_result(packet)
        if packet["worker_id"] != worker_id:
            raise RegisteredWorkerBridgeError("WORKER_RESULT_IDENTITY_MISMATCH")
        return packet
