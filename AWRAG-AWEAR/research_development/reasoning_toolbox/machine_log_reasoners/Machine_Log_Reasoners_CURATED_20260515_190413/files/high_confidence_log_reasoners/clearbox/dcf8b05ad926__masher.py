"""Masher — discovers endpoints, builds action queue, writes ACTION events.

The Masher declares intent but never claims success.  It:
  1. Fetches /openapi.json to discover all routes
  2. Builds an ordered queue (GETs → safe POSTs → guarded writes)
  3. Generates safe payloads (dry_run, minimal bodies)
  4. Auto-skips destructive keywords
  5. Writes ACTION lines to the actions JSONL

The Witness is the only actor that writes verdicts.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from .temporal import BOOT_ID, ts_utc, mono_ns


# ── Safety Constants ─────────────────────────────────────────────

DESTRUCTIVE_KEYWORDS = re.compile(
    r"delete|clear|shutdown|restart|kill|wipe|lock|purge|reset|remove|destroy|drop",
    re.IGNORECASE,
)

# Auth-gated paths — 401 is a valid response (not a failure)
AUTH_GATED_PATHS = {
    "/api/nodes/pair/devices",
    "/api/nodes/pair/confirm",
    "/api/nodes/pair/revoke",
    "/api/nodes/pair/usb/detect",
}
AUTH_GATED_PREFIXES = (
    "/api/network/",
    "/api/nodes/fs/mode/",
    "/api/nodes/pair/usb/bundle/",
)

# Static asset routes — may return 404 if files don't exist on disk
STATIC_ASSET_PATHS = {
    "/favicon.ico",
}
OPTIONAL_404_PATHS = {
    "/api/winutil/ui",
}

# Paths where POST is always safe (no side effects or uses dry_run)
SAFE_POST_PATHS = {
    "/api/map",
    "/api/616",
    "/api/analyze_unmapped",
    "/api/ollama/warmup",
    "/api/nodes/heartbeat",
    "/api/chat/send",
    "/api/debugwire/toggle",
    "/api/observe/read",
}

# Paths that need --allow-ingest (dry_run enforced)
INGEST_PATHS = {
    "/api/gutenberg/ingest",
    "/api/localfile/ingest",
    "/api/webscrape/ingest",
    "/api/rss/ingest",
    "/api/lakespeak/ingest",
}


# ── Data Structures ──────────────────────────────────────────────

@dataclass
class Action:
    run_id: str = ""
    seq: int = 0
    ts_utc: str = ""       # RFC3339 UTC with Z + milliseconds
    mono_ns: int = 0       # monotonic nanoseconds (process-relative)
    boot_id: str = ""      # GUID per process start
    action: str = ""       # GET | POST | PATCH | DELETE | WS
    target: str = "bridge"
    url: str = ""
    payload: Optional[dict] = None
    payload_hash: str = "none"
    intent: str = ""       # READ_ONLY | DRY_RUN | WRITE | SKIP
    expected: Dict[str, Any] = field(default_factory=dict)
    skip_reason: str = ""


# ── Payload Generation ───────────────────────────────────────────

# Known safe payloads for POST endpoints that require a body
SAFE_PAYLOADS: Dict[str, dict] = {
    "/api/map": {"text": "The water is clear today.", "source": "smoke_test"},
    "/api/616": {"word": "water", "topk": 3},
    "/api/analyze_unmapped": {},
    "/api/ollama/warmup": {},
    "/api/chat/send": {
        "message": "smoke test",
        "mode": "llm",
        "topk": 3,
        "tools_enabled": False,
    },
    "/api/nodes/heartbeat": {},
    "/api/observe/read": {"ids": ["cpu", "memory"]},
    "/api/debugwire/toggle": {"enabled": False},
    # Ingest endpoints — always dry_run
    "/api/gutenberg/ingest": {"book_ids": [1342], "dry_run": True},
    "/api/localfile/ingest": {"paths": ["C:\\nonexistent_smoke_test.txt"], "dry_run": True},
    "/api/webscrape/ingest": {"urls": ["https://example.com"], "dry_run": True},
    "/api/rss/ingest": {"feed_url": "https://example.com/rss", "latest": 1, "dry_run": True},
    "/api/lakespeak/ingest": {"text": "smoke test passage", "dry_run": True},
    # Config — no-op patch (empty body → handler returns 400 "no fields")
    "/api/config": {},
    "/api/routing/profile": {},
    "/api/snapshot": {"tag": "smoke_test"},
}


def _hash_payload(payload: Optional[dict]) -> str:
    if payload is None:
        return "none"
    return "sha256:" + hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()[:16]


def _is_loopback(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in {"127.0.0.1", "localhost", "::1"}


# ── OpenAPI Discovery ────────────────────────────────────────────

def discover_endpoints(
    bridge_url: str,
    auth_headers: Optional[Dict[str, str]] = None,
    auth_cookies: Optional[Dict[str, str]] = None,
) -> Optional[dict]:
    """Fetch /openapi.json and return the spec, or None."""
    openapi_url = f"{bridge_url}/openapi.json"
    request_kwargs: Dict[str, Any] = {"timeout": 8}
    if _is_loopback(openapi_url):
        # Smoke uses local self-signed TLS by default.
        request_kwargs["verify"] = False
    if auth_headers:
        request_kwargs["headers"] = auth_headers
    if auth_cookies:
        request_kwargs["cookies"] = auth_cookies
    try:
        r = httpx.get(openapi_url, **request_kwargs)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


# ── Fallback: known endpoints when OpenAPI is unavailable ────────
# These are the routes we know exist from code inspection.  Used when
# /openapi.json returns 500 (e.g. broken model annotations).

FALLBACK_ROUTES = [
    # Boot & System
    {"path": "/api/stats",              "method": "GET",  "has_body": False},
    {"path": "/api/system",             "method": "GET",  "has_body": False},
    {"path": "/api/boot",               "method": "GET",  "has_body": False},
    {"path": "/api/services/health",    "method": "GET",  "has_body": False},
    {"path": "/api/config",             "method": "GET",  "has_body": False},
    {"path": "/api/config",             "method": "PATCH","has_body": True},
    {"path": "/api/snapshots",          "method": "GET",  "has_body": False},
    # Lexicon
    {"path": "/api/lexicon/distribution","method": "GET", "has_body": False},
    {"path": "/api/lexicon/browse?letter=A&limit=5", "method": "GET", "has_body": False},
    {"path": "/api/search_lexicon?query=water",      "method": "GET", "has_body": False},
    {"path": "/api/lookup?word=the",    "method": "GET",  "has_body": False},
    {"path": "/api/lexicon/sample?count=5",          "method": "GET", "has_body": False},
    {"path": "/api/lexicon/top?count=5",             "method": "GET", "has_body": False},
    {"path": "/api/lexicon/recent?count=5",          "method": "GET", "has_body": False},
    {"path": "/api/lexicon/entry?word=water",        "method": "GET", "has_body": False},
    # DocuMap
    {"path": "/api/documap/stats",      "method": "GET",  "has_body": False},
    {"path": "/api/documap/docs?limit=5","method": "GET", "has_body": False},
    {"path": "/api/jobs",               "method": "GET",  "has_body": False},
    # Mapping
    {"path": "/api/map",                "method": "POST", "has_body": True},
    {"path": "/api/616",                "method": "POST", "has_body": True},
    # Data Streams — manifests
    {"path": "/api/gutenberg/manifest", "method": "GET",  "has_body": False},
    {"path": "/api/localfile/manifest", "method": "GET",  "has_body": False},
    {"path": "/api/webscrape/manifest", "method": "GET",  "has_body": False},
    {"path": "/api/rss/manifest",       "method": "GET",  "has_body": False},
    # Data Streams — ingest (dry_run)
    {"path": "/api/gutenberg/ingest",   "method": "POST", "has_body": True},
    {"path": "/api/localfile/ingest",   "method": "POST", "has_body": True},
    {"path": "/api/webscrape/ingest",   "method": "POST", "has_body": True},
    {"path": "/api/rss/ingest",         "method": "POST", "has_body": True},
    # Plugins
    {"path": "/api/plugins",            "method": "GET",  "has_body": False},
    {"path": "/api/lakespeak/status",   "method": "GET",  "has_body": False},
    # Tools
    {"path": "/api/tools",              "method": "GET",  "has_body": False},
    {"path": "/api/debugwire/status",   "method": "GET",  "has_body": False},
    # Artifacts
    {"path": "/api/artifacts",          "method": "GET",  "has_body": False},
    # Routing
    {"path": "/api/routing/profile",    "method": "GET",  "has_body": False},
    {"path": "/api/routing/profiles",   "method": "GET",  "has_body": False},
    {"path": "/api/routing/dev-mode",   "method": "GET",  "has_body": False},
    # Providers & Inference
    {"path": "/api/providers",          "method": "GET",  "has_body": False},
    {"path": "/api/inference/profiles", "method": "GET",  "has_body": False},
    # Nodes
    {"path": "/api/nodes/status",       "method": "GET",  "has_body": False},
    {"path": "/api/nodes/list",         "method": "GET",  "has_body": False},
    {"path": "/api/nodes/heartbeat",    "method": "POST", "has_body": False},
    {"path": "/api/nodes/pair/devices", "method": "GET",  "has_body": False},
    # Chat Packs
    {"path": "/api/chat-packs/list",    "method": "GET",  "has_body": False},
    {"path": "/api/chat-packs/sessions","method": "GET",  "has_body": False},
    {"path": "/api/chat-packs/status",  "method": "GET",  "has_body": False},
    # Help
    {"path": "/api/help/status",        "method": "GET",  "has_body": False},
    {"path": "/api/help/ids",           "method": "GET",  "has_body": False},
    {"path": "/api/help/search?q=chat", "method": "GET",  "has_body": False},
    {"path": "/api/help/content/gpt-prompt", "method": "GET", "has_body": False},
    # Monitoring
    {"path": "/api/observe/sensors",    "method": "GET",  "has_body": False},
    {"path": "/api/observe/sensors/categories", "method": "GET", "has_body": False},
    # Chat
    {"path": "/api/chat/send",          "method": "POST", "has_body": True},
    {"path": "/api/ollama/warmup",      "method": "POST", "has_body": False},
]


def _extract_routes(spec: dict) -> List[dict]:
    """Extract all routes from OpenAPI spec as {path, method, operationId, has_body, required_query_params, has_query_params}."""
    routes = []
    for path, methods in spec.get("paths", {}).items():
        for method, detail in methods.items():
            if method.lower() in ("get", "post", "put", "patch", "delete"):
                has_body = "requestBody" in detail
                requires_auth = bool(detail.get("security"))
                # Collect query param info
                required_query = []
                has_query = False
                for param in detail.get("parameters", []):
                    if param.get("in") == "query":
                        has_query = True
                        if param.get("required", False):
                            required_query.append(param.get("name", ""))
                routes.append({
                    "path": path,
                    "method": method.upper(),
                    "operation_id": detail.get("operationId", ""),
                    "has_body": has_body,
                    "summary": detail.get("summary", ""),
                    "required_query_params": required_query,
                    "has_query_params": has_query,
                    "requires_auth": requires_auth,
                })
    return routes


# ── Queue Builder ────────────────────────────────────────────────

class Masher:
    """Builds and manages the action queue."""

    def __init__(
        self,
        run_id: str,
        bridge_url: str,
        llm_url: str,
        logs_dir: Path,
        allow_writes: bool = False,
        allow_ingest: bool = False,
        skip_llm: bool = False,
        skip_ollama: bool = False,
    ):
        self.run_id = run_id
        self.bridge_url = bridge_url.rstrip("/")
        self.llm_url = llm_url.rstrip("/")
        self.logs_dir = logs_dir
        self.allow_writes = allow_writes
        self.allow_ingest = allow_ingest
        self.skip_llm = skip_llm
        self.skip_ollama = skip_ollama

        self.actions_path = logs_dir / f"{run_id}.actions.jsonl"
        self._seq = 0
        self._queue: List[Action] = []

    def build_queue(self, openapi_spec: Optional[dict] = None) -> List[Action]:
        """Build the full action queue."""
        self._queue = []
        self._seq = 0

        # Phase 0: Non-bridge service probes
        self._add_service_probes()

        # Phase 1: Routes — from OpenAPI or fallback
        if openapi_spec:
            routes = _extract_routes(openapi_spec)
        else:
            routes = FALLBACK_ROUTES

        gets = [r for r in routes if r["method"] == "GET"]
        posts = [r for r in routes if r["method"] == "POST"]
        patches = [r for r in routes if r["method"] == "PATCH"]
        others = [r for r in routes if r["method"] not in ("GET", "POST", "PATCH")]

        # GETs first (all safe)
        for r in sorted(gets, key=lambda x: x["path"]):
            self._add_route(r)

        # PATCHes (safe if body is empty or no-op)
        for r in sorted(patches, key=lambda x: x["path"]):
            self._add_route(r)

        # POSTs (tiered by safety)
        for r in sorted(posts, key=lambda x: x["path"]):
            self._add_route(r)

        # DELETEs etc. — always skip
        for r in sorted(others, key=lambda x: x["path"]):
            self._add_route(r)

        # Phase 2: WebSocket probe
        ws_url = self.bridge_url.replace("http://", "ws://").replace("https://", "wss://")
        self._enqueue(
            method="WS",
            url=f"{ws_url}/ws/stream",
            target="bridge",
            intent="READ_ONLY",
            expected={"http": [101]},
        )

        return self._queue

    def _add_service_probes(self):
        """Add non-bridge service liveness probes."""
        # Ollama
        if self.skip_ollama:
            self._enqueue_skip("GET", "http://127.0.0.1:11434/api/tags", "ollama", "--skip-ollama")
        else:
            self._enqueue(
                method="GET",
                url="http://127.0.0.1:11434/api/tags",
                target="ollama",
                intent="READ_ONLY",
                expected={"http": [200], "shape": "models"},
            )

        # LLM proxy (may be HTTP or HTTPS — accept either, or not running)
        if self.skip_llm:
            self._enqueue_skip("GET", f"{self.llm_url}/health", "llm", "--skip-llm")
            self._enqueue_skip("GET", f"{self.llm_url}/api/auth/status", "llm", "--skip-llm")
        else:
            self._enqueue(
                method="GET",
                url=f"{self.llm_url}/health",
                target="llm",
                intent="READ_ONLY",
                expected={"http": [200], "try_https": True},
            )
            self._enqueue(
                method="GET",
                url=f"{self.llm_url}/api/auth/status",
                target="llm",
                intent="READ_ONLY",
                expected={"http": [200], "shape": "authenticated,has_credential", "try_https": True},
            )

        # UI (may be HTTP or HTTPS — accept either, or not running)
        self._enqueue(
            method="GET",
            url="http://127.0.0.1:8080/",
            target="ui",
            intent="READ_ONLY",
            expected={"http": [200], "try_https": True},
        )

    def _add_route(self, route: dict):
        """Convert an OpenAPI route to an action and enqueue it."""
        path = route["path"]
        method = route["method"]
        original_path = path  # before param filling

        # Track whether we filled any path params (resource may not exist → 404/400)
        has_filled_path_param = False

        # Skip paths with path parameters we can't fill
        if "{" in path:
            # We can fill some known ones
            path = self._try_fill_path_params(path)
            if "{" in path:
                self._enqueue_skip(method, f"{self.bridge_url}{path}", "bridge", "unfilled path param")
                return
            # If we get here, all params were filled — resource may not exist
            has_filled_path_param = (path != original_path)

        url = f"{self.bridge_url}{path}"

        # Safety gate: destructive keywords
        if DESTRUCTIVE_KEYWORDS.search(path):
            self._enqueue_skip(method, url, "bridge", "destructive keyword")
            return

        # DELETE method — always skip
        if method == "DELETE":
            self._enqueue_skip(method, url, "bridge", "DELETE method")
            return

        # PUT method — always skip unless --allow-writes
        if method == "PUT" and not self.allow_writes:
            self._enqueue_skip(method, url, "bridge", "PUT requires --allow-writes")
            return

        # Check for query params
        required_query = route.get("required_query_params", [])
        has_missing_query = len(required_query) > 0
        has_query_params = route.get("has_query_params", False)
        requires_auth = bool(route.get("requires_auth", False))
        is_auth_gated = requires_auth or path in AUTH_GATED_PATHS or any(
            path.startswith(prefix) for prefix in AUTH_GATED_PREFIXES
        )
        auth_codes = [401, 403, 429] if is_auth_gated else []

        # GET — always safe
        if method == "GET":
            expected_codes = [200]
            expected_codes.extend(auth_codes)
            if has_filled_path_param or path in STATIC_ASSET_PATHS or path in OPTIONAL_404_PATHS:
                expected_codes.extend([400, 404])
            if has_missing_query:
                expected_codes.extend([400, 422])
            elif has_query_params:
                # Handlers may validate optional params and return 400 on empty defaults
                expected_codes.append(400)
            self._enqueue(
                method=method, url=url, target="bridge",
                intent="READ_ONLY", expected={"http": sorted(set(expected_codes))},
            )
            return

        # PATCH — safe with empty body (400 is valid for empty no-op payloads)
        if method == "PATCH":
            payload = SAFE_PAYLOADS.get(path, {})
            patch_codes = [200, 400]
            patch_codes.extend(auth_codes)
            if has_filled_path_param:
                patch_codes.append(404)
            if has_missing_query:
                patch_codes.append(422)
            self._enqueue(
                method=method, url=url, target="bridge",
                payload=payload, intent="READ_ONLY",
                expected={"http": sorted(set(patch_codes))},
            )
            return

        # POST — tiered
        if method == "POST":
            # Chat send needs LLM proxy; honor --skip-llm before generic safe-path logic
            if path == "/api/chat/send" and self.skip_llm:
                self._enqueue_skip(method, url, "bridge", "--skip-llm")
                return

            # Ingest paths need --allow-ingest
            if path in INGEST_PATHS:
                if not self.allow_ingest:
                    self._enqueue_skip(method, url, "bridge", "needs --allow-ingest")
                    return
                payload = SAFE_PAYLOADS.get(path, {"dry_run": True})
                # Force dry_run even if payload doesn't have it
                if isinstance(payload, dict):
                    payload["dry_run"] = True
                self._enqueue(
                    method=method, url=url, target="bridge",
                    payload=payload, intent="DRY_RUN",
                    expected={"http": [200, 422]},
                )
                return

            # Known safe POSTs
            if path in SAFE_POST_PATHS:
                payload = SAFE_PAYLOADS.get(path)
                post_codes = [200]
                post_codes.extend(auth_codes)
                if has_filled_path_param:
                    post_codes.extend([400, 404])
                if has_missing_query:
                    post_codes.extend([400, 422])
                self._enqueue(
                    method=method, url=url, target="bridge",
                    payload=payload, intent="READ_ONLY",
                    expected={"http": sorted(set(post_codes))},
                )
                return

            # Auth-gated POST paths — 401 is expected
            if path in AUTH_GATED_PATHS:
                payload = SAFE_PAYLOADS.get(path)
                auth_codes = [200, 401, 403, 429]
                if has_filled_path_param:
                    auth_codes.extend([400, 404])
                self._enqueue(
                    method=method, url=url, target="bridge",
                    payload=payload, intent="READ_ONLY",
                    expected={"http": sorted(set(auth_codes))},
                )
                return

            # Unknown POST — needs --allow-writes
            if self.allow_writes:
                payload = SAFE_PAYLOADS.get(path, {})
                self._enqueue(
                    method=method, url=url, target="bridge",
                    payload=payload, intent="WRITE",
                    expected={"http": [200, 201, 422]},
                )
            else:
                self._enqueue_skip(method, url, "bridge", "POST requires --allow-writes")

    def _try_fill_path_params(self, path: str) -> str:
        """Fill known path parameters with safe test values."""
        replacements = {
            "{plugin_id}": "lakespeak",
            "{name}": "file_reader",
            "{book_id}": "1342",
            "{receipt_id}": "_smoke_nonexistent_",
            "{fingerprint}": "_smoke_nonexistent_",
            "{session_id}": "_smoke_nonexistent_",
            "{pack_id}": "_smoke_nonexistent_",
            "{anchor}": "water",
            "{model}": "qwen2.5:7b-instruct",
            "{filename}": "_smoke_nonexistent_",
            "{help_id}": "gpt-prompt",
            "{provider}": "openai",
            "{index}": "0",
            "{tag}": "gpt-prompt",
            "{node_id}": "_smoke_nonexistent_",
            "{project_id}": "_smoke_nonexistent_",
            "{app_id}": "_smoke_nonexistent_",
            "{feature_id}": "_smoke_nonexistent_",
            "{tweak_id}": "_smoke_nonexistent_",
            "{symbol_id}": "_smoke_nonexistent_",
            "{word}": "water",
        }
        for param, value in replacements.items():
            path = path.replace(param, value)
        return path

    # ── Queue Helpers ────────────────────────────────────────

    def _enqueue(
        self,
        method: str,
        url: str,
        target: str,
        intent: str,
        expected: dict,
        payload: Optional[dict] = None,
    ):
        self._seq += 1
        action = Action(
            run_id=self.run_id,
            seq=self._seq,
            ts_utc=ts_utc(),
            mono_ns=mono_ns(),
            boot_id=BOOT_ID,
            action=method,
            target=target,
            url=url,
            payload=payload,
            payload_hash=_hash_payload(payload),
            intent=intent,
            expected=expected,
        )
        self._queue.append(action)

    def _enqueue_skip(self, method: str, url: str, target: str, reason: str):
        self._seq += 1
        action = Action(
            run_id=self.run_id,
            seq=self._seq,
            ts_utc=ts_utc(),
            mono_ns=mono_ns(),
            boot_id=BOOT_ID,
            action=method,
            target=target,
            url=url,
            intent="SKIP",
            skip_reason=reason,
        )
        self._queue.append(action)

    # ── JSONL Writer ─────────────────────────────────────────

    def write_action(self, action: Action) -> None:
        line = json.dumps(asdict(action), separators=(",", ":"), sort_keys=True)
        with open(self.actions_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
