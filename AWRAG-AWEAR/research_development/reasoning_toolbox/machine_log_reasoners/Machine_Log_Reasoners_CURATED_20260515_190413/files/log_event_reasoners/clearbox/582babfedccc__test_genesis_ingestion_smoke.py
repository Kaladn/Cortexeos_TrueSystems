# tests/test_genesis_ingestion_smoke.py
# Genesis ingestion readiness gate.
# Requires Bridge running on 127.0.0.1:5050 with core Genesis mounted at /api/genesis/*
#
# Run:  pytest -q tests/test_genesis_ingestion_smoke.py
# Skip when bridge is not running: pytest -q --ignore=tests/test_genesis_ingestion_smoke.py
#
# Environment overrides:
#   CLEARBOX_BRIDGE_HOST          default: 127.0.0.1
#   CLEARBOX_BRIDGE_PORT          default: 5050
#   GENESIS_EXPECTED_BLOCKS       default: 74
#   GENESIS_EXPECTED_COMMIT       default: ""  (set a prefix to enable commit check)

import json
import os
import re
import http.client
from typing import Any, Dict, Optional

import pytest

HOST = os.environ.get("CLEARBOX_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.environ.get("CLEARBOX_BRIDGE_PORT", "5050"))

EXPECTED_BLOCKS = int(os.environ.get("GENESIS_EXPECTED_BLOCKS", "74"))
EXPECTED_COMMIT_PREFIX = os.environ.get("GENESIS_EXPECTED_COMMIT", "")

TAG_RE = re.compile(r"^G-\d{4}$")
SHA_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{7,40}$")


def _genesis_available() -> bool:
    """Return True if core Genesis is mounted and healthy on the bridge."""
    try:
        conn = http.client.HTTPConnection(HOST, PORT, timeout=5)
        conn.request("GET", "/api/genesis/health")
        resp = conn.getresponse()
        conn.close()
        return resp.status == 200
    except (ConnectionRefusedError, OSError):
        return False


# Module-level skip: if bridge isn't up or core Genesis isn't mounted, skip all.
if not _genesis_available():
    pytest.skip(
        f"Bridge Genesis service not available at {HOST}:{PORT}/api/genesis — "
        "start the bridge and ensure core Genesis is mounted",
        allow_module_level=True,
    )


def _req(
    method: str,
    path: str,
    payload: Optional[Dict[str, Any]] = None,
    expected_status: int = 200,
) -> Dict[str, Any]:
    try:
        conn = http.client.HTTPConnection(HOST, PORT, timeout=10)
        headers = {"Content-Type": "application/json"}
        body = None if payload is None else json.dumps(payload).encode("utf-8")

        conn.request(method, path, body=body, headers=headers)
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8", errors="replace")
        conn.close()
    except (ConnectionRefusedError, OSError) as exc:
        pytest.skip(f"Bridge not reachable at {HOST}:{PORT} — {exc}")

    if resp.status != expected_status:
        raise AssertionError(
            f"{method} {path} -> HTTP {resp.status}, expected {expected_status}\n{raw}"
        )

    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        raise AssertionError(f"{method} {path} returned non-JSON:\n{raw}")


def _assert_citation_obj(obj: Dict[str, Any]) -> None:
    required = [
        "tag", "title", "source", "scope", "date_range",
        "write_perms", "derived", "source_commit", "block_hash",
        "body", "span", "retrieved_at",
    ]
    for k in required:
        assert k in obj, f"Missing field: {k}"

    assert TAG_RE.match(obj["tag"]), f"Bad tag: {obj['tag']}"
    assert isinstance(obj["title"], str) and obj["title"].strip(), "Empty title"
    assert isinstance(obj["source"], str) and obj["source"].strip(), "Empty source"
    assert isinstance(obj["scope"], str), "scope must be str"
    assert obj["write_perms"] == "READ_ONLY", f"Bad write_perms: {obj['write_perms']}"
    assert isinstance(obj["derived"], bool), "derived must be bool"

    assert COMMIT_RE.match(obj["source_commit"]), f"Bad source_commit: {obj['source_commit']}"
    if EXPECTED_COMMIT_PREFIX:
        assert obj["source_commit"].startswith(EXPECTED_COMMIT_PREFIX), (
            f"Commit mismatch: expected prefix {EXPECTED_COMMIT_PREFIX!r}, "
            f"got {obj['source_commit']!r}"
        )

    assert SHA_RE.match(obj["block_hash"]), f"Bad block_hash: {obj['block_hash']}"

    span = obj["span"]
    assert isinstance(span, dict), "span must be dict"
    assert isinstance(span.get("start_line"), int) and span["start_line"] > 0, (
        "start_line must be 1-indexed int"
    )
    assert isinstance(span.get("end_line"), int) and span["end_line"] >= span["start_line"], (
        "end_line must be >= start_line"
    )
    assert isinstance(obj["body"], str) and obj["body"].strip(), "body should be non-empty"


# ── Health ────────────────────────────────────────────────────────────────────

def test_health():
    h = _req("GET", "/api/genesis/health")
    assert h.get("ok") is True, f"health not ok: {h}"
    assert int(h.get("blocks", -1)) == EXPECTED_BLOCKS, (
        f"Expected {EXPECTED_BLOCKS} blocks, got {h.get('blocks')}"
    )
    assert "index_commit" in h, "health missing index_commit"
    if EXPECTED_COMMIT_PREFIX:
        assert str(h["index_commit"]).startswith(EXPECTED_COMMIT_PREFIX), (
            f"index_commit mismatch: expected {EXPECTED_COMMIT_PREFIX!r}, got {h['index_commit']!r}"
        )


# ── List ──────────────────────────────────────────────────────────────────────

def test_list_is_complete_sorted_no_bodies():
    items = _req("GET", "/api/genesis/list")
    assert isinstance(items, list), "list must return array"
    assert len(items) == EXPECTED_BLOCKS, f"Expected {EXPECTED_BLOCKS}, got {len(items)}"

    tags = []
    for it in items:
        assert "tag" in it and TAG_RE.match(it["tag"]), f"Bad tag in list: {it}"
        assert "title" in it and isinstance(it["title"], str), "list missing title"
        assert "source" in it and isinstance(it["source"], str), "list missing source"
        assert "series" in it, "list missing series"
        assert "body" not in it, "list must NOT include body"
        tags.append(it["tag"])

    assert tags == sorted(tags), "list must be sorted ascending by tag"


# ── Direct GET ────────────────────────────────────────────────────────────────

def test_direct_g0001_get():
    resp = _req("GET", "/api/genesis/cite/G-0001")
    assert resp.get("ok") is True, f"Expected ok:true, got: {resp}"
    _assert_citation_obj(resp["result"])
    assert resp["result"]["tag"] == "G-0001"


def test_direct_spot_checks():
    """Spot-check a few non-trivial blocks across series."""
    for tag in ("G-0017", "G-0028", "G-0058", "G-0074"):
        resp = _req("GET", f"/api/genesis/cite/{tag}")
        assert resp.get("ok") is True, f"{tag}: expected ok:true, got {resp}"
        _assert_citation_obj(resp["result"])
        assert resp["result"]["tag"] == tag


# ── Direct POST ───────────────────────────────────────────────────────────────

def test_direct_post_include_body_false():
    resp = _req("POST", "/api/genesis/cite", {"mode": "direct", "tag": "G-0001", "include_body": False})
    assert resp.get("ok") is True
    assert "body" not in resp["result"], "include_body=false must omit body"


def test_missing_tag_not_found_contract():
    resp = _req(
        "POST",
        "/api/genesis/cite",
        {"mode": "direct", "tag": "G-9999", "include_body": True},
        expected_status=404,
    )
    assert "G-9999" in resp.get("detail", ""), "detail should mention the missing tag"


# ── Search ────────────────────────────────────────────────────────────────────

def test_search_returns_results():
    payload = {
        "mode": "search",
        "query": "6-1-6 mapping lexicon",
        "limit": 5,
        "include_snippets": True,
    }
    resp = _req("POST", "/api/genesis/cite", payload)
    assert resp.get("ok") is True, f"search failed: {resp}"
    results = resp.get("results", [])
    assert len(results) > 0, "Expected non-empty search results"

    for r in results:
        for k in ("tag", "title", "score", "snippet", "block_hash", "span"):
            assert k in r, f"search result missing '{k}'"
        assert TAG_RE.match(r["tag"]), f"Bad tag: {r['tag']}"
        assert isinstance(r["snippet"], str), "snippet must be str"
        assert SHA_RE.match(r["block_hash"]), f"Bad block_hash: {r['block_hash']}"
        assert isinstance(r["score"], (int, float)) and r["score"] >= 0, "score must be non-negative number"


def test_search_deterministic():
    payload = {
        "mode": "search",
        "query": "6-1-6 mapping",
        "filters": {"derived": False},
        "limit": 10,
        "include_snippets": True,
    }
    r1 = _req("POST", "/api/genesis/cite", payload)
    r2 = _req("POST", "/api/genesis/cite", payload)

    assert r1.get("ok") is True and isinstance(r1.get("results"), list), f"Bad response: {r1}"
    assert r2.get("ok") is True and isinstance(r2.get("results"), list), f"Bad response: {r2}"

    tags1 = [x["tag"] for x in r1["results"]]
    tags2 = [x["tag"] for x in r2["results"]]
    assert tags1 == tags2, (
        f"Non-deterministic result ordering:\n  run1: {tags1}\n  run2: {tags2}"
    )


def test_search_series_filter():
    """Series 3 filter must only return G-0016–G-0021."""
    resp = _req("POST", "/api/genesis/cite", {
        "mode": "search",
        "query": "auth security",
        "filters": {"series": "3"},
        "limit": 20,
    })
    assert resp.get("ok") is True
    for r in resp.get("results", []):
        num = int(r["tag"].split("-")[1])
        assert 16 <= num <= 21, f"{r['tag']} is outside series 3 (G-0016–G-0021)"


def test_search_limit_enforced():
    resp = _req("POST", "/api/genesis/cite", {"mode": "search", "query": "clearbox", "limit": 3})
    assert resp.get("ok") is True
    assert len(resp.get("results", [])) <= 3, "limit=3 must cap results"


# ── Block hash stability (cross-request) ─────────────────────────────────────

def test_block_hashes_stable_across_requests():
    """Two separate fetches of the same tag return identical block_hash."""
    tag = "G-0001"
    h1 = _req("GET", f"/api/genesis/cite/{tag}")["result"]["block_hash"]
    h2 = _req("GET", f"/api/genesis/cite/{tag}")["result"]["block_hash"]
    assert h1 == h2, f"block_hash changed between requests: {h1!r} vs {h2!r}"


# ── Security ──────────────────────────────────────────────────────────────────

def test_path_injection_rejected():
    for bad in ("../etc/passwd", "G-0001/evil", "G-0001\\\\evil"):
        resp = _req(
            "POST",
            "/api/genesis/cite",
            {"mode": "direct", "tag": bad},
            expected_status=400,
        )
        assert "PATH_INJECTION" in resp.get("detail", ""), (
            f"Expected PATH_INJECTION detail for tag={bad!r}, got: {resp}"
        )
