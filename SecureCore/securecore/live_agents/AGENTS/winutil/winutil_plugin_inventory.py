#!/usr/bin/env python3
"""Inventory a desktop WinUtil plugin without executing WinUtil operations."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


DEFAULT_PLUGIN_ROOT = Path(r"C:\Users\mydyi\OneDrive\Documents\Desktop\plugins\winutil")
MUTATION_KEYWORDS = {
    "install",
    "uninstall",
    "apply",
    "tweak",
    "set_dns",
    "fix",
    "repair",
    "enable",
    "registry",
    "powershell",
    "admin",
}


@dataclass(frozen=True, slots=True)
class ToolSummary:
    name: str
    description: str
    parameters: dict[str, Any]
    required: list[str]
    authority_class: str
    risk_family: str


def main() -> int:
    parser = argparse.ArgumentParser(description="Inventory WinUtil plugin tool contracts.")
    parser.add_argument("--plugin-root", default=str(DEFAULT_PLUGIN_ROOT))
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()

    try:
        result = inventory_winutil_plugin(
            plugin_root=Path(args.plugin_root),
            out_dir=Path(args.out_dir),
            plan_only=args.plan_only,
        )
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2, sort_keys=True))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def inventory_winutil_plugin(*, plugin_root: Path, out_dir: Path, plan_only: bool = False) -> dict[str, Any]:
    root = plugin_root.resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"WinUtil plugin root does not exist: {root}")
    required_files = ["__init__.py", "tools.py", "ps_runner.py", "config_reader.py", "api/router.py"]
    missing = [name for name in required_files if not (root / name).exists()]
    if missing:
        raise ValueError("WinUtil plugin missing required file(s): " + ", ".join(missing))

    tools = _load_tool_summaries(root)
    read_only = [tool.name for tool in tools if tool.authority_class == "read"]
    mutation = [tool.name for tool in tools if tool.authority_class == "mutate"]
    payload = {
        "schema_version": 1,
        "kind": "securecore_winutil_plugin_inventory",
        "created_at_utc": _utc_now(),
        "dry_run": plan_only,
        "plugin_root": str(root),
        "tool_count": len(tools),
        "read_only_tools": read_only,
        "mutation_tools": mutation,
        "tools": [_tool_row(tool) for tool in tools],
        "file_hashes": _file_hashes(root),
        "writes_performed": False,
        "raw_content_logged": False,
        "mutation_authorized": False,
        "winutil_operation_executed": False,
        "artifact_kind": "winutil_inventory",
    }
    if plan_only:
        return payload

    out = out_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    run_id = f"winutil-inventory-{_safe_time()}-{uuid4().hex[:8]}"
    manifest_path = out / f"{run_id}.manifest.json"
    receipt_path = out / f"{run_id}.receipt.json"
    manifest = dict(payload)
    manifest.update({"run_id": run_id, "manifest_path": str(manifest_path)})
    _write_json(manifest_path, manifest)
    receipt = {
        "schema_version": 1,
        "kind": "securecore_winutil_plugin_inventory_receipt",
        "created_at_utc": _utc_now(),
        "run_id": run_id,
        "plugin_root": str(root),
        "manifest_path": str(manifest_path),
        "tool_count": len(tools),
        "read_only_tool_count": len(read_only),
        "mutation_tool_count": len(mutation),
        "raw_content_logged": False,
        "mutation_authorized": False,
        "winutil_operation_executed": False,
        "writes_performed": True,
        "artifact_kind": "winutil_inventory",
    }
    _write_json(receipt_path, receipt)
    return {
        "status": "ok",
        "dry_run": False,
        "run_id": run_id,
        "manifest_path": str(manifest_path),
        "receipt_path": str(receipt_path),
        "tool_count": len(tools),
        "read_only_tool_count": len(read_only),
        "mutation_tool_count": len(mutation),
        "writes_performed": True,
        "raw_content_logged": False,
        "mutation_authorized": False,
        "winutil_operation_executed": False,
    }


def _load_tool_summaries(plugin_root: Path) -> list[ToolSummary]:
    package_parent = str(plugin_root.parent)
    if package_parent not in sys.path:
        sys.path.insert(0, package_parent)
    tools_module = importlib.import_module("winutil.tools")
    rows = []
    for tool in getattr(tools_module, "TOOLS", []):
        params = dict(tool.get("parameters") or {})
        required = list(params.get("required") or [])
        name = str(tool.get("name") or "")
        description = str(tool.get("description") or "")
        authority = _authority_for_tool(name, description)
        rows.append(
            ToolSummary(
                name=name,
                description=description,
                parameters=params,
                required=required,
                authority_class=authority,
                risk_family=_risk_family(name, description, authority),
            )
        )
    return sorted(rows, key=lambda item: item.name)


def _authority_for_tool(name: str, description: str) -> str:
    haystack = f"{name} {description}".lower()
    if name.startswith("winutil_list_") or name == "winutil_status":
        return "read"
    if any(term in haystack for term in MUTATION_KEYWORDS):
        return "mutate"
    return "read"


def _risk_family(name: str, description: str, authority: str) -> str:
    haystack = f"{name} {description}".lower()
    if authority == "read":
        return "inventory_read"
    if "dns" in haystack or "network" in haystack:
        return "network_control"
    if "registry" in haystack or "tweak" in haystack:
        return "registry_or_system_tweak"
    if "install" in haystack or "uninstall" in haystack:
        return "software_installation"
    if "fix" in haystack or "repair" in haystack:
        return "system_repair"
    return "system_mutation"


def _tool_row(tool: ToolSummary) -> dict[str, Any]:
    return {
        "tool_name": tool.name,
        "description": tool.description,
        "required_params": tool.required,
        "parameters": tool.parameters,
        "authority_class": tool.authority_class,
        "risk_family": tool.risk_family,
        "securecore_gate": "read_only" if tool.authority_class == "read" else "approval_gated_mutation",
    }


def _file_hashes(root: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(root.rglob("*.py")):
        rows.append(
            {
                "relative_path": str(path.relative_to(root)),
                "sha256": _file_hash(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return rows


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _safe_time() -> str:
    return _utc_now().replace(":", "").replace(".", "").replace("-", "")


if __name__ == "__main__":
    raise SystemExit(main())
