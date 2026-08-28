"""API smoke probe — exercises all bridge endpoints via OpenAPI discovery.

Graduated from tests/smoke/masher.py + witness.py.
Self-contained: copies all constants locally (no imports from tests/).

Discovers endpoints via /openapi.json, builds a safe action queue,
executes each action, and converts results to ProbeResult.
"""

from __future__ import annotations

import hashlib
import json
import re
import socket
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from .base import Probe, RunContext, ProbeResult, make_result

# ── Safety Constants (copied from tests/smoke/masher.py) ─────

DESTRUCTIVE_KEYWORDS = re.compile(
    r"delete|clear|shutdown|restart|kill|wipe|lock|purge|reset|remove|destroy|drop",
    re.IGNORECASE,
)

AUTH_GATED_PATHS = {
    "/api/nodes/pair/devices",
    "/api/nodes/pair/confirm",
    "/api/nodes/pair/revoke",
    "/api/nodes/pair/usb/detect",
}

STATIC_ASSET_PATHS = {
    "/favicon.ico",
}

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

INGEST_PATHS = {
    "/api/gutenberg/ingest",
    "/api/localfile/ingest",
    "/api/webscrape/ingest",
    "/api/rss/ingest",
    "/api/lakespeak/ingest",
}

SAFE_PAYLOADS: Dict[str, dict] = {
    "/api/map": {"text": "The water is clear today.", "source": "smoke_test"},
    "/api/616": {"word": "water", "topk": 3},
    "/api/analyze_unmapped": {},
    "/api/ollama/warmup": {},
    "/api/chat/send": {
        "message": "smoke test",
        "mode": "reasoning",
        "execution_mode": "direct",
        "topk": 3,
        "tools_enabled": False,
    },
    "/api/nodes/heartbeat": {},
    "/api/observe/read": {"ids": ["cpu", "memory"]},
    "/api/debugwire/toggle": {"enabled": False},
    "/api/gutenberg/ingest": {"book_ids": [1342], "dry_run": True},
    "/api/localfile/ingest": {"paths": ["C:\\nonexistent_smoke_test.txt"], "dry_run": True},
    "/api/webscrape/ingest": {"urls": ["https://example.com"], "dry_run": True},
    "/api/rss/ingest": {"feed_url": "https://example.com/rss", "latest": 1, "dry_run": True},
    "/api/lakespeak/ingest": {"text": "smoke test passage", "dry_run": True},
    "/api/config": {},
    "/api/routing/profile": {},
    "/api/snapshot": {"tag": "smoke_test"},
}

PATH_PARAM_FILLS = {
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
}

