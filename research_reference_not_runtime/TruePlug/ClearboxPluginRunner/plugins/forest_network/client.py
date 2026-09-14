"""Forest Network — outbound client for bridge-to-bridge requests.

Makes authenticated HTTP requests from this node to remote peer nodes.
All requests carry X-Forest-Node-Key using the peer's configured api_key.

The browser NEVER talks directly to remote nodes.
All inter-node traffic flows: browser → local bridge → remote bridge.

Timeouts:
    connect: 5s   — peer must be reachable quickly
    read:   60s   — large file transfers need more time
    write:  60s   — large file uploads need more time

Raises:
    NodeNotFoundError — node_id not in forest.config.json
    NodeAuthError     — node has no api_key configured (cannot auth)
    httpx.HTTPStatusError   — remote returned non-2xx
    httpx.RequestError      — network error reaching remote node
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, AsyncIterator, Optional

import httpx

from .config import get_node

LOGGER = logging.getLogger("forest.network.client")

_TIMEOUT = httpx.Timeout(connect=5.0, read=60.0, write=60.0, pool=5.0)
_CHUNK = 65_536  # 64 KB


class NodeNotFoundError(Exception):
    """node_id was not found in forest.config.json nodes list."""


class NodeAuthError(Exception):
    """The node exists but has no api_key configured."""


# ── Internal helpers ──────────────────────────────────────────────────────────

def _base_url(node: dict[str, Any]) -> str:
    host = node["host"]
    port = node.get("port", 5050)
    return f"http://{host}:{port}"


def _key(node: dict[str, Any]) -> Optional[str]:
    return node.get("api_key") or None


def _resolve_node(node_id: str) -> tuple[dict[str, Any], str, str]:
    """Resolve node_id → (node, base_url, api_key). Raises on missing/unconfigured."""
    node = get_node(node_id)
    if not node:
        raise NodeNotFoundError(f"Node {node_id!r} is not in forest.config.json")
    api_key = _key(node)
    if not api_key:
        raise NodeAuthError(
            f"Node {node_id!r} has no api_key in config — cannot authenticate"
        )
    return node, _base_url(node), api_key


# ── Public API ────────────────────────────────────────────────────────────────

async def browse(node_id: str, path: str = "/") -> dict[str, Any]:
    """Browse a directory on a remote node.

    Returns the serve/browse JSON response with node_id injected.
    """
    node, base, api_key = _resolve_node(node_id)
    url = f"{base}/api/network/serve/browse"
    headers = {"X-Forest-Node-Key": api_key}

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(url, params={"path": path}, headers=headers)
        resp.raise_for_status()

    data: dict[str, Any] = resp.json()
    data["node_id"] = node_id
    return data


async def read_stream(
    node_id: str,
    path: str,
) -> tuple[dict[str, str], AsyncIterator[bytes]]:
    """Stream a file from a remote node.

    Returns (response_headers, async_byte_iterator).
    The caller is responsible for iterating the stream — it owns the connection.

    response_headers keys: Content-Length, X-Forest-Path, X-Forest-Node.
    """
    node, base, api_key = _resolve_node(node_id)
    url = f"{base}/api/network/serve/read"
    headers = {"X-Forest-Node-Key": api_key}

    client = httpx.AsyncClient(timeout=_TIMEOUT)
    req = client.build_request("GET", url, params={"path": path}, headers=headers)
    resp = await client.send(req, stream=True)
    resp.raise_for_status()

    resp_headers: dict[str, str] = {
        "Content-Length": resp.headers.get("content-length", ""),
        "X-Forest-Path": resp.headers.get("x-forest-path", path),
        "X-Forest-Node": node_id,
    }

    async def _gen() -> AsyncIterator[bytes]:
        try:
            async for chunk in resp.aiter_bytes(_CHUNK):
                yield chunk
        finally:
            await resp.aclose()
            await client.aclose()

    return resp_headers, _gen()


async def hash_file(node_id: str, path: str) -> dict[str, Any]:
    """Return SHA-256 of a file on a remote node.

    Response includes: { node_id, path, hash: "sha256:<hex>", size }
    """
    node, base, api_key = _resolve_node(node_id)
    url = f"{base}/api/network/serve/hash"
    headers = {"X-Forest-Node-Key": api_key}

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(url, params={"path": path}, headers=headers)
        resp.raise_for_status()

    data: dict[str, Any] = resp.json()
    data["node_id"] = node_id
    return data


async def write_file(
    node_id: str,
    path: str,
    content: bytes,
    filename: Optional[str] = None,
) -> dict[str, Any]:
    """Write a file to a remote node via multipart upload.

    content is the full file bytes (loaded into memory by the router before forwarding).
    filename defaults to the basename of path if not provided.

    Response includes: { node_id, ok, path, bytes_written }
    """
    node, base, api_key = _resolve_node(node_id)
    url = f"{base}/api/network/serve/write"
    headers = {"X-Forest-Node-Key": api_key}
    fname = filename or Path(path).name

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        files = {"file": (fname, content, "application/octet-stream")}
        data = {"path": path}
        resp = await client.post(url, data=data, files=files, headers=headers)
        resp.raise_for_status()

    result: dict[str, Any] = resp.json()
    result["node_id"] = node_id
    return result


async def get_roots(node_id: str) -> dict[str, Any]:
    """Return the allow_roots for a remote node.

    Response includes: { node_id, roots: ["docs/GENESIS", ...] }
    """
    node, base, api_key = _resolve_node(node_id)
    url = f"{base}/api/network/serve/roots"
    headers = {"X-Forest-Node-Key": api_key}

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()

    data: dict[str, Any] = resp.json()
    data["node_id"] = node_id
    return data
