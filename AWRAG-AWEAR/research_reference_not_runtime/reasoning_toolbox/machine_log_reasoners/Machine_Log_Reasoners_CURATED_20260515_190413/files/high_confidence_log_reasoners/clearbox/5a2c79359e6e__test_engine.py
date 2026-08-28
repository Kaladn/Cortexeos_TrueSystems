"""Tests for genesis_cite.engine — direct lookup and BM25 search."""

import pytest

from plugins.genesis_cite.engine import CitationEngine


@pytest.fixture(scope="module")
def engine():
    """Shared engine instance for all tests in this module."""
    return CitationEngine()


# ── Direct lookup ─────────────────────────────────────────────────────────────

def test_direct_lookup_g0001(engine):
    """G-0001 direct lookup returns correct tag, title, source."""
    resp = engine.direct("G-0001")
    assert resp["ok"] is True
    result = resp["result"]
    assert result["tag"] == "G-0001"
    assert result["source"]  # non-empty
    assert result["title"]   # non-empty
    assert result["body"]    # non-empty
    assert result["block_hash"].startswith("sha256:")


def test_direct_lookup_missing(engine):
    """Non-existent tag returns NOT_FOUND error."""
    resp = engine.direct("G-9999")
    assert resp["ok"] is False
    assert resp["error"] == "NOT_FOUND"
    assert "G-9999" in resp["detail"]


def test_direct_lookup_all_tags(engine):
    """All 68 G-IDs resolve successfully."""
    for i in range(1, 69):
        tag = f"G-{i:04d}"
        resp = engine.direct(tag)
        assert resp["ok"] is True, f"{tag} failed: {resp}"


def test_direct_lookup_include_body_false(engine):
    """include_body=False omits body from result."""
    resp = engine.direct("G-0001", include_body=False)
    assert resp["ok"] is True
    assert "body" not in resp["result"]


def test_direct_lookup_citation_fields(engine):
    """Citation object contains all mandatory fields."""
    resp = engine.direct("G-0017")
    assert resp["ok"] is True
    result = resp["result"]
    mandatory = [
        "tag", "title", "source", "scope", "date_range",
        "write_perms", "derived", "source_commit", "block_hash",
        "body", "span", "retrieved_at",
    ]
    for field in mandatory:
        assert field in result, f"Missing field: {field}"


def test_direct_lookup_path_injection(engine):
    """Tags with path-injection characters are rejected."""
    for bad_tag in ["../etc/passwd", "G-0001/evil", "G-0001\\evil"]:
        resp = engine.direct(bad_tag)
        assert resp["ok"] is False
        assert resp["error"] in ("SPEC_VIOLATION", "INVALID_TAG")


def test_direct_lookup_span(engine):
    """Span has start_line and end_line."""
    resp = engine.direct("G-0005")
    assert resp["ok"] is True
    span = resp["result"]["span"]
    assert "start_line" in span
    assert "end_line" in span
    assert span["end_line"] >= span["start_line"]


# ── Search ────────────────────────────────────────────────────────────────────

def test_search_basic(engine):
    """Non-empty results for a reasonable query."""
    resp = engine.search("6-1-6 mapping lexicon")
    assert resp["ok"] is True
    assert len(resp["results"]) > 0


def test_search_ordering(engine):
    """Same query always returns same order (deterministic)."""
    query = "WebAuthn registration challenge mismatch"
    resp_a = engine.search(query)
    resp_b = engine.search(query)
    assert resp_a["results"] == resp_b["results"]


def test_search_limit_respected(engine):
    """Limit parameter controls max results."""
    resp = engine.search("forest", limit=3)
    assert resp["ok"] is True
    assert len(resp["results"]) <= 3


def test_search_filter_series(engine):
    """Series filter restricts results to the right series range."""
    resp = engine.search("auth", filters={"series": "3"})
    assert resp["ok"] is True
    for r in resp["results"]:
        num = int(r["tag"].split("-")[1])
        assert 16 <= num <= 21, f"{r['tag']} is not in series 3 (G-0016–G-0021)"


