#!/usr/bin/env python3
"""Web Scrape Stream — extract and ingest content from web pages into LakeSpeak.

Usage:
    python scripts/webscrape_stream.py https://example.com/article
    python scripts/webscrape_stream.py https://example.com/p1 https://example.com/p2
    python scripts/webscrape_stream.py --file urls.txt
    python scripts/webscrape_stream.py https://example.com/article --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urldefrag

# ── Paths ────────────────────────────────────────────────────

WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))
sys.path.insert(0, str(WORKSPACE_ROOT / "plugins"))

MANIFEST_PATH = WORKSPACE_ROOT / "state" / "webscrape_manifest.jsonl"
SOURCE_TYPE = "web"
USER_AGENT = "ClearboxAI-Web-Stream/0.1 (research)"
REQUEST_TIMEOUT = 30
RATE_LIMIT_DELAY = 1.0

# Dependency check
try:
    import requests
    from bs4 import BeautifulSoup
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


# ── Fetch ────────────────────────────────────────────────────

def fetch(source_id: str) -> Optional[str]:
    """Fetch raw HTML from a web page."""
    if not HAS_DEPS:
        print("   Missing deps: pip install requests beautifulsoup4")
        return None
    try:
        r = requests.get(source_id, headers={"User-Agent": USER_AGENT},
                         timeout=REQUEST_TIMEOUT, allow_redirects=True)
        r.raise_for_status()
        return r.text
    except Exception as e:
        print(f"   Fetch error: {e}")
        return None


# ── Strip ────────────────────────────────────────────────────

def strip_boilerplate(html: str) -> str:
    """Extract main content from HTML and clean it."""
    if not html or not HAS_DEPS:
        return ""
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Remove junk tags
        for tag in soup(["script", "style", "nav", "header", "footer", "aside",
                         "iframe", "noscript", "form", "button", "input"]):
            tag.decompose()

        # Remove boilerplate by class/id
        for pat in ["cookie", "banner", "popup", "modal", "advertisement", "ad-",
                     "sidebar", "menu", "navigation", "breadcrumb", "share",
                     "social", "comment", "related", "newsletter", "subscribe"]:
            for tag in soup.find_all(class_=re.compile(pat, re.I)):
                tag.decompose()
            for tag in soup.find_all(id=re.compile(pat, re.I)):
                tag.decompose()

        # Find main content
        main = None
        for sel in ["article", "[role='main']", "main", ".article-content",
                     ".post-content", ".entry-content", ".content-body",
                     "#content", ".content"]:
            main = soup.select_one(sel)
            if main:
                break
        if not main:
            main = soup.find("body") or soup

        text = main.get_text(separator="\n", strip=True)
        return _clean_text(text)
    except Exception as e:
        print(f"   Extraction error: {e}")
        return ""


def _clean_text(text: str) -> str:
    """Normalize extracted plain text."""
    if not text:
        return ""
    for old, new in [("&nbsp;", " "), ("&amp;", "&"), ("&lt;", "<"),
                      ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'")]:
        text = text.replace(old, new)
    text = re.sub(r"[ \t]+", " ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    lines, cleaned, blank = text.split("\n"), [], 0
    skip = {"menu", "home", "about", "contact", "search", "login", "sign up"}
    for line in lines:
        line = line.strip()
        if line:
            if len(line) < 3 or line.lower() in skip:
                continue
            cleaned.append(line)
            blank = 0
        else:
            blank += 1
            if blank <= 1:
                cleaned.append("")
    text = "\n".join(cleaned)
    for pat in [r"(?i)accept\s+cookies?", r"(?i)cookie\s+policy",
                r"(?i)privacy\s+policy", r"(?i)terms\s+of\s+service",
                r"(?i)subscribe\s+to\s+our\s+newsletter",
                r"(?i)all\s+rights\s+reserved", r"(?i)copyright\s+©"]:
        text = re.sub(pat + r"[^\n]*", "", text)
    return text.strip()


# ── Ingest ───────────────────────────────────────────────────

def ingest_page(source_id: str, text: str, bridge, dry_run: bool = False) -> Optional[Dict]:
    """Pipe cleaned text through LakeSpeak ingest."""
    chars = len(text)
    words = len(text.split())
    if dry_run:
        print(f"   [DRY RUN] {chars:,} chars, {words:,} words")
        return {"chars": chars, "words": words, "status": "dry_run"}

    from core.lakespeak.ingest.pipeline import ingest_text
    receipt = ingest_text(text=text, source_type=SOURCE_TYPE, source_path=source_id, bridge=bridge)
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


def normalize_url(url: str) -> str:
    """Canonical URL: strip fragment and trailing slash."""
    url, _ = urldefrag(url)
    return url.rstrip("/")


# ── Bridge Loader ────────────────────────────────────────────

def _load_bridge():
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
    parser = argparse.ArgumentParser(description="Web Scrape Stream for Clearbox AI Studio")
    parser.add_argument("urls", nargs="*", help="URL(s) to scrape and ingest")
    parser.add_argument("--file", help="File containing URLs (one per line)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without ingesting")
    parser.add_argument("--force", action="store_true", help="Force re-ingest")
    parser.add_argument("--delay", type=float, default=RATE_LIMIT_DELAY, help="Seconds between requests")
    args = parser.parse_args()

    if not HAS_DEPS:
        print("Missing deps: pip install requests beautifulsoup4")
        sys.exit(1)

    urls: List[str] = list(args.urls or [])
    if args.file:
        try:
            for line in Path(args.file).read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    urls.append(line)
        except Exception as e:
            print(f"Error reading {args.file}: {e}")
            sys.exit(1)
    if not urls:
        parser.print_help()
        return

    urls = [normalize_url(u) for u in urls]
    manifest = load_manifest()
    bridge = None if args.dry_run else _load_bridge()
    results = {"ingested": 0, "skipped": 0, "failed": 0}

    print(f"\n{'='*60}")
    print(f" Web Scrape Stream — {len(urls)} URL(s) queued")
    print(f"{'='*60}\n")

    for i, url in enumerate(urls):
        if i > 0:
            time.sleep(args.delay)
        print(f"[{i+1}/{len(urls)}] {url}")

        if url in manifest and not args.force:
            print(f"   Already ingested — skipping")
            results["skipped"] += 1
            continue

        html = fetch(url)
        if not html:
            results["failed"] += 1
            continue
        text = strip_boilerplate(html)
        if not text or len(text) < 100:
            print(f"   Insufficient content after extraction")
            results["failed"] += 1
            continue

        receipt = ingest_page(url, text, bridge, dry_run=args.dry_run)
        if receipt and not args.dry_run and "receipt_id" in receipt:
            print(f"   Ingested: chunks={receipt.get('chunk_count', 0)}, anchors={receipt.get('anchor_count', 0)}")
            append_manifest({
                "source_type": SOURCE_TYPE,
                "source_id": url,
                "receipt_id": receipt["receipt_id"],
                "chunk_count": receipt.get("chunk_count", 0),
                "anchor_count": receipt.get("anchor_count", 0),
                "chars": receipt["chars"],
                "words": receipt["words"],
                "ingested_at": datetime.now(timezone.utc).isoformat(),
            })
            results["ingested"] += 1
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
