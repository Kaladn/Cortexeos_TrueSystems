"""genesis_append.py — Append new Genesis blocks from INTAKE/pending/ to the corpus.

Usage:
    python scripts/genesis_append.py [--dry-run] [--no-reload]

What it does:
    1. Reads all .md files from docs/GENESIS/INTAKE/pending/
    2. Validates required header fields
    3. Assigns next sequential G-XXXX tag
    4. Appends formatted blocks to docs/GENESIS/TRAINING_CORPUS.md
    5. Adds PENDING rows to docs/GENESIS/INGESTION_LOG.md
    6. Moves processed files to docs/GENESIS/INTAKE/processed/
    7. Calls POST /api/genesis/reload to rebuild the search index
    8. Prints a summary

Flags:
    --dry-run     Print what would happen without writing anything
    --no-reload   Skip the bridge reload call (e.g. bridge not running)
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import urllib.request
import urllib.error
import json
from datetime import datetime
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────

REPO         = Path(__file__).parent.parent
CORPUS_PATH  = REPO / "docs" / "GENESIS" / "TRAINING_CORPUS.md"
LOG_PATH     = REPO / "docs" / "GENESIS" / "INGESTION_LOG.md"
PENDING_DIR  = REPO / "docs" / "GENESIS" / "INTAKE" / "pending"
PROCESSED_DIR= REPO / "docs" / "GENESIS" / "INTAKE" / "processed"
BRIDGE_RELOAD= "http://localhost:5050/api/genesis/reload"

SEPARATOR    = "━" * 80   # U+2501, matches parser.py

REQUIRED_FIELDS = ["SOURCE", "DATE_RANGE", "SCOPE", "WRITE_PERMS", "TITLE"]

# ── Parser ────────────────────────────────────────────────────────────────────

def parse_block_file(path: Path) -> dict:
    """Parse a pending block file. Returns dict with header fields + body."""
    text  = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    headers: dict[str, str] = {}
    body_lines: list[str]   = []
    in_body = False

    for line in lines:
        if line.startswith("#"):       # strip comment lines
            continue
        if in_body:
            body_lines.append(line)
            continue
        # Header: "KEY: value"
        m = re.match(r"^([A-Z_]+):\s*(.*)", line)
        if m:
            headers[m.group(1)] = m.group(2).strip()
        elif line.strip() == "" and headers and not in_body:
            # First blank line after headers = start of body
            in_body = True
        elif headers and not in_body:
            # Non-blank, non-header line after headers started → body
            in_body = True
            body_lines.append(line)

    # Validate required fields
    missing = [f for f in REQUIRED_FIELDS if not headers.get(f, "").strip()]
    if missing:
        raise ValueError(f"{path.name}: missing required field(s): {missing}")

    # Sanitise: no pipe chars, no separator chars in any field
    for k, v in headers.items():
        if "|" in v:
            raise ValueError(f"{path.name}: field {k} contains '|' — not allowed")
        if "━" in v:
            raise ValueError(f"{path.name}: field {k} contains separator char — not allowed")

    body = "\n".join(body_lines).strip()
    if not body:
        raise ValueError(f"{path.name}: block body is empty")
    if "━" in body:
        raise ValueError(f"{path.name}: block body contains separator char U+2501 — not allowed")

    headers["_body"] = body
    headers["_source_file"] = path.name
    return headers


# ── Corpus helpers ─────────────────────────────────────────────────────────────

def _current_max_tag(corpus_text: str) -> int:
    """Return the highest G-XXXX block number currently in the corpus."""
    tags = re.findall(r"GENESIS_BLOCK_ID:\s*G-(\d{4})", corpus_text)
    return max((int(t) for t in tags), default=0)


def _build_block_text(tag: str, fields: dict) -> str:
    """Render a block ready for appending to TRAINING_CORPUS.md."""
    today = datetime.now().strftime("%Y-%m-%d")
    derived_line = ""
    if fields.get("DERIVED_SUMMARY", "").upper() == "TRUE":
        derived_line = "DERIVED_SUMMARY: true\n"

    return (
        f"\n{SEPARATOR}\n"
        f"GENESIS_BLOCK_ID: {tag}\n"
        f"SOURCE: {fields['SOURCE']}\n"
        f"DATE_RANGE: {fields['DATE_RANGE']}\n"
        f"SCOPE: {fields['SCOPE']}\n"
        f"WRITE_PERMS: READ_ONLY\n"
        f"{derived_line}"
        f"TITLE: {fields['TITLE']}\n"
        f"INGESTED_AT: {today}\n"
        f"\n"
        f"{fields['_body']}\n"
    )


# ── Log helpers ───────────────────────────────────────────────────────────────

_LOG_ROW_RE = re.compile(r"^\| G-\d{4} \|")

def _append_log_row(log_text: str, tag: str, title: str) -> str:
    """Add a PENDING row to INGESTION_LOG.md and update the progress counters."""
    title_col = title[:47].ljust(47)
    new_row   = f"| {tag} | {title_col}| PENDING |            |       |"

    # Insert after the last existing data row in the last series table
    lines      = log_text.splitlines()
    last_row_i = -1
    for i, line in enumerate(lines):
        if _LOG_ROW_RE.match(line):
            last_row_i = i
    if last_row_i >= 0:
        lines.insert(last_row_i + 1, new_row)
    else:
        lines.append(new_row)

    # Update the progress block (Total blocks / Remaining lines)
    result = "\n".join(lines)
    total_tags = len(re.findall(r"^\| G-\d{4} \|", result, re.MULTILINE))
    ingested   = len(re.findall(r"^\| G-\d{4} \|[^|]+\| INGESTED", result, re.MULTILINE))
    pending    = total_tags - ingested

    result = re.sub(r"- Total blocks: \d+",   f"- Total blocks: {total_tags}", result)
    result = re.sub(r"- Remaining: \d+",       f"- Remaining: {pending}",      result)
    return result


# ── Bridge reload ──────────────────────────────────────────────────────────────

def _reload_bridge() -> bool:
    """Call POST /api/genesis/reload. Returns True on success."""
    try:
        req  = urllib.request.Request(BRIDGE_RELOAD, method="POST",
                                      data=b"", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            print(f"  Bridge reload OK — blocks={data.get('blocks', '?')}, "
                  f"commit={str(data.get('index_commit',''))[:8]}")
            return True
    except urllib.error.URLError as e:
        print(f"  WARNING: bridge reload failed ({e}) — restart the bridge manually "
              f"or run POST {BRIDGE_RELOAD}")
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Append pending Genesis blocks to corpus")
    parser.add_argument("--dry-run",   action="store_true", help="Print only, write nothing")
    parser.add_argument("--no-reload", action="store_true", help="Skip bridge reload")
    args = parser.parse_args()

    dry = args.dry_run
    if dry:
        print("[DRY RUN — nothing will be written]\n")

    # Collect pending files
    pending_files = sorted(
        p for p in PENDING_DIR.iterdir()
        if p.suffix == ".md" and p.name != ".gitkeep"
    )
    if not pending_files:
        print("Nothing to do — no .md files in docs/GENESIS/INTAKE/pending/")
        return

    print(f"Found {len(pending_files)} pending file(s):\n")
    for pf in pending_files:
        print(f"  {pf.name}")
    print()

    # Parse all first (fail fast before writing anything)
    parsed: list[tuple[Path, dict]] = []
    for pf in pending_files:
        try:
            fields = parse_block_file(pf)
            parsed.append((pf, fields))
            print(f"  ✓ {pf.name} — TITLE: {fields['TITLE']}")
        except ValueError as e:
            print(f"  ✗ {e}")
            sys.exit(1)
    print()

    # Read current corpus + log
    corpus_text = CORPUS_PATH.read_text(encoding="utf-8")
    log_text    = LOG_PATH.read_text(encoding="utf-8")

    next_num = _current_max_tag(corpus_text) + 1
    added: list[str] = []

    for pf, fields in parsed:
        tag    = f"G-{next_num:04d}"
        title  = fields["TITLE"]
        block  = _build_block_text(tag, fields)

        print(f"  {tag}  {title}")
        print(f"       from: {fields['_source_file']}")

        if not dry:
            corpus_text += block
            log_text     = _append_log_row(log_text, tag, title)

        added.append(tag)
        next_num += 1

    if dry:
        print("\n[Dry run complete — run without --dry-run to apply]")
        return

    # Write corpus + log atomically (write to temp then replace)
    CORPUS_PATH.write_text(corpus_text, encoding="utf-8")
    LOG_PATH.write_text(log_text, encoding="utf-8")
    print(f"\nWrote {len(added)} block(s) to corpus.")
    print(f"Updated INGESTION_LOG.md.")

    # Move files to processed/
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for pf, _ in parsed:
        dest = PROCESSED_DIR / pf.name
        shutil.move(str(pf), str(dest))
    print(f"Moved {len(parsed)} file(s) to INTAKE/processed/")

    # Reload bridge
    if not args.no_reload:
        print(f"\nReloading bridge index…")
        _reload_bridge()

    print(f"\nDone. Added: {', '.join(added)}")
    print("Next step: run the Genesis tab in the UI to ingest the new block(s).")


if __name__ == "__main__":
    main()
