"""Build the system-wide callable-worker index from validated manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from truecore.live_agents.manifest import load_agent_manifest
from truecore.live_agents.worker_result import SCHEMA as WORKER_RESULT_SCHEMA
from truecore.live_agents.worker_result import canonical


SCHEMA = "truecore.skill_index@1"


def build_index(agent_dir: str | Path) -> dict[str, Any]:
    records = []
    seen = set()
    for path in sorted(Path(agent_dir).glob("*.agent.json")):
        path = path.resolve()
        manifest = load_agent_manifest(path)
        worker_id = manifest["agent_id"]
        if worker_id in seen:
            raise ValueError(f"duplicate worker identity: {worker_id}")
        seen.add(worker_id)
        records.append({
            "worker_id": worker_id,
            "name": manifest["name"],
            "version": manifest["version"],
            "runtime_language": manifest["runtime_language"],
            "entrypoint": manifest["entrypoint"],
            "entrypoint_hash": manifest["entrypoint_hash"],
            "required_params": manifest["required_params"],
            "allowed_reads": manifest["allowed_reads"],
            "allowed_writes": manifest["allowed_writes"],
            "requires_approval": manifest["requires_approval"],
            "approval_phrase": manifest["approval_phrase"],
            "mutation_class": manifest["mutation_class"],
            "risk_tier": manifest["risk_tier"],
            "callable": isinstance(manifest.get("command"), list),
            "worker_result_schema": manifest["worker_result_schema"],
            "manifest_path": str(path),
            "manifest_sha256": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
        })
    index = {"schema": SCHEMA, "worker_result_schema": WORKER_RESULT_SCHEMA, "workers": records}
    index["index_sha256"] = "sha256:" + hashlib.sha256(canonical(index)).hexdigest()
    return index


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    index = build_index(args.agent_dir)
    rendered = json.dumps(index, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
