#!/usr/bin/env python3
"""TrueCore-style gated runner for repo-local agents."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from truecore.live_agents.manifest import AgentManifestError, load_agent_manifest
from truecore.live_agents.worker_result import canonical, digest, normalize_process_result

DEFAULT_CATALOG = ROOT / "AGENTS" / "catalog" / "agent_catalog.csv"
DEFAULT_AGENT_DIR = ROOT / "AGENTS" / "agents"


@dataclass(frozen=True)
class CatalogEntry:
    operator_id: str
    requires_confirmation: bool
    sandbox_required: bool
    destruction_score: int
    risk_type: str
    risk_reason: str
    source_file: str


class AgentExecutionContractError(ValueError):
    """Raised when executable metadata cannot be enforced safely."""


def load_catalog(path: Path) -> Dict[str, CatalogEntry]:
    entries: Dict[str, CatalogEntry] = {}
    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        for row in csv.DictReader(handle):
            operator_id = row["operator_id"]
            entries[operator_id] = CatalogEntry(
                operator_id=operator_id,
                requires_confirmation=row.get("requires_confirmation") == "YES",
                sandbox_required=row.get("sandbox_required") == "YES",
                destruction_score=int(row.get("destruction_score") or 0),
                risk_type=row.get("risk_type", "unknown"),
                risk_reason=row.get("risk_reason", ""),
                source_file=row.get("source_file", ""),
            )
    return entries


def load_agent_spec(agent_dir: Path, agent_id: str) -> dict:
    path = agent_dir / f"{agent_id}.agent.json"
    if not path.exists():
        raise FileNotFoundError(f"Agent spec not found: {path}")
    return load_agent_manifest(path)


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def resolve_entrypoint(spec: dict) -> Path:
    entrypoint = resolve_repo_path(spec["entrypoint"])
    try:
        entrypoint.relative_to(REPO_ROOT.resolve())
    except ValueError as exc:
        raise AgentExecutionContractError("entrypoint escapes the TrueCore repository") from exc
    if not entrypoint.is_file():
        raise AgentExecutionContractError(f"entrypoint does not exist: {entrypoint}")
    actual_hash = "sha256:" + hashlib.sha256(entrypoint.read_bytes()).hexdigest()
    if actual_hash != spec["entrypoint_hash"]:
        raise AgentExecutionContractError(
            f"entrypoint hash mismatch: expected {spec['entrypoint_hash']}, found {actual_hash}"
        )
    return entrypoint


def verify_catalog_contract(spec: dict, entry: CatalogEntry) -> None:
    if spec["agent_id"] != entry.operator_id:
        raise AgentExecutionContractError("catalog and manifest agent IDs differ")
    if spec["entrypoint"] != entry.source_file:
        raise AgentExecutionContractError("catalog and manifest entrypoints differ")
    if spec["requires_approval"] != entry.requires_confirmation:
        raise AgentExecutionContractError("catalog and manifest approval requirements differ")
    if spec["risk_tier"] != entry.destruction_score:
        raise AgentExecutionContractError("catalog and manifest risk scores differ")
    if entry.sandbox_required:
        raise AgentExecutionContractError("catalog requires a sandbox that this runner does not provide")


def verify_command_entrypoint(spec: dict, command: list[str], entrypoint: Path) -> None:
    script_runtimes = {"python", "javascript", "typescript"}
    entrypoint_index = 1 if spec["runtime_language"] in script_runtimes else 0
    if len(command) <= entrypoint_index:
        raise AgentExecutionContractError("command has no executable entrypoint")
    if resolve_repo_path(command[entrypoint_index]) != entrypoint:
        raise AgentExecutionContractError("command does not invoke the hashed entrypoint")


def verify_write_boundaries(spec: dict, params: dict[str, str], out_dir: Path) -> None:
    for name in spec.get("write_params", []):
        candidate = Path(params[name]).expanduser().resolve()
        try:
            candidate.relative_to(out_dir)
        except ValueError as exc:
            raise AgentExecutionContractError(
                f"write parameter {name} escapes the selected output directory"
            ) from exc


def parse_params(raw_params: list[str] | None) -> dict[str, str]:
    values: dict[str, str] = {}
    for item in raw_params or []:
        if "=" not in item:
            raise ValueError(f"invalid --param value, expected key=value: {item}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("invalid --param value, key is empty")
        values[key] = value
    return values


def build_command(spec: dict, out_dir: Path, params: dict[str, str] | None = None) -> List[str]:
    values = {"out_dir": str(out_dir)}
    values.update(params or {})
    return [part.format(**values) for part in spec["command"]]


def missing_required_params(spec: dict, params: dict[str, str]) -> list[str]:
    return [name for name in spec.get("required_params", []) if name not in params]


def approval_error(entry: CatalogEntry, phrase: str) -> str:
    return (
        "APPROVAL REQUIRED\n"
        f"agent_id: {entry.operator_id}\n"
        f"destruction_score: {entry.destruction_score}\n"
        f"risk_type: {entry.risk_type}\n"
        f"risk_reason: {entry.risk_reason}\n"
        f"required_phrase: {phrase}\n"
    )


def run_agent(args: argparse.Namespace) -> int:
    catalog = load_catalog(args.catalog)
    if args.agent_id not in catalog:
        print(f"Unknown agent: {args.agent_id}", file=sys.stderr)
        return 1

    entry = catalog[args.agent_id]
    try:
        spec = load_agent_spec(args.agent_dir, args.agent_id)
    except (AgentManifestError, FileNotFoundError, json.JSONDecodeError) as exc:
        print(f"Invalid agent manifest: {exc}", file=sys.stderr)
        return 1
    missing_execution_fields = [field for field in ("command", "default_out_dir") if field not in spec]
    if missing_execution_fields:
        print(f"Invalid agent manifest: missing execution field {missing_execution_fields[0]}", file=sys.stderr)
        return 1
    phrase = spec["approval_phrase"]
    out_dir = resolve_repo_path(args.out_dir or spec["default_out_dir"])
    params = parse_params(args.param)
    missing_params = missing_required_params(spec, params)
    if missing_params:
        print(
            "Missing required agent parameters: " + ", ".join(missing_params),
            file=sys.stderr,
        )
        return 3
    try:
        command = build_command(spec, out_dir, params)
        entrypoint = resolve_entrypoint(spec)
        verify_catalog_contract(spec, entry)
        verify_command_entrypoint(spec, command, entrypoint)
        verify_write_boundaries(spec, params, out_dir)
    except (AgentExecutionContractError, KeyError, ValueError) as exc:
        print(f"Invalid agent parameters: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(json.dumps({
            "agent_id": args.agent_id,
            "approved": False,
            "would_execute": command,
            "out_dir": str(out_dir),
            "risk": {
                "score": entry.destruction_score,
                "type": entry.risk_type,
                "reason": entry.risk_reason,
                "confirmation": entry.requires_confirmation,
                "sandbox": entry.sandbox_required,
            },
        }, indent=2))
        return 0

    if entry.requires_confirmation and args.approve != phrase:
        print(approval_error(entry, phrase), file=sys.stderr)
        return 2

    if spec["allowed_writes"]:
        out_dir.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(command, cwd=ROOT, capture_output=True)
    packet = normalize_process_result(
        worker_id=args.agent_id,
        operation="execute",
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
        entrypoint_hash=spec["entrypoint_hash"],
        input_binding_hash=digest({"required_params": spec["required_params"], "params": params}),
    )
    sys.stdout.buffer.write(canonical(packet))
    return completed.returncode


def list_agents(args: argparse.Namespace) -> int:
    catalog = load_catalog(args.catalog)
    for entry in catalog.values():
        print(
            f"{entry.operator_id}\t"
            f"score={entry.destruction_score}\t"
            f"confirm={entry.requires_confirmation}\t"
            f"sandbox={entry.sandbox_required}\t"
            f"{entry.risk_type}"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run TrueCore-style repo-local agents.")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--agent-dir", type=Path, default=DEFAULT_AGENT_DIR)

    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Run an agent through its safety gate.")
    run.add_argument("agent_id")
    run.add_argument("--out-dir")
    run.add_argument("--approve")
    run.add_argument("--param", action="append", default=[])
    run.add_argument("--dry-run", action="store_true")
    run.set_defaults(func=run_agent)

    listed = subparsers.add_parser("list", help="List catalog agents.")
    listed.set_defaults(func=list_agents)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