FALLBACK_ROUTES = [
    {"path": "/api/stats",              "method": "GET",  "has_body": False},
    {"path": "/api/system",             "method": "GET",  "has_body": False},
    {"path": "/api/boot",               "method": "GET",  "has_body": False},
    {"path": "/api/services/health",    "method": "GET",  "has_body": False},
    {"path": "/api/config",             "method": "GET",  "has_body": False},
    {"path": "/api/config",             "method": "PATCH","has_body": True},
    {"path": "/api/snapshots",          "method": "GET",  "has_body": False},
    {"path": "/api/lexicon/distribution","method": "GET", "has_body": False},
    {"path": "/api/lexicon/browse?letter=A&limit=5", "method": "GET", "has_body": False},
    {"path": "/api/search_lexicon?query=water",      "method": "GET", "has_body": False},
    {"path": "/api/lookup?word=the",    "method": "GET",  "has_body": False},
    {"path": "/api/lexicon/sample?count=5",          "method": "GET", "has_body": False},
    {"path": "/api/lexicon/top?count=5",             "method": "GET", "has_body": False},
    {"path": "/api/lexicon/recent?count=5",          "method": "GET", "has_body": False},
    {"path": "/api/lexicon/entry?word=water",        "method": "GET", "has_body": False},
    {"path": "/api/documap/stats",      "method": "GET",  "has_body": False},
    {"path": "/api/documap/docs?limit=5","method": "GET", "has_body": False},
    {"path": "/api/jobs",               "method": "GET",  "has_body": False},
    {"path": "/api/map",                "method": "POST", "has_body": True},
    {"path": "/api/616",                "method": "POST", "has_body": True},
    {"path": "/api/gutenberg/manifest", "method": "GET",  "has_body": False},
    {"path": "/api/localfile/manifest", "method": "GET",  "has_body": False},
    {"path": "/api/webscrape/manifest", "method": "GET",  "has_body": False},
    {"path": "/api/rss/manifest",       "method": "GET",  "has_body": False},
    {"path": "/api/gutenberg/ingest",   "method": "POST", "has_body": True},
    {"path": "/api/localfile/ingest",   "method": "POST", "has_body": True},
    {"path": "/api/webscrape/ingest",   "method": "POST", "has_body": True},
    {"path": "/api/rss/ingest",         "method": "POST", "has_body": True},
    {"path": "/api/plugins",            "method": "GET",  "has_body": False},
    {"path": "/api/lakespeak/status",   "method": "GET",  "has_body": False},
    {"path": "/api/tools",              "method": "GET",  "has_body": False},
    {"path": "/api/debugwire/status",   "method": "GET",  "has_body": False},
    {"path": "/api/artifacts",          "method": "GET",  "has_body": False},
    {"path": "/api/routing/profile",    "method": "GET",  "has_body": False},
    {"path": "/api/routing/profiles",   "method": "GET",  "has_body": False},
    {"path": "/api/routing/dev-mode",   "method": "GET",  "has_body": False},
    {"path": "/api/providers",          "method": "GET",  "has_body": False},
    {"path": "/api/inference/profiles", "method": "GET",  "has_body": False},
    {"path": "/api/nodes/status",       "method": "GET",  "has_body": False},
    {"path": "/api/nodes/list",         "method": "GET",  "has_body": False},
    {"path": "/api/nodes/heartbeat",    "method": "POST", "has_body": False},
    {"path": "/api/nodes/pair/devices", "method": "GET",  "has_body": False},
    {"path": "/api/chat-packs/list",    "method": "GET",  "has_body": False},
    {"path": "/api/chat-packs/sessions","method": "GET",  "has_body": False},
    {"path": "/api/chat-packs/status",  "method": "GET",  "has_body": False},
    {"path": "/api/help/status",        "method": "GET",  "has_body": False},
    {"path": "/api/help/ids",           "method": "GET",  "has_body": False},
    {"path": "/api/help/search?q=chat", "method": "GET",  "has_body": False},
    {"path": "/api/help/content/gpt-prompt", "method": "GET", "has_body": False},
    {"path": "/api/observe/sensors",    "method": "GET",  "has_body": False},
    {"path": "/api/observe/sensors/categories", "method": "GET", "has_body": False},
    {"path": "/api/chat/send",          "method": "POST", "has_body": True},
    {"path": "/api/ollama/warmup",      "method": "POST", "has_body": False},
]

_HTTP_TIMEOUT = 10


# ── OpenAPI Discovery ────────────────────────────────────────

def _discover_endpoints(bridge_url: str) -> Optional[dict]:
    try:
        r = httpx.get(f"{bridge_url}/openapi.json", timeout=8, verify=False)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _extract_routes(spec: dict) -> List[dict]:
    routes = []
    for path, methods in spec.get("paths", {}).items():
        for method, detail in methods.items():
            if method.lower() in ("get", "post", "put", "patch", "delete"):
                has_body = "requestBody" in detail
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
                    "has_body": has_body,
                    "required_query_params": required_query,
                    "has_query_params": has_query,
                })
    return routes


def _fill_path_params(path: str) -> tuple[str, bool]:
    """Fill path params. Returns (filled_path, was_filled)."""
    original = path
    for param, value in PATH_PARAM_FILLS.items():
        path = path.replace(param, value)
    if "{" in path:
        return path, False  # unfilled params remain
    return path, (path != original)


# ── HTTP Execution ───────────────────────────────────────────

