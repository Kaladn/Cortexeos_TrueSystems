"""Migrate the monolithic lexicon into the governed address-space codex.

This script:
    1. Reads Lexicon_Canonical/lexicon_v2.json (134.5 MB, 147K entries)
    2. Partitions entries by first letter → 28 files (A-Z + _numeric + _other)
    3. Writes to lexicon/system/ under CLEARBOX_DATA_ROOT (protected zone)
    4. Generates manifest.json with entry counts + checksums
    5. Verifies round-trip integrity

After migration:
    - lexicon/system/ is the authoritative source (protected, read-only)
    - Lexicon_Canonical/lexicon_v2.json becomes legacy (kept for rollback)
    - The bridge reads from the partitioned layout

Usage:
    python scripts/migrate_lexicon.py [--dry-run]
"""

import argparse
import hashlib
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from security.storage_layout import (
    LEGACY_LEXICON_DIR,
    LEXICON_SYSTEM_DIR,
    LEXICON_PARTITIONS,
    lexicon_partition_key,
    lexicon_system_path,
    lexicon_manifest_path,
    build_lexicon_manifest,
    content_hash,
)


def migrate(dry_run: bool = False) -> dict:
    """Migrate lexicon_v2.json → partitioned address-space codex.

    Returns summary dict with counts and timing.
    """
    source = LEGACY_LEXICON_DIR / "lexicon_v2.json"
    if not source.exists():
        print(f"❌ Source not found: {source}")
        return {"error": "source not found"}

    print(f"📖 Reading {source} ...")
    start = time.time()
    with open(source, "r", encoding="utf-8") as f:
        raw = json.load(f)
    read_time = time.time() - start
    print(f"   {len(raw):,} entries loaded in {read_time:.1f}s")

    # ── Handle both formats: list of objects or dict ──────────
    # Current format: list of {"token": "...", "symbol": null, ...}
    # Normalize to dict keyed by token
    if isinstance(raw, list):
        print(f"   Format: list of objects (keying by 'token' field)")
        entries: dict[str, Any] = {}
        for item in raw:
            token = item.get("token", "")
            if token:
                entries[token] = item
        if len(entries) != len(raw):
            dupes = len(raw) - len(entries)
            print(f"   ⚠️  {dupes} duplicate tokens collapsed")
    elif isinstance(raw, dict):
        print(f"   Format: dict keyed by token")
        entries = raw
    else:
        print(f"❌ Unexpected format: {type(raw).__name__}")
        return {"error": f"unexpected format: {type(raw).__name__}"}

    # ── Partition by first letter ─────────────────────────────
    partitions: dict[str, dict] = defaultdict(dict)
    for token, entry in entries.items():
        key = lexicon_partition_key(token)
        partitions[key][token] = entry

    # ── Report partition distribution ─────────────────────────
    print(f"\n📊 Partition distribution ({len(partitions)} partitions):")
    part_counts = {}
    total = 0
    for pfile in LEXICON_PARTITIONS:
        count = len(partitions.get(pfile, {}))
        if count > 0:
            part_counts[pfile] = count
            total += count
    
    # Show sorted by count
    for pfile, count in sorted(part_counts.items(), key=lambda x: -x[1])[:10]:
        bar = "█" * (count // 1000)
        print(f"   {pfile:>15s}: {count:>7,} {bar}")
    if len(part_counts) > 10:
        print(f"   ... and {len(part_counts) - 10} more partitions")
    print(f"   {'TOTAL':>15s}: {total:>7,}")

    # ── Integrity check ───────────────────────────────────────
    if total != len(entries):
        print(f"❌ Partition count mismatch: {total} partitioned vs {len(entries)} original")
        return {"error": "count mismatch"}

    if dry_run:
        print("\n🧪 DRY RUN — no files written")
        return {
            "total": total,
            "partitions": len(part_counts),
            "dry_run": True,
        }

    # ── Write partition files ─────────────────────────────────
    print(f"\n📝 Writing to {LEXICON_SYSTEM_DIR} ...")
    LEXICON_SYSTEM_DIR.mkdir(parents=True, exist_ok=True)
    write_start = time.time()

    partition_hashes = {}
    for pfile in LEXICON_PARTITIONS:
        data = partitions.get(pfile, {})
        if not data:
            continue
        dest = lexicon_system_path(pfile)
        text = json.dumps(data, ensure_ascii=False, indent=None, separators=(",", ":"))
        dest.write_text(text, encoding="utf-8")
        partition_hashes[pfile] = content_hash(text)

    write_time = time.time() - write_start
    print(f"   {len(partition_hashes)} files written in {write_time:.1f}s")

    # ── Write manifest ────────────────────────────────────────
    manifest = build_lexicon_manifest(
        name="wordnet_147k",
        layer="system",
        version="2.0.0",
        entry_count=total,
        partitions=part_counts,
        description="WordNet 3.1 bulk import, partitioned into address-space codex",
        source=str(source),
    )
    manifest["partition_hashes"] = partition_hashes

    manifest_path = lexicon_manifest_path("system")
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"   Manifest: {manifest_path}")

    # ── Verify round-trip ─────────────────────────────────────
    print("\n🔍 Verifying round-trip integrity ...")
    verify_count = 0
    for pfile in LEXICON_PARTITIONS:
        path = lexicon_system_path(pfile)
        if not path.exists():
            continue
        loaded = json.loads(path.read_text(encoding="utf-8"))
        verify_count += len(loaded)

    if verify_count == total:
        print(f"   ✅ Round-trip verified: {verify_count:,} == {total:,}")
    else:
        print(f"   ❌ Round-trip FAILED: {verify_count:,} != {total:,}")
        return {"error": "round-trip failed"}

    # ── Summary ───────────────────────────────────────────────
    elapsed = time.time() - start
    summary = {
        "total": total,
        "partitions": len(partition_hashes),
        "manifest": str(manifest_path),
        "destination": str(LEXICON_SYSTEM_DIR),
        "elapsed_seconds": round(elapsed, 1),
        "verified": True,
    }

    print(f"\n✅ Migration complete in {elapsed:.1f}s")
    print(f"   Source:  {source}")
    print(f"   Dest:    {LEXICON_SYSTEM_DIR}")
    print(f"   Entries: {total:,}")
    print(f"   Files:   {len(partition_hashes)} partitions + manifest")

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate lexicon to partitioned layout")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without writing")
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)
