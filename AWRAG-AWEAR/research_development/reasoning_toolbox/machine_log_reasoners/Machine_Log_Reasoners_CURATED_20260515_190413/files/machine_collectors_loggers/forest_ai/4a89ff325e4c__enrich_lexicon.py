"""Merge 6-1-6 batch reports into the canonical lexicon.

This script consumes one or more `616_map.json` artifacts, aggregates frequency
and positional context data, and merges the results into the canonical lexicon
(`Lexicon_Canonical/lexicon_v2.json`). It is intentionally incremental and
idempotent: processed reports are recorded in a sidecar state file so re-running
against the same inputs will be a no-op unless `--force` is supplied.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import logging
import shutil
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

try:  # Optional progress reporting
    from tqdm.auto import tqdm  # type: ignore
except ImportError:  # pragma: no cover - fallback when tqdm missing
    tqdm = None  # type: ignore

try:  # Optional streaming parser for large JSON arrays
    import ijson  # type: ignore
except ImportError:  # pragma: no cover - fallback when ijson missing
    ijson = None  # type: ignore

LOGGER = logging.getLogger("enrich_lexicon")
DEFAULT_MAX_BUCKET = 50
DEFAULT_MAX_SOURCES = 10
STATE_FILENAME = "enrichment_state.json"


@dataclass
class ReportMeta:
    identifier: str
    path: Path
    size: int
    mtime: float
    sha256: str
    timestamp: str


@dataclass
class TokenUpdate:
    token: str  # normalised lowercase token
    display: str  # canonical display token
    frequency: int = 0
    before: Dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))
    after: Dict[str, Counter] = field(default_factory=lambda: defaultdict(Counter))
    report_ids: List[str] = field(default_factory=list)

    def touch(self, report_id: str) -> None:
        if report_id not in self.report_ids:
            self.report_ids.append(report_id)

    def add_frequency(self, value: int) -> None:
        if value <= 0:
            return
        self.frequency += value

    def merge_context(self, bucket: Dict[str, Iterable[Tuple[str, int]]], target: Dict[str, Counter]) -> None:
        for distance, items in bucket.items():
            counter = target[distance]
            for token, count in items:
                if not token:
                    continue
                counter[token] += max(int(count), 0)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Enrich the canonical lexicon with 6-1-6 reports")
    parser.add_argument("--lexicon", type=Path, default=Path("Lexicon_Canonical/lexicon_v2.json"))
    parser.add_argument("--reports-root", type=Path, default=Path("forest_ai/data/maps"))
    parser.add_argument("--report", action="append", type=Path, help="Specific report file(s) to process")
    parser.add_argument("--state", type=Path, help="Path to enrichment state file (defaults next to lexicon)")
    parser.add_argument("--max-bucket", type=int, default=DEFAULT_MAX_BUCKET, help="Maximum entries per context bucket")
    parser.add_argument("--max-sources", type=int, default=DEFAULT_MAX_SOURCES, help="Maximum recent report IDs to retain")
    parser.add_argument("--force", action="store_true", help="Reprocess reports even if already recorded")
    parser.add_argument("--dry-run", action="store_true", help="Compute updates without modifying files")
    parser.add_argument("--limit-tokens", type=int, help="Restrict number of tokens processed (debug/testing)")
    parser.add_argument("--no-backup", action="store_true", help="Skip lexicon backup before writing")
    parser.add_argument("--validate", action="store_true", help="Run schema validator after enrichment")
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args(argv)


def discover_reports(root: Path) -> List[Path]:
    if not root.exists():
        LOGGER.warning("Reports root %s does not exist; nothing to process", root)
        return []
    return sorted(root.rglob("616_map.json"))


def calculate_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_state(path: Path) -> Dict[str, Dict[str, Dict[str, object]]]:
    if not path.exists():
        return {"processed": {}, "history": []}
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        processed = data.get("processed", {})
        history = data.get("history", [])
        if not isinstance(processed, dict):
            processed = {}
        if not isinstance(history, list):
            history = []
        return {"processed": processed, "history": history}
    except json.JSONDecodeError as exc:
        LOGGER.warning("State file %s malformed (%s); starting fresh", path, exc)
        return {"processed": {}, "history": []}


def store_state(path: Path, data: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    tmp_path.replace(path)


def to_iso(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat()


def load_report(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def flatten_context(ctx: Dict[str, List[Dict[str, object]]]) -> Dict[str, List[Tuple[str, int]]]:
    output: Dict[str, List[Tuple[str, int]]] = {}
    for distance, items in (ctx or {}).items():
        bucket: List[Tuple[str, int]] = []
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            token = item.get("token")
            count = item.get("count", 0)
            if not isinstance(token, str):
                continue
            try:
                bucket.append((token, int(count)))
            except (TypeError, ValueError):
                continue
        if bucket:
            output[str(distance)] = bucket
    return output


def calculate_report_meta(path: Path) -> ReportMeta:
    stat = path.stat()
    sha = calculate_sha256(path)
    identifier = sha[:16]
    return ReportMeta(
        identifier=identifier,
        path=path.resolve(),
        size=stat.st_size,
        mtime=stat.st_mtime,
        sha256=sha,
        timestamp=to_iso(stat.st_mtime),
    )


def aggregate_reports(paths: List[Path], state: Dict[str, Dict[str, Dict[str, object]]], force: bool,
                      limit_tokens: Optional[int]) -> Tuple[Dict[str, TokenUpdate], List[Dict[str, object]]]:
    processed = state.get("processed", {})
    updates: Dict[str, TokenUpdate] = {}
    summaries: List[Dict[str, object]] = []
    tokens_seen = 0

    if tqdm is not None and paths:
        report_iterable: Iterable[Path] = tqdm(paths, desc="Reports", unit="report", leave=True)
    else:
        report_iterable = paths

    for report_path in report_iterable:
        if not report_path.exists():
            LOGGER.warning("Skipping missing report %s", report_path)
            continue
        meta = calculate_report_meta(report_path)
        if meta.sha256 in processed and not force:
            LOGGER.info("Skipping already applied report %s", report_path)
            continue

        payload = load_report(report_path)
        items = payload.get("items", {}) if isinstance(payload, dict) else {}
        if not isinstance(items, dict):
            LOGGER.warning("Report %s has unexpected payload; skipped", report_path)
            continue

        report_token_updates = 0
        report_frequency_added = 0
        window = payload.get("window")
        device_used = payload.get("device_used")

        token_iterable: Iterable[Tuple[str, Dict[str, object]]]
        if tqdm is not None and items:
            token_iterable = tqdm(
                items.items(),
                total=len(items),
                desc=f"Tokens {report_path.name}",
                unit="token",
                leave=False,
            )
        else:
            token_iterable = items.items()

        for key, value in token_iterable:
            if limit_tokens is not None and tokens_seen >= limit_tokens:
                LOGGER.info("Token limit reached (%s); remaining tokens skipped", limit_tokens)
                break
            if not isinstance(value, dict):
                continue
            display = value.get("lexicon_word") or key
            if not isinstance(display, str) or not display.strip():
                continue
            display = display.strip()
            norm = display.lower()
            token_update = updates.setdefault(norm, TokenUpdate(token=norm, display=display))
            token_update.touch(meta.identifier)

            frequency = value.get("frequency") or 0
            try:
                frequency_int = int(frequency)
            except (TypeError, ValueError):
                frequency_int = 0
            if frequency_int <= 0:
                before_counts = flatten_context(value.get("before") or {})
                after_counts = flatten_context(value.get("after") or {})
                frequency_int = sum(count for bucket in before_counts.values() for _, count in bucket)
                frequency_int += sum(count for bucket in after_counts.values() for _, count in bucket)
            else:
                before_counts = flatten_context(value.get("before") or {})
                after_counts = flatten_context(value.get("after") or {})

            token_update.add_frequency(frequency_int)
            token_update.merge_context(before_counts, token_update.before)
            token_update.merge_context(after_counts, token_update.after)

            report_frequency_added += frequency_int
            report_token_updates += 1
            tokens_seen += 1

        if tqdm is not None and hasattr(token_iterable, "close"):
            token_iterable.close()

        summaries.append({
            "id": meta.identifier,
            "path": str(meta.path),
            "sha256": meta.sha256,
            "size": meta.size,
            "mtime": meta.timestamp,
            "window": window,
            "device": device_used,
            "tokens": report_token_updates,
            "frequency_added": report_frequency_added,
        })
        processed[meta.sha256] = {
            "id": meta.identifier,
            "path": str(meta.path),
            "size": meta.size,
            "mtime": meta.timestamp,
        }

    state["processed"] = processed

    if tqdm is not None and hasattr(report_iterable, "close"):
        report_iterable.close()
    return updates, summaries


def iter_json_array(path: Path) -> Iterator[Dict[str, object]]:
    if not path.exists():
        raise FileNotFoundError(f"Lexicon file not found: {path}")

    if ijson is not None:
        with path.open("rb") as handle:
            for item in ijson.items(handle, "item"):
                if isinstance(item, dict):
                    yield item
        return

    decoder = json.JSONDecoder()
    buffer = ""
    with path.open("r", encoding="utf-8") as handle:
        in_array = False
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            buffer += chunk
            while True:
                if not in_array:
                    buffer = buffer.lstrip()
                    if not buffer:
                        break
                    if buffer[0] != "[":
                        raise ValueError(f"Expected '[' at start of {path}")
                    buffer = buffer[1:]
                    in_array = True

                buffer = buffer.lstrip()
                if not buffer:
                    break
                if buffer[0] == "]":
                    return
                try:
                    obj, idx = decoder.raw_decode(buffer)
                except json.JSONDecodeError:
                    break
                yield obj
                buffer = buffer[idx:]
                buffer = buffer.lstrip()
                if buffer.startswith(","):
                    buffer = buffer[1:]
                    continue
                if buffer.startswith("]"):
                    return
        buffer = buffer.strip()
        if buffer and buffer != "]":
            raise ValueError(f"Unexpected trailing data while reading {path}")


def normalise_entry(entry: Dict[str, object]) -> Dict[str, object]:
    token = entry.get("token") or entry.get("word")
    if isinstance(token, str):
        token = token.strip()
    if not token:
        raise ValueError("Lexicon entry missing token/word")
    entry["token"] = token
    entry.setdefault("word", token)
    entry.setdefault("aliases", [])
    entry.setdefault("categories", [])
    entry.setdefault("notes", "")
    entry.setdefault("status", "enriched")
    entry.setdefault("payload", {})
    entry.setdefault("context_before", {})
    entry.setdefault("context_after", {})
    entry.setdefault("frequency", 0)
    entry.setdefault("timestamp", dt.datetime.now(dt.timezone.utc).isoformat())
    return entry


def trim_bucket(counter: Counter, limit: int) -> List[Dict[str, int]]:
    return [
        {"token": token, "count": int(count)}
        for token, count in counter.most_common(limit)
    ]


def merge_entry(entry: Dict[str, object], update: TokenUpdate, timestamp: str, max_bucket: int,
                max_sources: int) -> Dict[str, object]:
    entry = normalise_entry(entry)
    current_freq = entry.get("frequency", 0)
    try:
        current_freq_int = int(current_freq)
    except (TypeError, ValueError):
        current_freq_int = 0
    entry["frequency"] = current_freq_int + update.frequency

    for ctx_key, source in (("context_before", update.before), ("context_after", update.after)):
        current = entry.get(ctx_key) or {}
        if not isinstance(current, dict):
            current = {}
        merged: Dict[str, Counter] = defaultdict(Counter)
        for distance, items in current.items():
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                token = item.get("token")
                try:
                    count = int(item.get("count", 0))
                except (TypeError, ValueError):
                    count = 0
                if token:
                    merged[str(distance)][token] += max(count, 0)
        for distance, counter in source.items():
            merged[str(distance)].update(counter)
        entry[ctx_key] = {
            distance: trim_bucket(counter, max_bucket)
            for distance, counter in merged.items()
            if counter
        }

    payload = entry.get("payload", {})
    if not isinstance(payload, dict):
        payload = {}
    enrichment = payload.get("enrichment")
    if not isinstance(enrichment, dict):
        enrichment = {}
    report_ids = enrichment.get("report_ids", [])
    if not isinstance(report_ids, list):
        report_ids = []
    combined_ids = report_ids + update.report_ids
    seen: List[str] = []
    for identifier in combined_ids[-max_sources:]:
        if identifier not in seen:
            seen.append(identifier)
    enrichment["report_ids"] = seen[-max_sources:]
    enrichment["last_enriched"] = timestamp
    payload["enrichment"] = enrichment
    entry["payload"] = payload
    entry["timestamp"] = timestamp
    entry.setdefault("symbol", None)
    entry.setdefault("aliases", [])
    entry.setdefault("categories", [])
    entry.setdefault("notes", "")
    return entry


def create_entry(update: TokenUpdate, timestamp: str, max_bucket: int, max_sources: int) -> Dict[str, object]:
    entry = {
        "token": update.display,
        "word": update.display,
        "symbol": None,
        "frequency": update.frequency,
        "payload": {},
        "context_before": {},
        "context_after": {},
        "aliases": [],
        "categories": [],
        "notes": "",
        "status": "enriched",
        "timestamp": timestamp,
    }
    entry = merge_entry(entry, update, timestamp, max_bucket, max_sources)
    return entry


def write_lexicon(lexicon_path: Path, updates: Dict[str, TokenUpdate], *, dry_run: bool, max_bucket: int,
                  max_sources: int, make_backup: bool) -> Dict[str, int]:
    timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
    processed_tokens = set()
    total_existing = 0
    total_new = 0

    if not lexicon_path.exists():
        raise FileNotFoundError(f"Lexicon file not found: {lexicon_path}")

    tmp_path = lexicon_path.with_suffix(".tmp")
    if not dry_run:
        if make_backup:
            backup_path = lexicon_path.with_suffix(".bak")
            shutil.copy2(lexicon_path, backup_path)
            LOGGER.info("Backup written to %s", backup_path)
        dst = tmp_path.open("w", encoding="utf-8")
    else:
        dst = None

    try:
        first = True
        if not dry_run:
            dst.write("[")
        for entry in iter_json_array(lexicon_path):
            try:
                normalised = normalise_entry(entry)
            except ValueError:
                continue
            norm = normalised["token"].lower()
            if norm in updates:
                normalised = merge_entry(normalised, updates[norm], timestamp, max_bucket, max_sources)
                processed_tokens.add(norm)
            total_existing += 1
            if not dry_run:
                if not first:
                    dst.write(",\n")
                json.dump(normalised, dst, ensure_ascii=False)
                first = False
        remaining = [updates[key] for key in updates if key not in processed_tokens]
        remaining.sort(key=lambda item: item.display.lower())
        for update in remaining:
            total_new += 1
            entry = create_entry(update, timestamp, max_bucket, max_sources)
            if not dry_run:
                if not first:
                    dst.write(",\n")
                json.dump(entry, dst, ensure_ascii=False)
                first = False
        if not dry_run:
            dst.write("]\n")
    finally:
        if dst is not None:
            dst.close()

    if not dry_run:
        tmp_path.replace(lexicon_path)
        LOGGER.info("Lexicon updated: %s existing entries touched, %s new entries appended", len(processed_tokens), total_new)
    else:
        LOGGER.info("Dry run complete: %s existing entries would be updated, %s new entries appended", len(processed_tokens), total_new)

    return {
        "existing_touched": len(processed_tokens),
        "new_entries": total_new,
        "timestamp": timestamp,
    }


def run_validator(lexicon_path: Path) -> None:
    validator = Path("tools/validate_lexicon_schema.py")
    if not validator.exists():
        LOGGER.warning("Validator script %s not found; skipping", validator)
        return
    import subprocess

    LOGGER.info("Running schema validator")
    proc = subprocess.run([
        "python",
        str(validator),
        "--input",
        str(lexicon_path),
    ], check=False)
    if proc.returncode != 0:
        raise RuntimeError("Schema validation failed")


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(levelname)s %(message)s")

    lexicon_path = args.lexicon
    state_path = args.state or lexicon_path.with_name(STATE_FILENAME)

    report_paths: List[Path]
    if args.report:
        report_paths = [Path(p) for p in args.report]
    else:
        report_paths = discover_reports(args.reports_root)

    if not report_paths:
        LOGGER.info("No reports discovered; nothing to do")
        return

    state = load_state(state_path)
    updates, summaries = aggregate_reports(report_paths, state, force=args.force, limit_tokens=args.limit_tokens)

    if not updates:
        LOGGER.info("No new token updates detected; exiting")
        if summaries:
            state.setdefault("history", []).append({
                "run_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "reports": summaries,
                "tokens_updated": 0,
                "frequency_added": 0,
            })
            if not args.dry_run:
                store_state(state_path, state)
        return

    run_stats = write_lexicon(
        lexicon_path,
        updates,
        dry_run=args.dry_run,
        max_bucket=args.max_bucket,
        max_sources=args.max_sources,
        make_backup=not args.no_backup,
    )

    total_frequency = sum(update.frequency for update in updates.values())

    history_entry = {
        "run_at": run_stats["timestamp"],
        "reports": summaries,
        "tokens_updated": len(updates),
        "existing_touched": run_stats["existing_touched"],
        "new_entries": run_stats["new_entries"],
        "frequency_added": total_frequency,
        "dry_run": args.dry_run,
    }
    state.setdefault("history", []).append(history_entry)

    if not args.dry_run:
        store_state(state_path, state)
    else:
        LOGGER.info("Dry run; state file not updated")

    LOGGER.info(
        "Enrichment complete: %s tokens updated (%s existing, %s new), frequency +%s",
        len(updates),
        run_stats["existing_touched"],
        run_stats["new_entries"],
        total_frequency,
    )

    if args.validate and not args.dry_run:
        run_validator(lexicon_path)


if __name__ == "__main__":
    main()