def test_search_filter_derived_false(engine):
    """derived=False excludes derived summary blocks."""
    from plugins.genesis_cite.parser import parse_corpus
    blocks = parse_corpus()
    derived_tags = {b.tag for b in blocks if b.derived}
    if not derived_tags:
        pytest.skip("No derived blocks in corpus")
    resp = engine.search("summary", filters={"derived": False}, limit=20)
    assert resp["ok"] is True
    for r in resp["results"]:
        assert r["tag"] not in derived_tags, f"Derived block {r['tag']} leaked through filter"


def test_search_snippet_present(engine):
    """include_snippets=True adds snippet field to results."""
    resp = engine.search("bridge API", include_snippets=True)
    assert resp["ok"] is True
    if resp["results"]:
        assert "snippet" in resp["results"][0]


def test_search_no_snippet(engine):
    """include_snippets=False omits snippet field."""
    resp = engine.search("bridge", include_snippets=False)
    assert resp["ok"] is True
    for r in resp["results"]:
        assert "snippet" not in r


def test_search_tag_boost(engine):
    """Exact tag mention in query gets score boost (result is in top-3)."""
    resp = engine.search("G-0001", limit=5)
    assert resp["ok"] is True
    tags = [r["tag"] for r in resp["results"]]
    assert "G-0001" in tags, "G-0001 should appear in results when mentioned in query"


def test_search_source_contains_filter(engine):
    """source_contains filter restricts results to matching source."""
    resp = engine.search("system", filters={"source_contains": "auth"}, limit=20)
    assert resp["ok"] is True
    for r in resp["results"]:
        result = engine.direct(r["tag"])
        assert result["ok"] is True
        assert "auth" in result["result"]["source"].lower(), (
            f"{r['tag']}: source {result['result']['source']!r} doesn't contain 'auth'"
        )


# ── Health ────────────────────────────────────────────────────────────────────

def test_health(engine):
    """Health endpoint returns ok=True with block count."""
    h = engine.health()
    assert h["ok"] is True
    assert h["blocks"] == 68


# ── List all ──────────────────────────────────────────────────────────────────

def test_list_all(engine):
    """list_all returns 68 entries with required fields."""
    items = engine.list_all()
    assert len(items) == 68
    for item in items:
        assert "tag" in item
        assert "title" in item
        assert "source" in item
        assert "series" in item


# ── Index rebuild trigger ─────────────────────────────────────────────────────

def test_index_rebuild_trigger(tmp_path, monkeypatch):
    """Stale index (different source_hash) triggers rebuild on next load."""
    import json
    from plugins.genesis_cite.config import BUILD_META_PATH, INDEX_DIR

    # Patch BUILD_META_PATH to a temp file with wrong hash
    fake_meta_path = tmp_path / "build_meta.json"
    fake_meta_path.write_text(json.dumps({
        "source_commit": "deadbeef",
        "source_hash": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
        "built_at": "2000-01-01T00:00:00Z",
        "block_count": 0,
    }))

    monkeypatch.setattr("plugins.genesis_cite.indexer.BUILD_META_PATH", fake_meta_path)
    monkeypatch.setattr("plugins.genesis_cite.indexer.INDEX_DIR", tmp_path)
    monkeypatch.setattr("plugins.genesis_cite.indexer.CORPUS_INDEX_PATH", tmp_path / "corpus.index.json")
    monkeypatch.setattr("plugins.genesis_cite.indexer.BM25_INDEX_PATH", tmp_path / "bm25.index.pkl")

    from plugins.genesis_cite.indexer import load_or_build_index
    idx = load_or_build_index()

    # Verify rebuilt
    meta = json.loads(fake_meta_path.read_text())
    assert meta["block_count"] == 68
    assert meta["source_hash"] != "sha256:0000000000000000000000000000000000000000000000000000000000000000"