def _execute_http(
    client: httpx.Client, method: str, url: str, payload: Optional[dict] = None,
) -> Dict[str, Any]:
    obs: Dict[str, Any] = {}
    t0 = time.perf_counter()
    try:
        r = client.request(method, url, json=payload if method != "GET" else None)
        obs["lat_ms"] = (time.perf_counter() - t0) * 1000
        obs["code"] = r.status_code
        obs["content_type"] = r.headers.get("content-type", "")
        obs["body_bytes"] = len(r.content)
        obs["body_sha256"] = hashlib.sha256(r.content).hexdigest()
        if r.status_code >= 400:
            obs["body_preview"] = r.content[:512].decode("utf-8", errors="replace")
        if "json" in obs.get("content_type", ""):
            try:
                body = r.json()
                if isinstance(body, dict):
                    obs["json_keys"] = sorted(body.keys())
                elif isinstance(body, list):
                    obs["json_keys"] = ["__list__"]
            except Exception:
                pass
    except httpx.ConnectError:
        obs["lat_ms"] = (time.perf_counter() - t0) * 1000
        obs["code"] = 0
    except httpx.TimeoutException:
        obs["lat_ms"] = _HTTP_TIMEOUT * 1000
        obs["code"] = 408
    except Exception:
        obs["lat_ms"] = (time.perf_counter() - t0) * 1000
        obs["code"] = -1
    return obs


def _execute_ws(url: str) -> Dict[str, Any]:
    """Probe a WebSocket endpoint. SKIPPED if websocket-client not installed."""
    obs: Dict[str, Any] = {}
    t0 = time.perf_counter()

    # Only use websocket-client library — no raw socket fallback (audit fix #1)
    try:
        import websocket as ws_lib
        sock = ws_lib.create_connection(url, timeout=3, sslopt={"cert_reqs": 0})
        sock.close()
        obs["code"] = 101
        obs["lat_ms"] = (time.perf_counter() - t0) * 1000
        return obs
    except ImportError:
        obs["code"] = -2  # websocket-client not installed
        obs["lat_ms"] = 0
        return obs
    except Exception:
        obs["code"] = 0
        obs["lat_ms"] = (time.perf_counter() - t0) * 1000
        return obs


# ── Action Queue Builder ─────────────────────────────────────

@dataclass
class _Action:
    method: str = ""
    path: str = ""
    url: str = ""
    target: str = "bridge"
    payload: Optional[dict] = None
    intent: str = ""       # READ_ONLY | DRY_RUN | WRITE | SKIP
    expected_codes: List[int] = field(default_factory=lambda: [200])
    skip_reason: str = ""


def _build_queue(
    bridge_url: str,
    llm_url: str,
    spec: Optional[dict],
    skip_llm: bool,
    skip_ollama: bool,
    allow_writes: bool,
    allow_ingest: bool,
) -> List[_Action]:
    """Build the full action queue."""
    queue: List[_Action] = []

    # Service probes
    if skip_ollama:
        queue.append(_Action(method="GET", path="/api/tags", url="http://127.0.0.1:11434/api/tags",
                             target="ollama", intent="SKIP", skip_reason="Ollama API — omit --skip-ollama to probe"))
    else:
        queue.append(_Action(method="GET", path="/api/tags", url="http://127.0.0.1:11434/api/tags",
                             target="ollama", intent="READ_ONLY"))

    if skip_llm:
        queue.append(_Action(method="GET", path="/health", url=f"{llm_url}/health",
                             target="llm", intent="SKIP", skip_reason="LLM proxy — omit --skip-llm to probe"))
    else:
        queue.append(_Action(method="GET", path="/health", url=f"{llm_url}/health",
                             target="llm", intent="READ_ONLY"))

    queue.append(_Action(method="GET", path="/", url="http://127.0.0.1:8080/",
                         target="ui", intent="READ_ONLY"))

    # Routes from OpenAPI or fallback
    if spec:
        routes = _extract_routes(spec)
    else:
        routes = FALLBACK_ROUTES

    gets = sorted([r for r in routes if r["method"] == "GET"], key=lambda x: x["path"])
    patches = sorted([r for r in routes if r["method"] == "PATCH"], key=lambda x: x["path"])
    posts = sorted([r for r in routes if r["method"] == "POST"], key=lambda x: x["path"])
    others = sorted([r for r in routes if r["method"] not in ("GET", "POST", "PATCH")], key=lambda x: x["path"])

    for r in gets + patches + posts + others:
        action = _route_to_action(r, bridge_url, allow_writes, allow_ingest, skip_llm)
        if action:
            queue.append(action)

    # WebSocket probe
    ws_url = bridge_url.replace("http://", "ws://").replace("https://", "wss://")
    queue.append(_Action(method="WS", path="/ws/stream", url=f"{ws_url}/ws/stream",
                         target="bridge", intent="READ_ONLY", expected_codes=[101]))

    return queue


