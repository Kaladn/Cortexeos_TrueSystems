#!/usr/bin/env python3
"""
Build a massive symbol reserve pool using the Symbol Genome Protocol.

Generates complete entries (hex, binary, font_symbol, tone_signature, status)
ready to use as-is. All fields are deterministic from the 5-byte symbol.

Steps:
  1. Generate all candidate symbols with full field set
  2. Load all live-used symbols (canonical, medical, structural, temp)
  3. Subtract live-used from pool
  4. Dedupe what remains
  5. Write single reserve_pool.bin to generated_pool/
  6. Emit generation report

Output goes to generated_pool/ — does NOT touch live system.
"""

import json
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# ── Symbol Genome Protocol ──────────────────────────────────────────────────

CATEGORIES = {
    "core":         0b000,
    "specialized":  0b001,
    "structural":   0b010,
    "temporary":    0b011,
    "spare":        0b100,
}

PRIORITIES = 8
RESERVED = 0b00
PER_GROUP = 25_000_000   # 25M per byte1 group × 40 groups = 1B total


def sym_to_hex(sym: bytes) -> str:
    return "0x" + sym.hex().upper()


def sym_to_fields(sym: bytes) -> dict:
    """Derive all entry fields from a 5-byte symbol."""
    val = int.from_bytes(sym, "big")
    binary = f"{val:040b}"
    hex_str = sym_to_hex(sym)
    return {
        "binary": binary,
        "hex": hex_str,
        "font_symbol": f"CHAR_{binary[:10]}",
        "tone_signature": f"TONE_{(val % 20000) + 100}",
        "status": "AVAILABLE",
    }


def generate_byte1_values():
    values = []
    for cat_code in CATEGORIES.values():
        for priority in range(PRIORITIES):
            byte1 = (cat_code << 5) | (priority << 2) | RESERVED
            values.append(byte1)
    return values


# ── Live symbol loader ──────────────────────────────────────────────────────

def load_live_used(lexicon_root: Path) -> set:
    """Load all 5-byte symbols currently in use."""
    used = set()
    for subdir in ("Canonical", "Medical", "Structural", "Temp_Pool"):
        d = lexicon_root / subdir
        if not d.exists():
            continue
        for f in sorted(d.glob("*.json")):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
            except (json.JSONDecodeError, OSError):
                continue
            if not isinstance(data, list):
                continue
            for entry in data:
                if isinstance(entry, dict) and entry.get("hex"):
                    try:
                        raw = bytes.fromhex(entry["hex"].replace("0x", "").replace("0X", ""))
                        if len(raw) == 5:
                            used.add(raw)
                    except (ValueError, TypeError):
                        pass
    return used


# ── Main builder ────────────────────────────────────────────────────────────

# Binary record format for reserve pool (compact, no JSON overhead):
#   [5 bytes] symbol
#   [2 bytes] tone (uint16 BE) — (val % 20000) + 100
# Total: 7 bytes per entry
# Full fields derivable from symbol bytes at read time.

RECORD_SIZE = 7
MAGIC = b"CBRP"  # Clearbox Reserve Pool


