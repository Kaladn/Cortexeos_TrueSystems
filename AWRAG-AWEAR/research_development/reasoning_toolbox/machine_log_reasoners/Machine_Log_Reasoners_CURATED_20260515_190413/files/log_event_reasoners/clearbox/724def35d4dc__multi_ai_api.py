"""
multi_ai_api.py — Multi-AI Orchestrator Bridge Routes
Optional Clearbox bridge mount. Only used when running inside Clearbox.
Standalone VSCode operation does NOT require this file.

Routes:
  POST /api/multi_ai/chat            — proxy a turn through a local endpoint
  GET  /api/multi_ai/sessions        — list saved sessions (index.jsonl)
  GET  /api/multi_ai/session/{id}    — full session: meta + turns
  GET  /api/multi_ai/config          — current config snapshot
  GET  /api/multi_ai/help            — machine-readable schema (AI + human usable)

This file does NOT call any external company API.
All LLM calls go through vscode.lm (in the extension) or through
user-configured local endpoints only.

When mounted via bridge, POST /chat accepts pre-built message arrays
and proxies them to a local endpoint the user has configured.
It is a convenience proxy, not an LLM gateway.

See CONTRACT.md for full boundary contract.
"""

import json
import os
import pathlib
import datetime
import urllib.request
import urllib.error

# ── Storage path ──────────────────────────────────────────────────────────────

def _base_path() -> pathlib.Path:
    override = os.environ.get("MULTI_AI_SESSION_PATH", "").strip()
    if override:
        return pathlib.Path(override)
    return pathlib.Path.home() / ".clearbox" / "multi_ai" / "sessions"


def _session_dir(session_id: str) -> pathlib.Path:
    return _base_path() / session_id


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ok(data: dict | list, status: int = 200) -> tuple:
    return json.dumps(data), status, {"Content-Type": "application/json"}


def _err(msg: str, status: int = 400) -> tuple:
    return json.dumps({"error": msg}), status, {"Content-Type": "application/json"}


def _read_jsonl(path: pathlib.Path) -> list:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                pass  # skip malformed line — never crash on corrupt data
    return records


def _is_local_url(url: str) -> bool:
    """Hard guard — only allow localhost / LAN URLs."""
    import re
    pattern = re.compile(
        r"^https?://(localhost|127\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|"
        r"10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+|0\.0\.0\.0)(:\d+)?"
    )
    return bool(pattern.match(url))


# ── Route handlers ────────────────────────────────────────────────────────────