def _route_to_action(
    route: dict, bridge_url: str,
    allow_writes: bool, allow_ingest: bool, skip_llm: bool,
) -> Optional[_Action]:
    path = route["path"]
    method = route["method"]

    # Fill path params
    filled_path, was_filled = _fill_path_params(path)
    if "{" in filled_path:
        return _Action(method=method, path=path, url=f"{bridge_url}{path}",
                       intent="SKIP", skip_reason="Path parameter required — add sample to SAMPLE_PATH_PARAMS")

    url = f"{bridge_url}{filled_path}"

    # Safety: destructive keywords
    if DESTRUCTIVE_KEYWORDS.search(filled_path):
        return _Action(method=method, path=filled_path, url=url,
                       intent="SKIP", skip_reason="Destructive endpoint (shutdown/reset/delete) — manual test only")

    if method == "DELETE":
        return _Action(method=method, path=filled_path, url=url,
                       intent="SKIP", skip_reason="DELETE method — run with --allow-writes to include")

    if method == "PUT" and not allow_writes:
        return _Action(method=method, path=filled_path, url=url,
                       intent="SKIP", skip_reason="PUT method — run with --allow-writes to include")

    required_query = route.get("required_query_params", [])
    has_missing_query = len(required_query) > 0
    has_query_params = route.get("has_query_params", False)

    if method == "GET":
        codes = [200]
        if filled_path in AUTH_GATED_PATHS:
            codes.append(401)
        if was_filled or filled_path in STATIC_ASSET_PATHS:
            codes.extend([400, 404])
        if has_missing_query:
            codes.extend([400, 422])
        elif has_query_params:
            codes.append(400)
        return _Action(method=method, path=filled_path, url=url,
                       intent="READ_ONLY", expected_codes=sorted(set(codes)))

    if method == "PATCH":
        payload = SAFE_PAYLOADS.get(filled_path, {})
        codes = [200, 400]
        if was_filled:
            codes.append(404)
        if has_missing_query:
            codes.append(422)
        return _Action(method=method, path=filled_path, url=url,
                       payload=payload, intent="READ_ONLY",
                       expected_codes=sorted(set(codes)))

    if method == "POST":
        if filled_path in INGEST_PATHS:
            if not allow_ingest:
                return _Action(method=method, path=filled_path, url=url,
                               intent="SKIP", skip_reason="Ingest endpoint — run with --allow-ingest to include")
            payload = SAFE_PAYLOADS.get(filled_path, {"dry_run": True})
            if isinstance(payload, dict):
                payload = {**payload, "dry_run": True}
            return _Action(method=method, path=filled_path, url=url,
                           payload=payload, intent="DRY_RUN",
                           expected_codes=[200, 422])

        if filled_path in SAFE_POST_PATHS:
            payload = SAFE_PAYLOADS.get(filled_path)
            codes = [200]
            if was_filled:
                codes.extend([400, 404])
            if has_missing_query:
                codes.extend([400, 422])
            return _Action(method=method, path=filled_path, url=url,
                           payload=payload, intent="READ_ONLY",
                           expected_codes=sorted(set(codes)))

        if filled_path == "/api/chat/send" and skip_llm:
            return _Action(method=method, path=filled_path, url=url,
                           intent="SKIP", skip_reason="LLM chat endpoint — omit --skip-llm to include")

        if filled_path in AUTH_GATED_PATHS:
            payload = SAFE_PAYLOADS.get(filled_path)
            codes = [200, 401]
            if was_filled:
                codes.extend([400, 404])
            return _Action(method=method, path=filled_path, url=url,
                           payload=payload, intent="READ_ONLY",
                           expected_codes=sorted(set(codes)))

        if allow_writes:
            payload = SAFE_PAYLOADS.get(filled_path, {})
            return _Action(method=method, path=filled_path, url=url,
                           payload=payload, intent="WRITE",
                           expected_codes=[200, 201, 422])
        else:
            return _Action(method=method, path=filled_path, url=url,
                           intent="SKIP", skip_reason="POST endpoint — run with --allow-writes to include")

    return None


