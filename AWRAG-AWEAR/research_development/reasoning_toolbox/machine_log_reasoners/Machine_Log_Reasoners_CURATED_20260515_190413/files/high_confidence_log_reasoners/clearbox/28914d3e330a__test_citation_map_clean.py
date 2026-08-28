#!/usr/bin/env python3
"""Test Citation-Map System with 3 sample documents."""

import json
import httpx
from pathlib import Path

BASE_URL = "http://localhost:11435"
TEST_DOCS_DIR = Path("test_docs")

def create_citation(content: str, filename: str):
    """Create citation for a document."""
    print(f"\n[+] Creating citation for {filename}...")

    resp = httpx.post(
        f"{BASE_URL}/api/library/citations/create",
        json={
            "content": content,
            "filename": filename
        },
        timeout=30.0
    )

    if resp.status_code == 200:
        data = resp.json()
        print(f"    OK: {data['cite_id']}")
        print(f"    Canonical: {data['canonical']}")
        print(f"    Filesize: {data['filesize']} bytes")
        return data['cite_id']
    else:
        print(f"    FAIL: {resp.status_code} - {resp.text}")
        return None

def create_map(cite_id: str, window_size: int = 6):
    """Create 6-1-6 map for a citation."""
    print(f"\n[+] Creating map for {cite_id}...")

    resp = httpx.post(
        f"{BASE_URL}/api/library/maps/create",
        json={
            "cite_id": cite_id,
            "window_size": window_size
        },
        timeout=60.0
    )

    if resp.status_code == 200:
        data = resp.json()
        print(f"    OK: {data['map_id']}")
        print(f"    Stats: {json.dumps(data['stats'], indent=6)}")
        return data['map_id']
    else:
        print(f"    FAIL: {resp.status_code} - {resp.text}")
        return None

def query_maps(keywords: list[str]):
    """Search maps by keywords."""
    print(f"\n[?] Querying maps for keywords: {keywords}...")

    resp = httpx.post(
        f"{BASE_URL}/api/library/query",
        json={
            "keywords": keywords,
            "limit": 10
        },
        timeout=30.0
    )

    if resp.status_code == 200:
        data = resp.json()
        print(f"    Found {data['count']} matching documents:")
        for i, result in enumerate(data['results'], 1):
            print(f"      {i}. {result['filename']} (score: {result['score']:.1f})")
            print(f"         Matched: {', '.join(result['matched_anchors'][:3])}")
    else:
        print(f"    FAIL: {resp.status_code} - {resp.text}")

def get_library_summary():
    """Get library statistics."""
    print(f"\n[i] Library Summary...")

    resp = httpx.get(f"{BASE_URL}/api/library/summary", timeout=30.0)

    if resp.status_code == 200:
        data = resp.json()
        print(f"    Citations: {data['total_citations']}")
        print(f"    Maps: {data['total_maps']}")
        print(f"    Unique anchors: {data['unique_anchors']}")
    else:
        print(f"    FAIL: {resp.status_code} - {resp.text}")

def main():
    print("=" * 60)
    print("Citation-Map System Test")
    print("=" * 60)

    # Check if test docs exist
    test_files = [
        "doc1_clearbox_ecology.txt",
        "doc2_biodiversity.txt",
        "doc3_climate_policy.txt"
    ]

    citations = []

    # Phase 1: Create citations
    print("\n" + "=" * 60)
    print("PHASE 1: Create Citations")
    print("=" * 60)

    for filename in test_files:
        filepath = TEST_DOCS_DIR / filename
        if not filepath.exists():
            print(f"ERROR: Test file not found: {filepath}")
            continue

        content = filepath.read_text(encoding='utf-8')
        cite_id = create_citation(content, filename)
        if cite_id:
            citations.append((cite_id, filename))

    # Phase 2: Create maps
    print("\n" + "=" * 60)
    print("PHASE 2: Create Maps (idempotent)")
    print("=" * 60)

    for cite_id, filename in citations:
        create_map(cite_id, window_size=6)

    # Phase 3: Test queries
    print("\n" + "=" * 60)
    print("PHASE 3: Test Queries")
    print("=" * 60)

    query_maps(["clearbox", "carbon"])
    query_maps(["biodiversity", "conservation"])
    query_maps(["climate", "policy"])

    # Phase 4: Library summary
    print("\n" + "=" * 60)
    print("PHASE 4: Library Summary")
    print("=" * 60)

    get_library_summary()

    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Check data/citations.db (SQLite database)")
    print("  2. Check %LOCALAPPDATA%/ClearboxAI/chat_history/citations/")
    print("  3. Check %LOCALAPPDATA%/ClearboxAI/chat_history/maps/")
    print("  4. Try more queries with different keywords")

if __name__ == "__main__":
    try:
        main()
    except httpx.ConnectError:
        print("\nERROR: Cannot connect to server at localhost:11435")
        print("   Make sure local_llm_server.py is running!")
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
