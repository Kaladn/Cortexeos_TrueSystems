#!/usr/bin/env python3
"""SecureCore-style gated runner for repo-local agents."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[2]
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
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_repo_path(path_text: str) -> Path:
    path = Path(path_text)
    if not path.is_absolute():
        path = ROOT / path
    return path


def build_command(spec: dict, out_dir: Path) -> List[str]:
    values = {"out_dir": str(out_dir)}
    return [part.format(**values) for part in spec["command"]]


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
    spec = load_agent_spec(args.agent_dir, args.agent_id)
    phrase = spec["approval_phrase"]
    out_dir = resolve_repo_path(args.out_dir or spec["default_out_dir"])
    command = build_command(spec, out_dir)

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

    out_dir.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(command, cwd=ROOT)
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
    parser = argparse.ArgumentParser(description="Run SecureCore-style repo-local agents.")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--agent-dir", type=Path, default=DEFAULT_AGENT_DIR)

    subparsers = parser.add_subparsers(dest="command", required=True)

    run = subparsers.add_parser("run", help="Run an agent through its safety gate.")
    run.add_argument("agent_id")
    run.add_argument("--out-dir")
    run.add_argument("--approve")
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