# ── The Probe ────────────────────────────────────────────────

class ApiSmokeProbe:
    """Exercises all bridge endpoints via OpenAPI discovery."""

    probe_id = "api_smoke"
    description = "Full bridge API endpoint coverage via OpenAPI"

    def run(self, ctx: RunContext) -> List[ProbeResult]:
        results: List[ProbeResult] = []
        bridge = ctx.bridge_url

        # Phase 1: OpenAPI discovery
        t0 = time.perf_counter()
        spec = _discover_endpoints(bridge)
        lat = (time.perf_counter() - t0) * 1000

        if spec:
            path_count = sum(len(m) for m in spec.get("paths", {}).values())
            results.append(make_result(
                ctx, self.probe_id, "api.openapi_discovery",
                "CONFIRMED", lat_ms=lat,
                detail={"paths": len(spec.get("paths", {})), "operations": path_count},
            ))
        else:
            results.append(make_result(
                ctx, self.probe_id, "api.openapi_discovery",
                "DENIED", lat_ms=lat,
                detail={"fallback_routes": len(FALLBACK_ROUTES)},
            ))

        # Phase 2: Build queue
        queue = _build_queue(
            bridge_url=bridge,
            llm_url=ctx.llm_url,
            spec=spec,
            skip_llm=ctx.skip_llm,
            skip_ollama=ctx.skip_ollama,
            allow_writes=ctx.allow_writes,
            allow_ingest=ctx.allow_ingest,
        )

        # Phase 3: Execute
        client = httpx.Client(timeout=_HTTP_TIMEOUT, verify=False, follow_redirects=True)
        try:
            for action in queue:
                check_id = f"api.{action.method}.{action.path}"

                # Skipped actions
                if action.intent == "SKIP":
                    results.append(make_result(
                        ctx, self.probe_id, check_id,
                        "SKIPPED", skip_reason=action.skip_reason,
                    ))
                    continue

                # Execute
                if action.method == "WS":
                    obs = _execute_ws(action.url)
                    if obs.get("code") == -2:
                        results.append(make_result(
                            ctx, self.probe_id, check_id,
                            "SKIPPED", skip_reason="WebSocket probe — pip install websocket-client to enable",
                            detail={"http": obs},
                        ))
                        continue
                else:
                    obs = _execute_http(client, action.method, action.url, action.payload)

                    # HTTPS fallback for non-bridge targets
                    if obs.get("code", 0) <= 0 and action.url.startswith("http://"):
                        https_url = "https://" + action.url[len("http://"):]
                        obs = _execute_http(client, action.method, https_url, action.payload)

                # Verdict
                code = obs.get("code", 0)
                if code in action.expected_codes:
                    verdict = "CONFIRMED"
                else:
                    verdict = "DENIED"

                results.append(make_result(
                    ctx, self.probe_id, check_id,
                    verdict,
                    lat_ms=obs.get("lat_ms", 0),
                    detail={"http": obs, "target": action.target},
                ))
        finally:
            client.close()

        return results
