"""Migrate existing 616 maps from workspace to governed data zones.

Moves:
    clearbox_ai/data/maps/clearbox_616/{run_id}/616_map.json
  → data/raw/{run_id}/input.txt + manifest.json     (immutable snapshot)
  → data/mapped/{run_id}/616_map.json + manifest.json (mapping output)

Usage:
    python scripts/migrate_maps.py [--dry-run]
"""

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from security.storage_layout import (
    LEGACY_MAPS_DIR,
    DATA_RAW_DIR,
    DATA_MAPPED_DIR,
    build_raw_manifest,
    build_mapped_manifest,
    content_hash,
)


def migrate(dry_run: bool = False) -> dict:
    """Migrate legacy map outputs to governed data zones."""
    source_dir = LEGACY_MAPS_DIR / "clearbox_616"
    if not source_dir.exists():
        print(f"❌ Source not found: {source_dir}")
        return {"error": "source not found"}

    # Find all run directories
    run_dirs = sorted([d for d in source_dir.iterdir() if d.is_dir()])
    print(f"📦 Found {len(run_dirs)} map runs in {source_dir}")

    migrated = 0
    for run_dir in run_dirs:
        run_id = run_dir.name
        map_file = run_dir / "616_map.json"

        if not map_file.exists():
            print(f"   ⚠️  {run_id}: no 616_map.json, skipping")
            continue

        print(f"   📄 {run_id}: {map_file.stat().st_size // 1024} KB")

        if dry_run:
            migrated += 1
            continue

        # Read the map data
        map_data = json.loads(map_file.read_text(encoding="utf-8"))
        map_text = json.dumps(map_data, ensure_ascii=False, indent=2)

        # ── Write to data/mapped/ ─────────────────────────────
        mapped_dir = DATA_MAPPED_DIR / run_id
        mapped_dir.mkdir(parents=True, exist_ok=True)

        mapped_file = mapped_dir / "616_map.json"
        mapped_file.write_text(map_text, encoding="utf-8")

        # Count entries from the map structure
        entry_count = 0
        mapped_count = 0
        unmapped_count = 0
        if isinstance(map_data, dict):
            items = map_data.get("items", {})
            if isinstance(items, dict):
                entry_count = len(items)
                for t, info in items.items():
                    if isinstance(info, dict) and info.get("symbol"):
                        mapped_count += 1
                    else:
                        unmapped_count += 1
            # Fallback to total_tokens metadata
            if entry_count == 0:
                entry_count = map_data.get("total_tokens", 0)

        mapped_manifest = build_mapped_manifest(
            run_id=run_id,
            raw_run_id=run_id,
            source="legacy_migration",
            lexicon_version="wordnet_147k_v2.0.0",
            entry_count=entry_count,
            mapped_count=mapped_count,
            unmapped_count=unmapped_count,
            output_hash=content_hash(map_text),
        )
        (mapped_dir / "manifest.json").write_text(
            json.dumps(mapped_manifest, indent=2), encoding="utf-8"
        )

        # ── Write to data/raw/ (input snapshot) ──────────────
        raw_dir = DATA_RAW_DIR / run_id
        raw_dir.mkdir(parents=True, exist_ok=True)

        # We don't have the original input text, so record that
        raw_manifest = build_raw_manifest(
            run_id=run_id,
            source="legacy_migration (original input not available)",
            token_count=entry_count,
            input_hash="unavailable",
            lexicon_version="wordnet_147k_v2.0.0",
        )
        (raw_dir / "manifest.json").write_text(
            json.dumps(raw_manifest, indent=2), encoding="utf-8"
        )

        migrated += 1

    # ── Summary ───────────────────────────────────────────────
    action = "would migrate" if dry_run else "migrated"
    print(f"\n✅ {action} {migrated}/{len(run_dirs)} map runs")
    if not dry_run:
        print(f"   Raw:    {DATA_RAW_DIR}")
        print(f"   Mapped: {DATA_MAPPED_DIR}")

    return {"migrated": migrated, "total": len(run_dirs), "dry_run": dry_run}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate maps to governed storage")
    parser.add_argument("--dry-run", action="store_true", help="Show plan without writing")
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)
