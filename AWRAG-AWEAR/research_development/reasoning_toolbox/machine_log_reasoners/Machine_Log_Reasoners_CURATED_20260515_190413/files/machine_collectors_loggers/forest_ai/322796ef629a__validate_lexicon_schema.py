"""Validate or repair lexicon entries against the canonical schema."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, cast

from rebuild_lexicon import (
    CANONICAL_FIELDS,
    CANONICAL_STATUS_DEFAULT,
    canonical_template,
)


def ensure_timestamp(existing: Any) -> str:
    if isinstance(existing, str) and existing:
        return existing
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def validate_entry(entry: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    if not isinstance(entry.get("token"), str) or not entry["token"].strip():
        issues.append("missing-token")
    for field in CANONICAL_FIELDS:
        if field not in entry:
            issues.append(f"missing-{field}")
    return issues


def fix_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    fixed = canonical_template()
    fixed.update(entry)
    if not fixed.get("token") and entry.get("token"):
        fixed["token"] = str(entry["token"]).strip()
    if not fixed.get("status"):
        fixed["status"] = CANONICAL_STATUS_DEFAULT
    fixed["timestamp"] = ensure_timestamp(fixed.get("timestamp"))
    return fixed


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Forest AI lexicon schema")
    parser.add_argument("--input", type=Path, default=Path("Lexicon_Canonical/lexicon_v2.json"))
    parser.add_argument("--fix", action="store_true", help="Repair entries in-place")
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Lexicon file not found: {args.input}")

    data = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("Lexicon file must contain a list of entries")

    issues_total = 0
    repaired: List[Dict[str, Any]] = []
    entries_raw = cast(List[Any], data)
    for entry in entries_raw:
        if not isinstance(entry, dict):
            issues_total += 1
            continue
        dict_entry = cast(Dict[str, Any], entry)
        issues = validate_entry(dict_entry)
        if issues:
            issues_total += 1
        if args.fix:
            repaired.append(fix_entry(dict_entry))
        else:
            repaired.append(dict_entry)

    if args.fix:
        args.input.write_text(json.dumps(repaired, ensure_ascii=False, indent=2), encoding="utf-8")

    if issues_total:
        print(f"Schema validation found issues in {issues_total} entries{' (repaired)' if args.fix else ''}.")
    else:
        print("Lexicon schema validated successfully.")


if __name__ == "__main__":
    main()