def handle_chat(request_body: dict) -> tuple:
    """
    POST /api/multi_ai/chat

    Proxies a pre-built message array to a user-configured local endpoint.
    Does NOT call any external company API.
    Does NOT accept external URLs — local only, enforced by _is_local_url().

    Expected body:
    {
      "local_url":   "http://localhost:11434/v1/chat/completions",
      "local_model": "qwen2.5:7b",
      "messages":    [{"role": "user", "content": "..."}, ...],
      "node_id":     1,
      "session_id":  "20260311_strategist_run"
    }
    """
    url   = request_body.get("local_url", "").strip()
    model = request_body.get("local_model", "").strip()
    msgs  = request_body.get("messages", [])

    if not url:
        return _err("local_url is required")
    if not _is_local_url(url):
        return _err("Only localhost/LAN endpoints are permitted. External URLs rejected.")
    if not model:
        return _err("local_model is required")
    if not msgs:
        return _err("messages array is required")

    payload = json.dumps({
        "model":    model,
        "messages": msgs,
        "stream":   False,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        return _err(f"Local endpoint unreachable: {e.reason}", 502)
    except Exception as e:
        return _err(f"Proxy error: {str(e)}", 500)

    content = (
        data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        if "choices" in data
        else json.dumps(data)
    )

    return _ok({
        "node_id":  request_body.get("node_id"),
        "response": content,
        "model":    model,
        "raw":      data,
    })


def handle_sessions(request_body: dict = None) -> tuple:
    """
    GET /api/multi_ai/sessions
    Returns index.jsonl as array — newest first.
    """
    index_path = _base_path() / "index.jsonl"
    sessions   = _read_jsonl(index_path)
    sessions.reverse()  # newest first
    return _ok({
        "sessions":    sessions,
        "count":       len(sessions),
        "storage_base": str(_base_path()),
    })


def handle_session(request_body: dict) -> tuple:
    """
    GET /api/multi_ai/session/{id}
    Returns meta + all turns for one session. Full fidelity — no truncation.

    Body: { "session_id": "..." }
    """
    session_id = (request_body or {}).get("session_id", "").strip()
    if not session_id:
        return _err("session_id is required")

    sd = _session_dir(session_id)
    if not sd.exists():
        return _err(f"Session '{session_id}' not found", 404)

    meta_path = sd / "meta.json"
    if not meta_path.exists():
        return _err(f"Session '{session_id}' has no meta.json", 404)

    meta           = json.loads(meta_path.read_text(encoding="utf-8"))
    turns          = _read_jsonl(sd / "turns.jsonl")
    config_changes = _read_jsonl(sd / "config_changes.jsonl")

    return _ok({
        "session_id":    session_id,
        "meta":          meta,
        "turns":         turns,
        "turn_count":    len(turns),
        "config_changes": config_changes,
    })


def handle_config(request_body: dict = None) -> tuple:
    """
    GET /api/multi_ai/config
    Returns current config snapshot — storage path, session count.
    """
    base       = _base_path()
    index_path = base / "index.jsonl"
    sessions   = _read_jsonl(index_path)
    active     = [s for s in sessions if not s.get("ended_at")]
    ended      = [s for s in sessions if s.get("ended_at")]

    return _ok({
        "storage_base":    str(base),
        "storage_exists":  base.exists(),
        "session_count":   len(sessions),
        "active_sessions": len(active),
        "ended_sessions":  len(ended),
        "version":         "1.0.0",
    })


def handle_help(request_body: dict = None) -> tuple:
    """
    GET /api/multi_ai/help
    Machine-readable schema. AI-usable and human-usable.
    """
    schema = {
        "plugin":      "multi_ai_orchestrator",
        "version":     "1.0.0",
        "description": "Hub/chain multi-AI conversation panel. Up to 10 nodes. Zero direct company API calls.",
        "endpoints": {
            "POST /api/multi_ai/chat": {
                "description": "Proxy a message array to a user-configured local endpoint only.",
                "body": {
                    "local_url":   "string — must be localhost or LAN",
                    "local_model": "string — model name passed to local endpoint",
                    "messages":    "array of {role, content}",
                    "node_id":     "int — which node this turn belongs to",
                    "session_id":  "string — active session id",
                },
                "returns": {
                    "node_id":  "int",
                    "response": "string — assistant content",
                    "model":    "string",
                    "raw":      "object — full response from local endpoint",
                },
            },
            "GET /api/multi_ai/sessions": {
                "description": "List all saved sessions from index.jsonl, newest first.",
                "returns": {
                    "sessions":     "array of session summary records",
                    "count":        "int",
                    "storage_base": "string — path to session storage directory",
                },
            },
            "GET /api/multi_ai/session/{id}": {
                "description": "Full session data — meta + all turns. No truncation.",
                "body":    { "session_id": "string" },
                "returns": {
                    "session_id":     "string",
                    "meta":           "object — node config snapshot at start",
                    "turns":          "array — every turn, full content",
                    "turn_count":     "int",
                    "config_changes": "array — mid-session node config changes",
                },
            },
            "GET /api/multi_ai/config": {
                "description": "Storage config snapshot and session counts.",
            },
            "GET /api/multi_ai/help": {
                "description": "This document.",
            },
        },
        "data_model": {
            "turn_record": {
                "session_id":       "string",
                "turn_id":          "uuid-v4",
                "seq":              "int — global sequence within session",
                "timestamp":        "ISO 8601",
                "node_id":          "int 1-10",
                "node_label":       "string",
                "slot_type":        "LLM | HUMAN",
                "provider_tier":    "lm_api | ext_export | local_http | none",
                "provider_display": "string — human-readable provider name",
                "role":             "user | assistant",
                "content":          "string — FULL content, never truncated",
                "source":           "manual | hub_dispatch | chain_from_{id} | human",
                "chain_from_node":  "int | null",
                "char_count":       "int",
            },
        },
        "storage": {
            "base":             "~/.clearbox/multi_ai/sessions/ (override via env MULTI_AI_SESSION_PATH)",
            "index":            "index.jsonl — one record per session, fast listing",
            "session_dir":      "{base}/{session_id}/",
            "turns_file":       "{session_dir}/turns.jsonl — append-only, full fidelity",
            "meta_file":        "{session_dir}/meta.json — node config snapshot",
            "config_changes":   "{session_dir}/config_changes.jsonl — mid-session changes",
            "session_notes":    "{session_dir}/session_notes.md — Lee-written only, never auto-written",
        },
        "invariants": [
            "turns.jsonl is append-only — never rewritten or truncated",
            "Every turn written to disk before chain propagates",
            "HUMAN slot forces chain_mode PREVIEW_FIRST — chain never skips a human",
            "isLocalUrl() hard guard — no external URLs accepted in proxy",
            "No model names hardcoded anywhere",
            "No API keys stored or injected",
            "Max 10 nodes enforced",
        ],
    }
    return _ok(schema)


# ── ROUTES dict — picked up by Clearbox plugin runner ────────────────────────

ROUTES = {
    "POST /api/multi_ai/chat":         handle_chat,
    "GET  /api/multi_ai/sessions":     handle_sessions,
    "GET  /api/multi_ai/session":      handle_session,
    "GET  /api/multi_ai/config":       handle_config,
    "GET  /api/multi_ai/help":         handle_help,
}
