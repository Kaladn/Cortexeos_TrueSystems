"""Rebuild the Clearbox AI lexicon into the canonical schema."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, cast

LOGGER = logging.getLogger("rebuild_lexicon")

CANONICAL_FIELDS = {
    "token",
    "symbol",
    "frequency",
    "payload",
    "context_before",
    "context_after",
    "aliases",
    "categories",
    "notes",
    "status",
    "timestamp",
}

LEGACY_SYMBOL_FIELDS = ("symbol", "glyph", "hex", "font_symbol")
LEGACY_FREQUENCY_FIELDS = ("frequency", "freq", "count")
LEGACY_TOKEN_FIELDS = ("token", "word", "status", "name", "label")
CANONICAL_STATUS_DEFAULT = "unassigned"


def canonical_template() -> Dict[str, Any]:
    """Return a fresh canonical entry template."""
    return {
        "token": None,
        "symbol": None,
        "frequency": 0,
        "payload": {},
        "context_before": {},
        "context_after": {},
        "aliases": [],
        "categories": [],
        "notes": "",
        "status": CANONICAL_STATUS_DEFAULT,
        "timestamp": None,
    }


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _ensure_timestamp(existing: Optional[str]) -> str:
    if existing:
        return existing
    return dt.datetime.now(dt.timezone.utc).isoformat()


def normalise_entry(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    record = canonical_template()

    token: Optional[str] = None
    for field in LEGACY_TOKEN_FIELDS:
        raw = entry.get(field)
        if isinstance(raw, str) and raw.strip():
            token = raw.strip()
            break
    if not token:
        return None
    record["token"] = token

    for field in LEGACY_SYMBOL_FIELDS:
        raw = entry.get(field)
        if isinstance(raw, str) and raw.strip():
            record["symbol"] = raw.strip()
            break

    freq = None
    for field in LEGACY_FREQUENCY_FIELDS:
        if field in entry:
            freq = entry.get(field)
            break
    record["frequency"] = _coerce_int(freq, default=0)

    if isinstance(entry.get("context_before"), dict):
        record["context_before"] = cast(Dict[str, List[Dict[str, Any]]], deepcopy(entry["context_before"]))
    if isinstance(entry.get("context_after"), dict):
        record["context_after"] = cast(Dict[str, List[Dict[str, Any]]], deepcopy(entry["context_after"]))

    if isinstance(entry.get("aliases"), list):
        record["aliases"] = [str(item) for item in entry["aliases"] if isinstance(item, (str, int, float))]
    if isinstance(entry.get("categories"), list):
        record["categories"] = [str(item) for item in entry["categories"] if isinstance(item, (str, int, float))]

    if isinstance(entry.get("notes"), str):
        record["notes"] = entry["notes"].strip()

    status = entry.get("status")
    if isinstance(status, str) and status.strip():
        record["status"] = status.strip()

    record["timestamp"] = _ensure_timestamp(entry.get("timestamp"))

    payload: Dict[str, Any] = {}
    for key, value in entry.items():
        if key in CANONICAL_FIELDS:
            continue
        if key in LEGACY_SYMBOL_FIELDS or key in LEGACY_FREQUENCY_FIELDS or key in LEGACY_TOKEN_FIELDS:
            continue
        payload[key] = value
    record["payload"] = payload

    return record


def merge_entries(base: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two canonical entries for the same token."""
    merged = deepcopy(base)

    for field in ("symbol", "status"):
        if not merged.get(field) and update.get(field):
            merged[field] = update[field]

    if _coerce_int(update.get("frequency", 0)):
        merged["frequency"] = max(_coerce_int(merged.get("frequency", 0)), _coerce_int(update["frequency"]))

    for ctx_field in ("context_before", "context_after"):
        merged_ctx = cast(Dict[str, List[Dict[str, Any]]], merged.get(ctx_field) or {})
        update_ctx = cast(Dict[str, Sequence[Dict[str, Any]]], update.get(ctx_field) or {})
        for distance, items in update_ctx.items():
            if distance not in merged_ctx:
                merged_ctx[distance] = []
            merged_items = merged_ctx[distance]
            existing = {item["token"]: item for item in merged_items if "token" in item}
            for item in items:
                token = item.get("token")
                if not token:
                    continue
                current = existing.get(token)
                if current:
                    current_count = _coerce_int(current.get("count", 0))
                    incoming_count = _coerce_int(item.get("count", 0))
                    current["count"] = max(current_count, incoming_count)
                else:
                    merged_items.append({"token": token, "count": _coerce_int(item.get("count", 0))})
            merged_ctx[distance] = merged_items
        merged[ctx_field] = merged_ctx

    for list_field in ("aliases", "categories"):
        merged_list = list(merged.get(list_field, []))
        existing_set = {str(item) for item in merged_list}
        for item in update.get(list_field, []):
            sval = str(item)
            if sval not in existing_set:
                merged_list.append(sval)
                existing_set.add(sval)
        merged[list_field] = merged_list

    if update.get("notes"):
        if merged.get("notes"):
            if update["notes"] not in merged["notes"]:
                merged["notes"] = f"{merged['notes']} | {update['notes']}"
        else:
            merged["notes"] = update["notes"]

    merged_payload = merged.get("payload", {}).copy()
    merged_payload.update(update.get("payload", {}))
    merged["payload"] = merged_payload

    merged["timestamp"] = update.get("timestamp", merged.get("timestamp"))
    return merged


