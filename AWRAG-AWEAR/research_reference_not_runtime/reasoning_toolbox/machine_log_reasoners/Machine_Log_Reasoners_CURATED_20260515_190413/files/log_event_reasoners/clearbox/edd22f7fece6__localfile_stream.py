#!/usr/bin/env python3
"""Local File Stream — ingest local .txt, .md, .pdf files into LakeSpeak.

Usage:
    python scripts/localfile_stream.py document.txt
    python scripts/localfile_stream.py --dir ./documents --recursive
    python scripts/localfile_stream.py document.txt --dry-run
    python scripts/localfile_stream.py document.txt --force
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# ── Paths ────────────────────────────────────────────────────

WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "plugins"))

MANIFEST_PATH = WORKSPACE_ROOT / "state" / "localfile_manifest.jsonl"
SOURCE_TYPE = "localfile"
SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf"}

# PDF extraction (optional)
try:
    import pdfplumber
    HAS_PDF = True
except ImportError:
    HAS_PDF = False


# ── Fetch ────────────────────────────────────────────────────

def fetch(source_id: str) -> Optional[str]:
    """Read raw content from a local file."""
    try:
        file_path = Path(source_id)
        if not file_path.exists() or not file_path.is_file():
            print(f"   Error: not found — {source_id}")
            return None

        ext = file_path.suffix.lower()

        if ext in {".txt", ".md"}:
            # Contract C: encoding cascade — never errors="ignore"
            text = None
            for enc in ("utf-8-sig", "utf-8", "utf-16", "cp1252"):
                try:
                    text = file_path.read_text(encoding=enc)
                    break
                except (UnicodeDecodeError, ValueError):
                    continue
            if text is None:
                text = file_path.read_text(encoding="utf-8", errors="replace")
            return text

        if ext == ".pdf":
            if not HAS_PDF:
                print("   Error: PDF support requires pdfplumber (pip install pdfplumber)")
                return None
            parts = []
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        parts.append(t)
            return "\n\n".join(parts)

        print(f"   Error: unsupported file type {ext}")
        return None
    except Exception as e:
        print(f"   Error fetching {source_id}: {e}")
        return None


# ── Strip ────────────────────────────────────────────────────

def strip_boilerplate(text: str) -> str:
    """Clean and normalize raw text (BOM, line endings, excessive blanks)."""
    if not text:
        return ""
    if text.startswith("\ufeff"):
        text = text[1:]
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines = text.split("\n")
    cleaned, blank = [], 0
    for line in lines:
        if line.strip():
            cleaned.append(line)
            blank = 0
        else:
            blank += 1
            if blank <= 2:
                cleaned.append(line)
    return "\n".join(cleaned).strip()


# ── Ingest ───────────────────────────────────────────────────

def ingest_file(source_id: str, text: str, bridge, dry_run: bool = False) -> Optional[Dict]:
    """Pipe cleaned text through LakeSpeak ingest."""
    chars = len(text)
    words = len(text.split())

    if dry_run:
        print(f"   [DRY RUN] {chars:,} chars, {words:,} words")
        return {"chars": chars, "words": words, "status": "dry_run"}

    from core.lakespeak.ingest.pipeline import ingest_text
    receipt = ingest_text(
        text=text,
        source_type=SOURCE_TYPE,
        source_path=source_id,
        bridge=bridge,
    )
    if receipt:
        receipt["chars"] = chars
        receipt["words"] = words
    return receipt


# ── Manifest ─────────────────────────────────────────────────

def load_manifest() -> Dict[str, Dict]:
    manifest = {}
    if MANIFEST_PATH.exists():
        for line in MANIFEST_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    entry = json.loads(line)
                    manifest[entry.get("source_id", "")] = entry
                except json.JSONDecodeError:
                    pass
    return manifest


def append_manifest(entry: Dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ── Directory Scanner ────────────────────────────────────────

def scan_directory(directory: str, recursive: bool = False) -> List[str]:
    """Scan directory for supported files."""
    dir_path = Path(directory)
    if not dir_path.is_dir():
        print(f"   Error: not a directory — {directory}")
        return []
    pattern = "**/*" if recursive else "*"
    return sorted(
        str(p) for p in dir_path.glob(pattern)
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    )


# ── Bridge Loader ────────────────────────────────────────────

def _load_bridge():
    """Lazy-load the ClearboxLexiconBridge for anchor extraction."""
    try:
        from bridges.clearbox_bridge import ClearboxLexiconBridge
        bridge = ClearboxLexiconBridge()
        if hasattr(bridge, "word_index") and len(bridge.word_index) > 0:
            print(f"   Bridge loaded: {len(bridge.word_index):,} lexicon entries")
            return bridge
        return bridge
    except Exception as e:
        print(f"   Bridge not available ({e}) — ingesting without anchors")
        return None


# ── Main ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Local File Stream for Clearbox AI Studio")
    parser.add_argument("files", nargs="*", help="File path(s) to ingest")
    parser.add_argument("--dir", help="Directory to scan for files")
    parser.add_argument("--recursive", action="store_true", help="Scan directory recursively")
    parser.add_argument("--dry-run", action="store_true", help="Preview without ingesting")
    parser.add_argument("--force", action="store_true", help="Force re-ingest")
    args = parser.parse_args()

    files = list(args.files or [])
    if args.dir:
        files.extend(scan_directory(args.dir, args.recursive))
    if not files:
        parser.print_help()
        return

    manifest = load_manifest()
    bridge = None if args.dry_run else _load_bridge()
    results = {"ingested": 0, "skipped": 0, "failed": 0}

    print(f"\n{'='*60}")
    print(f" Local File Stream — {len(files)} file(s) queued")
    print(f"{'='*60}\n")

    for i, fp in enumerate(files):
        source_id = str(Path(fp).resolve())
        print(f"[{i+1}/{len(files)}] {fp}")

        if source_id in manifest and not args.force:
            print(f"   Already ingested — skipping")
            results["skipped"] += 1
            continue

        text = fetch(source_id)
        if text is None:
            results["failed"] += 1
            continue

        text = strip_boilerplate(text)
        if not text:
            print(f"   Empty after cleaning — skipping")
            results["failed"] += 1
            continue

        receipt = ingest_file(source_id, text, bridge, dry_run=args.dry_run)
        if receipt and not args.dry_run:
            if "receipt_id" in receipt:
                print(f"   Ingested: receipt={receipt['receipt_id']}, "
                      f"chunks={receipt.get('chunk_count', 0)}, "
                      f"anchors={receipt.get('anchor_count', 0)}")
                append_manifest({
                    "source_type": SOURCE_TYPE,
                    "source_id": source_id,
                    "receipt_id": receipt["receipt_id"],
                    "chunk_count": receipt.get("chunk_count", 0),
                    "anchor_count": receipt.get("anchor_count", 0),
                    "chars": receipt["chars"],
                    "words": receipt["words"],
                    "ingested_at": datetime.now(timezone.utc).isoformat(),
                })
                results["ingested"] += 1
            else:
                results["failed"] += 1
        elif args.dry_run:
            results["ingested"] += 1
        else:
            results["failed"] += 1

    print(f"\n{'='*60}")
    print(f" Results: {results['ingested']} ingested, "
          f"{results['skipped']} skipped, {results['failed']} failed")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
