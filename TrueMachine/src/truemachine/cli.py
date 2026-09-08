"""TrueMachine command line."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .collectors import IdentityCollector, MemoryCollector, NetworkCollector, ProcessCollector, StateArtifactCollector
from .engine import TemporalEngine
from .fusion import FusionStore


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
    return root


def main() -> int:
    args = parser().parse_args()
    store = FusionStore(args.state_dir)
    if args.command == "verify":
        print(json.dumps(store.verify(), sort_keys=True))
        return 0
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
