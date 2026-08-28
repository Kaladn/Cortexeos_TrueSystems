# tests/test_clearbox_network_phase1.py
# Clearbox Network core router — Phase 1 smoke tests.
#
# Requires Clearbox AI Bridge running on 127.0.0.1:5050
# with clearbox_network mounted at /api/network/
#
# Run:  pytest -q tests/test_clearbox_network_phase1.py
#
# Environment overrides:
#   CLEARBOX_BRIDGE_HOST        default: 127.0.0.1
#   CLEARBOX_BRIDGE_PORT        default: 5050
#
# Tests:
#   1. Health endpoint responds 200 with ok=True
#   2. Serve endpoint without key → 401
#   3. Serve endpoint with invalid key → 401
#   4. Browse local node "this" → 200 with entries list
#   5. Path traversal attempt on local browse → 400
#   6. Path outside allow_roots on local browse → 403
#   7. Hash of a known local file → sha256:... prefix
#   8. Write to allowed path → 200 + file on disk
#   9. Write to disallowed path → 403

import http.client
import io
import json
import mimetypes
import os
import uuid
from typing import Any, Dict, Optional

import pytest

HOST = os.environ.get("CLEARBOX_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.environ.get("CLEARBOX_BRIDGE_PORT", "5050"))

# A file we know exists within the default allow_roots (docs/GENESIS)
_KNOWN_FILE = "docs/GENESIS/INGESTION_LOG.md"
# An allowed root directory for testing browse
_ALLOWED_DIR = "docs/GENESIS"
# A path outside any allow_root
_DENIED_PATH = "bridges/clearbox_bridge_server.py"
# A traversal attempt
_TRAVERSAL_PATH = "../etc/passwd"


# ── Availability check ────────────────────────────────────────────────────────

def _service_available() -> bool:
    """Return True if clearbox_network core router is mounted and healthy."""
    try:
        conn = http.client.HTTPConnection(HOST, PORT, timeout=5)
        conn.request("GET", "/api/network/health")
        resp = conn.getresponse()
        conn.close()
        return resp.status == 200
    except (ConnectionRefusedError, OSError):
        return False


if not _service_available():
    pytest.skip(
        f"clearbox_network service not available at {HOST}:{PORT}/api/network — "
        "start the bridge and ensure clearbox_network is mounted",
        allow_module_level=True,
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

def _get(path: str, headers: Optional[Dict[str, str]] = None) -> tuple[int, Any]:
    conn = http.client.HTTPConnection(HOST, PORT, timeout=10)
    conn.request("GET", path, headers=headers or {})
    resp = conn.getresponse()
    body = resp.read()
    conn.close()
    try:
        return resp.status, json.loads(body)
    except json.JSONDecodeError:
        return resp.status, body.decode("utf-8", errors="replace")


def _post_multipart(
    path: str,
    fields: Dict[str, str],
    file_field: str,
    filename: str,
    content: bytes,
    headers: Optional[Dict[str, str]] = None,
) -> tuple[int, Any]:
    """Send a multipart/form-data POST with one file field."""
    boundary = f"ClearboxSmoke{uuid.uuid4().hex}"
    body_parts: list[bytes] = []

    for name, value in fields.items():
        body_parts.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n".encode()
        )

    body_parts.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n".encode()
        + content
        + b"\r\n"
    )
    body_parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(body_parts)

    req_headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    req_headers.update(headers or {})

    conn = http.client.HTTPConnection(HOST, PORT, timeout=10)
    conn.request("POST", path, body=body, headers=req_headers)
    resp = conn.getresponse()
    body_resp = resp.read()
    conn.close()
    try:
        return resp.status, json.loads(body_resp)
    except json.JSONDecodeError:
        return resp.status, body_resp.decode("utf-8", errors="replace")


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_health_ok():
    """Network health endpoint returns ok=True."""
    status, data = _get("/api/network/health")
    assert status == 200, f"Expected 200, got {status}: {data}"
    assert data.get("ok") is True
    assert data.get("service") == "clearbox_network"
    assert data.get("phase") == 1


