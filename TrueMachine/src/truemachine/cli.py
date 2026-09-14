"""TrueMachine command line."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .collectors import IdentityCollector, MemoryCollector, NetworkCollector, ProcessCollector, StateArtifactCollector
from .engine import TemporalEngine
from .fusion import FusionStore
from . import repository_map


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="truemachine")
    commands = root.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--duration", type=float, default=60.0)
    run.add_argument("--interval", type=float, default=1.0)
    run.add_argument("--state-dir", type=Path, default=Path("state"))
    run.add_argument("--truevision-state", type=Path, action="append", default=[])
    run.add_argument("--trueaudio-state", type=Path, action="append", default=[])
    run.add_argument("--truemem-state", type=Path, action="append", default=[])
    verify = commands.add_parser("verify")
    verify.add_argument("--state-dir", type=Path, default=Path("state"))
    mapping = commands.add_parser(
        "map-repository",
        help="observe an exact source-grounded repository structure",
    )
    mapping.add_argument("--repo", type=Path, required=True)
    mapping.add_argument("--output-parent", type=Path, required=True)
    mapping.add_argument("--ownership-n", type=int, default=2)
    mapping.add_argument("--source-order-n", dest="flow_n", type=int, default=6)
    mapping.add_argument("--dependency-n", type=int, default=3)
    mapping.add_argument("--progress", type=int, default=250)
    query = commands.add_parser(
        "query-repository",
        help="return a location-only N-N-N packet from a repository map",
    )
    query.add_argument("--map-dir", type=Path, required=True)
    query.add_argument("--exact", required=True)
    query.add_argument("--path")
    query.add_argument("--ownership-n", type=int, default=2)
    query.add_argument("--source-order-n", dest="flow_n", type=int, default=6)
    query.add_argument("--dependency-n", type=int, default=3)
    map_verify = commands.add_parser(
        "verify-repository-map",
        help="verify repository-map artifacts against their observed source",
    )
    map_verify.add_argument("--map-dir", type=Path, required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    if args.command in {"map-repository", "query-repository", "verify-repository-map"}:
        if args.command == "verify-repository-map":
            return repository_map.verify(args)
        for name in ("ownership_n", "flow_n", "dependency_n"):
            if not 0 <= getattr(args, name) <= 64:
                raise SystemExit(f"{name} must be 0..64")
        if args.command == "map-repository":
            return repository_map.build(args)
        return repository_map.query(args)
    if args.command == "verify":
        store = FusionStore(args.state_dir, create=False)
        print(json.dumps(store.verify(), sort_keys=True))
        return 0
    store = FusionStore(args.state_dir)
    cadence_ns = int(args.interval * 1_000_000_000)
    collectors = [IdentityCollector(), MemoryCollector(), ProcessCollector(), NetworkCollector()]
    for system, paths in (
        ("truevision", args.truevision_state),
        ("trueaudio", args.trueaudio_state),
        ("truemem", args.truemem_state),
    ):
        collectors.extend(StateArtifactCollector(system, path) for path in paths)
    engine = TemporalEngine(
        store,
        collectors,
        cadence_ns=cadence_ns,
    )
    count = engine.run(args.duration, args.interval)
    result = store.verify()
    print(json.dumps({"run_id": engine.run_id, "pulses": count, **result}, sort_keys=True))
    return 0
