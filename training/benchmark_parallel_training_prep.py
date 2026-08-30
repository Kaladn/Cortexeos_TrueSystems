#!/usr/bin/env python3
"""Benchmark deterministic process parallelism for training preparation."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import json
import multiprocessing
import os
from pathlib import Path
import resource
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "TrueCore"))
from truecore.training import code_intake, selection  # noqa: E402


def measured(operation):
    before_self = resource.getrusage(resource.RUSAGE_SELF)
    before_child = resource.getrusage(resource.RUSAGE_CHILDREN)
    start = time.perf_counter(); result = operation(); wall = time.perf_counter() - start
    after_self = resource.getrusage(resource.RUSAGE_SELF)
    after_child = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (after_self.ru_utime + after_self.ru_stime - before_self.ru_utime - before_self.ru_stime) + (after_child.ru_utime + after_child.ru_stime - before_child.ru_utime - before_child.ru_stime)
    return result, {"elapsed_wall_seconds": wall, "aggregate_cpu_seconds": cpu, "effective_cpu_cores": cpu / wall if wall else 0.0, "machine_cpu_utilization_percent": cpu / wall / (os.cpu_count() or 1) * 100.0 if wall else 0.0, "maximum_resident_kib": max(after_self.ru_maxrss, after_child.ru_maxrss)}


def parse_tasks(root: Path, limit: int) -> list[tuple[str, str, bytes, str | None]]:
    candidates = []
    for component in ("TrueMem", "TrueCore", "TrueVision"):
        base = root / component
        for path in code_intake._files(base):
            if path.suffix.lower() == ".py": candidates.append((component, path))
    candidates.sort(key=lambda row: (row[1].stat().st_size, row[0], row[1].as_posix()), reverse=True)
    chosen = candidates[:limit]
    return [(component, path.relative_to(root / component).as_posix(), path.read_bytes(), None) for component, path in chosen]


def run_parse(tasks, workers: int) -> tuple[str, int]:
    if workers == 1: results = list(map(code_intake._analyze_file, tasks))
    else:
        with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("fork")) as executor:
            results = list(executor.map(code_intake._analyze_file, tasks, chunksize=max(1, min(8, len(tasks) // (workers * 4)))))
    return selection.digest(results), len(results)


def relationship_tasks(corpus: Path, limit: int):
    builder = selection.SelectionBuilder(corpus, corpus.parent / "unused-benchmark-output", workers=1)
    builder.load_level_one()
    groups, duplicate_map = selection.duplicate_groups(builder.level_one)
    builder.select_level_one(duplicate_map)
    selection._SELECT_UNITS = builder.units
    selection._SELECT_UNIT_ROLES = builder.unit_roles
    selection._SELECT_SOURCES = builder.sources
    selection._SELECT_RESERVATIONS = {}
    path = corpus / "TrueMem" / "level-2-operational-relationships.jsonl"
    artifact_hash = selection.digest(path.read_bytes()); tasks = []
    for line_number, row in enumerate(selection.read_jsonl(path), 1):
        tasks.append(("call", "TrueMem", row, {"artifact": f"TrueMem/{path.name}", "line": line_number, "artifact_sha256": artifact_hash}, row["caller_record_id"], "call_edge"))
        if len(tasks) >= limit: break
    return tasks


def run_relationships(tasks, workers: int) -> tuple[str, int]:
    if workers == 1: results = list(map(selection._relationship_worker, tasks))
    else:
        pool = multiprocessing.get_context("fork").Pool(processes=workers)
        try: results = list(pool.imap(selection._relationship_worker, tasks, chunksize=max(1, min(256, len(tasks) // (workers * 12)))))
        finally: pool.close(); pool.join()
    return selection.digest(results), len(results)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--systems-root", type=Path, required=True)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--parse-files", type=int, default=768)
    parser.add_argument("--relationship-records", type=int, default=40000)
    parser.add_argument("--workers", type=int, nargs="+", default=[16, 24, 28])
    args = parser.parse_args()
    parse = parse_tasks(args.systems_root.resolve(), args.parse_files)
    relationships = relationship_tasks(args.corpus_root.resolve(), args.relationship_records)
    serial_parse, serial_parse_metrics = measured(lambda: run_parse(parse, 1))
    serial_rel, serial_rel_metrics = measured(lambda: run_relationships(relationships, 1))
    candidates = []
    for workers in args.workers:
        parse_result, parse_metrics = measured(lambda workers=workers: run_parse(parse, workers))
        relation_result, relation_metrics = measured(lambda workers=workers: run_relationships(relationships, workers))
        stable = parse_result[0] == serial_parse[0] and relation_result[0] == serial_rel[0]
        candidates.append({"workers": workers, "stable": stable, "combined_wall_seconds": parse_metrics["elapsed_wall_seconds"] + relation_metrics["elapsed_wall_seconds"], "parse": {**parse_metrics, "files": parse_result[1], "files_per_second": parse_result[1] / parse_metrics["elapsed_wall_seconds"], "output_hash": parse_result[0]}, "relationships": {**relation_metrics, "records": relation_result[1], "records_per_second": relation_result[1] / relation_metrics["elapsed_wall_seconds"], "output_hash": relation_result[0]}})
    stable = [row for row in candidates if row["stable"]]
    selected = min(stable, key=lambda row: row["combined_wall_seconds"])["workers"] if stable else None
    result = {"schema": "truesystems_parallel_benchmark@1", "logical_cpus": os.cpu_count(), "samples": {"parse_files": len(parse), "relationship_records": len(relationships)}, "serial_reference": {"parse": {**serial_parse_metrics, "output_hash": serial_parse[0]}, "relationships": {**serial_rel_metrics, "output_hash": serial_rel[0]}}, "candidates": candidates, "selected_workers": selected}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if selected is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