def test_serve_browse_no_key_rejected():
    """Serve endpoint without X-Clearbox-Node-Key header → 401."""
    status, data = _get(f"/api/network/serve/browse?path=/{_ALLOWED_DIR}")
    assert status == 401, f"Expected 401 (no key), got {status}: {data}"


def test_serve_browse_invalid_key_rejected():
    """Serve endpoint with a garbage key → 401."""
    status, data = _get(
        f"/api/network/serve/browse?path=/{_ALLOWED_DIR}",
        headers={"X-Clearbox-Node-Key": "definitely-not-a-valid-key"},
    )
    assert status == 401, f"Expected 401 (bad key), got {status}: {data}"


def test_browse_local_this():
    """Browse 'this' node's GENESIS directory → list of entries."""
    status, data = _get(f"/api/network/files/this?path={_ALLOWED_DIR}")
    assert status == 200, f"Expected 200, got {status}: {data}"
    assert "entries" in data, f"Missing 'entries' key: {data}"
    assert isinstance(data["entries"], list)
    assert data.get("node_id") == "this"
    # At minimum we expect TRAINING_CORPUS.md and INGESTION_LOG.md to exist
    names = {e["name"] for e in data["entries"]}
    assert len(names) > 0, "Browse returned empty directory"


def test_browse_path_traversal_blocked():
    """Path traversal in query parameter → 400."""
    status, data = _get(f"/api/network/files/this?path={_TRAVERSAL_PATH}")
    assert status == 400, f"Expected 400 (traversal), got {status}: {data}"
    assert "traversal" in str(data).lower() or "illegal" in str(data).lower()


def test_browse_denied_path_blocked():
    """Path outside allow_roots → 403."""
    status, data = _get(f"/api/network/files/this?path={_DENIED_PATH}")
    assert status == 403, f"Expected 403 (denied), got {status}: {data}"
    assert "allowed" in str(data).lower() or "outside" in str(data).lower()


def test_hash_known_file():
    """Hash of a known file returns sha256: prefixed string."""
    status, data = _get(f"/api/network/files/this/hash?path={_KNOWN_FILE}")
    assert status == 200, f"Expected 200, got {status}: {data}"
    assert "hash" in data, f"Missing 'hash' key: {data}"
    assert data["hash"].startswith("sha256:"), f"Unexpected hash format: {data['hash']}"
    assert len(data["hash"]) == 71, f"sha256: + 64 hex chars = 71, got {len(data['hash'])}"
    assert "size" in data and data["size"] > 0


def test_write_to_allowed_path():
    """Write a small test file to an allowed root, verify 200 response."""
    test_content = b"Clearbox Network Phase 1 write smoke test\n"
    unique_name = f"_smoke_test_{uuid.uuid4().hex[:8]}.txt"
    write_path = f"docs/GENESIS/{unique_name}"

    status, data = _post_multipart(
        "/api/network/files/this/write",
        fields={"path": write_path},
        file_field="file",
        filename=unique_name,
        content=test_content,
    )
    assert status == 200, f"Expected 200, got {status}: {data}"
    assert data.get("ok") is True
    assert data.get("bytes_written") == len(test_content)

    # Verify the file actually landed on disk
    from pathlib import Path
    repo_root = Path(__file__).resolve().parent.parent
    written = repo_root / write_path
    assert written.exists(), f"File was not written to disk: {written}"
    assert written.read_bytes() == test_content

    # Cleanup
    written.unlink()


def test_write_to_denied_path_blocked():
    """Write to a path outside allow_roots → 403."""
    status, data = _post_multipart(
        "/api/network/files/this/write",
        fields={"path": _DENIED_PATH},
        file_field="file",
        filename="malicious.py",
        content=b"# should not land\n",
    )
    assert status == 403, f"Expected 403 (write denied), got {status}: {data}"