def _iter_entry_dicts(obj: Any) -> Iterable[Dict[str, Any]]:
    if isinstance(obj, dict):
        for value_any in cast(Iterable[Any], obj.values()):
            if isinstance(value_any, dict):
                yield cast(Dict[str, Any], value_any)
    elif isinstance(obj, list):
        for value_any in cast(Iterable[Any], obj):
            if isinstance(value_any, dict):
                yield cast(Dict[str, Any], value_any)


def load_curated(path: Optional[Path]) -> List[Dict[str, Any]]:
    if not path:
        return []
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    iterable_list: List[Dict[str, Any]] = list(_iter_entry_dicts(data))
    if not iterable_list:
        raise ValueError("Curated file must be a list or object of entries")
    entries: List[Dict[str, Any]] = []
    for entry in iterable_list:
        normalised = normalise_entry(entry)
        if normalised:
            entries.append(normalised)
    return entries


def iter_source_entries(source_dir: Path) -> Iterable[Dict[str, Any]]:
    for path in sorted(source_dir.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception as exc:  # pragma: no cover - diagnostic output
            LOGGER.warning("Failed to load %s: %s", path, exc)
            continue

        iterable_list = list(_iter_entry_dicts(data))
        if not iterable_list:
            LOGGER.warning("Unsupported JSON root in %s (type %s)", path, type(data).__name__)
            continue

        for entry in iterable_list:
            yield entry


def rebuild_lexicon(source: Path, curated_path: Optional[Path], output: Path) -> Dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)

    records: Dict[str, Dict[str, Any]] = {}
    skipped = 0

    for entry in iter_source_entries(source):
        normalised = normalise_entry(entry)
        if not normalised:
            skipped += 1
            continue
        token = normalised["token"]
        if token in records:
            records[token] = merge_entries(records[token], normalised)
        else:
            records[token] = normalised

    curated_entries = load_curated(curated_path)
    for entry in curated_entries:
        token = entry["token"]
        if token in records:
            records[token] = merge_entries(records[token], entry)
        else:
            records[token] = entry

    sorted_records = sorted(records.values(), key=lambda item: item["token"].lower())

    with output.open("w", encoding="utf-8") as handle:
        json.dump(sorted_records, handle, ensure_ascii=False, indent=2)

    return {
        "total": len(sorted_records),
        "skipped": skipped,
        "curated": len(curated_entries),
        "output": str(output),
    }


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rebuild lexicon into canonical schema")
    parser.add_argument("--source", type=Path, default=Path("Cleaned_Lexicon"))
    parser.add_argument("--output", type=Path, default=Path("Lexicon_Canonical/lexicon_v2.json"))
    parser.add_argument("--curated", type=Path, default=None)
    parser.add_argument("--log-level", default="INFO")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO), format="%(levelname)s %(message)s")

    if not args.source.exists():
        raise SystemExit(f"Source directory not found: {args.source}")

    stats = rebuild_lexicon(args.source, args.curated, args.output)
    LOGGER.info("Lexicon rebuild complete: %s entries (skipped %s, curated %s)", stats["total"], stats["skipped"], stats["curated"])
    LOGGER.info("Output written to %s", stats["output"])


if __name__ == "__main__":
    main()