def build_reserve_pool(lexicon_root: Path, output_dir: Path, per_group: int = PER_GROUP):
    output_dir.mkdir(parents=True, exist_ok=True)
    byte1_values = generate_byte1_values()
    num_groups = len(byte1_values)
    target = per_group * num_groups

    print(f"=== Symbol Reserve Pool Builder ===")
    print(f"  Target:        {target:,}")
    print(f"  Byte1 groups:  {num_groups}")
    print(f"  Per group:     {per_group:,}")
    print(f"  Record size:   {RECORD_SIZE} bytes")
    print(f"  Est file size: ~{(target * RECORD_SIZE + 8) / 1024**3:.2f} GB")
    print()

    # Step 1: Load live-used
    print("Step 1: Loading live-used symbols...")
    t0 = time.time()
    used = load_live_used(lexicon_root)
    print(f"  Live-used: {len(used):,} ({time.time() - t0:.1f}s)")

    # Step 2: Generate, subtract, dedupe — single pass
    print(f"\nStep 2: Generate > subtract > dedupe ({target:,} candidates)...")
    t1 = time.time()

    seen = set()
    kept = 0
    skipped_live = 0
    skipped_dupe = 0
    total_generated = 0

    pool_path = output_dir / "reserve_pool.bin"
    with open(pool_path, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack(">I", 0))  # placeholder count

        for group_idx, byte1 in enumerate(byte1_values):
            buf = bytearray()

            for addr in range(per_group):
                sym = bytes([byte1]) + struct.pack(">I", addr)
                total_generated += 1

                if sym in used:
                    skipped_live += 1
                    continue
                if sym in seen:
                    skipped_dupe += 1
                    continue

                seen.add(sym)
                val = int.from_bytes(sym, "big")
                tone = (val % 20000) + 100
                buf += sym + struct.pack(">H", tone)
                kept += 1

            f.write(buf)

            if (group_idx + 1) % 10 == 0:
                elapsed = time.time() - t1
                rate = total_generated / elapsed / 1e6
                pct = total_generated * 100 / target
                print(f"  [{group_idx+1}/{num_groups}] {pct:.0f}%  "
                      f"kept={kept:,}  skip_live={skipped_live:,}  "
                      f"skip_dupe={skipped_dupe:,}  {rate:.1f}M/s")

        # Write count
        f.seek(4)
        f.write(struct.pack(">I", kept))

    elapsed = time.time() - t1
    file_size = pool_path.stat().st_size

    print(f"\n  Done in {elapsed:.1f}s")
    print(f"  Generated:     {total_generated:,}")
    print(f"  Skipped live:  {skipped_live:,}")
    print(f"  Skipped dupe:  {skipped_dupe:,}")
    print(f"  Final pool:    {kept:,}")
    print(f"  File:          {file_size / 1024**3:.2f} GB")

    # Step 3: Verify
    print(f"\nStep 3: Verifying...")
    assert len(seen) == kept, f"Dedupe error: seen={len(seen)} kept={kept}"
    overlap = seen & used
    assert len(overlap) == 0, f"Overlap with live: {len(overlap)}"
    print(f"  VERIFIED: {kept:,} unique, zero overlap with live")

    # Step 4: Report
    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_candidates": target,
        "total_generated": total_generated,
        "live_used_count": len(used),
        "skipped_live": skipped_live,
        "skipped_dupe": skipped_dupe,
        "final_pool_count": kept,
        "file_path": str(pool_path),
        "file_size_bytes": file_size,
        "record_size_bytes": RECORD_SIZE,
        "symbol_width_bytes": 5,
        "fields_per_symbol": ["hex", "binary", "font_symbol", "tone_signature", "status"],
        "field_derivation": {
            "hex": "0x + symbol.hex().upper()",
            "binary": "40-bit binary string of symbol int",
            "font_symbol": "CHAR_ + binary[:10]",
            "tone_signature": "TONE_ + (int(symbol) % 20000) + 100",
            "status": "always AVAILABLE",
        },
        "how_to_read": (
            "Read 8-byte header (4 magic + 4 uint32 count), "
            "then N x 7-byte records (5 symbol + 2 tone). "
            "All other fields derive from the 5-byte symbol."
        ),
    }
    report_path = output_dir / "generation_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"  Report: {report_path}")

    # Show samples
    print(f"\n  Sample entries:")
    with open(pool_path, "rb") as f:
        f.read(8)  # skip header
        for i in range(5):
            rec = f.read(RECORD_SIZE)
            if len(rec) < RECORD_SIZE:
                break
            sym = rec[:5]
            tone = struct.unpack(">H", rec[5:7])[0]
            fields = sym_to_fields(sym)
            print(f"    {fields['hex']}  bin={fields['binary']}  "
                  f"font={fields['font_symbol']}  tone=TONE_{tone}")

    return report


if __name__ == "__main__":
    lexicon_root = Path(__file__).resolve().parents[1] / "Lexical Data"
    output_dir = Path(__file__).resolve().parents[1] / "generated_pool"
    report = build_reserve_pool(lexicon_root, output_dir)
    print(f"\n=== DONE ===")
    print(f"  {report['final_pool_count']:,} complete symbols ready")
    print(f"  {report['file_path']}")
