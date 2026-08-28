"""Materialize real local SecureCore capabilities as runnable agents."""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from securecore.live_agents.manifest import validate_agent_manifest


CATALOG_FIELDS = (
    "operator_id", "requires_confirmation", "sandbox_required",
    "destruction_score", "risk_type", "risk_reason", "source_file",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def module_name(source_file: str) -> str:
    path = Path(source_file)
    if path.suffix != ".py":
        raise ValueError(f"Python agent source must end in .py: {source_file}")
    parts = list(path.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def symbol_exists(source_path: Path, symbol: str) -> bool:
    tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    parts = symbol.split(".")
    if len(parts) == 1:
        return any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == parts[0]
            for node in tree.body
        )
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == parts[0]:
            names = {item.name for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))}
            return len(parts) == 2 and parts[1] in names
    return False


def load_rows(catalog_path: Path) -> list[dict[str, str]]:
    with catalog_path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        return list(csv.DictReader(handle))


def build_manifest(row: dict[str, str], source_root: Path, runtime_path: Path) -> dict[str, Any]:
    source_file = row["source_file"]
    source_path = (source_root / source_file).resolve()
    if not source_path.is_relative_to(source_root.resolve()) or not source_path.is_file():
        raise FileNotFoundError(f"catalog source does not exist under source root: {source_file}")
    if not symbol_exists(source_path, row["name"]):
        raise ValueError(f"catalog symbol does not exist in source: {row['name']}")
    score = int(row.get("destruction_score") or 0)
    requires_approval = row.get("requires_confirmation") == "YES"
    agent_id = row["operator_id"]
    manifest = {
        "agent_id": agent_id,
        "id": agent_id,
        "catalog_id": agent_id,
        "name": row["name"],
        "version": "1.0.0",
        "description": row.get("definition") or row["name"],
        "runtime_language": "python",
        "entrypoint": "securecore.live_agents.generated_runtime",
        "entrypoint_hash": sha256_file(runtime_path),
        "source_entrypoint": f"{module_name(source_file)}:{row['name']}",
        "source_entrypoint_hash": sha256_file(source_path),
        "allowed_reads": [source_file],
        "allowed_writes": [],
        "requires_approval": requires_approval,
        "approval_phrase": f"APPROVE {agent_id}" if requires_approval else "",
        "mutation_class": "contract_declared:" + (row.get("side_effects") or "none"),
        "dry_run_supported": True,
        "log_stream": "agent_decision",
        "test_command": ["python3", "-m", "unittest", "tests.live_agents.test_agent_creator"],
        "risk_tier": score,
        "prompt_only_allowed": False,
        "required_params": ["input_json"],
        "default_out_dir": "AGENTS/generated/runtime",
        "command": [
            "python3", "-m", "securecore.live_agents.generated_runtime",
            "--module", module_name(source_file), "--symbol", row["name"],
            "--input-json", "{input_json}",
        ],
    }
    return validate_agent_manifest(manifest)


def materialize(
    catalog_path: Path,
    source_root: Path,
    agent_dir: Path,
    output_catalog: Path,
    operator_ids: set[str] | None = None,
) -> list[Path]:
    runtime_path = Path(__file__).with_name("generated_runtime.py")
    selected = []
    for row in load_rows(catalog_path):
        if operator_ids and row["operator_id"] not in operator_ids:
            continue
        if row.get("promotion_ready") != "YES" or row.get("sandbox_required") == "YES":
            continue
        selected.append((row, build_manifest(row, source_root, runtime_path)))
    if operator_ids:
        found = {row["operator_id"] for row, _ in selected}
        missing = sorted(operator_ids - found)
        if missing:
            raise ValueError("operators were not materializable: " + ", ".join(missing))
    agent_dir.mkdir(parents=True, exist_ok=True)
    output_catalog.parent.mkdir(parents=True, exist_ok=True)
    written = []
    for row, manifest in selected:
        path = agent_dir / f"{row['operator_id']}.agent.json"
        path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written.append(path)
    with output_catalog.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CATALOG_FIELDS)
        writer.writeheader()
        for row, _ in selected:
            writer.writerow({field: row.get(field, "") for field in CATALOG_FIELDS})
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create runnable SecureCore agents from a real local catalog.")
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--agent-dir", type=Path, required=True)
    parser.add_argument("--output-catalog", type=Path, required=True)
    parser.add_argument("--operator-id", action="append", default=[])
    args = parser.parse_args(argv)
    written = materialize(
        args.catalog.resolve(), args.source_root.resolve(), args.agent_dir.resolve(),
        args.output_catalog.resolve(), set(args.operator_id) or None,
    )
    print(json.dumps({"created": len(written), "agent_dir": str(args.agent_dir.resolve())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
