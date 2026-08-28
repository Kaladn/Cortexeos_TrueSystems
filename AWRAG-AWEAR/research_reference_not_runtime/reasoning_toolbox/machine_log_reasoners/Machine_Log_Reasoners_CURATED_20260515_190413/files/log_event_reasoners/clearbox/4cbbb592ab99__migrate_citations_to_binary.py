"""Migrate data citations from JSON sidecars + library files to binary store.

Non-destructive: reads existing JSON files, never modifies or deletes them.
Writes to DATA_CITATIONS_BIN_DIR (citations/binary/).

Usage:
    python scripts/migrate_citations_to_binary.py [--dry-run]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Add repo root to path for imports
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from security.data_paths import CHAT_CITATIONS_DIR, DATA_CITATIONS_BIN_DIR
from bridges.binary_store import CitationStoreWriter, CitationRecord


def _is_data_citation(record: dict) -> bool:
    """True if this citation belongs in the data layer (INGEST or DOC coord)."""
    coord = record.get("coord", record.get("canonical", ""))
    if coord.startswith("INGEST:"):
        return True
    if coord.startswith("DOC:") or ":DOC:" in coord:
        return True
    return False


def _load_day_sharded(path: Path) -> list[dict]:
    """Load data citations from a day-sharded sidecar."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    by_id = data.get("by_id", {})
    return [rec for rec in by_id.values() if _is_data_citation(rec)]


def _load_library_cite(path: Path) -> dict | None:
    """Load a library citation file (cite_*.json)."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and _is_data_citation(data):
        return data
    return None


def migrate(dry_run: bool = False) -> dict:
    """Run the migration. Returns stats."""
    citations_dir = CHAT_CITATIONS_DIR
    output_dir = DATA_CITATIONS_BIN_DIR

    if not citations_dir.exists():
        print(f"Source directory not found: {citations_dir}")
        return {"error": "source_not_found"}

    writer = CitationStoreWriter(output_dir)
    stats = {
        "day_sharded_files": 0,
        "library_files": 0,
        "data_citations_found": 0,
        "chat_citations_skipped": 0,
        "errors": 0,
    }

    # 1. Scan day-sharded sidecars: YYYY-MM-DD.citations.json
    day_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}\.citations\.json$")
    for f in sorted(citations_dir.iterdir()):
        if not f.is_file() or not day_pattern.match(f.name):
            continue
        stats["day_sharded_files"] += 1
        print(f"  Scanning {f.name}...", end=" ")
        try:
            with open(f, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            by_id = data.get("by_id", {})
            found = 0
            skipped = 0
            for rec in by_id.values():
                if _is_data_citation(rec):
                    writer.add_from_json(rec)
                    found += 1
                else:
                    skipped += 1
            stats["data_citations_found"] += found
            stats["chat_citations_skipped"] += skipped
            print(f"{found} data, {skipped} chat")
        except Exception as e:
            print(f"ERROR: {e}")
            stats["errors"] += 1

    # 2. Scan library citation files: cite_*.json
    lib_pattern = re.compile(r"^cite_[a-f0-9]+\.json$")
    for f in sorted(citations_dir.iterdir()):
        if not f.is_file() or not lib_pattern.match(f.name):
            continue
        stats["library_files"] += 1
        print(f"  Scanning {f.name} ({f.stat().st_size / 1024:.0f}KB)...", end=" ")
        try:
            rec = _load_library_cite(f)
            if rec:
                writer.add_from_json(rec)
                stats["data_citations_found"] += 1
                print("migrated")
            else:
                stats["chat_citations_skipped"] += 1
                print("skipped (not data citation)")
        except Exception as e:
            print(f"ERROR: {e}")
            stats["errors"] += 1

    print(f"\n{'DRY RUN — ' if dry_run else ''}Migration summary:")
    print(f"  Day-sharded files scanned: {stats['day_sharded_files']}")
    print(f"  Library files scanned:     {stats['library_files']}")
    print(f"  Data citations found:      {stats['data_citations_found']}")
    print(f"  Chat citations skipped:    {stats['chat_citations_skipped']}")
    print(f"  Errors:                    {stats['errors']}")

    if dry_run:
        print("\nDry run complete. No files written.")
        return stats

    if stats["data_citations_found"] == 0:
        print("\nNo data citations to migrate.")
        return stats

    # Write binary store
    write_stats = writer.write()
    stats.update(write_stats)
    print(f"\n  Binary store written: {write_stats['bin_path']}")
    print(f"  Records: {write_stats['records']}")
    print(f"  Size: {write_stats['bin_size'] / 1024:.1f} KB")

    return stats


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    print(f"Citation Binary Migration {'(DRY RUN)' if dry else ''}")
    print(f"  Source: {CHAT_CITATIONS_DIR}")
    print(f"  Target: {DATA_CITATIONS_BIN_DIR}")
    print()
    migrate(dry_run=dry)
