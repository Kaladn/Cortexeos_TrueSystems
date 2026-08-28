"""HTTP and WebSocket server exposing the Forest Lexicon bridge."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import random
import threading
import time
import uuid
from datetime import datetime, timezone
import sys
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, cast

import glob

from fastapi import FastAPI, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import httpx

if __package__ is None or __package__ == "":
    BASE_DIR = Path(__file__).resolve().parent.parent
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
    _plugins_dir = str(BASE_DIR / "plugins")
    if _plugins_dir not in sys.path:
        sys.path.insert(0, _plugins_dir)
    from bridges.forest_bridge import ForestLexiconBridge, load_bridge_from_config
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    _plugins_dir = str(BASE_DIR / "plugins")
    if _plugins_dir not in sys.path:
        sys.path.insert(0, _plugins_dir)
    from .forest_bridge import ForestLexiconBridge, load_bridge_from_config

from security.data_paths import (
    FOREST_CONFIG_PATH as _SEC_CONFIG, STATE_DIR, LAKESPEAK_INDEX_DIR, LAKESPEAK_CHUNKS_DIR,
    AUDIT_DIR, DIAGNOSTIC_DIR,
)
from security.storage_layout import DATA_MAPPED_DIR, DATA_RAW_DIR
from security.secure_storage import secure_json_load, secure_json_dump
from security.runtime_log import RUNTIME_LOG_PATH, debug_enter, debug_exit, log_error as _rt_error  # DEBUGWIRE:HTTP
from security.tool_telemetry import TOOL_TELEMETRY_PATH
def _trace_id(request) -> str | None:  # DEBUGWIRE:TRACE
    try: return request.headers.get("X-Trace-Id")
    except Exception: return None
from routing.config import load_routing_profile, DEFAULTS as _ROUTING_DEFAULTS

# Single source of truth for the fallback model name (routing/config.py)
DEFAULT_MODEL = _ROUTING_DEFAULTS["pipeline"][2]["config"]["model"]
from routing.engine import RouteEngine

# Chat logging + history retrieval — bridge handles directly
from Conversations.threads import log_message as _log_message
from Conversations.threads.reader import load_recent_days as _load_recent_days


def _build_chat_messages(current_msg: str, max_turns: int = 20) -> list[dict]:
    """Build messages array from recent conversation history + current message.

    Returns list of {"role": "user"|"assistant", "content": "..."} dicts.
    Uses a 3-day window so context survives midnight rollover.
    Most recent `max_turns` messages kept to stay within context limits.
    Includes pinned AI_BRIEF digest (if pinned today) as first system message.
    """
    history = _load_recent_days(days=3)
    branch_msgs = [m for m in history if m.branch == "main"]
    # Convert logged messages to role/content pairs
    msgs = []
    for m in branch_msgs:
        # Skip AI_BRIEF pin entries from chat history (they're system notes)
        if getattr(m, "kind", None) == "AI_BRIEF":
            continue
        role = "user" if m.sender == "user" else "assistant"
        msgs.append({"role": role, "content": m.content})
    # Keep tail to avoid blowing context window
    if len(msgs) > max_turns:
        msgs = msgs[-max_turns:]

    # Check for pinned AI_BRIEF today — include as first system message
    _brief_digest = _get_todays_pinned_digest()
    if _brief_digest:
        msgs.insert(0, {"role": "system", "content": _brief_digest})

    # Append current user message
    msgs.append({"role": "user", "content": current_msg})
    return msgs


def _get_todays_pinned_digest() -> str | None:
    """Return the pinned AI_BRIEF digest content for today, or None."""
    try:
        from Conversations.threads.daily_logger import get_today_file
        from security.secure_storage import secure_read_lines
        today_file = get_today_file()
        if not today_file.exists():
            return None
        for line in secure_read_lines(today_file):
            try:
                obj = json.loads(line)
                if obj.get("kind") == "AI_BRIEF":
                    return obj.get("content")
            except (json.JSONDecodeError, AttributeError):
                continue
    except Exception:
        pass
    return None


def _merge_consecutive_roles(messages: list[dict]) -> list[dict]:
    """Merge consecutive same-role messages for APIs that require alternation.

    Used by Claude mode only. Merges content with double-newline separator.
    Does NOT drop messages — information is preserved.
    """
    if not messages:
        return messages
    out = [messages[0].copy()]
    for m in messages[1:]:
        if m.get("role") == out[-1].get("role"):
            out[-1]["content"] = f'{out[-1].get("content", "")}\n\n{m.get("content", "")}'.strip()
        else:
            out.append(m.copy())
    return out


# ── Extracted cloud API callers (used by chain executor + mode handlers) ──

async def _call_openai(api_key: str, model: str, messages: list[dict],
                       inference_params: dict | None = None) -> tuple[str, dict, int]:
    """Call OpenAI Responses API. Returns (reply, usage, latency_ms)."""
    payload: dict = {"model": model, "input": messages}
    if inference_params:
        if "temperature" in inference_params:
            payload["temperature"] = inference_params["temperature"]
        if "top_p" in inference_params:
            payload["top_p"] = inference_params["top_p"]
        if "max_tokens" in inference_params:
            payload["max_output_tokens"] = inference_params["max_tokens"]
    t0 = time.time()
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
    ms = int((time.time() - t0) * 1000)
    if not r.is_success:
        return "", {"error": f"HTTP {r.status_code}: {r.text[:300]}"}, ms
    data = r.json()
    reply = ""
    for item in data.get("output", []):
        if item.get("type") == "message":
            for block in item.get("content", []):
                if block.get("type") == "output_text":
                    reply += block.get("text", "")
    if reply and ("tool_call" in reply or "<tool_call>" in reply):
        from bridges.tool_defs import strip_tool_calls
        reply = strip_tool_calls(reply)
    return reply, data.get("usage", {}), ms


async def _call_claude(api_key: str, model: str, messages: list[dict],
                       inference_params: dict | None = None) -> tuple[str, dict, int]:
    """Call Anthropic Messages API. Returns (reply, usage, latency_ms)."""
    payload: dict = {
        "model": model,
        "max_tokens": 4096,
        "messages": _merge_consecutive_roles(messages),
    }
    if inference_params:
        if "temperature" in inference_params:
            payload["temperature"] = inference_params["temperature"]
        if "top_p" in inference_params:
            payload["top_p"] = inference_params["top_p"]
        if "top_k" in inference_params:
            payload["top_k"] = inference_params["top_k"]
        if "max_tokens" in inference_params:
            payload["max_tokens"] = inference_params["max_tokens"]
    t0 = time.time()
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01",
                     "Content-Type": "application/json"},
            json=payload,
        )
    ms = int((time.time() - t0) * 1000)
    if not r.is_success:
        return "", {"error": f"HTTP {r.status_code}: {r.text[:300]}"}, ms
    data = r.json()
    reply = "".join(
        block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
    )
    if reply and ("tool_call" in reply or "<tool_call>" in reply):
        from bridges.tool_defs import strip_tool_calls
        reply = strip_tool_calls(reply)
    return reply, data.get("usage", {}), ms


async def _call_gemini(api_key: str, model: str, messages: list[dict],
                       inference_params: dict | None = None) -> tuple[str, dict, int]:
    """Call Google Gemini generateContent. Returns (reply, usage, latency_ms)."""
    _GEMINI_ROLE = {"user": "user", "assistant": "model", "system": "user"}
    _system_parts = [m["content"] for m in messages if m["role"] == "system"]
    _chat_msgs = [m for m in messages if m["role"] != "system"]
    payload: dict = {
        "contents": [
            {"role": _GEMINI_ROLE.get(m["role"], "user"), "parts": [{"text": m["content"]}]}
            for m in _chat_msgs
        ],
    }
    if _system_parts:
        payload["systemInstruction"] = {"parts": [{"text": "\n".join(_system_parts)}]}
    _gen_config: dict = {}
    if inference_params:
        if "temperature" in inference_params:
            _gen_config["temperature"] = inference_params["temperature"]
        if "top_p" in inference_params:
            _gen_config["topP"] = inference_params["top_p"]
        if "top_k" in inference_params:
            _gen_config["topK"] = inference_params["top_k"]
        if "max_tokens" in inference_params:
            _gen_config["maxOutputTokens"] = inference_params["max_tokens"]
    if _gen_config:
        payload["generationConfig"] = _gen_config
    t0 = time.time()
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
            json=payload,
        )
    ms = int((time.time() - t0) * 1000)
    if not r.is_success:
        return "", {"error": f"HTTP {r.status_code}: {r.text[:300]}"}, ms
    data = r.json()
    reply = ""
    for candidate in data.get("candidates", []):
        for part in candidate.get("content", {}).get("parts", []):
            reply += part.get("text", "")
    if reply and ("tool_call" in reply or "<tool_call>" in reply):
        from bridges.tool_defs import strip_tool_calls
        reply = strip_tool_calls(reply)
    return reply, data.get("usageMetadata", {}), ms


async def _call_grok(api_key: str, model: str, messages: list[dict],
                     inference_params: dict | None = None) -> tuple[str, dict, int]:
    """Call xAI Chat Completions API. Returns (reply, usage, latency_ms)."""
    payload: dict = {"model": model, "messages": messages, "stream": False}
    if inference_params:
        if "temperature" in inference_params:
            payload["temperature"] = inference_params["temperature"]
        if "top_p" in inference_params:
            payload["top_p"] = inference_params["top_p"]
        if "max_tokens" in inference_params:
            payload["max_tokens"] = inference_params["max_tokens"]
    t0 = time.time()
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
        )
    ms = int((time.time() - t0) * 1000)
    if not r.is_success:
        return "", {"error": f"HTTP {r.status_code}: {r.text[:300]}"}, ms
    data = r.json()
    reply = ""
    choices = data.get("choices", [])
    if choices:
        reply = choices[0].get("message", {}).get("content", "")
    if reply and ("tool_call" in reply or "<tool_call>" in reply):
        from bridges.tool_defs import strip_tool_calls
        reply = strip_tool_calls(reply)
    return reply, data.get("usage", {}), ms


async def _call_ollama(api_key: str, model: str, messages: list[dict],
                       inference_params: dict | None = None) -> tuple[str, dict, int]:
    """Call local Ollama /api/chat. api_key unused (local)."""
    _ = api_key
    payload: dict = {
        "model": model or DEFAULT_MODEL,
        "messages": messages,
        "stream": False,
    }
    if inference_params:
        opts: dict = {}
        if "temperature" in inference_params:
            opts["temperature"] = inference_params["temperature"]
        if "top_p" in inference_params:
            opts["top_p"] = inference_params["top_p"]
        if "top_k" in inference_params:
            opts["top_k"] = int(inference_params["top_k"])
        if "repeat_penalty" in inference_params:
            opts["repeat_penalty"] = inference_params["repeat_penalty"]
        if "max_tokens" in inference_params:
            opts["num_predict"] = int(inference_params["max_tokens"])
        if opts:
            payload["options"] = opts

    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post("http://localhost:11434/api/chat", json=payload)
        ms = int((time.time() - t0) * 1000)
        if not r.is_success:
            return "", {"error": f"HTTP {r.status_code}: {r.text[:300]}"}, ms
        data = r.json()
        reply = data.get("message", {}).get("content", "")
        if reply and ("tool_call" in reply or "<tool_call>" in reply):
            from bridges.tool_defs import strip_tool_calls
            reply = strip_tool_calls(reply)
        usage = {
            "prompt_eval_count": data.get("prompt_eval_count"),
            "eval_count": data.get("eval_count"),
        }
        return reply, usage, ms
    except Exception as e:
        return f"[Ollama error: {e}]", {}, int((time.time() - t0) * 1000)


async def _call_grounded(api_key: str, model: str, messages: list[dict],
                         inference_params: dict | None = None) -> tuple[str, dict, int]:
    """Query LakeSpeak for grounded retrieval-augmented response. api_key unused (local)."""
    raw_msg = messages[-1].get("content", "") if messages else ""
    # When called as a chain slot, the message contains full chain context.
    # Extract just the user question from "## User Message\n...\n\n##" block.
    import re as _re
    _um = _re.search(r"## User Message\n(.+?)(?:\n\n##|\Z)", raw_msg, _re.DOTALL)
    user_msg = _um.group(1).strip() if _um else raw_msg
    t0 = time.time()
    try:
        from lakespeak.api.router import get_engine
        import asyncio as _aio
        engine = get_engine()
        ls_result = await _aio.to_thread(engine.query, query=user_msg, mode="grounded", topk=8)

        citations = ls_result.citations or []
        if ls_result.verdict == "trash":
            reply = ls_result.answer_text or "(No grounded evidence found)"
            return reply, {"verdict": "trash", "citations": 0}, int((time.time() - t0) * 1000)

        # Build evidence block
        evidence_lines = []
        for i, c in enumerate(citations[:8]):
            snippet = c.get("snippet", c.get("text", ""))[:600]
            score = c.get("score", 0)
            evidence_lines.append(f"[{i+1}] (score: {score:.3f}) {snippet}")
        evidence_block = "\n\n".join(evidence_lines)

        # Call Ollama with evidence
        grounded_messages = [
            {"role": "system", "content": (
                "You are a grounded research assistant. Answer using ONLY the evidence provided. "
                "Cite evidence by number [1], [2], etc. If the evidence does not contain the answer, say so."
            )},
            {"role": "user", "content": user_msg},
            {"role": "system", "content": f"EVIDENCE FROM ARCHIVE:\n\n{evidence_block}"},
        ]
        ollama_model = model or "gpt_oss:20b"
        payload = {"model": ollama_model, "messages": grounded_messages, "stream": False}
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post("http://localhost:11434/api/chat", json=payload)
        ms = int((time.time() - t0) * 1000)
        if r.is_success:
            reply = r.json().get("message", {}).get("content", "")
            return reply, {"citations": len(citations), "verdict": ls_result.verdict}, ms
        else:
            return ls_result.answer_text or "(Ollama error in grounded)", {}, ms
    except ImportError:
        return "(LakeSpeak plugin not available)", {}, int((time.time() - t0) * 1000)
    except Exception as e:
        return f"[Grounded error: {e}]", {}, int((time.time() - t0) * 1000)


# ── Reasoning engine singleton (in-process, no HTTP) ──────────
_reasoning_engine = None

def _get_reasoning_engine():
    """Lazy-load the reasoning engine (SQLite-backed, no external deps)."""
    global _reasoning_engine
    if _reasoning_engine is None:
        from reasoning_engine.engine import ReasoningEngine
        _reasoning_engine = ReasoningEngine()
        _reasoning_engine.scan_and_update_indexes()
        LOGGER.info("Reasoning engine loaded in-process")
    return _reasoning_engine

def _extract_subject(question: str) -> str:
    """Extract the subject term from a natural-language question."""
    q = question.lower()
    for pattern, keyword in [
        ("what does", "does"), ("what do", "do"),
        ("what is", "is"), ("what are", "are"),
    ]:
        if pattern in q:
            parts = q.split()
            if keyword in parts:
                idx = parts.index(keyword)
                if idx + 1 < len(parts):
                    return parts[idx + 1]
    # Fallback: last noun-like word
    words = question.lower().replace("?", "").split()
    return words[-1] if words else question

async def _call_reasoning(api_key: str, model: str, messages: list[dict],
                          inference_params: dict | None = None) -> tuple[str, dict, int]:
    """Query the 6-1-6 reasoning engine in-process. api_key unused (local)."""
    import asyncio as _aio
    user_msg = messages[-1].get("content", "") if messages else ""
    t0 = time.time()
    try:
        engine = _get_reasoning_engine()
        subject = _extract_subject(user_msg)
        answer = await _aio.to_thread(engine.query_what_does_x_do, subject, 8)
        ms = int((time.time() - t0) * 1000)
        return answer.surface_text, answer.reasoning_trace, ms
    except HTTPException as he:
        ms = int((time.time() - t0) * 1000)
        if he.status_code == 404:
            return f"No map data for that term.", {"note": "anchor_not_found"}, ms
        return f"[Reasoning error: {he.detail}]", {}, ms
    except Exception as e:
        return f"[Reasoning engine error: {e}]", {}, int((time.time() - t0) * 1000)


_CHAIN_CALLERS = {
    "ollama": _call_ollama,
    "openai": _call_openai,
    "claude": _call_claude,
    "gemini": _call_gemini,
    "grok": _call_grok,
    "grounded": _call_grounded,
    "reasoning": _call_reasoning,
}


def _parse_tool_request(text: str) -> list[dict] | None:
    """Parse structured tool_request JSON from a slot response.

    Expected format (anywhere in text):
        {"type": "tool_request", "requests": [{"name": "...", "arguments": {}, "reason": "..."}]}

    Returns list of request dicts, or None if not found.
    """
    import json as _json
    import re as _re

    # Look for JSON object with type: tool_request
    for match in _re.finditer(r'\{[^{}]*"type"\s*:\s*"tool_request"[^{}]*"requests"\s*:\s*\[.*?\]\s*\}', text, _re.DOTALL):
        try:
            parsed = _json.loads(match.group())
            if parsed.get("type") == "tool_request" and isinstance(parsed.get("requests"), list):
                reqs = []
                for r in parsed["requests"]:
                    if isinstance(r, dict) and "name" in r:
                        reqs.append({
                            "name": r["name"],
                            "arguments": r.get("arguments", {}),
                            "reason": r.get("reason", ""),
                        })
                return reqs if reqs else None
        except (_json.JSONDecodeError, TypeError):
            continue
    return None


LOGGER = logging.getLogger("forest_bridge_server")
VERSION = "forest-bridge-1.4.0"


@dataclass
class JobRecord:
    job_id: str
    job_type: str
    created_at: float
    status: str = "queued"
    progress: Dict[str, Any] = field(default_factory=dict)
    result_path: Optional[str] = None
    error: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    updated_at: float = field(default_factory=lambda: time.time())
    cancel_requested: bool = False


class JobManager:
    def __init__(self) -> None:
        self._jobs: Dict[str, JobRecord] = {}
        self._lock = threading.Lock()

    def create_job(self, job_type: str, payload: Optional[Dict[str, Any]] = None) -> JobRecord:
        job_id = uuid.uuid4().hex
        record = JobRecord(job_id=job_id, job_type=job_type, created_at=time.time(), payload=payload or {})
        with self._lock:
            self._jobs[job_id] = record
        return record

    def get(self, job_id: str) -> Optional[JobRecord]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self) -> List[JobRecord]:
        with self._lock:
            return list(self._jobs.values())

    def start(self, job_id: str, **progress: Any) -> None:
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                return
            record.status = "running"
            record.progress.update(progress)
            record.updated_at = time.time()

    def update_progress(self, job_id: str, **progress: Any) -> None:
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                return
            record.progress.update(progress)
            record.updated_at = time.time()

    def complete(self, job_id: str, result_path: Optional[str] = None) -> None:
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                return
            record.status = "completed"
            record.result_path = result_path
            record.updated_at = time.time()

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                return
            record.status = "error"
            record.error = error
            record.updated_at = time.time()

    def cancel(self, job_id: str) -> Optional[JobRecord]:
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                return None
            record.cancel_requested = True
            record.status = "cancelling" if record.status == "running" else "cancelled"
            record.updated_at = time.time()
            return record

    def finish_cancel(self, job_id: str) -> None:
        with self._lock:
            record = self._jobs.get(job_id)
            if not record:
                return
            record.status = "cancelled"
            record.updated_at = time.time()


class BridgeState:
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config = self._load_json(config_path)
        self.bridge: ForestLexiconBridge = load_bridge_from_config(config_path, load_lexicon=False)
        self.lock = asyncio.Lock()
        self.jobs = JobManager()
        # Shared httpx client for Ollama calls — connection pooling, reuse TCP
        self.ollama_client: Optional[httpx.AsyncClient] = None
        # Cache for disk-derived stats when bridge is not loaded.
        self._disk_stats_cache_sig: Optional[tuple] = None
        self._disk_stats_cache_values: Optional[Dict[str, Any]] = None
        # Cache for lexicon pack inventory shown in Lexicon Browser strip.
        self._pack_inventory_cache_sig: Optional[tuple] = None
        self._pack_inventory_cache_values: Optional[Dict[str, Any]] = None

    async def get_ollama_client(self) -> httpx.AsyncClient:
        """Lazy-init shared httpx client for Ollama. Connection pooled."""
        if self.ollama_client is None or self.ollama_client.is_closed:
            self.ollama_client = httpx.AsyncClient(timeout=120.0)
        return self.ollama_client

    async def close(self):
        """Shutdown: close shared clients."""
        if self.ollama_client and not self.ollama_client.is_closed:
            await self.ollama_client.close()

    @staticmethod
    def _load_json(path: Path) -> Dict[str, Any]:
        return secure_json_load(path)

    def _disk_stats_signature(self) -> tuple:
        root = self.bridge.lexicon_root
        parts: List[tuple] = []
        for file_path in root.rglob("*.json"):
            if file_path.name == "enrichment_state.json":
                continue
            try:
                st = file_path.stat()
            except OSError:
                continue
            rel = str(file_path.relative_to(root))
            parts.append((rel, int(st.st_mtime_ns), int(st.st_size)))
        parts.sort()
        return tuple(parts)

    def _compute_disk_stats(self) -> Dict[str, Any]:
        sig = self._disk_stats_signature()
        if self._disk_stats_cache_sig == sig and self._disk_stats_cache_values:
            return dict(self._disk_stats_cache_values)

        entries = 0
        entries_with_frequency = 0
        entries_with_context = 0
        total_frequency = 0
        slots_total = 0
        slots_assigned = 0
        slots_available = 0

        for file_path in self.bridge.lexicon_root.rglob("*.json"):
            if file_path.name == "enrichment_state.json":
                continue
            try:
                with open(file_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except (OSError, json.JSONDecodeError):
                continue

            if isinstance(data, list) and data and isinstance(data[0], dict) and self.bridge._is_spare_slot(data[0]):
                slots_total += len(data)
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    status = str(item.get("status", "AVAILABLE")).upper()
                    word = item.get("word")
                    if status == "ASSIGNED" and isinstance(word, str) and word.strip():
                        slots_assigned += 1
                    else:
                        slots_available += 1
                continue

            if isinstance(data, dict):
                items = data.items()
            elif isinstance(data, list):
                hydrated: List[tuple] = []
                for entry in data:
                    if not isinstance(entry, dict):
                        continue
                    word = entry.get("word") or entry.get("token")
                    if isinstance(word, str) and word.strip():
                        hydrated.append((word.strip(), entry))
                items = hydrated
            else:
                continue

            for _, payload in items:
                entries += 1
                if isinstance(payload, dict):
                    freq = payload.get("frequency") or payload.get("freq") or 0
                    try:
                        freq_int = int(freq)
                    except (TypeError, ValueError):
                        freq_int = 0
                    total_frequency += freq_int
                    if freq_int > 0:
                        entries_with_frequency += 1
                    before = payload.get("context_before")
                    after = payload.get("context_after")
                    if (isinstance(before, dict) and before) or (isinstance(after, dict) and after):
                        entries_with_context += 1

        if slots_total > 0 and entries == 0:
            entries = slots_total

        computed = {
            "entries": entries,
            "entries_with_frequency": entries_with_frequency,
            "entries_with_context": entries_with_context,
            "total_frequency": total_frequency,
            "slots_total": slots_total,
            "slots_assigned": slots_assigned,
            "slots_available": slots_available,
        }
        self._disk_stats_cache_sig = sig
        self._disk_stats_cache_values = dict(computed)
        return computed

    def _lexical_base_dir(self) -> Path:
        root = self.bridge.lexicon_root
        # Runtime root is usually .../Lexical Data/Canonical. Base is .../Lexical Data.
        if root.name.lower() == "canonical":
            return root.parent
        return root

    @staticmethod
    def _count_entries_lightweight(path: Path) -> int:
        # Fast/low-memory: count actual `"hex":` object keys, not word values like `"hex"`.
        hex_key_re = re.compile(r'"hex"\s*:')
        count = 0
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                for line in handle:
                    count += len(hex_key_re.findall(line))
            if count > 0:
                return count
        except OSError:
            return 0

        # Fallback for non-slot legacy JSON.
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, list):
                return len(data)
            if isinstance(data, dict):
                return len(data)
        except Exception:
            return 0
        return 0

    def _pack_inventory_signature(self) -> tuple:
        base = self._lexical_base_dir()
        targets = [
            ("Canonical", "canonical_[A-Z].json"),
            ("Medical", "med_[A-Z].json"),
            ("Spare_Slots", "pool_[A-Z].json"),
        ]
        parts: List[tuple] = []
        for folder, pattern in targets:
            dir_path = base / folder
            if not dir_path.exists():
                continue
            for file_path in sorted(dir_path.glob(pattern)):
                try:
                    st = file_path.stat()
                except OSError:
                    continue
                parts.append((folder, file_path.name, int(st.st_mtime_ns), int(st.st_size)))
        return tuple(parts)

    def _compute_pack_inventory(self) -> Dict[str, Any]:
        sig = self._pack_inventory_signature()
        if self._pack_inventory_cache_sig == sig and self._pack_inventory_cache_values:
            return dict(self._pack_inventory_cache_values)

        base = self._lexical_base_dir()
        canonical_dir = base / "Canonical"
        medical_dir = base / "Medical"
        pool_dir = base / "Spare_Slots"

        letters = {chr(i): 0 for i in range(ord("A"), ord("Z") + 1)}
        canonical_total = 0
        medical_total = 0
        pool_total = 0

        if canonical_dir.exists():
            for path in sorted(canonical_dir.glob("canonical_[A-Z].json")):
                n = self._count_entries_lightweight(path)
                canonical_total += n
                suffix = path.stem.split("_")[-1].upper()
                if len(suffix) == 1 and suffix in letters:
                    letters[suffix] = n

        if medical_dir.exists():
            for path in sorted(medical_dir.glob("med_[A-Z].json")):
                medical_total += self._count_entries_lightweight(path)

        if pool_dir.exists():
            for path in sorted(pool_dir.glob("pool_[A-Z].json")):
                pool_total += self._count_entries_lightweight(path)

        computed = {
            "canonical": int(canonical_total),
            "medical": int(medical_total),
            "spare_slots": int(pool_total),
            "total_indexed": int(canonical_total + medical_total),
            "letters": letters,
        }
        self._pack_inventory_cache_sig = sig
        self._pack_inventory_cache_values = dict(computed)
        return computed

    async def ensure_bridge_loaded(self, reason: str = "on-demand") -> None:
        if self.bridge.loaded:
            return
        async with self.lock:
            if self.bridge.loaded:
                return
            t0 = time.perf_counter()
            await asyncio.to_thread(self.bridge.load)
            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            LOGGER.info(
                "Lexicon lazy-loaded: entries=%s in %sms [reason=%s]",
                len(self.bridge.entries),
                elapsed_ms,
                reason,
            )

    async def stats_snapshot(self) -> Dict[str, Any]:
        stats = self.bridge.stats()
        if self.bridge.loaded:
            return stats
        disk_stats = await asyncio.to_thread(self._compute_disk_stats)
        stats.update(disk_stats)
        return stats

    async def reload(self, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        async with self.lock:
            config_data = dict(self.config)
            if overrides:
                config_data.update(overrides)
            secure_json_dump(self.config_path, config_data)
            self.config = config_data
            self.bridge = load_bridge_from_config(self.config_path)
            stats = self.bridge.stats()
            stats["version"] = VERSION
            return stats

    async def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        async with self.lock:
            new_config = self.bridge.update_config(updates)
            stats = self.bridge.stats()
            stats["version"] = VERSION
            return {"config": new_config, "stats": stats, "version": VERSION}


def _normalise_path(raw: str) -> Path:
    path = Path(raw).expanduser()
    if not path.is_absolute():
        return (BASE_DIR / path).resolve()
    return path.resolve()


# ── DocuMap Job Ledger ────────────────────────────────────────
_DOCUMAP_LEDGER = STATE_DIR / "documap_jobs.jsonl"


def _read_documap_ledger() -> dict:
    """Read documap job ledger, return last event per fingerprint."""
    events: Dict[str, dict] = {}
    if not _DOCUMAP_LEDGER.exists():
        return events
    try:
        with open(_DOCUMAP_LEDGER, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                evt = json.loads(line)
                fp = evt.get("fingerprint")
                if fp:
                    events[fp] = evt
    except Exception as e:
        LOGGER.warning("Could not read documap ledger: %s", e)
    return events


def _append_documap_event(event: dict) -> None:
    """Append an event to the documap job ledger."""
    _DOCUMAP_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(_DOCUMAP_LEDGER, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _mapped_fingerprints() -> set:
    """Return set of fingerprints with last event == 'completed'."""
    ledger = _read_documap_ledger()
    return {fp for fp, evt in ledger.items() if evt.get("event") == "completed"}


def _parse_patterns(pattern: Optional[str]) -> List[str]:
    if not pattern:
        return ["*"]
    parts = [part.strip() for part in re.split(r"[;,]", pattern) if part.strip()]
    return parts or ["*"]


def _iter_directory(path: Path, recursive: bool, patterns: List[str]) -> Iterable[Path]:
    for pattern in patterns:
        iterator = path.rglob(pattern) if recursive else path.glob(pattern)
        for candidate in iterator:
            if candidate.is_file():
                yield candidate.resolve()


def resolve_job_inputs(paths: List[str], recursive: bool, pattern: Optional[str]) -> Tuple[List[Path], List[str]]:
    patterns = _parse_patterns(pattern)
    resolved: List[Path] = []
    missing: List[str] = []
    seen: Set[Path] = set()

    for raw in paths:
        raw_clean = raw.strip()
        if not raw_clean:
            continue

        if any(ch in raw_clean for ch in "*?["):
            pattern_path = Path(raw_clean).expanduser()
            if not pattern_path.is_absolute():
                pattern_path = BASE_DIR / pattern_path
            matches = [Path(match).resolve() for match in glob.glob(str(pattern_path), recursive=True)]
            files = [candidate for candidate in matches if candidate.is_file()]
            if files:
                for candidate in files:
                    if candidate not in seen:
                        seen.add(candidate)
                        resolved.append(candidate)
            else:
                missing.append(raw_clean)
            continue

        normalised = _normalise_path(raw_clean)

        if normalised.is_dir():
            files = list(_iter_directory(normalised, recursive, patterns))
            if files:
                for candidate in files:
                    if candidate not in seen:
                        seen.add(candidate)
                        resolved.append(candidate)
            else:
                missing.append(raw_clean)
            continue

        if normalised.is_file():
            if normalised not in seen:
                seen.add(normalised)
                resolved.append(normalised)
            continue

        missing.append(raw_clean)

    return resolved, missing


class MapRequest(BaseModel):
    text: str
    source: Optional[str] = "inline"


class MapFilesRequest(BaseModel):
    paths: List[str]
    source: Optional[str] = "batch"
    recursive: Optional[bool] = True
    pattern: Optional[str] = None
    ignore_missing: Optional[bool] = False


class ConfigUpdateRequest(BaseModel):
    min_len: Optional[int] = None
    topK: Optional[int] = None
    window: Optional[int] = None
    alpha_only: Optional[bool] = None
    regex_include: Optional[str] = None
    regex_exclude: Optional[str] = None
    gpu: Optional[str] = None


class CancelRequest(BaseModel):
    job_id: str


class SnapshotRequest(BaseModel):
    tag: Optional[str] = None


class RollbackRequest(BaseModel):
    path: str


class Get616Request(BaseModel):
    word: str
    topk: Optional[int] = None


class AnalyzeUnmappedRequest(BaseModel):
    """Request to analyze unmapped tokens from 616 reports."""
    reports_root: Optional[str] = None
    report_paths: Optional[List[str]] = None


class LexiconAppendRequest(BaseModel):
    word: str
    status: Optional[str] = None


class AssignSymbolRequest(BaseModel):
    word: str
    symbol: Optional[str] = None
    force: Optional[bool] = False


class SetStatusRequest(BaseModel):
    word: str
    status: Optional[str] = None


class LexiconImportRequest(BaseModel):
    words_dir: str


class ChainSlot(BaseModel):
    slot_id: int  # 1-4
    enabled: bool = False
    provider: str = ""  # "openai", "claude", "gemini", "grok"
    model: str = ""


class ChatSendRequest(BaseModel):
    message: str
    mode: str = "llm"  # "llm", "reasoning", "hybrid", "grounded", "wolf_analysis", "openai", "claude", "gemini", "grok"
    model: Optional[str] = None  # Ollama model name for LLM mode
    session_id: Optional[str] = None
    execution_mode: str = "pipeline"  # LEGACY — kept for backward compat, replaced by routing_enabled
    routing_enabled: bool = False  # When True, routing profile controls model + stages + parking
    topk: int = 8
    inference_params: Optional[Dict[str, Any]] = None  # Per-model inference overrides
    tools_enabled: bool = False  # Enables tool calling in LLM mode (hub only)
    # ── Chain builder fields ──
    plugins_enabled: bool = False
    enabled_plugins: List[str] = []
    local_model: Optional[str] = None  # Hub model override (falls back to DEFAULT_MODEL)
    chain_slots: Optional[List[ChainSlot]] = None  # 0-4 API slots, sequential


class ChatSendResponse(BaseModel):
    mode: str
    source: str
    response: str
    answer_frame: Optional[Dict[str, Any]] = None
    reasoning_trace: Optional[Dict[str, Any]] = None
    citations: Optional[List[Dict[str, Any]]] = None
    grounded: bool = False
    verdict: Optional[str] = None
    error: Optional[Dict[str, Any]] = None
    seat: Optional[Dict[str, Any]] = None  # {provider, model, seat_id?, node_id?}
    contributions: Optional[List[Dict[str, Any]]] = None  # Chain: all mind outputs


class LoadRequest(BaseModel):
    lexicon_root: Optional[str] = None
    reports_root: Optional[str] = None
    gpu: Optional[str] = None
    window: Optional[int] = None
    topK: Optional[int] = None
    min_len: Optional[int] = None


class CommitMapRequest(BaseModel):
    job_name: Optional[str] = "616_map"
    report: Optional[Dict[str, Any]] = None
    cite_id: Optional[str] = None


class PluginToggleRequest(BaseModel):
    connected: bool


class GutenbergIngestRequest(BaseModel):
    book_ids: List[int]
    dry_run: bool = False
    force: bool = False


class LocalFileIngestRequest(BaseModel):
    paths: List[str]
    dry_run: bool = False
    force: bool = False
    recursive: bool = False


class WebScrapeIngestRequest(BaseModel):
    urls: List[str]
    dry_run: bool = False
    force: bool = False


class RssIngestRequest(BaseModel):
    feed_url: str
    latest: int = 10
    dry_run: bool = False
    force: bool = False


class WebSocketManager:
    def __init__(self):
        self.active: List[WebSocket] = []
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active.append(websocket)

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active:
                self.active.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        payload = json.dumps(message)
        async with self._lock:
            stale = []
            for ws in self.active:
                try:
                    await ws.send_text(payload)
                except (WebSocketDisconnect, Exception):
                    stale.append(ws)
            for ws in stale:
                if ws in self.active:
                    self.active.remove(ws)


def create_app(state: BridgeState) -> FastAPI:
    app = FastAPI(title="Clearbox AI Studio Bridge", version=VERSION)
    ws_manager = WebSocketManager()
    _mounted_plugins: set[str] = set()  # Track actually-mounted plugin IDs
    _background_tasks: set[asyncio.Task] = set()  # prevent GC of fire-and-forget tasks

    def _task_done(task: asyncio.Task) -> None:
        """Discard from tracking set + log unhandled exceptions."""
        _background_tasks.discard(task)
        if not task.cancelled() and task.exception():
            LOGGER.error("Background task %s failed: %s", task.get_name(), task.exception(), exc_info=task.exception())

    @app.on_event("shutdown")
    async def _on_shutdown():
        await state.close()

    # Build dynamic CORS origins from TLS cert SANs (LAN IPs + Tailscale)
    _cors_origins = ["http://localhost:8080", "http://127.0.0.1:8080",
                     "https://localhost:8080", "https://127.0.0.1:8080"]
    try:
        from security.tls import get_cert_san_ips, get_cert_san_hostnames
        for ip in get_cert_san_ips():
            if ip != "127.0.0.1":
                _cors_origins.append(f"https://{ip}:8080")
        for hostname in get_cert_san_hostnames():
            _cors_origins.append(f"https://{hostname}:8080")
    except Exception:
        pass
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request metrics (in-memory, reset on restart) ──────────────────────
    import time as _time
    from collections import defaultdict as _defaultdict

    _METRICS: dict = {
        "started_at": _time.time(),
        "by_path": _defaultdict(lambda: {"count": 0, "errors": 0, "latency_ms_sum": 0.0}),
    }

    @app.middleware("http")
    async def _metrics_middleware(request: Request, call_next):
        t0 = _time.perf_counter()
        path = request.url.path
        status = 200
        try:
            resp = await call_next(request)
            status = getattr(resp, "status_code", 200)
            return resp
        except Exception:
            status = 500
            raise
        finally:
            dt_ms = (_time.perf_counter() - t0) * 1000.0
            row = _METRICS["by_path"][path]
            row["count"] += 1
            if status >= 400:
                row["errors"] += 1
            row["latency_ms_sum"] += dt_ms

    @app.get("/api/metrics")
    def api_metrics():
        """Return per-endpoint request counts, error counts, and avg latency."""
        out: dict = {"started_at": _METRICS["started_at"], "by_path": {}}
        for path, row in _METRICS["by_path"].items():
            c = row["count"] or 1
            out["by_path"][path] = {
                "count":          row["count"],
                "errors":         row["errors"],
                "avg_latency_ms": round(row["latency_ms_sum"] / c, 2),
            }
        return out

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        """Log validation details so 422s are debuggable from the server log."""
        LOGGER.warning("422 Validation Error on %s %s: %s",
                       request.method, request.url.path, exc.errors())
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    async def _ensure_lexicon_loaded(reason: str) -> None:
        await state.ensure_bridge_loaded(reason)

    @app.get("/api/stats")
    async def get_stats():
        stats = await state.stats_snapshot()
        stats["version"] = VERSION
        return stats

    OLLAMA_BASE = "http://localhost:11434"

    # ── Ollama warm-up (event-driven model pre-load) ──────────
    @app.post("/api/ollama/warmup")
    async def ollama_warmup():
        """Pre-load the active model into VRAM. Fire-and-forget from UI on prompt focus."""
        try:
            _model = state.config.get("model", DEFAULT_MODEL)
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.post(f"{OLLAMA_BASE}/api/generate", json={
                    "model": _model,
                    "prompt": ".",
                    "stream": False,
                    "keep_alive": "5m",
                    "options": {"num_predict": 1},
                })
            return {"status": "ready" if r.is_success else "error"}
        except Exception:
            return {"status": "warming"}

    def _build_seat(provider: str, model: str, seat_id: str | None = None, node_id: str = "server") -> dict:
        """Build seat dict for ChatSendResponse."""
        return {"provider": provider, "model": model, "seat_id": seat_id, "node_id": node_id}

    # ── Chain executor: Local Hub + Multi-API sequential chain ──

    async def _execute_chain(req: ChatSendRequest, msg: str, route, rctx, request) -> ChatSendResponse:
        """Execute a turn-based chain: hub (local) → slot1 → slot2 → slot3 → slot4.

        Hub is the ONLY tool executor. Slots see full context but cannot run tools.
        All contributions are returned — every mind's voice is indelible.
        """
        _tid = _trace_id(request)
        contributions: list[dict] = []
        _hub_model = req.local_model or req.model or DEFAULT_MODEL

        # ── Stage A: Local Hub (Ollama) ──
        hub_messages = _build_chat_messages(msg)

        # Tool injection (hub only)
        _server_tools_allowed = state.config.get("tools_enabled", True)
        _tools_active = req.tools_enabled and _server_tools_allowed
        _tool_trace: list[dict] = []
        if _tools_active:
            from bridges.tool_defs import TOOL_SYSTEM_PROMPT
            hub_messages.insert(0, {"role": "system", "content": TOOL_SYSTEM_PROMPT})

        # ── Plugin pre-hooks ──
        if req.plugins_enabled and req.enabled_plugins:
            from bridges.plugin_hooks import run_pre_hooks
            _pre_ctx = await run_pre_hooks(
                enabled_plugins=req.enabled_plugins,
                mounted_plugins=_mounted_plugins,
                request_ctx={
                    "user_message": msg,
                    "hub_model": _hub_model,
                    "tools_enabled": _tools_active,
                    "hub_messages": hub_messages,
                    "extra": {},
                },
            )
            hub_messages = _pre_ctx.get("hub_messages", hub_messages)

        ollama_payload = {
            "model": _hub_model,
            "messages": hub_messages,
            "stream": False,
        }
        if req.inference_params:
            if "temperature" in req.inference_params:
                ollama_payload["options"] = ollama_payload.get("options", {})
                ollama_payload["options"]["temperature"] = req.inference_params["temperature"]
            if "top_p" in req.inference_params:
                ollama_payload["options"] = ollama_payload.get("options", {})
                ollama_payload["options"]["top_p"] = req.inference_params["top_p"]

        t0_hub = time.time()
        hub_reply = ""
        hub_usage = {}
        try:
            client = await state.get_ollama_client()
            r = await client.post(f"{OLLAMA_BASE}/api/chat", json=ollama_payload)
            hub_ms = int((time.time() - t0_hub) * 1000)
            if r.is_success:
                data = r.json()
                hub_reply = data.get("message", {}).get("content", "")
                hub_usage = {
                    "eval_count": data.get("eval_count", 0),
                    "prompt_eval_count": data.get("prompt_eval_count", 0),
                }

                # Tool pipeline (hub only, same as LLM handler)
                if _tools_active and hub_reply:
                    from bridges.tool_defs import parse_tool_calls, execute_tool, strip_tool_calls
                    _parsed_tools = parse_tool_calls(hub_reply)
                    if _parsed_tools:
                        _parsed_tools = _parsed_tools[:1]
                        _clean = strip_tool_calls(hub_reply)
                        hub_messages.append({"role": "assistant", "content": _clean or "(calling tool)"})
                        for tc in _parsed_tools:
                            t0_tool = time.time()
                            result_str = await execute_tool(
                                tc["name"], tc["arguments"],
                                session_id=req.session_id, model_name=_hub_model,
                            )
                            _tool_ms = int((time.time() - t0_tool) * 1000)
                            _tool_trace.append({
                                "tool": tc["name"], "args": tc["arguments"],
                                "ms": _tool_ms, "result_preview": result_str[:200],
                            })
                            hub_messages.append({
                                "role": "system",
                                "content": f"[TOOL RESULT — {tc['name']}]\n{result_str}\n[END TOOL RESULT]\nNow summarize this result for the user. Do NOT call another tool.",
                            })
                        # Second hub call to summarize tool results
                        ollama_payload["messages"] = hub_messages
                        r2 = await client.post(f"{OLLAMA_BASE}/api/chat", json=ollama_payload)
                        if r2.is_success:
                            _second = r2.json().get("message", {}).get("content", "")
                            hub_reply = _second if _second.strip() else _clean
                        else:
                            hub_reply = _clean

                # Final strip
                if hub_reply and ("tool_call" in hub_reply or "<tool_call>" in hub_reply):
                    from bridges.tool_defs import strip_tool_calls
                    hub_reply = strip_tool_calls(hub_reply)
            else:
                hub_ms = int((time.time() - t0_hub) * 1000)
                hub_reply = f"[Hub error: Ollama returned {r.status_code}]"
        except Exception as e:
            hub_ms = int((time.time() - t0_hub) * 1000)
            hub_reply = f"[Hub error: {e}]"

        # Log hub contribution
        try:
            _log_message(sender="user", content=msg)
        except Exception:
            pass
        try:
            _log_message(sender="ai", content=hub_reply,
                         model_identity={"provider": "ollama", "model": _hub_model, "engine": "chat"})
        except Exception:
            pass

        contributions.append({
            "author": "hub", "provider": "ollama", "model": _hub_model,
            "content": hub_reply, "tools_used": _tool_trace, "ms": hub_ms,
        })

        # ── Plugin post-hooks ──
        if req.plugins_enabled and req.enabled_plugins:
            from bridges.plugin_hooks import run_post_hooks
            _post_ctx = await run_post_hooks(
                enabled_plugins=req.enabled_plugins,
                mounted_plugins=_mounted_plugins,
                response_ctx={
                    "user_message": msg,
                    "hub_model": _hub_model,
                    "hub_reply": hub_reply,
                    "tools_used": _tool_trace,
                    "contributions": contributions,
                    "extra": {},
                },
            )
            contributions = _post_ctx.get("contributions", contributions)

        # ── Stage B: Chain Slots (0-4 API providers) ──
        _tool_results_text = ""
        if _tool_trace:
            _tool_results_text = "\n".join(
                f"[Tool: {t['tool']}] {t['result_preview']}" for t in _tool_trace
            )

        # ── Build identity roster ──
        _active_slots = [s for s in (req.chain_slots or []) if s.enabled and s.provider and s.model]
        _roster_lines = [f"- HUB: {_hub_model} (ollama, local — tool executor)"]
        for s in _active_slots:
            _roster_lines.append(f"- SLOT {s.slot_id}: {s.model} ({s.provider})")

        _roster_block = "## Chain Participants\n" + "\n".join(_roster_lines)
        _identity_instructions = (
            "\n\n## Identity & Interaction Rules\n"
            "You are one mind in a multi-model chain. Each participant sees all prior outputs.\n"
            "- You may address another participant by name: @hub, @slot_1, @slot_2, etc.\n"
            "- You may challenge, agree with, or build on any prior output.\n"
            "- If you have a followup question for a specific participant, write it as:\n"
            "  @slot_N: your question here?\n"
            "  (One followup per response. The addressed model gets one reply turn.)\n"
            "- Be direct. No filler. Contradict if you disagree — this is a think tank."
        )

        prior_outputs: list[str] = []
        _slot_identity_map: dict[str, dict] = {}  # "slot_1" -> {provider, model, api_key}
        for slot in _active_slots:
            if slot.provider not in _CHAIN_CALLERS:
                contributions.append({
                    "author": f"slot_{slot.slot_id}", "provider": slot.provider,
                    "model": slot.model, "content": f"[Unknown provider: {slot.provider}]", "ms": 0,
                })
                continue

            # Local providers (grounded, reasoning) don't need API keys
            _local_providers = {"ollama", "grounded", "reasoning"}
            api_key = "" if slot.provider in _local_providers else _prov_get_key(slot.provider)
            if not api_key and slot.provider not in _local_providers:
                contributions.append({
                    "author": f"slot_{slot.slot_id}", "provider": slot.provider,
                    "model": slot.model,
                    "content": f"[{slot.provider} API key not configured]", "ms": 0,
                })
                continue

            _slot_identity_map[f"slot_{slot.slot_id}"] = {
                "provider": slot.provider, "model": slot.model, "api_key": api_key,
            }

            # Build slot context with identity
            slot_context = f"## You are SLOT {slot.slot_id}: {slot.model} ({slot.provider})\n\n"
            slot_context += _roster_block
            slot_context += f"\n\n## User Message\n{msg}\n\n## HUB Analysis ({_hub_model})\n{hub_reply}"
            if _tool_results_text:
                slot_context += f"\n\n## Tool Results\n{_tool_results_text}"
            for i, prior in enumerate(prior_outputs):
                _prior_slot = _active_slots[i] if i < len(_active_slots) else None
                _prior_label = f"SLOT {_prior_slot.slot_id}: {_prior_slot.model}" if _prior_slot else f"Prior Slot {i+1}"
                slot_context += f"\n\n## {_prior_label} Output\n{prior}"
            slot_context += _identity_instructions

            slot_messages = [{"role": "user", "content": slot_context}]

            caller = _CHAIN_CALLERS[slot.provider]
            try:
                reply, usage, slot_ms = await caller(api_key, slot.model, slot_messages, req.inference_params)
            except Exception as e:
                reply, usage, slot_ms = f"[Error: {e}]", {}, 0

            # ── Phase 4: Tool request bounce-back ──
            # If slot emits structured tool_request JSON, route to hub, resume slot.
            _bounce_trace: list[dict] = []
            if _tools_active and reply:
                _tool_req = _parse_tool_request(reply)
                if _tool_req:
                    from bridges.tool_defs import execute_tool
                    _bounce_results: list[str] = []
                    for tr in _tool_req[:2]:  # Max 2 bounce-back tools per slot
                        t0_bounce = time.time()
                        _br = await execute_tool(
                            tr["name"], tr.get("arguments", {}),
                            session_id=req.session_id, model_name=_hub_model,
                        )
                        _bounce_ms = int((time.time() - t0_bounce) * 1000)
                        _bounce_trace.append({
                            "tool": tr["name"], "args": tr.get("arguments", {}),
                            "requested_by": f"slot_{slot.slot_id}",
                            "ms": _bounce_ms, "result_preview": _br[:200],
                        })
                        _bounce_results.append(f"[Tool: {tr['name']}] {_br}")

                    # Resume slot with tool results
                    _bounce_context = reply + "\n\n## Tool Results (executed by Hub)\n" + "\n".join(_bounce_results)
                    _bounce_context += "\n\nContinue your analysis with these tool results."
                    slot_messages.append({"role": "assistant", "content": reply})
                    slot_messages.append({"role": "user", "content": "## Tool Results (executed by Hub)\n" + "\n".join(_bounce_results) + "\n\nContinue your analysis with these tool results."})
                    try:
                        reply2, usage2, ms2 = await caller(api_key, slot.model, slot_messages, req.inference_params)
                        reply = reply2 if reply2.strip() else reply
                        slot_ms += ms2
                    except Exception:
                        pass  # Keep original reply

            # Log slot contribution
            _provider_map = {"openai": "openai", "claude": "anthropic", "gemini": "google", "grok": "xai"}
            try:
                _log_message(sender="ai", content=reply,
                             model_identity={"provider": _provider_map.get(slot.provider, slot.provider),
                                             "model": slot.model, "engine": "chain_slot"})
            except Exception:
                pass

            contributions.append({
                "author": f"slot_{slot.slot_id}",
                "provider": _provider_map.get(slot.provider, slot.provider),
                "model": slot.model, "content": reply, "ms": slot_ms,
                "bounce_tools": _bounce_trace if _bounce_trace else None,
            })
            prior_outputs.append(reply)

        # ── Followup pass: scan for @mentions, 1 followup per addressee ──
        _followup_pattern = re.compile(r'@(hub|slot_[1-4])\s*:\s*(.+?)(?:\n|$)', re.IGNORECASE)
        _followup_targets: dict[str, tuple[str, str]] = {}  # target -> (question, from_author)
        for contrib in contributions:
            if contrib["author"] == "hub":
                continue  # hub doesn't ask followups
            for m in _followup_pattern.finditer(contrib["content"]):
                target = m.group(1).lower()
                question = m.group(2).strip()
                if target not in _followup_targets and question:
                    _followup_targets[target] = (question, contrib["author"])

        for target, (question, from_author) in _followup_targets.items():
            if target == "hub":
                # Followup to hub — send question to Ollama
                _fup_messages = _build_chat_messages(
                    f"A chain participant ({from_author}) asks you: {question}\n\n"
                    f"Original user message: {msg}\nYour prior analysis: {hub_reply}\n\n"
                    f"Answer concisely."
                )
                try:
                    client = await state.get_ollama_client()
                    t0_fup = time.time()
                    r_fup = await client.post(f"{OLLAMA_BASE}/api/chat", json={
                        "model": _hub_model, "messages": _fup_messages, "stream": False,
                    })
                    fup_ms = int((time.time() - t0_fup) * 1000)
                    fup_reply = r_fup.json().get("message", {}).get("content", "") if r_fup.is_success else "(hub followup failed)"
                except Exception as e:
                    fup_reply, fup_ms = f"[Hub followup error: {e}]", 0
                contributions.append({
                    "author": "hub", "provider": "ollama", "model": _hub_model,
                    "content": fup_reply, "ms": fup_ms,
                    "followup_to": from_author,
                })
            elif target in _slot_identity_map:
                # Followup to a slot — call its provider
                _si = _slot_identity_map[target]
                _fup_context = (
                    f"A chain participant ({from_author}) asks you directly:\n{question}\n\n"
                    f"Original user message: {msg}\n\n"
                    f"Answer concisely. One response only."
                )
                caller = _CHAIN_CALLERS.get(_si["provider"])
                if caller:
                    try:
                        t0_fup = time.time()
                        fup_reply, _, fup_ms = await caller(
                            _si["api_key"], _si["model"],
                            [{"role": "user", "content": _fup_context}],
                            req.inference_params,
                        )
                    except Exception as e:
                        fup_reply, fup_ms = f"[Followup error: {e}]", 0
                    contributions.append({
                        "author": target, "provider": _si["provider"], "model": _si["model"],
                        "content": fup_reply, "ms": fup_ms,
                        "followup_to": from_author,
                    })

        # ── Stage C: Finalize ──
        # Last contribution is the final response (backward compat)
        final_response = contributions[-1]["content"] if contributions else hub_reply
        final_seat = _build_seat(
            contributions[-1].get("provider", "ollama"),
            contributions[-1].get("model", _hub_model),
        )

        total_ms = sum(c.get("ms", 0) for c in contributions)
        route.record(rctx, "chain_executor", "chain", True, ms=total_ms,
                     slots_run=len([c for c in contributions if c["author"] != "hub"]))

        return ChatSendResponse(
            mode="chain", source="chain",
            response=final_response,
            contributions=contributions,
            reasoning_trace={
                "chain": {
                    "contributions": contributions,
                    "hub_model": _hub_model,
                    "slots_run": len(contributions) - 1,
                    "tools": {"enabled": _tools_active, "calls": _tool_trace},
                    "latency_ms_total": total_ms,
                },
                "routing": route.telemetry_block(rctx),
            },
            seat=final_seat,
        )

    @app.post("/api/chat/send", response_model=ChatSendResponse)
    async def chat_send(req: ChatSendRequest, request: Request):
        """
        Unified chat router. All modes route through their owning server.
        LLM mode → local_llm_server (owns logging, history, citations, identity).
        """
        _tid = _trace_id(request)  # DEBUGWIRE:TRACE
        msg = (req.message or "").strip()
        if not msg:
            return ChatSendResponse(
                mode=req.mode, source="bridge_router", response="",
                error={"type": "bad_request", "message": "Empty message"}
            )

        # ── Load routing profile ──────────────────────────────────
        _route_profile = load_routing_profile(state.config.get("routing"))
        route = RouteEngine(_route_profile)
        rctx = route.prepare(req.mode, msg)

        # ── Routing toggle ─────────────────────────────────────────
        # Accept both new routing_enabled and legacy execution_mode
        _routing_on = req.routing_enabled or req.execution_mode == "pipeline"

        if _routing_on:
            # Routing active: profile controls model + stages + parking
            _model_name = req.model or route.config(rctx, "model_call", "model", DEFAULT_MODEL)

            # Engine parking gate
            _original_mode = req.mode
            req.mode = route.redirect_mode(rctx, req.mode)
            if req.mode != _original_mode:
                route.record(rctx, "engine_parking", "engine_parking", True, ms=0,
                             redirect_from=_original_mode, redirect_to=req.mode,
                             reason="mode_parked")
                LOGGER.info("Parked mode %s → redirected to %s", _original_mode, req.mode)
        else:
            # Routing off: use model as-is, no parking, no routing stages
            route.record(rctx, "routing_bypass", "routing_disabled", True, ms=0)
            _model_name = req.model or DEFAULT_MODEL

        # ── Chain mode: if chain_slots present with enabled slots, use chain executor ──
        _chain_active = req.chain_slots and any(s.enabled for s in req.chain_slots)
        if _chain_active:
            # Hub model resolved in _execute_chain as:
            #   req.local_model (chain config) -> req.model (chat dropdown) -> DEFAULT_MODEL
            # Do NOT override with routing config — chat dropdown is authoritative.
            return await _execute_chain(req, msg, route, rctx, request)

        # === LLM Mode: Call Ollama directly, log via log_message() ===
        if req.mode == "llm":
            _persist_warn = False

            # Log user message
            try:
                user_log = _log_message(sender="user", content=msg)
            except Exception as e:
                LOGGER.warning(f"User log failed: {e}")
                user_log = {}
                _persist_warn = True

            retrieval_hits = None  # LLM mode has no retrieval

            ollama_payload = {
                "model": _model_name,
                "messages": _build_chat_messages(msg),
                "stream": False,
                "keep_alive": "5m",
            }

            # Inject per-model inference params if provided
            _INFERENCE_KEYS = {
                "temperature", "top_p", "top_k", "repeat_penalty",
                "frequency_penalty", "presence_penalty", "seed",
                "mirostat_mode", "mirostat_tau", "mirostat_eta",
            }
            # GPU offload: -1 = all layers to GPU (avoid CPU/GPU blend)
            _opts = {"num_gpu": -1}
            if req.inference_params:
                for k, v in req.inference_params.items():
                    if k in _INFERENCE_KEYS:
                        _opts[k] = v
                if "max_tokens" in req.inference_params:
                    _opts["num_predict"] = req.inference_params["max_tokens"]
            ollama_payload["options"] = _opts

            # Server-side tools policy: config can disable tools regardless of client flag
            _server_tools_allowed = state.config.get("tools_enabled", True)
            _tools_active = req.tools_enabled and _server_tools_allowed
            if req.tools_enabled and not _server_tools_allowed:
                LOGGER.info(f"[{_tid}] tools_enabled overridden by server policy")

            # Inject tool system prompt when tools are enabled (prompt-based, no native tools)
            _tool_trace = []
            if _tools_active:
                from bridges.tool_defs import TOOL_SYSTEM_PROMPT
                ollama_payload["messages"].insert(0, {
                    "role": "system",
                    "content": TOOL_SYSTEM_PROMPT,
                })

            # Non-injection receipt: log AI brief status (proves brief is NOT in prompt prefix)
            _pinned_digest = _get_todays_pinned_digest()
            _brief_pinned = _pinned_digest is not None
            debug_enter("http", f"chat/brief_receipt", extra={  # DEBUGWIRE:HTTP
                "ai_brief_pinned": _brief_pinned,
                "ai_brief_source": "thread_note" if _brief_pinned else "none",
                "ai_brief_chars": len(_pinned_digest) if _pinned_digest else 0,
            })

            try:
                # ── Stage: model_call ─────────────────────────────
                t0_model = time.time()
                client = await state.get_ollama_client()
                r = await client.post(f"{OLLAMA_BASE}/api/chat", json=ollama_payload)
                _model_ms = int((time.time() - t0_model) * 1000)

                if not r.is_success:
                    route.record(rctx, "model_call", "model_call", True, ms=_model_ms)
                    return ChatSendResponse(
                        mode=_original_mode,
                        source="ollama",
                        response="",
                        reasoning_trace={"routing": route.telemetry_block(rctx)},
                        error={"type": "ollama_error", "status": r.status_code, "detail": r.text[:500]}
                    )

                route.record(rctx, "model_call", "model_call", True, ms=_model_ms)

                data = r.json()
                resp_message = data.get("message", {})
                reply = resp_message.get("content", "")

                # Handle tool calls when tools are enabled
                # Path A: prompt-based (any format in content — gemma3, etc.)
                # Path B: native tool_calls array (thinking models — gpt-oss)
                _parsed_tools = []
                if _tools_active:
                    from bridges.tool_defs import parse_tool_calls, execute_tool, strip_tool_calls

                    # Path A: parse all known formats from content
                    if reply:
                        _parsed_tools = parse_tool_calls(reply)

                    # Path B: native tool_calls (thinking models emit these)
                    if not _parsed_tools and resp_message.get("tool_calls"):
                        for tc in resp_message["tool_calls"][:3]:
                            fn = tc.get("function", {})
                            fn_name = fn.get("name", "")
                            # Strip "tool." prefix (gpt-oss quirk)
                            if fn_name.startswith("tool."):
                                fn_name = fn_name[5:]
                            fn_args = fn.get("arguments", {})
                            if fn_name:
                                _parsed_tools.append({
                                    "name": fn_name,
                                    "arguments": fn_args if isinstance(fn_args, dict) else {},
                                })

                # Execute at most ONE tool per round
                if _parsed_tools:
                    _parsed_tools = _parsed_tools[:1]

                if _parsed_tools:
                    # Save the prose portion (without tags) as fallback
                    _first_reply_clean = strip_tool_calls(reply) if reply else ""

                    messages = ollama_payload["messages"]
                    # Append the CLEAN assistant text (no raw tags in context)
                    messages.append({"role": "assistant", "content": _first_reply_clean or "(calling tool)"})

                    for tc in _parsed_tools:
                        t0_tool = time.time()
                        result_str = await execute_tool(
                            tc["name"], tc["arguments"],
                            session_id=req.session_id,
                            model_name=_model_name,
                        )
                        _tool_ms = int((time.time() - t0_tool) * 1000)
                        _tool_trace.append({
                            "tool": tc["name"],
                            "args": tc["arguments"],
                            "ms": _tool_ms,
                            "result_preview": result_str[:200],
                        })
                        messages.append({
                            "role": "system",
                            "content": f"[TOOL RESULT — {tc['name']}]\n{result_str}\n[END TOOL RESULT]\nNow summarize this result for the user. Do NOT call another tool.",
                        })

                    # Second LLM call — model summarizes tool results
                    ollama_payload["messages"] = messages
                    client = await state.get_ollama_client()
                    r2 = await client.post(
                            f"{OLLAMA_BASE}/api/chat", json=ollama_payload,
                        )
                    if r2.is_success:
                        data = r2.json()
                        _second_reply = data.get("message", {}).get("content", "")
                        # Use second call if it produced content, else fallback to stripped first
                        reply = _second_reply if _second_reply.strip() else _first_reply_clean
                    else:
                        reply = _first_reply_clean

                # Always strip any tool call artifacts from final reply
                # (covers <tool_call> tags, ```tool_call=```, bare tool_call=, etc.)
                if reply and ("tool_call" in reply or "<tool_call>" in reply):
                    from bridges.tool_defs import strip_tool_calls
                    reply = strip_tool_calls(reply)

                # Extract Ollama performance metadata
                _eval_count = data.get("eval_count", 0)
                _eval_dur_ns = data.get("eval_duration", 0)
                _prompt_count = data.get("prompt_eval_count", 0)
                _load_dur_ns = data.get("load_duration", 0)
                _total_dur_ns = data.get("total_duration", 0)
                _ollama_perf = {
                    "eval_count": _eval_count,
                    "prompt_eval_count": _prompt_count,
                    "eval_duration_ms": _eval_dur_ns // 1_000_000,
                    "load_duration_ms": _load_dur_ns // 1_000_000,
                    "total_duration_ms": _total_dur_ns // 1_000_000,
                    "tokens_per_second": round(
                        _eval_count / max(_eval_dur_ns / 1e9, 0.001), 1
                    ) if _eval_dur_ns else None,
                }

                # Log AI response
                try:
                    ai_log = _log_message(
                        sender="ai",
                        content=reply,
                        model_identity={
                            "provider": "ollama",
                            "model": _model_name,
                            "engine": "generate",
                        },
                    )
                except Exception as e:
                    LOGGER.warning(f"AI log failed: {e}")
                    ai_log = {}
                    _persist_warn = True

                return ChatSendResponse(
                    mode=_original_mode,
                    source="ollama",
                    response=reply,
                    answer_frame=None,
                    reasoning_trace={
                        "user_message_id": user_log.get("message_id"),
                        "ai_message_id": ai_log.get("message_id"),
                        "routing": route.telemetry_block(rctx),
                        "ollama": _ollama_perf,
                        **({"tool_calls": _tool_trace} if _tool_trace else {}),
                        **({"persistence_warning": "Message may not have been saved"} if _persist_warn else {}),
                    },
                    citations=retrieval_hits or None,
                    grounded=bool(retrieval_hits),
                    error=None,
                    seat=_build_seat("ollama", _model_name, "local"),
                )

            except Exception as e:
                return ChatSendResponse(
                    mode=_original_mode,
                    source="ollama",
                    response="",
                    reasoning_trace={"routing": route.telemetry_block(rctx)},
                    error={"type": "connection_error", "message": str(e)}
                )

        # === Grounded Mode: LakeSpeak retrieval + LLM synthesis via tool calling ===
        if req.mode == "grounded":
            try:
                from lakespeak.api.router import get_engine
                engine = get_engine()

                # Step 1: Retrieve evidence from LakeSpeak
                t0_retrieval = time.time()
                ls_result = await asyncio.to_thread(
                    engine.query,
                    query=msg,
                    mode="grounded",
                    topk=req.topk,
                    session_id=req.session_id,
                )
                route.record(rctx, "plugin_chain", "plugin_chain", True,
                             ms=int((time.time() - t0_retrieval) * 1000))

                citations = ls_result.citations or []
                trace = ls_result.trace or {}
                verdict = ls_result.verdict

                # If verdict is trash (no usable evidence), return miss template directly
                if verdict == "trash":
                    trace["routing"] = route.telemetry_block(rctx)
                    return ChatSendResponse(
                        mode="grounded",
                        source="lakespeak",
                        response=ls_result.answer_text,
                        reasoning_trace=trace,
                        citations=citations,
                        grounded=False,
                        verdict=verdict,
                        error=None,
                    )

                # Step 2: Build evidence block for LLM
                # Guard: suppress directive-heavy chunks on short queries
                _DIRECTIVE_STARTS = re.compile(
                    r"^\s*("
                    r"you\s+(must|should|are|will)|always\s|never\s|"
                    r"respond\s+as|format:|style:|rule:|story[_ ]|"
                    r"instructions?:|system\s*prompt|do\s+not\b"
                    r")", re.IGNORECASE
                )
                _short_query = len(msg.split()) < 8

                evidence_lines = []
                for i, c in enumerate(citations[:req.topk]):
                    snippet = c.get("snippet", c.get("text", ""))[:600]
                    # On short queries, skip chunks that look like directives
                    if _short_query and _DIRECTIVE_STARTS.search(snippet):
                        continue
                    score = c.get("score", 0)
                    evidence_lines.append(f"[{len(evidence_lines)+1}] (score: {score:.3f}) {snippet}")
                evidence_block = "\n\n".join(evidence_lines)

                # Step 3: Send to Ollama /api/chat with tool results pre-filled
                system_prompt = (
                    "You are a grounded research assistant. You MUST answer using ONLY "
                    "the evidence provided below. Cite evidence by number [1], [2], etc. "
                    "If the evidence does not contain the answer, say so explicitly. "
                    "Do NOT make up facts beyond what the evidence states."
                )

                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": msg},
                    {"role": "system", "content": f"EVIDENCE FROM ARCHIVE:\n\n{evidence_block}"},
                ]

                # Tool definition for search_archive (model can request additional searches)
                tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": "search_archive",
                            "description": "Search the Clearbox AI Studio knowledge archive for grounded evidence on a topic. Use this when you need more evidence or a different angle on the question.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "query": {
                                        "type": "string",
                                        "description": "Search query for the archive"
                                    }
                                },
                                "required": ["query"]
                            }
                        }
                    }
                ]

                ollama_payload = {
                    "model": _model_name,
                    "messages": messages,
                    "tools": tools,
                    "stream": False,
                    "keep_alive": "5m",
                    "options": {"num_gpu": -1},
                }

                # ── Stage: model_call ─────────────────────────────
                t0_model = time.time()
                client = await state.get_ollama_client()
                r = await client.post(f"{OLLAMA_BASE}/api/chat", json=ollama_payload)

                if not r.is_success:
                    # Fallback: return raw evidence if Ollama fails
                    route.record(rctx, "model_call", "model_call", True,
                                 ms=int((time.time() - t0_model) * 1000))
                    trace["routing"] = route.telemetry_block(rctx)
                    return ChatSendResponse(
                        mode="grounded",
                        source="lakespeak",
                        response=ls_result.answer_text,
                        reasoning_trace=trace,
                        citations=citations,
                        grounded=ls_result.grounded,
                        verdict=verdict,
                        error={"type": "ollama_error", "status": r.status_code, "detail": r.text[:500]},
                    )

                data = r.json()
                resp_message = data.get("message", {})

                # Step 4: Handle tool calls (one round of follow-up search)
                tool_calls = resp_message.get("tool_calls")
                if tool_calls:
                    # Append the assistant's tool-call message ONCE (before the loop)
                    messages.append(resp_message)
                    _tool_results_added = 0

                    # Execute each tool call
                    for tc in tool_calls[:2]:  # Max 2 follow-up searches
                        fn = tc.get("function", {})
                        if fn.get("name") == "search_archive":
                            follow_query = fn.get("arguments", {}).get("query", msg)

                            follow_result = await asyncio.to_thread(
                                engine.query,
                                query=follow_query,
                                mode="grounded",
                                topk=req.topk,
                                session_id=req.session_id,
                            )

                            # Add follow-up citations (dedup by chunk_id)
                            existing_ids = {c.get("chunk_id") for c in citations}
                            for fc in (follow_result.citations or []):
                                if fc.get("chunk_id") not in existing_ids:
                                    citations.append(fc)
                                    existing_ids.add(fc.get("chunk_id"))

                            # Build follow-up evidence
                            follow_lines = []
                            for i, c in enumerate(follow_result.citations or []):
                                snippet = c.get("snippet", c.get("text", ""))[:600]
                                score = c.get("score", 0)
                                follow_lines.append(f"[{len(evidence_lines)+i+1}] (score: {score:.3f}) {snippet}")

                            # Append tool result to messages
                            messages.append({
                                "role": "tool",
                                "content": "\n\n".join(follow_lines) if follow_lines else "No additional results found.",
                            })
                            _tool_results_added += 1

                    # Second LLM call — only if at least one tool result was actually added
                    if _tool_results_added > 0:
                        ollama_payload["messages"] = messages
                        del ollama_payload["tools"]  # No more tool calls in round 2
                        client = await state.get_ollama_client()
                        r2 = await client.post(f"{OLLAMA_BASE}/api/chat", json=ollama_payload)

                        if r2.is_success:
                            data = r2.json()
                            resp_message = data.get("message", {})

                reply = resp_message.get("content", "")

                # Extract Ollama performance metadata (grounded)
                _eval_count = data.get("eval_count", 0)
                _eval_dur_ns = data.get("eval_duration", 0)
                _prompt_count = data.get("prompt_eval_count", 0)
                _load_dur_ns = data.get("load_duration", 0)
                _total_dur_ns = data.get("total_duration", 0)
                trace["ollama"] = {
                    "eval_count": _eval_count,
                    "prompt_eval_count": _prompt_count,
                    "eval_duration_ms": _eval_dur_ns // 1_000_000,
                    "load_duration_ms": _load_dur_ns // 1_000_000,
                    "total_duration_ms": _total_dur_ns // 1_000_000,
                    "tokens_per_second": round(
                        _eval_count / max(_eval_dur_ns / 1e9, 0.001), 1
                    ) if _eval_dur_ns else None,
                }

                route.record(rctx, "model_call", "model_call", True,
                             ms=int((time.time() - t0_model) * 1000))

                # Log grounded exchange to thread
                _grounded_reply = reply or ls_result.answer_text
                _persist_warn = False
                try:
                    _log_message(sender="user", content=msg)
                except Exception as e:
                    LOGGER.warning(f"Grounded user log failed: {e}")
                    _persist_warn = True
                _grounded_ai_log = {}
                try:
                    _grounded_ai_log = _log_message(
                        sender="ai", content=_grounded_reply,
                        model_identity={"provider": "ollama", "model": _model_name, "engine": "grounded"},
                    )
                except Exception as e:
                    LOGGER.warning(f"Grounded AI log failed: {e}")
                    _persist_warn = True

                # Auto-persist citations to sidecar store
                if citations and _grounded_ai_log.get("message_id") is not None:
                    _cite_day = _grounded_ai_log.get("date", "")
                    _cite_msg_id = str(_grounded_ai_log["message_id"])
                    try:
                        from Conversations.threads.citation_store import CitationStore
                        _cs = CitationStore()
                        for _ci, _cite in enumerate(citations):
                            _coord = _cite.get("coord", "")
                            if not _coord:
                                continue
                            try:
                                _cs.attach(
                                    day=_cite_day,
                                    message_id=_cite_msg_id,
                                    block_id=f"b{_ci}",
                                    block_ordinal=_ci,
                                    canonical=_coord,
                                    subject=_cite.get("text", "")[:200] if _cite.get("text") else None,
                                    source="lakespeak",
                                )
                            except ValueError:
                                pass  # Dedup — already attached
                            except Exception as ce:
                                LOGGER.warning(f"Citation auto-persist failed: {ce}")
                    except Exception as ce:
                        LOGGER.warning(f"Citation store init failed: {ce}")

                trace["routing"] = route.telemetry_block(rctx)
                if _persist_warn:
                    trace["persistence_warning"] = "Message may not have been saved"
                return ChatSendResponse(
                    mode="grounded",
                    source="lakespeak",
                    response=_grounded_reply,
                    reasoning_trace=trace,
                    citations=citations,
                    grounded=ls_result.grounded,
                    verdict=verdict,
                    error=None,
                    seat=_build_seat("ollama", _model_name, "local"),
                )

            except ImportError:
                return ChatSendResponse(
                    mode="grounded",
                    source="bridge_router",
                    response="LakeSpeak plugin not installed.",
                    reasoning_trace={"routing": route.telemetry_block(rctx)},
                    error={"type": "not_available", "message": "LakeSpeak plugin not installed"}
                )
            except Exception as e:
                LOGGER.exception("Grounded mode error")
                return ChatSendResponse(
                    mode="grounded",
                    source="lakespeak",
                    response="",
                    reasoning_trace={"routing": route.telemetry_block(rctx)},
                    error={"type": "lakespeak_error", "message": str(e)}
                )

        # === Wolf Analysis Mode: Symbol-first cognitive analysis ===
        if req.mode == "wolf_analysis":
            try:
                from wolf_engine.api.router import get_engine as get_wolf_engine
                wolf = get_wolf_engine()

                t0_wolf = time.time()
                raw = await asyncio.to_thread(
                    wolf.analyze,
                    text=msg,
                    session_id=req.session_id,
                )
                route.record(rctx, "plugin_chain", "plugin_chain", True,
                             ms=int((time.time() - t0_wolf) * 1000))

                # Adapt Wolf Engine output to Clearbox AI Studio contract
                verdict = raw.get("verdict", {})
                _wolf_reply = (
                    f"Verdict: {verdict.get('status', 'unknown')} "
                    f"(confidence: {verdict.get('adjusted_confidence', 0):.3f})"
                )

                # Log wolf_analysis exchange to thread
                _persist_warn = False
                try:
                    _log_message(sender="user", content=msg)
                except Exception as e:
                    LOGGER.warning(f"Wolf user log failed: {e}")
                    _persist_warn = True
                try:
                    _log_message(
                        sender="ai", content=_wolf_reply,
                        model_identity={"provider": "wolf_engine", "model": "wolf", "engine": "analysis"},
                    )
                except Exception as e:
                    LOGGER.warning(f"Wolf AI log failed: {e}")
                    _persist_warn = True

                return ChatSendResponse(
                    mode="wolf_analysis",
                    source="wolf_engine",
                    response=_wolf_reply,
                    answer_frame=verdict,
                    reasoning_trace={
                        "engine": raw.get("engine"),
                        "patterns": raw.get("patterns"),
                        "session_id": raw.get("session_id"),
                        "routing": route.telemetry_block(rctx),
                        **({"persistence_warning": "Message may not have been saved"} if _persist_warn else {}),
                    },
                    citations=None,
                    grounded=False,
                    verdict=verdict.get("status"),
                    error=None,
                    seat=_build_seat("wolf_engine", "wolf"),
                )

            except ImportError:
                return ChatSendResponse(
                    mode="wolf_analysis",
                    source="bridge_router",
                    response="Wolf Engine plugin not installed.",
                    reasoning_trace={"routing": route.telemetry_block(rctx)},
                    error={"type": "not_available", "message": "Wolf Engine plugin not installed"}
                )
            except Exception as e:
                LOGGER.exception("Wolf analysis mode error")
                return ChatSendResponse(
                    mode="wolf_analysis",
                    source="wolf_engine",
                    response="",
                    reasoning_trace={"routing": route.telemetry_block(rctx)},
                    error={"type": "wolf_engine_error", "message": str(e)}
                )

        # === Hybrid Mode: Placeholder ===
        if req.mode == "hybrid":
            return ChatSendResponse(
                mode="hybrid",
                source="bridge_router",
                response="Hybrid mode not implemented yet.",
                reasoning_trace={"routing": route.telemetry_block(rctx)},
                error={"type": "not_implemented", "message": "Use LLM or Reasoning mode"}
            )

        # === OpenAI Mode: Cloud chat via OpenAI Responses API ===
        if req.mode == "openai":
            api_key = _prov_get_key("openai")
            if not api_key:
                return ChatSendResponse(
                    mode="openai", source="bridge_router", response="",
                    error={"type": "not_configured",
                           "message": "OpenAI API key not configured. Add it in Connections."}
                )

            # Accept real OpenAI model names; reject local model names; "default" → server picks
            _openai_model = "gpt-4o"
            if req.model and req.model not in ("", "default"):
                if req.model.startswith(("gpt-", "o1", "o3", "o4")):
                    _openai_model = req.model

            openai_payload = {
                "model": _openai_model,
                "input": _build_chat_messages(msg),
            }
            if req.inference_params:
                if "temperature" in req.inference_params:
                    openai_payload["temperature"] = req.inference_params["temperature"]
                if "top_p" in req.inference_params:
                    openai_payload["top_p"] = req.inference_params["top_p"]
                if "max_tokens" in req.inference_params:
                    openai_payload["max_output_tokens"] = req.inference_params["max_tokens"]

            try:
                t0 = time.time()
                async with httpx.AsyncClient(timeout=120.0) as client:
                    r = await client.post(
                        "https://api.openai.com/v1/responses",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json=openai_payload,
                    )
                _ms = int((time.time() - t0) * 1000)

                if not r.is_success:
                    return ChatSendResponse(
                        mode="openai", source="openai_api", response="",
                        error={"type": "openai_error",
                               "message": f"OpenAI ({_openai_model}) rejected request: {r.status_code} {r.text[:300]}"}
                    )

                data = r.json()

                # Parse reply: output[] → message → content[] → output_text → .text
                reply = ""
                for item in data.get("output", []):
                    if item.get("type") == "message":
                        for block in item.get("content", []):
                            if block.get("type") == "output_text":
                                reply += block.get("text", "")

                if not reply:
                    LOGGER.warning("OpenAI: 0 text in output. Keys: %s", list(data.keys()))

                # Strip tool-call artifacts — tools are local-only
                if reply and ("tool_call" in reply or "<tool_call>" in reply):
                    from bridges.tool_defs import strip_tool_calls
                    reply = strip_tool_calls(reply)

                usage = data.get("usage")

                _persist_warn = False
                try:
                    user_log = _log_message(sender="user", content=msg)
                except Exception:
                    user_log = {}
                    _persist_warn = True
                try:
                    ai_log = _log_message(
                        sender="ai", content=reply,
                        model_identity={"provider": "openai", "model": _openai_model, "engine": "responses"},
                    )
                except Exception:
                    ai_log = {}
                    _persist_warn = True

                return ChatSendResponse(
                    mode="openai", source="openai_api", response=reply,
                    reasoning_trace={
                        "user_message_id": user_log.get("message_id"),
                        "ai_message_id": ai_log.get("message_id"),
                        "model": _openai_model,
                        "usage": usage,
                        "latency_ms": _ms,
                        **({"persistence_warning": "Message may not have been saved"} if _persist_warn else {}),
                    },
                    seat=_build_seat("openai", _openai_model),
                )
            except Exception as e:
                return ChatSendResponse(
                    mode="openai", source="openai_api", response="",
                    error={"type": "connection_error", "message": f"OpenAI ({_openai_model}): {e}"}
                )

        # === Claude Mode: Cloud chat via Anthropic Messages API ===
        if req.mode == "claude":
            api_key = _prov_get_key("claude")
            if not api_key:
                return ChatSendResponse(
                    mode="claude", source="bridge_router", response="",
                    error={"type": "not_configured",
                           "message": "Claude API key not configured. Add it in Connections."}
                )

            _claude_model = req.model if (req.model and req.model not in ("", "default") and req.model.startswith("claude")) else "claude-sonnet-4-20250514"

            claude_payload = {
                "model": _claude_model,
                "max_tokens": 4096,
                "messages": _merge_consecutive_roles(_build_chat_messages(msg)),
            }
            if req.inference_params:
                if "temperature" in req.inference_params:
                    claude_payload["temperature"] = req.inference_params["temperature"]
                if "top_p" in req.inference_params:
                    claude_payload["top_p"] = req.inference_params["top_p"]
                if "top_k" in req.inference_params:
                    claude_payload["top_k"] = req.inference_params["top_k"]
                if "max_tokens" in req.inference_params:
                    claude_payload["max_tokens"] = req.inference_params["max_tokens"]

            try:
                t0 = time.time()
                async with httpx.AsyncClient(timeout=120.0) as client:
                    r = await client.post(
                        "https://api.anthropic.com/v1/messages",
                        headers={
                            "x-api-key": api_key,
                            "anthropic-version": "2023-06-01",
                            "Content-Type": "application/json",
                        },
                        json=claude_payload,
                    )
                _ms = int((time.time() - t0) * 1000)

                if not r.is_success:
                    return ChatSendResponse(
                        mode="claude", source="anthropic_api", response="",
                        error={"type": "claude_error",
                               "message": f"Claude ({_claude_model}) rejected request: {r.status_code} {r.text[:300]}"}
                    )

                data = r.json()
                content_blocks = data.get("content", [])
                reply = "".join(
                    block.get("text", "") for block in content_blocks if block.get("type") == "text"
                )

                # Strip tool-call artifacts — tools are local-only
                if reply and ("tool_call" in reply or "<tool_call>" in reply):
                    from bridges.tool_defs import strip_tool_calls
                    reply = strip_tool_calls(reply)

                usage = data.get("usage")

                _persist_warn = False
                try:
                    user_log = _log_message(sender="user", content=msg)
                except Exception:
                    user_log = {}
                    _persist_warn = True
                try:
                    ai_log = _log_message(
                        sender="ai", content=reply,
                        model_identity={"provider": "anthropic", "model": _claude_model, "engine": "messages"},
                    )
                except Exception:
                    ai_log = {}
                    _persist_warn = True

                return ChatSendResponse(
                    mode="claude", source="anthropic_api", response=reply,
                    reasoning_trace={
                        "user_message_id": user_log.get("message_id"),
                        "ai_message_id": ai_log.get("message_id"),
                        "model": _claude_model,
                        "usage": usage,
                        "latency_ms": _ms,
                        **({"persistence_warning": "Message may not have been saved"} if _persist_warn else {}),
                    },
                    seat=_build_seat("anthropic", _claude_model),
                )
            except Exception as e:
                return ChatSendResponse(
                    mode="claude", source="anthropic_api", response="",
                    error={"type": "connection_error", "message": f"Claude ({_claude_model}): {e}"}
                )

        # === Gemini Mode: Cloud chat via Google Gemini API ===
        if req.mode == "gemini":
            api_key = _prov_get_key("gemini")
            if not api_key:
                return ChatSendResponse(
                    mode="gemini", source="bridge_router", response="",
                    error={"type": "not_configured",
                           "message": "Gemini API key not configured. Add it in Connections."}
                )

            _gemini_default = route.config(rctx, "model_call", "gemini_model", "gemini-2.5-flash")
            _gemini_model = req.model if (req.model and req.model not in ("", "default")) else _gemini_default

            # Build Gemini contents — role mapping table
            _GEMINI_ROLE = {"user": "user", "assistant": "model", "system": "user"}
            _raw_msgs = _build_chat_messages(msg)
            _system_parts = [m["content"] for m in _raw_msgs if m["role"] == "system"]
            _chat_msgs = [m for m in _raw_msgs if m["role"] != "system"]

            gemini_payload = {
                "contents": [
                    {"role": _GEMINI_ROLE.get(m["role"], "user"),
                     "parts": [{"text": m["content"]}]}
                    for m in _chat_msgs
                ],
            }
            if _system_parts:
                gemini_payload["systemInstruction"] = {
                    "parts": [{"text": "\n".join(_system_parts)}]
                }

            _gen_config = {}
            if req.inference_params:
                if "temperature" in req.inference_params:
                    _gen_config["temperature"] = req.inference_params["temperature"]
                if "top_p" in req.inference_params:
                    _gen_config["topP"] = req.inference_params["top_p"]
                if "top_k" in req.inference_params:
                    _gen_config["topK"] = req.inference_params["top_k"]
                if "max_tokens" in req.inference_params:
                    _gen_config["maxOutputTokens"] = req.inference_params["max_tokens"]
            if _gen_config:
                gemini_payload["generationConfig"] = _gen_config

            try:
                t0 = time.time()
                async with httpx.AsyncClient(timeout=120.0) as client:
                    r = await client.post(
                        f"https://generativelanguage.googleapis.com/v1beta/models/{_gemini_model}:generateContent",
                        headers={
                            "x-goog-api-key": api_key,
                            "Content-Type": "application/json",
                        },
                        json=gemini_payload,
                    )
                _ms = int((time.time() - t0) * 1000)

                if not r.is_success:
                    return ChatSendResponse(
                        mode="gemini", source="gemini_api", response="",
                        error={"type": "gemini_error",
                               "message": f"Gemini ({_gemini_model}) rejected request: {r.status_code} {r.text[:300]}"}
                    )

                data = r.json()
                # Parse: candidates[0].content.parts[].text
                reply = ""
                for candidate in data.get("candidates", []):
                    for part in candidate.get("content", {}).get("parts", []):
                        reply += part.get("text", "")

                # Strip tool-call artifacts — tools are local-only
                if reply and ("tool_call" in reply or "<tool_call>" in reply):
                    from bridges.tool_defs import strip_tool_calls
                    reply = strip_tool_calls(reply)

                usage = data.get("usageMetadata")

                _persist_warn = False
                try:
                    user_log = _log_message(sender="user", content=msg)
                except Exception:
                    user_log = {}
                    _persist_warn = True
                try:
                    ai_log = _log_message(
                        sender="ai", content=reply,
                        model_identity={"provider": "google", "model": _gemini_model, "engine": "generateContent"},
                    )
                except Exception:
                    ai_log = {}
                    _persist_warn = True

                return ChatSendResponse(
                    mode="gemini", source="gemini_api", response=reply,
                    reasoning_trace={
                        "user_message_id": user_log.get("message_id"),
                        "ai_message_id": ai_log.get("message_id"),
                        "model": _gemini_model,
                        "usage": usage,
                        "latency_ms": _ms,
                        "routing": route.telemetry_block(rctx),
                        **({"persistence_warning": "Message may not have been saved"} if _persist_warn else {}),
                    },
                    seat=_build_seat("google", _gemini_model),
                )
            except Exception as e:
                return ChatSendResponse(
                    mode="gemini", source="gemini_api", response="",
                    error={"type": "connection_error", "message": f"Gemini ({_gemini_model}): {e}"}
                )

        # === Grok Mode: Cloud chat via xAI Chat Completions API ===
        if req.mode == "grok":
            api_key = _prov_get_key("grok")
            if not api_key:
                return ChatSendResponse(
                    mode="grok", source="bridge_router", response="",
                    error={"type": "not_configured",
                           "message": "xAI API key not configured. Add it in Connections."}
                )

            _grok_model = "grok-3-fast"
            if req.model and req.model not in ("", "default"):
                if req.model.startswith("grok"):
                    _grok_model = req.model

            grok_payload = {
                "model": _grok_model,
                "messages": _build_chat_messages(msg),
                "stream": False,
            }
            if req.inference_params:
                if "temperature" in req.inference_params:
                    grok_payload["temperature"] = req.inference_params["temperature"]
                if "top_p" in req.inference_params:
                    grok_payload["top_p"] = req.inference_params["top_p"]
                if "max_tokens" in req.inference_params:
                    grok_payload["max_tokens"] = req.inference_params["max_tokens"]

            try:
                t0 = time.time()
                async with httpx.AsyncClient(timeout=120.0) as client:
                    r = await client.post(
                        "https://api.x.ai/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json=grok_payload,
                    )
                _ms = int((time.time() - t0) * 1000)

                if not r.is_success:
                    return ChatSendResponse(
                        mode="grok", source="xai_api", response="",
                        error={"type": "xai_error",
                               "message": f"Grok ({_grok_model}) rejected request: {r.status_code} {r.text[:300]}"}
                    )

                data = r.json()
                # Standard Chat Completions: choices[0].message.content
                reply = ""
                choices = data.get("choices", [])
                if choices:
                    reply = choices[0].get("message", {}).get("content", "")

                # Strip tool-call artifacts — tools are local-only
                if reply and ("tool_call" in reply or "<tool_call>" in reply):
                    from bridges.tool_defs import strip_tool_calls
                    reply = strip_tool_calls(reply)

                usage = data.get("usage")

                _persist_warn = False
                try:
                    user_log = _log_message(sender="user", content=msg)
                except Exception:
                    user_log = {}
                    _persist_warn = True
                try:
                    ai_log = _log_message(
                        sender="ai", content=reply,
                        model_identity={"provider": "xai", "model": _grok_model, "engine": "chat_completions"},
                    )
                except Exception:
                    ai_log = {}
                    _persist_warn = True

                return ChatSendResponse(
                    mode="grok", source="xai_api", response=reply,
                    reasoning_trace={
                        "user_message_id": user_log.get("message_id"),
                        "ai_message_id": ai_log.get("message_id"),
                        "model": _grok_model,
                        "usage": usage,
                        "latency_ms": _ms,
                        "routing": route.telemetry_block(rctx),
                        **({"persistence_warning": "Message may not have been saved"} if _persist_warn else {}),
                    },
                    seat=_build_seat("xai", _grok_model),
                )
            except Exception as e:
                return ChatSendResponse(
                    mode="grok", source="xai_api", response="",
                    error={"type": "connection_error", "message": f"Grok ({_grok_model}): {e}"}
                )

        # === Chat Pack Mode: Stepwise lesson instruction ===
        if req.mode == "chat_pack":
            try:
                from chat_packs.api.router import get_engine as _get_cp_engine
                _cp_engine = _get_cp_engine()

                _cp_session_id = req.session_id or ""
                if not _cp_session_id:
                    _trace = {"routing": route.telemetry_block(rctx)}
                    return ChatSendResponse(
                        mode="chat_pack", source="chat_packs", response="",
                        reasoning_trace=_trace,
                        error={"type": "no_session", "message": "No pack session active. Start a pack first."},
                    )

                _cp_session = _cp_engine.get_session(_cp_session_id)
                if not _cp_session:
                    _trace = {"routing": route.telemetry_block(rctx)}
                    return ChatSendResponse(
                        mode="chat_pack", source="chat_packs", response="",
                        reasoning_trace=_trace,
                        error={"type": "no_session", "message": f"Session {_cp_session_id} not found."},
                    )

                _cp_messages = _cp_engine.build_messages(_cp_session_id, msg)
                if not _cp_messages:
                    _trace = {"routing": route.telemetry_block(rctx)}
                    return ChatSendResponse(
                        mode="chat_pack", source="chat_packs", response="",
                        reasoning_trace=_trace,
                        error={"type": "build_error", "message": "Failed to build messages for pack session."},
                    )

                _cp_payload = {
                    "model": _model_name,
                    "messages": _cp_messages,
                    "stream": False,
                    "keep_alive": "5m",
                }

                _CP_INFERENCE_KEYS = {
                    "temperature", "top_p", "top_k", "repeat_penalty",
                    "frequency_penalty", "presence_penalty", "seed",
                    "mirostat_mode", "mirostat_tau", "mirostat_eta",
                }
                # GPU offload: -1 = all layers to GPU
                _cp_opts = {"num_gpu": -1}
                if req.inference_params:
                    for k, v in req.inference_params.items():
                        if k in _CP_INFERENCE_KEYS:
                            _cp_opts[k] = v
                    if "max_tokens" in req.inference_params:
                        _cp_opts["num_predict"] = req.inference_params["max_tokens"]
                _cp_payload["options"] = _cp_opts

                # Log user message scoped to session
                _persist_warn = False
                try:
                    _cp_user_log = _log_message(sender="user", content=msg, conversation_id=_cp_session_id)
                except Exception as e:
                    LOGGER.warning(f"Chat Pack user log failed: {e}")
                    _cp_user_log = {}
                    _persist_warn = True

                # Call Ollama /api/chat
                _cp_t0 = time.time()
                client = await state.get_ollama_client()
                _cp_r = await client.post(f"{OLLAMA_BASE}/api/chat", json=_cp_payload)
                _cp_model_ms = int((time.time() - _cp_t0) * 1000)
                route.record(rctx, "model_call", "model_call", True, ms=_cp_model_ms)

                if not _cp_r.is_success:
                    _trace = {"routing": route.telemetry_block(rctx)}
                    return ChatSendResponse(
                        mode="chat_pack", source="chat_packs", response="",
                        reasoning_trace=_trace,
                        error={"type": "ollama_error", "status": _cp_r.status_code, "detail": _cp_r.text[:500]},
                    )

                _cp_data = _cp_r.json()
                _cp_reply = _cp_data.get("message", {}).get("content", "")

                # Ollama perf metadata
                _cp_eval_count = _cp_data.get("eval_count", 0)
                _cp_eval_dur_ns = _cp_data.get("eval_duration", 0)
                _cp_ollama_perf = {
                    "eval_count": _cp_eval_count,
                    "prompt_eval_count": _cp_data.get("prompt_eval_count", 0),
                    "eval_duration_ms": _cp_eval_dur_ns // 1_000_000,
                    "load_duration_ms": _cp_data.get("load_duration", 0) // 1_000_000,
                    "total_duration_ms": _cp_data.get("total_duration", 0) // 1_000_000,
                    "tokens_per_second": round(
                        _cp_eval_count / max(_cp_eval_dur_ns / 1e9, 0.001), 1
                    ) if _cp_eval_dur_ns else None,
                }

                # Log AI response
                try:
                    _cp_ai_log = _log_message(
                        sender="ai", content=_cp_reply,
                        model_identity={"provider": "ollama", "model": _model_name, "engine": "chat_pack"},
                        conversation_id=_cp_session_id,
                    )
                except Exception as e:
                    LOGGER.warning(f"Chat Pack AI log failed: {e}")
                    _cp_ai_log = {}
                    _persist_warn = True

                _cp_pack_id = _cp_session.get("pack_id", "")
                return ChatSendResponse(
                    mode="chat_pack",
                    source="chat_packs",
                    response=_cp_reply,
                    reasoning_trace={
                        "user_message_id": _cp_user_log.get("message_id"),
                        "ai_message_id": _cp_ai_log.get("message_id"),
                        "routing": route.telemetry_block(rctx),
                        "ollama": _cp_ollama_perf,
                        **({"persistence_warning": "Message may not have been saved"} if _persist_warn else {}),
                        "pack_session": {
                            "session_id": _cp_session_id,
                            "pack_id": _cp_pack_id,
                            "phase": _cp_session.get("phase"),
                            "section_index": _cp_session.get("section_index"),
                            "total_sections": _cp_session.get("total_sections"),
                            "question_index": _cp_session.get("question_index"),
                            "total_questions": _cp_session.get("total_questions"),
                        },
                    },
                    seat=_build_seat("ollama", _model_name, "local"),
                )
            except ImportError:
                return ChatSendResponse(
                    mode="chat_pack", source="bridge_router",
                    response="Chat Packs plugin not installed.",
                    reasoning_trace={"routing": route.telemetry_block(rctx)},
                    error={"type": "not_available", "message": "Chat Packs plugin not installed"},
                )
            except Exception as e:
                LOGGER.exception("Chat Pack mode error")
                return ChatSendResponse(
                    mode="chat_pack", source="chat_packs", response="",
                    reasoning_trace={"routing": route.telemetry_block(rctx)},
                    error={"type": "chat_pack_error", "message": str(e)},
                )

        # === Reasoning Mode: 6-1-6 Map Query (in-process) ===
        if req.mode == "reasoning":
            if not route.enabled(rctx, "reasoning_engine"):
                route.record(rctx, "reasoning_engine", "reasoning_engine", False, ms=0,
                             reason="stage_disabled")
                return ChatSendResponse(
                    mode="reasoning",
                    source="bridge_router",
                    response="Reasoning engine is currently parked.",
                    reasoning_trace={"routing": route.telemetry_block(rctx)},
                    error={"type": "parked", "message": "Reasoning engine disabled in routing profile"}
                )

            t0_reasoning = time.time()
            try:
                engine = _get_reasoning_engine()
                subject = _extract_subject(msg)
                answer = await asyncio.to_thread(engine.query_what_does_x_do, subject, req.topk)
                ms_reasoning = int((time.time() - t0_reasoning) * 1000)
                route.record(rctx, "plugin_chain", "plugin_chain", True, ms=ms_reasoning)

                surface = answer.surface_text
                _r_trace = answer.reasoning_trace or {}

            except HTTPException as he:
                ms_reasoning = int((time.time() - t0_reasoning) * 1000)
                if he.status_code == 404:
                    # Anchor not found — check lexicon for fallback offer
                    await _ensure_lexicon_loaded("reasoning-404-check")
                    term_lower = msg.lower().strip()
                    lexicon_present = term_lower in state.bridge.word_index
                    if lexicon_present:
                        msg_out = f"No map hits for '{msg}', although it does appear in the lexicon. Would you like to query the LLM?"
                    else:
                        msg_out = "No map data for that term yet."
                    return ChatSendResponse(
                        mode="reasoning", source="reasoning_engine",
                        response=msg_out, answer_frame=None,
                        reasoning_trace={
                            "note": "anchor_not_found",
                            "lexicon_present": lexicon_present,
                            "suggested_next_mode": "llm" if lexicon_present else None,
                            "routing": route.telemetry_block(rctx),
                        }, error=None,
                    )
                return ChatSendResponse(
                    mode="reasoning", source="reasoning_engine",
                    response=f"Reasoning engine error: {he.detail}",
                    reasoning_trace={"routing": route.telemetry_block(rctx)},
                    error={"type": "engine_error", "message": str(he.detail)},
                )
            except Exception as e:
                LOGGER.exception("Reasoning engine query failed")
                return ChatSendResponse(
                    mode="reasoning", source="reasoning_engine",
                    response=f"Reasoning engine error: {e}",
                    reasoning_trace={"routing": route.telemetry_block(rctx)},
                    error={"type": "engine_error", "message": str(e)},
                )

            # Log reasoning exchange to thread
            _persist_warn = False
            try:
                _log_message(sender="user", content=msg)
            except Exception as e:
                LOGGER.warning(f"Reasoning user log failed: {e}")
                _persist_warn = True
            try:
                _log_message(
                    sender="ai", content=surface,
                    model_identity={"provider": "reasoning_engine", "model": "616", "engine": "reasoning"},
                )
            except Exception as e:
                LOGGER.warning(f"Reasoning AI log failed: {e}")
                _persist_warn = True

            _r_trace["routing"] = route.telemetry_block(rctx)
            if _persist_warn:
                _r_trace["persistence_warning"] = "Message may not have been saved"
            return ChatSendResponse(
                mode="reasoning",
                source="reasoning_engine",
                response=surface,
                answer_frame=answer.__dict__,
                reasoning_trace=_r_trace,
                error=None,
                seat=_build_seat("reasoning_engine", "616"),
            )

        # === Unknown Mode: reject cleanly ===
        LOGGER.warning("Unknown chat mode: %s", req.mode)
        return ChatSendResponse(
            mode=req.mode,
            source="bridge_router",
            response="",
            reasoning_trace={"routing": route.telemetry_block(rctx)},
            error={"type": "unknown_mode", "message": f"Unknown mode: {req.mode}"}
        )

    @app.post("/api/load")
    async def post_load(body: LoadRequest):
        overrides = cast(Dict[str, Any], body.dict(exclude_none=True))
        stats = await state.reload(overrides or None)
        await ws_manager.broadcast({
            "evt": "reload",
            "version": VERSION,
            "device": stats.get("device_name"),
            "entries": stats.get("entries"),
        })
        return stats

    @app.post("/api/map")
    async def post_map(body: MapRequest, request: Request):
        _t0 = time.perf_counter()  # DEBUGWIRE:HTTP
        _tid = _trace_id(request)  # DEBUGWIRE:TRACE
        debug_enter("documap", "/api/map", trace_id=_tid, extra={"source": body.source or "inline", "text_len": len(body.text or "")})  # DEBUGWIRE:HTTP
        if not body.text:
            debug_exit("documap", "/api/map", ok=False, detail="empty_text", ms=(time.perf_counter() - _t0) * 1000, trace_id=_tid)  # DEBUGWIRE:HTTP
            raise HTTPException(status_code=400, detail="text is required")
        try:
            await _ensure_lexicon_loaded("map")
            result = state.bridge.map_text(body.text, source=body.source or "inline")
        except Exception as _e:
            _rt_error("documap", "/api/map", str(_e), level=3, trace_id=_tid)  # DEBUGWIRE:HTTP
            debug_exit("documap", "/api/map", ok=False, detail=str(_e), ms=(time.perf_counter() - _t0) * 1000, trace_id=_tid)  # DEBUGWIRE:HTTP
            raise
        result["version"] = VERSION
        # ── Temp staging: always save last map for retrieval ──
        staging_dir = state.bridge.reports_root / "_staging"
        staging_dir.mkdir(parents=True, exist_ok=True)
        staging_path = staging_dir / "last_map.json"
        import json as _json
        with open(staging_path, "w", encoding="utf-8") as f:
            _json.dump(result, f, ensure_ascii=False, indent=2)
        LOGGER.info("Staged map result to %s", staging_path)
        debug_exit("documap", "/api/map", ok=True, ms=(time.perf_counter() - _t0) * 1000, trace_id=_tid, extra={"anchors": result.get("unique_anchors")})  # DEBUGWIRE:HTTP
        return result

    @app.post("/api/map/commit")
    async def post_map_commit(body: CommitMapRequest):
        """Commit a staged map result or provided report to the canonical data lake."""
        report = body.report
        if report is None:
            staging_path = state.bridge.reports_root / "_staging" / "last_map.json"
            if not staging_path.exists():
                raise HTTPException(status_code=404, detail="No staged map found. Run a mapping job first.")
            import json as _json
            with open(staging_path, "r", encoding="utf-8") as f:
                report = _json.load(f)
        elif not isinstance(report, dict):
            raise HTTPException(status_code=400, detail="report must be an object when provided")

        report.setdefault("version", VERSION)
        output_path = state.bridge.write_report(body.job_name or "616_map", report)
        LOGGER.info("Committed map to data lake: %s", output_path)

        # ── Grove ingestion: fetch source text from citation and ingest ──
        grove_receipt = None
        grove_error = None
        _cite_id = body.cite_id or report.get("cite_id") or report.get("source")
        if _cite_id:
            try:
                # Fetch original text from LLM proxy citation store
                _llm_tls = state.config.get("server", {}).get("tls", False)
                _llm_base = f"{'https' if _llm_tls else 'http'}://127.0.0.1:11435"
                async with httpx.AsyncClient(verify=False, timeout=30.0) as _c:
                    _cr = await _c.get(f"{_llm_base}/api/library/citations/{_cite_id}/content")
                    if _cr.status_code == 200:
                        _cite_data = _cr.json()
                        _text = _cite_data.get("content") or _cite_data.get("text") or ""
                        if _text:
                            import concurrent.futures
                            def _do_ingest():
                                sys.path.insert(0, str(BASE_DIR))
                                sys.path.insert(0, str(BASE_DIR / "plugins"))
                                from lakespeak.ingest.pipeline import ingest_text
                                return ingest_text(
                                    text=_text,
                                    source_type="documap",
                                    source_path=_cite_id,
                                    bridge=state.bridge,
                                    skip_mapped_guard=True,
                                )
                            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as _pool:
                                grove_receipt = await asyncio.get_event_loop().run_in_executor(_pool, _do_ingest)
                            LOGGER.info("Grove ingested from citation %s: %s", _cite_id, grove_receipt.get("receipt_id", "?"))
                        else:
                            grove_error = "Citation content empty"
                    else:
                        grove_error = f"Citation fetch failed: HTTP {_cr.status_code}"
            except Exception as e:
                LOGGER.warning("Grove ingestion failed for %s: %s", _cite_id, e)
                grove_error = str(e)

        result = {
            "status": "committed",
            "path": str(output_path),
            "version": VERSION,
        }
        if grove_receipt:
            result["grove_receipt"] = grove_receipt.get("receipt_id")
            result["grove_chunks"] = grove_receipt.get("chunk_count", 0)
        if grove_error:
            result["grove_error"] = grove_error
        return result

    async def _map_files_job(job_id: str, paths: List[str], source: str):
        resolved = [Path(p) for p in paths]
        job = state.jobs.get(job_id)
        if not job:
            return
        loop = asyncio.get_running_loop()

        state.jobs.start(job_id, total=len(resolved), processed=0, source=source)
        await ws_manager.broadcast({
            "evt": "job-start",
            "job_id": job_id,
            "job": job.job_type,
            "count": len(resolved),
            "source": source,
            "version": VERSION,
        })

        def cancel_cb() -> bool:
            current = state.jobs.get(job_id)
            return bool(current and current.cancel_requested)

        def progress_cb(idx: int, total: int, current_path: Path, result: Dict[str, Any]):
            state.jobs.update_progress(job_id, processed=idx, total=total, current=str(current_path))
            payload = {
                "evt": "job-progress",
                "job_id": job_id,
                "job": job.job_type,
                "processed": idx,
                "total": total,
                "current": str(current_path),
                "version": VERSION,
            }
            asyncio.run_coroutine_threadsafe(ws_manager.broadcast(payload), loop)

        try:
            result = await asyncio.to_thread(
                state.bridge.map_files,
                resolved,
                progress_cb=progress_cb,
                cancel_cb=cancel_cb,
            )
            if cancel_cb():
                state.jobs.finish_cancel(job_id)
                await ws_manager.broadcast({
                    "evt": "job-cancelled",
                    "job_id": job_id,
                    "job": job.job_type,
                    "version": VERSION,
                })
                return

            output_path = state.bridge.write_report("616_map", result)
            state.jobs.complete(job_id, str(output_path))
            await ws_manager.broadcast({
                "evt": "job-complete",
                "job_id": job_id,
                "job": job.job_type,
                "result_path": str(output_path),
                "device": state.bridge.device_info.name,
                "version": VERSION,
            })
        except Exception as exc:  # pragma: no cover - surfaced to clients
            LOGGER.exception("map_files job failed")
            state.jobs.fail(job_id, str(exc))
            await ws_manager.broadcast({
                "evt": "job-error",
                "job_id": job_id,
                "job": job.job_type,
                "error": str(exc),
                "version": VERSION,
            })

    @app.post("/api/map_files")
    async def post_map_files(body: MapFilesRequest):
        if not body.paths:
            raise HTTPException(status_code=400, detail="paths is required")
        await _ensure_lexicon_loaded("map_files")
        recursive = bool(body.recursive) if body.recursive is not None else True
        try:
            resolved, missing = resolve_job_inputs(body.paths, recursive, body.pattern)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if missing and not body.ignore_missing:
            raise HTTPException(status_code=404, detail={"missing": missing})

        if not resolved:
            raise HTTPException(status_code=400, detail="No files matched provided paths")

        resolved_paths = [str(path) for path in resolved]
        job_payload = {
            "paths": resolved_paths,
            "source": body.source or "batch",
            "recursive": recursive,
            "pattern": body.pattern,
            "missing": missing,
        }
        job = state.jobs.create_job("map_files", job_payload)
        task = asyncio.create_task(_map_files_job(job.job_id, resolved_paths, body.source or "batch"))
        _background_tasks.add(task)
        task.add_done_callback(_task_done)
        response = {
            "status": "queued",
            "job_id": job.job_id,
            "files": len(resolved_paths),
            "missing": missing,
            "version": VERSION,
        }
        return response

    @app.get("/api/lookup")
    async def get_lookup(word: str):
        if not word:
            raise HTTPException(status_code=400, detail="word parameter is required")
        await _ensure_lexicon_loaded("lookup")
        result = state.bridge.lookup(word)
        result["version"] = VERSION
        return result

    @app.get("/api/config")
    async def get_config():
        return {"config": state.bridge.get_config(), "version": VERSION}

    @app.patch("/api/config")
    async def patch_config(body: ConfigUpdateRequest):
        payload = cast(Dict[str, Any], body.dict(exclude_none=True))
        if not payload:
            raise HTTPException(status_code=400, detail="No config fields provided")
        result = await state.update_config(payload)
        await ws_manager.broadcast({
            "evt": "config-update",
            "config": result["config"],
            "version": VERSION,
        })
        return result

    @app.post("/api/cancel")
    async def post_cancel(body: CancelRequest):
        record = state.jobs.cancel(body.job_id)
        if not record:
            raise HTTPException(status_code=404, detail="Job not found")
        await ws_manager.broadcast({
            "evt": "job-cancel",
            "job_id": record.job_id,
            "job": record.job_type,
            "version": VERSION,
        })
        return {"status": record.status, "job_id": record.job_id, "version": VERSION}

    @app.get("/api/jobs")
    async def list_jobs():
        jobs = state.jobs.list_jobs()
        return {
            "jobs": [
                {
                    "job_id": job.job_id,
                    "job": job.job_type,
                    "status": job.status,
                    "created_at": job.created_at,
                    "updated_at": job.updated_at,
                    "progress": job.progress,
                    "result_path": job.result_path,
                    "error": job.error,
                }
                for job in jobs
            ],
            "version": VERSION,
        }

    @app.post("/api/snapshot")
    async def post_snapshot(body: SnapshotRequest):
        await _ensure_lexicon_loaded("snapshot")
        path = state.bridge.create_snapshot(body.tag)
        await ws_manager.broadcast({
            "evt": "snapshot",
            "path": str(path),
            "version": VERSION,
        })
        return {"path": str(path), "version": VERSION}

    @app.post("/api/rollback")
    async def post_rollback(body: RollbackRequest):
        await _ensure_lexicon_loaded("rollback")
        snapshot_path = Path(body.path)
        stats = state.bridge.rollback(snapshot_path)
        stats["version"] = VERSION
        await ws_manager.broadcast({
            "evt": "rollback",
            "path": str(snapshot_path),
            "stats": stats,
            "version": VERSION,
        })
        return stats

    @app.get("/api/snapshots")
    async def list_snapshots():
        """List available lexicon snapshots, newest first."""
        snapshots = []
        # Check both governed (state/snapshots) and legacy (reports/snapshots) paths
        search_dirs = [state.bridge._snapshot_folder()]
        try:
            from security.storage_layout import STATE_DIR
            governed_snap = STATE_DIR / "snapshots"
            if governed_snap != search_dirs[0]:
                search_dirs.append(governed_snap)
        except ImportError:
            pass
        seen = set()
        for snap_dir in search_dirs:
            if not snap_dir.exists():
                continue
            for d in snap_dir.iterdir():
                if d.is_dir() and (d / "lexicon.json").exists() and d.name not in seen:
                    seen.add(d.name)
                    snapshots.append({
                        "name": d.name,
                        "path": str(d),
                        "created": d.stat().st_mtime,
                    })
        snapshots.sort(key=lambda s: s["created"], reverse=True)
        return {"snapshots": snapshots[:20]}

    @app.get("/api/search_lexicon")
    async def get_search_lexicon(query: str = ""):
        """Search bound lexicon entries by prefix/substring match."""
        if not query or len(query) < 2:
            return []
        await _ensure_lexicon_loaded("search_lexicon")
        q = query.lower()
        results = []
        for norm, hex_addr in state.bridge.word_index.items():
            if q in norm:
                entry = state.bridge.entries.get(hex_addr)
                if not entry:
                    continue
                results.append({
                    "word": entry.word or norm,
                    "symbol": entry.symbol,
                    "status": entry.status,
                    "frequency": int(state.bridge.frequency.get(norm, 0)),
                    "frequencies": {norm: int(state.bridge.frequency.get(norm, 0))},
                    "in_lexicon": True,
                })
            if len(results) >= 50:
                break
        # Sort by frequency descending
        results.sort(key=lambda r: r["frequency"], reverse=True)
        return results[:20]

    @app.get("/api/lexicon/distribution")
    async def get_lexicon_distribution(pack: str = "all"):
        """Get lexicon statistics and letter distribution."""
        inventory = await asyncio.to_thread(state._compute_pack_inventory)
        return {
            "total": inventory["total_indexed"],
            "canonical": inventory["canonical"],
            "domain_packs": {
                "medical": inventory["medical"],
            },
            "spare_slots": inventory["spare_slots"],
            # Kept for compatibility with older UI versions.
            "with_context": 0,
            "with_frequency": 0,
            "letters": inventory["letters"],
        }

    @app.get("/api/lexicon/browse")
    async def get_lexicon_browse(letter: str = "A", limit: int = 50, pack: str = "all"):
        """Browse lexicon entries by first letter."""
        await _ensure_lexicon_loaded("lexicon_browse")

        if not letter or len(letter) != 1:
            raise HTTPException(status_code=400, detail="Letter must be a single character")

        letter_upper = letter.upper()
        results = []

        for norm, hex_addr in state.bridge.word_index.items():
            entry = state.bridge.entries.get(hex_addr)
            if not entry or entry.status != "ASSIGNED":
                continue

            # Filter by first letter
            if entry.word and len(entry.word) > 0 and entry.word[0].upper() == letter_upper:
                results.append({
                    "word": entry.word or norm,
                    "symbol": entry.symbol,
                    "status": entry.status,
                    "frequency": int(state.bridge.frequency.get(norm, 0)),
                    "frequencies": {norm: int(state.bridge.frequency.get(norm, 0))},
                    "in_lexicon": True,
                })

            if len(results) >= limit:
                break

        # Sort by word alphabetically
        results.sort(key=lambda r: r["word"].lower())

        return {
            "entries": results[:limit],
            "total": len(results)
        }

    @app.get("/api/lexicon/sample")
    async def get_lexicon_sample(count: int = 24, pack: str = "all"):
        """Get random sample of lexicon entries."""
        await _ensure_lexicon_loaded("lexicon_sample")

        # Collect all assigned entries
        all_entries = []
        for norm, hex_addr in state.bridge.word_index.items():
            entry = state.bridge.entries.get(hex_addr)
            if not entry or entry.status != "ASSIGNED":
                continue

            all_entries.append({
                "word": entry.word or norm,
                "symbol": entry.symbol,
                "status": entry.status,
                "frequency": int(state.bridge.frequency.get(norm, 0)),
                "frequencies": {norm: int(state.bridge.frequency.get(norm, 0))},
                "in_lexicon": True,
            })

        # Random sample
        sample_size = min(count, len(all_entries))
        sample = random.sample(all_entries, sample_size) if all_entries else []

        return {
            "entries": sample,
            "total": len(all_entries)
        }

    @app.get("/api/lexicon/top")
    async def get_lexicon_top(count: int = 30, pack: str = "all"):
        """Get top entries by frequency."""
        await _ensure_lexicon_loaded("lexicon_top")

        # Collect all assigned entries with frequency
        all_entries = []
        for norm, hex_addr in state.bridge.word_index.items():
            entry = state.bridge.entries.get(hex_addr)
            if not entry or entry.status != "ASSIGNED":
                continue

            freq = int(state.bridge.frequency.get(norm, 0))
            all_entries.append({
                "word": entry.word or norm,
                "symbol": entry.symbol,
                "status": entry.status,
                "frequency": freq,
                "frequencies": {norm: freq},
                "in_lexicon": True,
            })

        # Sort by frequency descending
        all_entries.sort(key=lambda r: r["frequency"], reverse=True)

        return {
            "entries": all_entries[:count],
            "total": len(all_entries)
        }

    @app.get("/api/lexicon/recent")
    async def get_lexicon_recent(count: int = 30, pack: str = "all"):
        """Get recently added entries."""
        await _ensure_lexicon_loaded("lexicon_recent")

        # Collect all assigned entries
        # Note: Current schema doesn't track timestamps, so return by reverse alpha for now
        # Future: Add 'added_at' timestamp to track recent additions
        all_entries = []
        for norm, hex_addr in state.bridge.word_index.items():
            entry = state.bridge.entries.get(hex_addr)
            if not entry or entry.status != "ASSIGNED":
                continue

            all_entries.append({
                "word": entry.word or norm,
                "symbol": entry.symbol,
                "status": entry.status,
                "frequency": int(state.bridge.frequency.get(norm, 0)),
                "frequencies": {norm: int(state.bridge.frequency.get(norm, 0))},
                "in_lexicon": True,
            })

        # Sort by word (reverse alpha as placeholder for "recent")
        # Future: Sort by added_at timestamp
        all_entries.sort(key=lambda r: r["word"].lower(), reverse=True)

        return {
            "entries": all_entries[:count],
            "total": len(all_entries)
        }

    @app.get("/api/lexicon/entry")
    async def get_lexicon_entry(word: str = ""):
        """Get detailed information for a specific word."""
        await _ensure_lexicon_loaded("lexicon_entry")

        if not word:
            raise HTTPException(status_code=400, detail="word parameter required")

        norm = word.lower().strip()
        hex_addr = state.bridge.word_index.get(norm)

        if not hex_addr:
            return {
                "found": False,
                "word": word,
                "message": "Word not found in lexicon"
            }

        entry = state.bridge.entries.get(hex_addr)
        if not entry:
            return {
                "found": False,
                "word": word,
                "message": "Entry data not available"
            }

        return {
            "found": True,
            "word": entry.word or norm,
            "symbol": entry.symbol,
            "status": entry.status,
            "frequency": int(state.bridge.frequency.get(norm, 0)),
            "frequencies": {norm: int(state.bridge.frequency.get(norm, 0))},
            "in_lexicon": True,
            "payload": entry.payload  # Full entry data
        }

    @app.get("/api/system")
    async def get_system_info():
        """Get system information."""
        import platform
        stats = await state.stats_snapshot()

        # Get basic system info
        system_info = {
            "version": VERSION,
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "lexicon_loaded": bool(stats.get("loaded")),
            "lexicon_entries": int(stats.get("entries", 0)),
            "device_type": stats.get("device_used", state.bridge.device_info.type),
            "device_name": stats.get("device_name", state.bridge.device_info.name),
        }

        # Add memory info if available
        try:
            import psutil
            mem = psutil.virtual_memory()
            system_info["memory_percent"] = mem.percent
            system_info["memory_available_gb"] = round(mem.available / (1024**3), 2)
        except ImportError:
            pass

        return system_info

    @app.get("/api/boot")
    async def boot_payload():
        """Consolidated init payload — one request instead of 8+.

        Returns stats, system info, and plugin health so the UI can
        boot with a single round-trip to the bridge.
        """
        import platform

        # Stats (same as /api/stats)
        stats = await state.stats_snapshot()
        stats["version"] = VERSION

        # System info (same as /api/system)
        system = {
            "version": VERSION,
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "lexicon_loaded": bool(stats.get("loaded")),
            "lexicon_entries": int(stats.get("entries", 0)),
            "device_type": stats.get("device_used", state.bridge.device_info.type),
            "device_name": stats.get("device_name", state.bridge.device_info.name),
        }
        try:
            import psutil
            mem = psutil.virtual_memory()
            system["memory_percent"] = mem.percent
            system["memory_available_gb"] = round(mem.available / (1024**3), 2)
            system["os_boot_time"] = psutil.boot_time()   # epoch seconds — OS lifetime uptime
        except ImportError:
            pass
        system["bridge_started_at"] = _METRICS.get("started_at", _time.time())

        # Plugin health — check _mounted_plugins (already in-process, no HTTP)
        health = {
            "bridge": True,
            "lakespeak": "lakespeak" in _mounted_plugins,
            "wolf": "wolf_engine" in _mounted_plugins,
            "nodes": "forest_node" in _mounted_plugins,
        }

        # Reasoning engine — in-process check
        health["reasoning"] = _reasoning_engine is not None

        # Origin identity — so the UI always reveals which workspace is running
        _ws = Path(__file__).resolve().parent.parent
        origin = {"workspace": str(_ws)}
        try:
            import subprocess as _sp
            _hash = _sp.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=str(_ws), stderr=_sp.DEVNULL, timeout=2,
            ).decode().strip()
            origin["commit"] = _hash
        except Exception:
            origin["commit"] = "unknown"

        return {"stats": stats, "system": system, "health": health, "origin": origin}

    @app.get("/api/services/health")
    async def services_health():
        """Probe all Clearbox AI Studio services and return combined health."""
        _tls = state.config.get("server", {}).get("tls", False)
        _proto = "https" if _tls else "http"

        async def _probe(url: str) -> bool:
            try:
                async with httpx.AsyncClient(timeout=2.0, verify=False) as client:
                    r = await client.get(url)
                    return r.status_code < 500
            except Exception:
                return False

        llm_ok, ui_ok = await asyncio.gather(
            _probe("http://127.0.0.1:11434/api/tags"),       # Ollama: always HTTP
            _probe(f"{_proto}://127.0.0.1:8080/"),            # UI: follows TLS config
        )
        return {
            "bridge": True,
            "llm": llm_ok,
            "reasoning": _reasoning_engine is not None,       # In-process
            "ui": ui_ok,
        }

    @app.get("/api/nodes")
    async def list_nodes():
        """Return node registry from config + async health-check each remote node.

        Nodes are defined in forest.config.json under the "nodes" key.
        Each entry: {id, name, host, port, ui_port}
        """
        nodes_cfg = state.config.get("nodes", [])
        if not nodes_cfg:
            return {"nodes": []}

        async def _ping_node(node: dict) -> dict:
            result = dict(node)
            host = node.get("host", "localhost")
            port = node.get("port", 5050)
            is_self = host in ("localhost", "127.0.0.1") and port == 5050
            if is_self:
                result["online"] = True
                result["self"]   = True
                result["bridge_started_at"] = _METRICS.get("started_at")
                return result
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    r = await client.get(f"http://{host}:{port}/api/stats")
                    if r.status_code == 200:
                        data = r.json()
                        result["online"]  = True
                        result["entries"] = data.get("entries", 0)
                        result["version"] = data.get("version", "?")
                    else:
                        result["online"] = False
            except Exception:
                result["online"] = False
            return result

        results = await asyncio.gather(*[_ping_node(n) for n in nodes_cfg])
        return {"nodes": list(results)}

    # ── System Control Endpoints ──────────────────────────────────

    def _kill_all_forest_processes():
        """Kill ALL Clearbox AI Studio processes on our ports, then close terminal windows.

        Uses Get-NetTCPConnection (LISTEN state only) → Stop-Process -Force.
        Never uses Get-CimInstance (can hang / go interactive).
        Always -NonInteractive + timeout.
        """
        import os
        import subprocess as _sp
        import textwrap

        def _ps(cmd: str, timeout_s: int = 12):
            cmd = textwrap.dedent(cmd).strip()
            try:
                p = _sp.run(
                    ["powershell", "-NoProfile", "-NonInteractive",
                     "-ExecutionPolicy", "Bypass", "-Command", cmd],
                    capture_output=True, text=True, timeout=timeout_s,
                )
                return p.returncode, (p.stdout or "") + (p.stderr or "")
            except _sp.TimeoutExpired:
                return 1, "PowerShell timed out"
            except Exception as e:
                return 1, str(e)

        my_pid = os.getpid()
        killed = []

        # Phase 1: Kill processes LISTENING on Clearbox AI Studio ports
        _, out = _ps(f"""
            $ports = @(5050, 11435, 8080)
            $pids = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
                Where-Object {{ $ports -contains $_.LocalPort }} |
                Select-Object -ExpandProperty OwningProcess -Unique
            foreach ($pid in $pids) {{
                if ($pid -eq {my_pid}) {{ continue }}
                try {{
                    Stop-Process -Id $pid -Force -ErrorAction Stop
                    Write-Output "$pid"
                }} catch {{}}
            }}
        """)
        for line in out.strip().splitlines():
            line = line.strip()
            if line.isdigit():
                killed.append({"name": "port_listener", "pid": int(line)})
                LOGGER.info("Killed pid %s (port listener)", line)

        # Phase 2: Close orphaned PowerShell terminal windows by title
        _ps("""
            Get-Process powershell -ErrorAction SilentlyContinue |
                Where-Object {
                    $_.MainWindowTitle -like '*Bridge Server*' -or
                    $_.MainWindowTitle -like '*LLM Server*' -or
                    $_.MainWindowTitle -like '*UI Server*'
                } | Stop-Process -Force -ErrorAction SilentlyContinue
        """)

        # Phase 3: Clean temp launcher scripts
        _ps(f"Remove-Item '{BASE_DIR}\\temp_*.ps1' -Force -ErrorAction SilentlyContinue")

        return killed

    # Sentinel file path — must match scripts/forest_start.py
    import tempfile
    _STOP_SENTINEL = Path(tempfile.gettempdir()) / "forest_stop"

    @app.post("/api/system/shutdown")
    async def system_shutdown():
        """Shut down all Clearbox AI Studio services.

        Drops a sentinel file so the loop-based terminal scripts exit
        after the Python processes die → windows close automatically.
        """
        import os

        LOGGER.warning("System shutdown requested via UI")

        # Drop sentinel BEFORE killing — loops check it on process exit
        try:
            _STOP_SENTINEL.write_text("stop", encoding="utf-8")
            LOGGER.info("Shutdown sentinel created: %s", _STOP_SENTINEL)
        except Exception as e:
            LOGGER.warning("Failed to create sentinel: %s", e)

        killed = _kill_all_forest_processes()

        async def _self_terminate():
            await asyncio.sleep(0.5)
            LOGGER.warning("Bridge server shutting down")
            os._exit(0)

        task = asyncio.get_running_loop().create_task(_self_terminate())
        _background_tasks.add(task)
        task.add_done_callback(_task_done)

        return {"status": "shutting_down", "killed": killed}

    @app.post("/api/system/restart")
    async def system_restart():
        """Restart all Clearbox AI Studio services.

        Just kills the Python listeners. The loop-based terminal scripts
        detect the exit and relaunch the services in the SAME windows.
        No new windows, no forest_start.py needed.
        """
        import os

        LOGGER.warning("System restart requested via UI")

        # Make sure sentinel does NOT exist so loops keep running
        if _STOP_SENTINEL.exists():
            _STOP_SENTINEL.unlink()

        # Kill other services — their loops will restart them
        _kill_all_forest_processes()

        # Kill ourselves — our loop will restart us too
        async def _self_terminate():
            await asyncio.sleep(0.5)
            LOGGER.warning("Bridge server restarting via loop")
            os._exit(0)

        task = asyncio.get_running_loop().create_task(_self_terminate())
        _background_tasks.add(task)
        task.add_done_callback(_task_done)

        return {"status": "restarting"}

    @app.post("/api/system/lock")
    async def system_lock():
        """Lock the Windows workstation (best-effort)."""
        import subprocess as _sp

        LOGGER.info("System lock requested via UI")
        try:
            _sp.Popen(
                ["rundll32.exe", "user32.dll,LockWorkStation"],
                creationflags=_sp.CREATE_NO_WINDOW,
            )
            return {"status": "locked"}
        except Exception as e:
            LOGGER.warning("Failed to lock workstation: %s", e)
            return {"status": "lock_failed", "error": str(e)}

    # ── Artifact Viewer API ─────────────────────────────────────

    @app.get("/api/artifacts")
    async def list_artifacts():
        """List all files in the ARTIFACTS zone with metadata."""
        from security.gateway import gateway, WriteZone, _zone_root, sanitize_artifact_path

        names = gateway.list_zone(WriteZone.ARTIFACTS)
        root = _zone_root(WriteZone.ARTIFACTS)
        items = []
        for name in sorted(names):
            if not sanitize_artifact_path(name):
                continue  # Skip entries with invalid paths
            path = root / name
            try:
                st = path.stat()
                items.append({
                    "name": name,
                    "size_bytes": st.st_size,
                    "created_at": datetime.fromtimestamp(st.st_mtime).isoformat(),
                })
            except Exception:
                items.append({"name": name, "size_bytes": 0, "created_at": None})
        return {"artifacts": items, "count": len(items)}

    @app.post("/api/artifacts/upload")
    async def upload_artifact(file: UploadFile = File(...)):
        """Upload a file to artifacts/user/. Human caller, audited, any file type."""
        from security.gateway import gateway, WriteZone, sanitize_artifact_path

        MAX_UPLOAD = 10 * 1024 * 1024  # 10 MB
        content_bytes = await file.read()
        if len(content_bytes) > MAX_UPLOAD:
            raise HTTPException(413, f"File exceeds {MAX_UPLOAD // (1024 * 1024)}MB limit")

        # Server decides the path — human uploads go to user/
        raw_name = file.filename or "unnamed"
        safe_name = re.sub(r'[^\w._-]', '_', raw_name)[:128] or "unnamed"
        rel_path = sanitize_artifact_path(f"user/{safe_name}")
        if not rel_path:
            raise HTTPException(400, "Invalid filename")

        result = gateway.write_bytes("human", WriteZone.ARTIFACTS, rel_path, content_bytes)
        if not result.success:
            raise HTTPException(500, result.error or "Upload failed")

        LOGGER.info("Artifact uploaded: %s (%d bytes, audit=%s)", rel_path, len(content_bytes), result.audit_id)
        return {
            "ok": True,
            "path": rel_path,
            "size_bytes": len(content_bytes),
            "sha256": hashlib.sha256(content_bytes).hexdigest(),
            "audit_id": result.audit_id,
        }

    @app.get("/api/artifacts/{filename:path}/download")
    async def download_artifact(filename: str):
        """Download an artifact as a file attachment (supports subdirectories)."""
        from security.gateway import WriteZone, _zone_root, sanitize_artifact_path
        from fastapi.responses import FileResponse

        safe = sanitize_artifact_path(filename)
        if not safe:
            raise HTTPException(status_code=400, detail="Invalid path")

        path = _zone_root(WriteZone.ARTIFACTS) / safe
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Artifact not found: {safe}")

        return FileResponse(path, filename=path.name)

    @app.get("/api/artifacts/{filename:path}")
    async def read_artifact(filename: str):
        """Read an artifact, returning its content (supports subdirectories)."""
        from security.gateway import WriteZone, _zone_root, sanitize_artifact_path

        safe = sanitize_artifact_path(filename)
        if not safe:
            raise HTTPException(status_code=400, detail="Invalid path")

        path = _zone_root(WriteZone.ARTIFACTS) / safe
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Artifact not found: {safe}")

        # Try text first, fall back to binary (base64-encoded for JSON response)
        try:
            content = path.read_text(encoding="utf-8")
            return {"name": safe, "content": content, "size_bytes": len(content)}
        except UnicodeDecodeError:
            import base64
            content_b64 = base64.b64encode(path.read_bytes()).decode("ascii")
            return {"name": safe, "content": content_b64, "size_bytes": path.stat().st_size, "binary": True}

    @app.delete("/api/artifacts/{filename:path}")
    async def delete_artifact(filename: str):
        """Delete an artifact (human caller only, audited, supports subdirectories)."""
        from security.gateway import gateway, WriteZone, sanitize_artifact_path

        safe = sanitize_artifact_path(filename)
        if not safe:
            raise HTTPException(status_code=400, detail="Invalid path")

        result = gateway.delete("human", WriteZone.ARTIFACTS, safe)
        if result.success:
            LOGGER.info("Artifact deleted: %s (audit_id=%s)", safe, result.audit_id)
            return {"ok": True, "audit_id": result.audit_id}
        raise HTTPException(status_code=404, detail=result.error or "Delete failed")

    # ── Tool Workshop CRUD ─────────────────────────────────────

    @app.get("/api/tools")
    async def list_tools():
        """List all registered tools (built-in + custom)."""
        from bridges.tool_defs import tool_directory
        return {"tools": tool_directory()}

    @app.get("/api/tools/{name}")
    async def get_tool(name: str):
        """Get a single tool definition. Returns full JSON for custom tools."""
        from bridges.tool_defs import tool_directory, get_custom_tool_json, _BUILTIN_NAMES
        # Check if tool exists in registry
        for t in tool_directory():
            if t["name"] == name:
                result = dict(t)
                # For custom tools, include the runner config
                if name not in _BUILTIN_NAMES:
                    raw = get_custom_tool_json(name)
                    if raw:
                        result["runner"] = raw.get("runner", {})
                        result["params"] = raw.get("params", {})
                return result
        raise HTTPException(status_code=404, detail=f"Tool not found: {name}")

    @app.post("/api/tools")
    async def create_or_update_tool(request: Request):
        """Create or update a custom tool definition."""
        from bridges.tool_defs import save_custom_tool
        data = await request.json()
        err = save_custom_tool(data)
        if err:
            raise HTTPException(status_code=400, detail=err)
        LOGGER.info("Tool saved: %s", data.get("name"))
        return {"ok": True, "name": data["name"]}

    @app.delete("/api/tools/{name}")
    async def delete_tool(name: str):
        """Delete a custom tool (built-ins cannot be deleted)."""
        from bridges.tool_defs import delete_custom_tool
        err = delete_custom_tool(name)
        if err:
            raise HTTPException(status_code=400, detail=err)
        LOGGER.info("Tool deleted: %s", name)
        return {"ok": True}

    @app.post("/api/tools/{name}/test")
    async def test_tool(name: str, request: Request):
        """Execute a tool with given args (dry run for testing)."""
        from bridges.tool_defs import execute_tool
        body = await request.json()
        args = body.get("arguments", {})
        result = await execute_tool(name, args, session_id="tool_workshop_test")
        return {"name": name, "result": result}

    @app.post("/api/tools/reload")
    async def reload_tools():
        """Hot-reload: re-scan custom tools dir, rebuild registry."""
        from bridges.tool_defs import reload_custom_tools
        count = reload_custom_tools()
        return {"ok": True, "custom_tools_loaded": count}

    # ── DEBUGWIRE Runtime Toggle ─────────────────────────────────

    @app.get("/api/debugwire/status")
    async def debugwire_get_status():
        """Return current DEBUGWIRE tracing state."""
        from security.runtime_log import debugwire_status
        return debugwire_status()

    @app.post("/api/debugwire/toggle")
    async def debugwire_toggle(request: Request):
        """Toggle DEBUGWIRE tracing on/off.

        Body: {"enabled": bool, "components": ["auth","toolcall",...] | null}
        If enabled=true and components is null → trace ALL.
        If enabled=true and components list → trace only those.
        If enabled=false → stop all tracing.
        """
        from security.runtime_log import debugwire_set, debugwire_status
        body = await request.json()
        enabled = bool(body.get("enabled", False))
        components = body.get("components")  # list[str] | None
        debugwire_set(enabled, components)
        # Forward to LLM server so both processes stay in sync
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    "http://127.0.0.1:11435/api/debugwire/toggle",
                    json={"enabled": enabled, "components": components},
                    timeout=3.0,
                )
        except Exception:
            pass  # LLM server may be down — bridge toggle still applies
        return debugwire_status()

    @app.post("/api/616")
    async def post_get_616(body: Get616Request):
        if not body.word:
            raise HTTPException(status_code=400, detail="word is required")
        await _ensure_lexicon_loaded("616")
        payload = state.bridge.get_616(body.word, body.topk)
        payload["version"] = VERSION
        return payload

    @app.post("/api/analyze_unmapped")
    async def post_analyze_unmapped(body: AnalyzeUnmappedRequest):
        """Analyze unmapped tokens from 616 reports and return statistics."""

        import sys
        sys.path.insert(0, str(BASE_DIR / "tools" / "lexicon"))
        try:
            from analyze_unmapped_tokens import analyze_reports, generate_review_report, discover_reports
        except ImportError as exc:
            raise HTTPException(status_code=500, detail=f"Failed to load analysis tool: {exc}")
        
        # Determine which reports to analyze
        report_paths: List[Path] = []
        if body.report_paths:
            report_paths = [Path(p) for p in body.report_paths if Path(p).exists()]
        else:
            # Search governed storage (AppData) first, fall back to workspace
            try:
                from security.storage_layout import DATA_MAPPED_DIR
                report_paths = discover_reports(DATA_MAPPED_DIR)
            except ImportError:
                pass
            # Also check workspace reports_root for legacy maps
            if not report_paths:
                reports_root = Path(body.reports_root) if body.reports_root else state.bridge.reports_root
                report_paths = discover_reports(reports_root)
        
        if not report_paths:
            return {
                "status": "success",
                "tokens": [],
                "reports_analyzed": 0,
                "summary": {},
                "version": VERSION
            }
        
        # Analyze reports
        stats_list, unmapped = analyze_reports(report_paths)
        
        # Generate internal report
        report = generate_review_report(stats_list, unmapped, output_path=None)
        
        # Flatten tokens into the shape the UI expects:
        # flat array with .token, .category, .occurrences, .total_contexts, etc.
        flat_tokens = []
        for category, token_list in report.get("unmapped_tokens_by_recommendation", {}).items():
            for t in token_list:
                t["category"] = category
                flat_tokens.append(t)
        
        return {
            "status": "success",
            "tokens": flat_tokens,
            "reports_analyzed": report.get("reports_analyzed", 0),
            "summary": report.get("summary", {}),
            "recommendations": report.get("recommendations", {}),
            "version": VERSION
        }

    @app.post("/api/lexicon/append")
    async def post_lexicon_append(body: LexiconAppendRequest):
        if not body.word:
            raise HTTPException(status_code=400, detail="word is required")
        await _ensure_lexicon_loaded("lexicon_append")
        result = state.bridge.append_word(body.word, body.status)
        result["version"] = VERSION
        await ws_manager.broadcast({
            "evt": "lexicon-append",
            "word": body.word,
            "version": VERSION,
        })
        return result

    @app.post("/api/symbol/assign")
    async def post_assign_symbol(body: AssignSymbolRequest):
        if not body.word:
            raise HTTPException(status_code=400, detail="word is required")
        await _ensure_lexicon_loaded("symbol_assign")
        try:
            result = state.bridge.assign_symbol(body.word, body.symbol, body.force or False)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        result["version"] = VERSION
        await ws_manager.broadcast({
            "evt": "symbol-assign",
            "word": body.word,
            "symbol": result.get("symbol"),
            "version": VERSION,
        })
        return result

    @app.post("/api/lexicon/status")
    async def post_lexicon_status(body: SetStatusRequest):
        if not body.word:
            raise HTTPException(status_code=400, detail="word is required")
        await _ensure_lexicon_loaded("lexicon_status")
        result = state.bridge.set_status(body.word, body.status)
        result["version"] = VERSION
        await ws_manager.broadcast({
            "evt": "lexicon-status",
            "word": body.word,
            "status": body.status,
            "version": VERSION,
        })
        return result

    @app.delete("/api/lexicon/canonical")
    async def delete_lexicon_canonical():
        """Clear all canonical word bindings, returning slots to AVAILABLE."""
        await _ensure_lexicon_loaded("lexicon_clear_canonical")
        result = state.bridge.clear_canonical()
        result["version"] = VERSION
        await ws_manager.broadcast({
            "evt": "lexicon-cleared",
            "purged": result["purged"],
            "version": VERSION,
        })
        return result

    @app.post("/api/lexicon/return-to-pool")
    async def post_lexicon_return_to_pool():
        """Move all ASSIGNED slots back to the available pool."""
        await _ensure_lexicon_loaded("lexicon_return_to_pool")
        result = state.bridge.return_to_pool()
        result["version"] = VERSION
        await ws_manager.broadcast({
            "evt": "lexicon-pool-reset",
            "moved": result["moved"],
            "version": VERSION,
        })
        return result

    @app.post("/api/lexicon/import")
    async def post_lexicon_import(body: LexiconImportRequest):
        """Import verified word lists from a directory."""
        await _ensure_lexicon_loaded("lexicon_import")
        words_dir = Path(body.words_dir)
        try:
            result = state.bridge.import_word_list(words_dir)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        result["version"] = VERSION
        await ws_manager.broadcast({
            "evt": "lexicon-imported",
            "imported": result["imported"],
            "version": VERSION,
        })
        return result

    @app.post("/api/lexicon/unload")
    async def lexicon_unload():
        """Release lexicon entries from RAM.

        Safe to call at any time — the lexicon will lazy-reload on the next
        operation that needs it.  Called automatically by the UI when the user
        leaves the Lexicon Browser tab or closes the browser window.
        """
        import gc as _gc
        async with state.lock:
            count = len(state.bridge.entries)
            if not state.bridge.loaded:
                return {"ok": True, "was_loaded": False, "entries_freed": 0}
            state.bridge.entries.clear()
            state.bridge.loaded = False
        _gc.collect()
        LOGGER.info("Lexicon unloaded on request — %d entries freed", count)
        return {"ok": True, "was_loaded": True, "entries_freed": count}

    @app.websocket("/ws/stream")
    async def websocket_endpoint(websocket: WebSocket):
        await ws_manager.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            pass
        except Exception:
            # Network drop, ConnectionReset, etc. — clean up stale socket
            pass
        finally:
            await ws_manager.disconnect(websocket)

    ui_dir = BASE_DIR / "ui"
    if ui_dir.exists():
        app.mount("/ui", StaticFiles(directory=str(ui_dir), html=True), name="ui")
        art_dir = BASE_DIR / "ART"
        if art_dir.exists():
            app.mount("/ART", StaticFiles(directory=str(art_dir), html=False), name="art")

        # Serve root — the production HTML entry point
        _ui_html = ui_dir / "forest_ai_production.html"

        @app.get("/")
        async def serve_ui_root():
            if _ui_html.exists():
                return FileResponse(_ui_html)
            raise HTTPException(status_code=404, detail="UI entry point not found")

        @app.get("/favicon.ico")
        async def serve_favicon():
            # Try common favicon locations
            for candidate in (ui_dir / "favicon.ico", ui_dir / "assets" / "logo.svg"):
                if candidate.exists():
                    return FileResponse(candidate)
            raise HTTPException(status_code=404, detail="No favicon available")

    # ── Plugin Management Endpoints ──────────────────────────────

    # Known plugin metadata (non-executing scan uses this for display)
    _PLUGIN_META = {
        "lakespeak": {
            "name": "GroveSpeak",
            "description": "Retrieval-augmented grounding (BM25 + dense)",
            "mount": "/api/lakespeak",
            "type": "router",
            "color": "#00ff88",
        },
        "wolf_engine": {
            "name": "Wolf Engine",
            "description": "Symbol-first cognitive architecture with governance",
            "mount": "/api/wolf",
            "type": "router",
            "color": "#00d4ff",
        },
        "reasoning_engine": {
            "name": "Reasoning Engine",
            "description": "Non-LLM inference over 6-1-6 maps",
            "mount": "in-process",
            "type": "embedded",
            "color": "#ffd700",
        },
        "forest_node": {
            "name": "Forest Node",
            "description": "LAN-based distributed job execution",
            "mount": "/api/nodes",
            "type": "router",
            "health_url": "/api/nodes/status",
            "color": "#cc7a00",
        },
        "help_system": {
            "name": "Help System",
            "description": "Contextual help and guided tutorials",
            "mount": "/api/help",
            "type": "router",
            "color": "#9b59b6",
        },
        "chat_packs": {
            "name": "Chat Packs",
            "description": "Data-only lesson bundles with stepwise instruction",
            "mount": "/api/chat-packs",
            "type": "router",
            "color": "#e67e22",
        },
    }

    def _scan_plugins() -> list:
        """Scan plugins/ directory and return plugin cards."""
        plugins_dir = BASE_DIR / "plugins"
        connected_list = state.config.get("plugins", {}).get("connected", [])
        pipeline_order = state.config.get("plugins", {}).get("pipeline_order", [])
        cards = []
        for entry in sorted(plugins_dir.iterdir()):
            if not entry.is_dir() or entry.name.startswith(("_", ".")):
                continue
            has_init = (entry / "__init__.py").exists()
            if not has_init:
                continue
            pid = entry.name
            meta = _PLUGIN_META.get(pid, {})
            # Try to read version from __init__.py without importing
            version = "unknown"
            try:
                init_text = (entry / "__init__.py").read_text(encoding="utf-8")
                for line in init_text.splitlines():
                    if "VERSION" in line and "=" in line:
                        version = line.split("=", 1)[1].strip().strip("\"'")
                        break
            except Exception:
                pass
            cards.append({
                "id": pid,
                "name": meta.get("name", pid),
                "version": version,
                "description": meta.get("description", ""),
                "connected": pid in connected_list,
                "mounted": pid in _mounted_plugins,
                "pipeline_index": pipeline_order.index(pid) if pid in pipeline_order else -1,
                "mount": meta.get("mount", ""),
                "type": meta.get("type", "unknown"),
                "color": meta.get("color", "#888"),
                "status": "unknown",
            })
        return cards

    @app.get("/api/plugins")
    async def list_plugins():
        """List all discovered plugins with connection status."""
        cards = _scan_plugins()
        # Quick health probe for connected plugins
        for card in cards:
            if not card["connected"]:
                card["status"] = "disconnected"
                continue
            meta = _PLUGIN_META.get(card["id"], {})
            if meta.get("type") == "service":
                url = meta.get("health_url", "")
                if url:
                    try:
                        async with httpx.AsyncClient(timeout=2.0) as client:
                            r = await client.get(url)
                            card["status"] = "ok" if r.status_code < 500 else "down"
                    except Exception:
                        card["status"] = "down"
                else:
                    card["status"] = "ok"
            else:
                # Router-type: if it's mounted, it's ok
                card["status"] = "ok"
        return cards

    @app.post("/api/plugins/{plugin_id}/connect")
    async def plugin_connect(plugin_id: str):
        """Connect a plugin (add to connected list)."""
        connected = list(state.config.get("plugins", {}).get("connected", []))
        pipeline = list(state.config.get("plugins", {}).get("pipeline_order", []))
        if plugin_id not in connected:
            connected.append(plugin_id)
        if plugin_id not in pipeline:
            pipeline.append(plugin_id)
        plugins_cfg = {"connected": connected, "pipeline_order": pipeline}
        config_data = dict(state.config)
        config_data["plugins"] = plugins_cfg
        secure_json_dump(state.config_path, config_data, indent=2)
        state.config = config_data
        return {"ok": True, "plugin_id": plugin_id, "connected": True}

    @app.post("/api/plugins/{plugin_id}/disconnect")
    async def plugin_disconnect(plugin_id: str):
        """Disconnect a plugin (remove from connected + pipeline)."""
        connected = list(state.config.get("plugins", {}).get("connected", []))
        pipeline = list(state.config.get("plugins", {}).get("pipeline_order", []))
        connected = [p for p in connected if p != plugin_id]
        pipeline = [p for p in pipeline if p != plugin_id]
        plugins_cfg = {"connected": connected, "pipeline_order": pipeline}
        config_data = dict(state.config)
        config_data["plugins"] = plugins_cfg
        secure_json_dump(state.config_path, config_data, indent=2)
        state.config = config_data
        return {"ok": True, "plugin_id": plugin_id, "connected": False}

    @app.post("/api/plugins/reorder")
    async def plugin_reorder(order: list[str]):
        """Update pipeline execution order."""
        config_data = dict(state.config)
        plugins_cfg = dict(config_data.get("plugins", {}))
        plugins_cfg["pipeline_order"] = order
        config_data["plugins"] = plugins_cfg
        secure_json_dump(state.config_path, config_data, indent=2)
        state.config = config_data
        return {"ok": True, "pipeline_order": order}

    # ── Mount LakeSpeak plugin (optional, non-fatal) ────────
    try:
        from lakespeak.api.router import router as lakespeak_router
        app.include_router(lakespeak_router)
        _mounted_plugins.add("lakespeak")
        LOGGER.info("LakeSpeak plugin mounted at /api/lakespeak")
    except ImportError:
        LOGGER.info("LakeSpeak plugin not available (optional)")

    # ── Mount Wolf Engine plugin (optional, non-fatal) ────
    try:
        from wolf_engine.api.router import router as wolf_engine_router
        app.include_router(wolf_engine_router)
        _mounted_plugins.add("wolf_engine")
        LOGGER.info("Wolf Engine plugin mounted at /api/wolf")
    except ImportError:
        LOGGER.info("Wolf Engine plugin not available (optional)")

    # ── Mount Observe plugin (optional, non-fatal) ────────
    try:
        from observe.router import router as observe_router
        app.include_router(observe_router)
        _mounted_plugins.add("observe")
        LOGGER.info("Observe plugin mounted at /api/observe")
    except ImportError:
        LOGGER.info("Observe plugin not available (optional)")

    # ── Mount Forest Node plugin (optional, non-fatal) ────
    try:
        from forest_node.api.router import router as forest_node_router
        app.include_router(forest_node_router)
        _mounted_plugins.add("forest_node")
        LOGGER.info("Forest Node plugin mounted at /api/nodes")
        # Mobile pairing sub-router (USB + Hello pairing endpoints)
        try:
            from forest_node.api.pairing import router as pairing_router
            app.include_router(pairing_router)
            LOGGER.info("Mobile pairing endpoints mounted at /api/nodes/pair")
        except ImportError:
            LOGGER.info("Mobile pairing not available (optional)")
    except ImportError:
        LOGGER.info("Forest Node plugin not available (optional)")

    # ── Mount Help System plugin (optional, non-fatal) ────
    try:
        from help_system.api.router import router as help_system_router
        app.include_router(help_system_router)
        _mounted_plugins.add("help_system")
        LOGGER.info("Help System plugin mounted at /api/help")
    except ImportError:
        LOGGER.info("Help System plugin not available (optional)")

    # ── Mount Chat Packs plugin (optional, non-fatal) ─────
    try:
        from chat_packs.api.router import router as chat_packs_router
        app.include_router(chat_packs_router)
        _mounted_plugins.add("chat_packs")
        LOGGER.info("Chat Packs plugin mounted at /api/chat-packs")
    except ImportError:
        LOGGER.info("Chat Packs plugin not available (optional)")

    # ── Mount Genesis Citation plugin (optional, non-fatal) ─
    try:
        from genesis_cite.router import router as genesis_cite_router
        app.include_router(genesis_cite_router)
        _mounted_plugins.add("genesis_cite")
        LOGGER.info("Genesis Citation plugin mounted at /api/genesis")
    except ImportError:
        LOGGER.info("Genesis Citation plugin not available (optional)")

    # ── Mount Forest Network plugin (optional, non-fatal) ─
    try:
        from forest_network.router import router as forest_network_router
        app.include_router(forest_network_router)
        _mounted_plugins.add("forest_network")
        LOGGER.info("Forest Network plugin mounted at /api/network")
    except ImportError:
        LOGGER.info("Forest Network plugin not available (optional)")

    # ── Dev Routing endpoints ─────────────────────────────
    from routing.config import (
        validate_profile as _rt_validate,
        list_named_profiles as _rt_list,
        load_named_profile as _rt_load_named,
        save_named_profile as _rt_save_named,
        DEFAULTS as _RT_DEFAULTS,
    )

    @app.get("/api/routing/profile")
    async def routing_get_profile():
        """Return the active routing profile."""
        return load_routing_profile(state.config.get("routing"))

    @app.post("/api/routing/profile")
    async def routing_update_profile(profile: dict):
        """Update the active routing profile. Validates first."""
        ok, err = _rt_validate(profile)
        if not ok:
            raise HTTPException(status_code=400, detail=err)
        config_data = dict(state.config)
        config_data["routing"] = profile
        secure_json_dump(state.config_path, config_data, indent=2)
        state.config = config_data
        return {"ok": True, "profile": profile.get("name")}

    @app.get("/api/routing/profiles")
    async def routing_list_profiles():
        """List all saved named profiles."""
        return {"profiles": _rt_list()}

    @app.post("/api/routing/profiles/{name}")
    async def routing_save_named(name: str):
        """Save the current active profile as a named profile."""
        active = load_routing_profile(state.config.get("routing"))
        ok, err = _rt_save_named(name, active)
        if not ok:
            raise HTTPException(status_code=400, detail=err)
        return {"ok": True, "name": name}

    @app.post("/api/routing/profiles/{name}/activate")
    async def routing_activate_named(name: str):
        """Load a named profile as the active profile."""
        profile = _rt_load_named(name)
        if profile is None:
            raise HTTPException(status_code=404, detail=f"Profile '{name}' not found")
        ok, err = _rt_validate(profile)
        if not ok:
            raise HTTPException(status_code=400, detail=f"Saved profile invalid: {err}")
        config_data = dict(state.config)
        config_data["routing"] = profile
        secure_json_dump(state.config_path, config_data, indent=2)
        state.config = config_data
        return {"ok": True, "name": name, "profile": profile}

    @app.post("/api/routing/reset")
    async def routing_reset():
        """Restore the default routing profile."""
        import copy
        defaults = copy.deepcopy(_RT_DEFAULTS)
        config_data = dict(state.config)
        config_data["routing"] = defaults
        secure_json_dump(state.config_path, config_data, indent=2)
        state.config = config_data
        return {"ok": True, "profile": "default"}

    @app.get("/api/routing/dev-mode")
    async def routing_get_dev_mode():
        """Check if dev routing panel is enabled."""
        routing = state.config.get("routing", {})
        return {"enabled": routing.get("dev_mode", False)}

    @app.post("/api/routing/dev-mode")
    async def routing_toggle_dev_mode():
        """Toggle the dev_mode flag."""
        config_data = dict(state.config)
        routing = dict(config_data.get("routing", {}))
        routing["dev_mode"] = not routing.get("dev_mode", False)
        config_data["routing"] = routing
        secure_json_dump(state.config_path, config_data, indent=2)
        state.config = config_data
        return {"ok": True, "dev_mode": routing["dev_mode"]}

    # ── Provider Key Management endpoints ─────────────────────
    from security.provider_keys import (
        list_providers as _prov_list,
        get_provider_status as _prov_status,
        save_provider_key as _prov_save,
        delete_provider_key as _prov_delete,
        get_provider_key as _prov_get_key,
        _load_all as _prov_load_all,
        _save_all as _prov_save_all,
        VALID_PROVIDERS as _prov_valid,
    )
    from security.provider_test import TESTERS as _prov_testers
    from security.inference_profiles import (
        load_all_profiles as _inf_load_all,
        load_profile as _inf_load,
        save_profile as _inf_save,
    )

    @app.get("/api/providers")
    async def providers_list():
        """List all configured providers with status. Keys never returned."""
        return {"providers": _prov_list()}

    @app.get("/api/providers/{name}")
    async def provider_status(name: str):
        """Get status of a single provider."""
        if name not in _prov_valid:
            raise HTTPException(status_code=404, detail=f"Unknown provider: {name}")
        return _prov_status(name)

    @app.post("/api/providers/{name}/key")
    async def provider_save_key(name: str, body: dict):
        """Save an API key for a provider. Body: {"key": "sk-..."}"""
        if name not in _prov_valid:
            raise HTTPException(status_code=404, detail=f"Unknown provider: {name}")
        key = body.get("key", "").strip()
        if not key:
            raise HTTPException(status_code=400, detail="Key is required")
        if name == "openai" and not key.startswith("sk-"):
            raise HTTPException(status_code=400, detail="OpenAI keys start with 'sk-'")
        if name == "claude" and not key.startswith("sk-ant-"):
            raise HTTPException(status_code=400, detail="Claude keys start with 'sk-ant-'")
        if name == "gemini" and not key.startswith("AIza"):
            raise HTTPException(status_code=400, detail="Gemini keys typically start with 'AIza'")
        result = _prov_save(name, key)
        LOGGER.info(f"Provider key saved: {name}")
        return result

    @app.delete("/api/providers/{name}/key")
    async def provider_delete_key(name: str):
        """Remove a provider's API key."""
        if name not in _prov_valid:
            raise HTTPException(status_code=404, detail=f"Unknown provider: {name}")
        result = _prov_delete(name)
        LOGGER.info(f"Provider key removed: {name}")
        return result

    @app.post("/api/providers/{name}/test")
    async def provider_test(name: str):
        """Test connection to a provider using the stored key."""
        if name not in _prov_valid:
            raise HTTPException(status_code=404, detail=f"Unknown provider: {name}")
        key = _prov_get_key(name)
        if not key:
            raise HTTPException(status_code=400, detail=f"No key configured for {name}")
        tester = _prov_testers.get(name)
        if not tester:
            raise HTTPException(status_code=500, detail=f"No tester for {name}")
        ok, message = await tester(key)
        # Update test timestamp in storage
        data = _prov_load_all()
        if name in data:
            data[name]["last_tested"] = datetime.now(timezone.utc).isoformat()
            data[name]["test_ok"] = ok
            _prov_save_all(data)
        return {"ok": ok, "message": message, "provider": name}

    # ── Per-Model Inference Profile endpoints ─────────────────

    @app.get("/api/inference/profiles")
    async def inference_profiles_list():
        """Get all per-model inference profiles."""
        return {"profiles": _inf_load_all()}

    @app.get("/api/inference/profiles/{model:path}")
    async def inference_profile_get(model: str):
        """Get inference profile for a specific model."""
        profile = _inf_load(model)
        if profile is None:
            return {"model": model, "profile": None, "using_defaults": True}
        return {"model": model, "profile": profile, "using_defaults": False}

    @app.post("/api/inference/profiles/{model:path}")
    async def inference_profile_save(model: str, body: dict):
        """Save inference profile for a specific model."""
        result = _inf_save(model, body)
        LOGGER.info(f"Inference profile saved: {model}")
        return {"ok": True, "model": model, "profile": result}

    # ── Gutenberg Stream endpoints ─────────────────────────
    _GUTENBERG_MANIFEST = BASE_DIR / "state" / "gutenberg_manifest.jsonl"

    def _read_gutenberg_manifest() -> list:
        """Read the Gutenberg ingest manifest."""
        entries = []
        if _GUTENBERG_MANIFEST.exists():
            for line in _GUTENBERG_MANIFEST.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries

    @app.get("/api/gutenberg/manifest")
    async def gutenberg_manifest():
        """Return list of previously ingested Gutenberg books."""
        entries = _read_gutenberg_manifest()
        return {
            "count": len(entries),
            "total_chunks": sum(e.get("chunk_count", 0) for e in entries),
            "total_words": sum(e.get("words", 0) for e in entries),
            "entries": entries,
        }

    @app.post("/api/gutenberg/ingest")
    async def gutenberg_ingest(req: GutenbergIngestRequest):
        """Kick off Gutenberg ingest for given book IDs.

        Runs synchronously in a thread to avoid blocking the event loop.
        Returns results when complete.
        """
        import concurrent.futures

        def _do_ingest():
            sys.path.insert(0, str(BASE_DIR))
            sys.path.insert(0, str(BASE_DIR / "plugins"))
            from scripts.gutenberg_stream import (
                fetch_gutenberg_text, ingest_book, _load_bridge,
                _load_manifest, _append_manifest, do_reindex,
            )
            manifest = _load_manifest()
            bridge = None if req.dry_run else _load_bridge()
            results = []
            for book_id in req.book_ids:
                entry = {"gutenberg_id": book_id}
                if book_id in manifest and not req.force:
                    entry["status"] = "skipped"
                    entry["reason"] = "already ingested"
                    results.append(entry)
                    continue
                text = fetch_gutenberg_text(book_id)
                if text is None:
                    entry["status"] = "failed"
                    entry["reason"] = "download failed"
                    results.append(entry)
                    continue
                entry["chars"] = len(text)
                entry["words"] = len(text.split())
                if req.dry_run:
                    entry["status"] = "dry_run"
                    results.append(entry)
                    continue
                receipt = ingest_book(book_id, text, bridge, dry_run=False)
                if receipt:
                    entry["status"] = "ingested"
                    entry["receipt_id"] = receipt.get("receipt_id")
                    entry["chunk_count"] = receipt.get("chunk_count", 0)
                    entry["anchor_count"] = receipt.get("anchor_count", 0)
                    from datetime import datetime, timezone
                    _append_manifest({
                        "gutenberg_id": book_id,
                        "receipt_id": receipt["receipt_id"],
                        "chunk_count": receipt["chunk_count"],
                        "anchor_count": receipt["anchor_count"],
                        "chars": entry["chars"],
                        "words": entry["words"],
                        "ingested_at": datetime.now(timezone.utc).isoformat(),
                    })
                else:
                    entry["status"] = "failed"
                    entry["reason"] = "ingest returned no receipt"
                results.append(entry)
            return results

        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            results = await loop.run_in_executor(pool, _do_ingest)

        ingested = sum(1 for r in results if r.get("status") == "ingested")
        return {
            "results": results,
            "ingested": ingested,
            "total": len(results),
        }

    @app.get("/api/gutenberg/preview/{book_id}")
    async def gutenberg_preview(book_id: int):
        """Download and preview a Gutenberg book without ingesting."""
        import concurrent.futures

        def _fetch():
            sys.path.insert(0, str(BASE_DIR))
            from scripts.gutenberg_stream import fetch_gutenberg_text
            return fetch_gutenberg_text(book_id)

        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            text = await loop.run_in_executor(pool, _fetch)

        if text is None:
            raise HTTPException(404, f"Could not download Gutenberg book #{book_id}")
        return {
            "gutenberg_id": book_id,
            "chars": len(text),
            "words": len(text.split()),
            "preview": text[:2000],
            "paragraphs": len([p for p in text.split("\n\n") if p.strip()]),
        }

    # ── Local File Stream endpoints ──────────────────────────
    _LOCALFILE_MANIFEST = BASE_DIR / "state" / "localfile_manifest.jsonl"

    def _read_localfile_manifest() -> list:
        entries = []
        if _LOCALFILE_MANIFEST.exists():
            for line in _LOCALFILE_MANIFEST.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries

    @app.get("/api/localfile/manifest")
    async def localfile_manifest():
        entries = _read_localfile_manifest()
        return {
            "count": len(entries),
            "total_chunks": sum(e.get("chunk_count", 0) for e in entries),
            "total_words": sum(e.get("words", 0) for e in entries),
            "entries": entries,
        }

    @app.post("/api/localfile/ingest")
    async def localfile_ingest(req: LocalFileIngestRequest):
        import concurrent.futures

        def _do():
            sys.path.insert(0, str(BASE_DIR))
            sys.path.insert(0, str(BASE_DIR / "plugins"))
            from scripts.localfile_stream import (
                fetch, strip_boilerplate, ingest_file,
                load_manifest, append_manifest, scan_directory, _load_bridge,
            )
            manifest = load_manifest()
            bridge = None if req.dry_run else _load_bridge()
            results = []
            # Expand directories
            all_files = []
            for p in req.paths:
                fp = Path(p)
                if fp.is_dir():
                    all_files.extend(scan_directory(str(fp), req.recursive))
                else:
                    all_files.append(str(fp.resolve()))

            for source_id in all_files:
                entry = {"source_id": source_id}
                if source_id in manifest and not req.force:
                    entry["status"] = "skipped"
                    results.append(entry)
                    continue
                text = fetch(source_id)
                if not text:
                    entry["status"] = "failed"
                    entry["reason"] = "read failed"
                    results.append(entry)
                    continue
                text = strip_boilerplate(text)
                if not text:
                    entry["status"] = "failed"
                    entry["reason"] = "empty after cleaning"
                    results.append(entry)
                    continue
                entry["chars"] = len(text)
                entry["words"] = len(text.split())
                if req.dry_run:
                    entry["status"] = "dry_run"
                    results.append(entry)
                    continue
                receipt = ingest_file(source_id, text, bridge, dry_run=False)
                if receipt and "receipt_id" in receipt:
                    entry["status"] = "ingested"
                    entry["receipt_id"] = receipt["receipt_id"]
                    entry["chunk_count"] = receipt.get("chunk_count", 0)
                    entry["anchor_count"] = receipt.get("anchor_count", 0)
                    from datetime import datetime, timezone
                    append_manifest({
                        "source_type": "localfile", "source_id": source_id,
                        "receipt_id": receipt["receipt_id"],
                        "chunk_count": receipt.get("chunk_count", 0),
                        "anchor_count": receipt.get("anchor_count", 0),
                        "chars": entry["chars"], "words": entry["words"],
                        "ingested_at": datetime.now(timezone.utc).isoformat(),
                    })
                else:
                    entry["status"] = "failed"
                    entry["reason"] = "ingest returned no receipt"
                results.append(entry)
            return results

        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            results = await loop.run_in_executor(pool, _do)
        ingested = sum(1 for r in results if r.get("status") == "ingested")
        return {"results": results, "ingested": ingested, "total": len(results)}

    # ── Web Scrape Stream endpoints ──────────────────────────
    _WEBSCRAPE_MANIFEST = BASE_DIR / "state" / "webscrape_manifest.jsonl"

    def _read_webscrape_manifest() -> list:
        entries = []
        if _WEBSCRAPE_MANIFEST.exists():
            for line in _WEBSCRAPE_MANIFEST.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries

    @app.get("/api/webscrape/manifest")
    async def webscrape_manifest():
        entries = _read_webscrape_manifest()
        return {
            "count": len(entries),
            "total_chunks": sum(e.get("chunk_count", 0) for e in entries),
            "total_words": sum(e.get("words", 0) for e in entries),
            "entries": entries,
        }

    @app.post("/api/webscrape/ingest")
    async def webscrape_ingest(req: WebScrapeIngestRequest):
        import concurrent.futures

        def _do():
            sys.path.insert(0, str(BASE_DIR))
            sys.path.insert(0, str(BASE_DIR / "plugins"))
            from scripts.webscrape_stream import (
                fetch, strip_boilerplate, ingest_page, normalize_url,
                load_manifest, append_manifest, _load_bridge,
            )
            manifest = load_manifest()
            bridge = None if req.dry_run else _load_bridge()
            results = []
            for raw_url in req.urls:
                url = normalize_url(raw_url)
                entry = {"source_id": url}
                if url in manifest and not req.force:
                    entry["status"] = "skipped"
                    results.append(entry)
                    continue
                html = fetch(url)
                if not html:
                    entry["status"] = "failed"
                    entry["reason"] = "download failed"
                    results.append(entry)
                    continue
                text = strip_boilerplate(html)
                if not text or len(text) < 100:
                    entry["status"] = "failed"
                    entry["reason"] = "insufficient content"
                    results.append(entry)
                    continue
                entry["chars"] = len(text)
                entry["words"] = len(text.split())
                if req.dry_run:
                    entry["status"] = "dry_run"
                    results.append(entry)
                    continue
                receipt = ingest_page(url, text, bridge, dry_run=False)
                if receipt and "receipt_id" in receipt:
                    entry["status"] = "ingested"
                    entry["receipt_id"] = receipt["receipt_id"]
                    entry["chunk_count"] = receipt.get("chunk_count", 0)
                    entry["anchor_count"] = receipt.get("anchor_count", 0)
                    from datetime import datetime, timezone
                    append_manifest({
                        "source_type": "web", "source_id": url,
                        "receipt_id": receipt["receipt_id"],
                        "chunk_count": receipt.get("chunk_count", 0),
                        "anchor_count": receipt.get("anchor_count", 0),
                        "chars": entry["chars"], "words": entry["words"],
                        "ingested_at": datetime.now(timezone.utc).isoformat(),
                    })
                else:
                    entry["status"] = "failed"
                    entry["reason"] = "ingest returned no receipt"
                results.append(entry)
            return results

        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            results = await loop.run_in_executor(pool, _do)
        ingested = sum(1 for r in results if r.get("status") == "ingested")
        return {"results": results, "ingested": ingested, "total": len(results)}

    @app.get("/api/webscrape/preview")
    async def webscrape_preview(url: str):
        import concurrent.futures

        def _do():
            sys.path.insert(0, str(BASE_DIR))
            from scripts.webscrape_stream import fetch, strip_boilerplate, normalize_url
            canon = normalize_url(url)
            html = fetch(canon)
            if not html:
                return None
            text = strip_boilerplate(html)
            return {"url": canon, "chars": len(text), "words": len(text.split()),
                    "preview": text[:2000],
                    "paragraphs": len([p for p in text.split("\n\n") if p.strip()])}

        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(pool, _do)
        if result is None:
            raise HTTPException(404, f"Could not fetch {url}")
        return result

    # ── RSS Stream endpoints ─────────────────────────────────────
    _RSS_MANIFEST = BASE_DIR / "state" / "rss_manifest.jsonl"

    def _read_rss_manifest() -> list:
        entries = []
        if _RSS_MANIFEST.exists():
            for line in _RSS_MANIFEST.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        return entries

    @app.get("/api/rss/manifest")
    async def rss_manifest():
        entries = _read_rss_manifest()
        return {
            "count": len(entries),
            "total_chunks": sum(e.get("chunk_count", 0) for e in entries),
            "total_words": sum(e.get("words", 0) for e in entries),
            "entries": entries[-100:],  # cap at last 100 entries
        }

    @app.post("/api/rss/ingest")
    async def rss_ingest(req: RssIngestRequest):
        import concurrent.futures

        def _do():
            sys.path.insert(0, str(BASE_DIR))
            sys.path.insert(0, str(BASE_DIR / "plugins"))
            from scripts.rss_stream import (
                fetch, fetch_feed_entries, strip_boilerplate,
                ingest_entry, load_manifest, append_manifest, _load_bridge,
            )
            manifest = load_manifest()
            bridge = None if req.dry_run else _load_bridge()
            feed_entries = fetch_feed_entries(req.feed_url, limit=req.latest)
            results = []
            for fe in feed_entries:
                sid = fe["source_id"]
                entry = {"source_id": sid, "title": fe.get("title", "")}
                if sid in manifest and not req.force:
                    entry["status"] = "skipped"
                    entry["reason"] = "already ingested"
                    results.append(entry)
                    continue
                text = fetch(sid)
                if not text:
                    entry["status"] = "failed"
                    entry["reason"] = "download failed"
                    results.append(entry)
                    continue
                text = strip_boilerplate(text)
                if not text or len(text) < 100:
                    entry["status"] = "failed"
                    entry["reason"] = "insufficient content"
                    results.append(entry)
                    continue
                entry["chars"] = len(text)
                entry["words"] = len(text.split())
                if req.dry_run:
                    entry["status"] = "dry_run"
                    results.append(entry)
                    continue
                receipt = ingest_entry(sid, text, bridge, dry_run=False)
                if receipt and "receipt_id" in receipt:
                    entry["status"] = "ingested"
                    entry["receipt_id"] = receipt["receipt_id"]
                    entry["chunk_count"] = receipt.get("chunk_count", 0)
                    entry["anchor_count"] = receipt.get("anchor_count", 0)
                    from datetime import datetime as _dt, timezone as _tz
                    append_manifest({
                        "source_type": "rss", "source_id": sid,
                        "receipt_id": receipt["receipt_id"],
                        "chunk_count": receipt.get("chunk_count", 0),
                        "anchor_count": receipt.get("anchor_count", 0),
                        "chars": entry["chars"], "words": entry["words"],
                        "ingested_at": _dt.now(_tz.utc).isoformat(),
                    })
                else:
                    entry["status"] = "failed"
                    entry["reason"] = "ingest returned no receipt"
                results.append(entry)
            return results

        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            results = await loop.run_in_executor(pool, _do)
        ingested = sum(1 for r in results if r.get("status") == "ingested")
        return {"results": results, "ingested": ingested, "total": len(results)}

    @app.get("/api/rss/preview")
    async def rss_preview(feed_url: str):
        import concurrent.futures

        def _do():
            sys.path.insert(0, str(BASE_DIR))
            sys.path.insert(0, str(BASE_DIR / "plugins"))
            from scripts.rss_stream import fetch_feed_entries
            entries = fetch_feed_entries(feed_url, limit=20)
            return {"feed_url": feed_url, "entry_count": len(entries), "entries": entries}

        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(pool, _do)
        return result

    # ── DocuMap Stats ────────────────────────────────────────────

    @app.get("/api/documap/stats")
    async def documap_stats():
        # Job ledger stats (upload queue tracking)
        ledger = _read_documap_ledger()
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ledger_counts = {"queued": 0, "started": 0, "completed": 0, "failed": 0}
        mapped_today = 0
        for _fp, evt in ledger.items():
            status = evt.get("event", "")
            if status in ledger_counts:
                ledger_counts[status] += 1
            if status == "completed" and evt.get("ts", "")[:10] == today_str:
                mapped_today += 1

        # Data Grove: count actual receipt directories
        grove_doc_count = 0
        try:
            if LAKESPEAK_CHUNKS_DIR.exists():
                grove_doc_count = sum(
                    1 for d in LAKESPEAK_CHUNKS_DIR.iterdir()
                    if d.is_dir() and (d / "chunks.jsonl").exists()
                )
        except Exception as e:
            LOGGER.warning("Could not count grove receipts: %s", e)

        # Anchor stats from grove index
        grove_anchors = 0
        try:
            stats_path = LAKESPEAK_INDEX_DIR / "anchor_stats.json"
            if stats_path.exists():
                with open(stats_path, "r", encoding="utf-8") as f:
                    anchor_data = json.load(f)
                grove_anchors = anchor_data.get("unique_anchors", 0)
        except Exception as e:
            LOGGER.warning("Could not read anchor stats: %s", e)

        sys_verified = state.bridge.slots_assigned if state.bridge.loaded else 0

        return {
            "updated_utc": datetime.now(timezone.utc).isoformat(),
            "uploads_queued": ledger_counts["queued"],
            "uploads_processing": ledger_counts["started"],
            "uploads_failed": ledger_counts["failed"],
            "docs_mapped_total": grove_doc_count,
            "mapped_today": mapped_today,
            "anchors_total_grove": grove_anchors,
            "anchors_sys_verified": sys_verified,
            "grove_label": "Data Grove",
            "documap_label": "DocuMap",
            "version": VERSION,
        }

    @app.get("/api/documap/fingerprint/{fingerprint}")
    async def documap_check_fingerprint(fingerprint: str):
        ledger = _read_documap_ledger()
        evt = ledger.get(fingerprint)
        if not evt:
            return {"exists": False}
        return {"exists": True, "event": evt.get("event"), "fingerprint": fingerprint}

    @app.post("/api/documap/jobs/event")
    async def documap_job_event(body: dict):
        event = body.get("event")
        fingerprint = body.get("fingerprint")
        if not event or not fingerprint:
            raise HTTPException(400, "Missing event or fingerprint")
        body["ts"] = datetime.now(timezone.utc).isoformat()
        _append_documap_event(body)
        return {"ok": True}

    # ── DocuMap Grove Explorer ────────────────────────────────────

    @app.get("/api/documap/docs")
    async def documap_docs(limit: int = 50, offset: int = 0):
        """List documents in the Data Grove (LakeSpeak receipts)."""
        docs = []
        if LAKESPEAK_CHUNKS_DIR.exists():
            receipt_dirs = sorted(
                [d for d in LAKESPEAK_CHUNKS_DIR.iterdir() if d.is_dir()],
                reverse=True,  # newest first (receipt IDs sort by date)
            )
            for rdir in receipt_dirs:
                receipt_id = rdir.name
                chunks_file = rdir / "chunks.jsonl"
                anchors_file = rdir / "anchors.json"
                if not chunks_file.exists():
                    continue
                # Count chunks
                chunk_count = 0
                total_tokens = 0
                try:
                    with open(chunks_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                chunk_count += 1
                                try:
                                    c = json.loads(line)
                                    total_tokens += c.get("token_count", 0)
                                except json.JSONDecodeError:
                                    pass
                except OSError:
                    pass
                # Count anchors
                anchor_count = 0
                if anchors_file.exists():
                    try:
                        adata = json.loads(anchors_file.read_text(encoding="utf-8"))
                        if isinstance(adata, list):
                            anchor_count = sum(a.get("anchor_count", 0) for a in adata)
                    except (json.JSONDecodeError, OSError):
                        pass
                docs.append({
                    "receipt_id": receipt_id,
                    "chunk_count": chunk_count,
                    "total_tokens": total_tokens,
                    "anchor_count": anchor_count,
                    "has_relations": (rdir / "relations.json").exists(),
                })
        total = len(docs)
        page = docs[offset:offset + limit]
        return {"docs": page, "total": total}

    @app.get("/api/documap/docs/{receipt_id}")
    async def documap_doc_detail(receipt_id: str):
        """Get detail for a Data Grove receipt."""
        rdir = LAKESPEAK_CHUNKS_DIR / receipt_id
        if not rdir.is_dir():
            raise HTTPException(404, f"Receipt {receipt_id} not found in grove")
        chunks_file = rdir / "chunks.jsonl"
        anchors_file = rdir / "anchors.json"
        result = {"receipt_id": receipt_id, "files": [f.name for f in rdir.iterdir()]}
        if chunks_file.exists():
            chunks = []
            with open(chunks_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            chunks.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
            result["chunk_count"] = len(chunks)
            result["total_tokens"] = sum(c.get("token_count", 0) for c in chunks)
            if chunks:
                result["source_hash"] = chunks[0].get("source_hash", "")
        if anchors_file.exists():
            try:
                adata = json.loads(anchors_file.read_text(encoding="utf-8"))
                if isinstance(adata, list):
                    result["anchor_count"] = sum(a.get("anchor_count", 0) for a in adata)
            except (json.JSONDecodeError, OSError):
                pass
        return result

    @app.get("/api/documap/docs/{receipt_id}/reconstruct")
    async def documap_reconstruct(receipt_id: str):
        """Reconstruct human-readable text from Data Grove chunks."""
        rdir = LAKESPEAK_CHUNKS_DIR / receipt_id
        chunks_file = rdir / "chunks.jsonl"
        anchors_file = rdir / "anchors.json"
        if not chunks_file.exists():
            raise HTTPException(404, f"Receipt {receipt_id} not found in grove")

        # Read chunks in order
        chunks = []
        with open(chunks_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        chunks.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        chunks.sort(key=lambda c: c.get("ordinal", 0))

        # Reconstruct text from chunk texts (overlap-aware)
        text_parts = []
        prev_end = 0
        for ch in chunks:
            span_start = ch.get("span_start", prev_end)
            chunk_text = ch.get("text", "")
            if span_start >= prev_end:
                text_parts.append(chunk_text)
            else:
                # Overlapping chunk — skip the overlap portion
                overlap = prev_end - span_start
                if overlap < len(chunk_text):
                    text_parts.append(chunk_text[overlap:])
            prev_end = max(prev_end, ch.get("span_end", span_start + len(chunk_text)))
        text = "".join(text_parts)

        # Collect anchors
        anchors = []
        if anchors_file.exists():
            try:
                adata = json.loads(anchors_file.read_text(encoding="utf-8"))
                if isinstance(adata, list):
                    for chunk_anchors in adata:
                        for a in chunk_anchors.get("anchors", []):
                            anchors.append({
                                "word": a.get("token", ""),
                                "hex_addr": a.get("hex_addr", ""),
                            })
            except (json.JSONDecodeError, OSError):
                pass
        # Deduplicate anchors by word
        seen = set()
        unique_anchors = []
        for a in anchors:
            if a["word"] not in seen:
                seen.add(a["word"])
                unique_anchors.append(a)

        total_tokens = sum(c.get("token_count", 0) for c in chunks)
        return {
            "text": text,
            "lossy": False,
            "anchors": unique_anchors,
            "total_tokens": total_tokens,
            "anchor_count": len(unique_anchors),
            "chunk_count": len(chunks),
        }

    @app.get("/api/documap/docs/{receipt_id}/graph")
    async def documap_graph(receipt_id: str, max_nodes: int = 100, max_edges: int = 500):
        """Build Cytoscape graph from grove anchors + relations."""
        rdir = LAKESPEAK_CHUNKS_DIR / receipt_id
        anchors_file = rdir / "anchors.json"
        relations_file = rdir / "relations.json"
        if not rdir.is_dir():
            raise HTTPException(404, f"Receipt {receipt_id} not found in grove")

        # Collect unique anchors with frequency from anchors.json
        anchor_freq: Dict[str, int] = {}
        anchor_addr: Dict[str, str] = {}
        if anchors_file.exists():
            try:
                adata = json.loads(anchors_file.read_text(encoding="utf-8"))
                if isinstance(adata, list):
                    for chunk_anchors in adata:
                        for a in chunk_anchors.get("anchors", []):
                            tok = a.get("token", "")
                            anchor_freq[tok] = anchor_freq.get(tok, 0) + 1
                            if tok not in anchor_addr:
                                anchor_addr[tok] = a.get("hex_addr", "")
            except (json.JSONDecodeError, OSError):
                pass

        # TopN anchors by frequency
        sorted_anchors = sorted(anchor_freq.items(), key=lambda x: x[1], reverse=True)[:max_nodes]
        anchor_set = {a[0] for a in sorted_anchors}

        nodes = [
            {"data": {"id": tok, "label": tok, "freq": freq, "addr": anchor_addr.get(tok, "")}}
            for tok, freq in sorted_anchors
        ]

        # Build edges from relations.json
        edges = []
        edge_count = 0
        if relations_file.exists():
            try:
                rdata = json.loads(relations_file.read_text(encoding="utf-8"))
                if isinstance(rdata, list):
                    for chunk_rels in rdata:
                        for rel in chunk_rels.get("relations", []):
                            src = rel.get("source_token", "")
                            tgt = rel.get("target_token", "")
                            weight = rel.get("co_occurrence_count", 1)
                            if src in anchor_set and tgt in anchor_set and src != tgt:
                                edges.append({"data": {"source": src, "target": tgt, "weight": weight}})
                                edge_count += 1
                                if edge_count >= max_edges:
                                    break
                        if edge_count >= max_edges:
                            break
            except (json.JSONDecodeError, OSError):
                pass

        return {"nodes": nodes, "edges": edges, "total_anchors": len(sorted_anchors), "capped": len(sorted_anchors) >= max_nodes}

    # ── Anchor Cloud (hover context) ────────────────────────────

    @app.get("/api/documap/anchors/{anchor}/cloud")
    async def documap_anchor_cloud(anchor: str, receipt_id: str = "", topk: int = 20):
        if not receipt_id:
            raise HTTPException(400, "receipt_id query param required")
        rdir = LAKESPEAK_CHUNKS_DIR / receipt_id
        relations_file = rdir / "relations.json"
        if not rdir.is_dir():
            raise HTTPException(404, f"Receipt {receipt_id} not found in grove")

        # Collect co-occurring anchors from relations
        cooccur: Dict[str, float] = {}
        if relations_file.exists():
            try:
                rdata = json.loads(relations_file.read_text(encoding="utf-8"))
                if isinstance(rdata, list):
                    for chunk_rels in rdata:
                        for rel in chunk_rels.get("relations", []):
                            src = rel.get("source_token", "")
                            tgt = rel.get("target_token", "")
                            count = rel.get("co_occurrence_count", 1)
                            if src == anchor and tgt != anchor:
                                cooccur[tgt] = cooccur.get(tgt, 0) + count
                            elif tgt == anchor and src != anchor:
                                cooccur[src] = cooccur.get(src, 0) + count
            except (json.JSONDecodeError, OSError):
                pass

        max_score = max(cooccur.values()) if cooccur else 1
        cloud = sorted(
            [{"anchor": k, "score": round(v / max_score, 3)} for k, v in cooccur.items()],
            key=lambda x: x["score"],
            reverse=True,
        )[:topk]

        return {"anchor": anchor, "topk": cloud, "receipt_id": receipt_id}

    # ── AI Briefs (locked, read-only, strict allowlist) ──────
    _AI_BRIEF_DIR = BASE_DIR / "docs" / "ai"
    _BRIEF_NAME_RE = re.compile(r'^[A-Za-z0-9_-]+$')
    _BRIEF_DISPLAY_LIMIT = 20_000  # chars
    _BRIEF_DIGEST_LIMIT = 6_000   # chars (~1,200 tokens)
    _PROVIDER_BRIEF_MAP = {
        "local": "local", "ollama": "local",
        "google": "gemini", "gemini": "gemini",
        "openai": "openai",
        "anthropic": "anthropic", "claude": "anthropic",
    }

    # Build startup allowlist: scan docs/ai/*.ai.md once
    _BRIEF_ALLOWLIST: dict[str, Path] = {}
    if _AI_BRIEF_DIR.is_dir():
        for _p in sorted(_AI_BRIEF_DIR.glob("*.ai.md")):
            _base = _p.stem.removesuffix(".ai")  # "FOREST" from "FOREST.ai.md"
            if not _p.is_symlink():
                _BRIEF_ALLOWLIST[_base] = _p.resolve()
    LOGGER.info("AI Brief allowlist: %s", list(_BRIEF_ALLOWLIST.keys()))

    def _brief_sha(content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _extract_digest(content: str) -> str | None:
        """Extract BRIEF_DIGEST section between markers. None if missing."""
        start = content.find("<!-- BRIEF_DIGEST -->")
        end = content.find("<!-- END_BRIEF_DIGEST -->")
        if start == -1 or end == -1 or end <= start:
            return None
        return content[start + len("<!-- BRIEF_DIGEST -->"):end].strip()

    def _brief_response(name: str, path: Path) -> dict:
        """Build a standard brief response with sha256, digest info, display limit."""
        content = path.read_text(encoding="utf-8")
        total_chars = len(content)
        truncated = total_chars > _BRIEF_DISPLAY_LIMIT
        display = content[:_BRIEF_DISPLAY_LIMIT] if truncated else content
        digest = _extract_digest(content)
        return {
            "name": name, "file": path.name,
            "content": display, "sha256": _brief_sha(content),
            "content_truncated": truncated, "content_total_chars": total_chars,
            "digest_present": digest is not None,
            "digest": digest,
        }

    @app.get("/api/ai-briefs")
    async def list_ai_briefs():
        """List all available .ai.md briefs from startup allowlist."""
        briefs = [{"name": k, "file": f"{k}.ai.md"} for k in sorted(_BRIEF_ALLOWLIST)]
        return {"briefs": briefs, "provider_map": _PROVIDER_BRIEF_MAP}

    @app.get("/api/ai-briefs/for-provider/{provider}")
    async def get_brief_for_provider(provider: str):
        """Get the global brief + model-specific brief for a provider."""
        result: dict[str, Any] = {
            "global": None, "global_sha256": None,
            "model": None, "model_sha256": None,
            "provider": provider,
        }
        gpath = _BRIEF_ALLOWLIST.get("FOREST")
        if gpath and gpath.is_file():
            gc = gpath.read_text(encoding="utf-8")
            result["global"] = gc[:_BRIEF_DISPLAY_LIMIT]
            result["global_sha256"] = _brief_sha(gc)
        model_key = _PROVIDER_BRIEF_MAP.get(provider.lower())
        if model_key:
            mpath = _BRIEF_ALLOWLIST.get(model_key)
            if mpath and mpath.is_file():
                mc = mpath.read_text(encoding="utf-8")
                result["model"] = mc[:_BRIEF_DISPLAY_LIMIT]
                result["model_sha256"] = _brief_sha(mc)
        return result

    @app.get("/api/ai-briefs/pin-status")
    async def brief_pin_status():
        """Check if an AI brief is pinned for today's session."""
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        pin = _find_todays_pin(today_str)
        if pin:
            content = pin.get("content", "")
            sha = _brief_sha(content) if content else ""
            return {"pinned": True, "sha256": sha, "date": today_str}
        return {"pinned": False, "date": today_str}

    @app.post("/api/ai-briefs/pin")
    async def pin_brief_to_session(request: Request):
        """Pin the BRIEF_DIGEST to today's session (one per day, operator-triggered)."""
        body = await request.json()
        provider = body.get("provider", "")
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Check if already pinned today
        existing = _find_todays_pin(today_str)
        if existing:
            return {"pinned": False, "reason": "already_pinned",
                    "sha256": existing.get("integrity_hash", "")[:16]}

        # Collect digests
        digests = []
        brief_names = []
        gpath = _BRIEF_ALLOWLIST.get("FOREST")
        if gpath and gpath.is_file():
            gd = _extract_digest(gpath.read_text(encoding="utf-8"))
            if gd:
                digests.append(gd)
                brief_names.append("FOREST.ai.md")
        model_key = _PROVIDER_BRIEF_MAP.get(provider.lower(), "")
        if model_key:
            mpath = _BRIEF_ALLOWLIST.get(model_key)
            if mpath and mpath.is_file():
                md = _extract_digest(mpath.read_text(encoding="utf-8"))
                if md:
                    digests.append(md)
                    brief_names.append(f"{model_key}.ai.md")

        if not digests:
            return {"pinned": False, "reason": "missing_digest_markers"}

        combined = "\n\n---\n\n".join(digests)
        if len(combined) > _BRIEF_DIGEST_LIMIT:
            return {"pinned": False, "reason": "digest_too_large",
                    "chars": len(combined), "limit": _BRIEF_DIGEST_LIMIT}

        sha = _brief_sha(combined)

        # Write to today's thread as system note with kind=AI_BRIEF
        try:
            _log_message(
                sender="ai",
                content=combined,
                actor="system",
                seat={"provider": "forest_bridge", "model": "ai_brief"},
                kind="AI_BRIEF",
            )
        except Exception as e:
            LOGGER.exception("Failed to pin AI brief")
            return {"pinned": False, "reason": f"write_error: {e}"}

        return {"pinned": True, "sha256": sha, "chars": len(combined),
                "briefs": brief_names}

    def _find_todays_pin(today_str: str) -> dict | None:
        """Check today's thread JSONL for an existing AI_BRIEF pin."""
        try:
            from Conversations.threads.daily_logger import get_today_file
            from security.secure_storage import secure_read_lines
            today_file = get_today_file()
            if not today_file.exists():
                return None
            for line in secure_read_lines(today_file):
                try:
                    obj = json.loads(line)
                    if obj.get("kind") == "AI_BRIEF" and obj.get("content"):
                        return obj
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass
        return None

    @app.get("/api/ai-briefs/{name}")
    async def get_ai_brief(name: str):
        """Read a specific .ai.md brief by base name (e.g. 'FOREST', 'local')."""
        if not _BRIEF_NAME_RE.match(name):
            raise HTTPException(400, "Invalid brief name")
        path = _BRIEF_ALLOWLIST.get(name)
        if not path or not path.is_file():
            raise HTTPException(404, "Brief not found")
        return _brief_response(name, path)

    # ── Control Panel: Logger Streams ─────────────────────────
    _LOGGER_STREAMS = [
        {
            "name": "runtime_log",
            "path": str(RUNTIME_LOG_PATH) if RUNTIME_LOG_PATH else "",
            "toggleable": False,
            "description": "Runtime errors and events (always on)",
        },
        {
            "name": "debugwire",
            "path": str(RUNTIME_LOG_PATH) if RUNTIME_LOG_PATH else "",
            "toggleable": True,
            "description": "DEBUGWIRE entry/exit tracing",
        },
        {
            "name": "tool_telemetry",
            "path": str(TOOL_TELEMETRY_PATH) if TOOL_TELEMETRY_PATH else "",
            "toggleable": True,
            "description": "Tool execution telemetry (per-model)",
        },
        {
            "name": "p5_diagnostic",
            "path": str(DIAGNOSTIC_DIR) if DIAGNOSTIC_DIR else "",
            "toggleable": False,
            "description": "P5 diagnostic suite output (on demand)",
        },
        {
            "name": "gateway_denials",
            "path": str(RUNTIME_LOG_PATH) if RUNTIME_LOG_PATH else "",
            "toggleable": False,
            "description": "Gateway write denials (always on)",
        },
    ]

    @app.get("/api/control/loggers")
    async def list_loggers():
        """List all logger streams with status."""
        from security.runtime_log import debugwire_status
        dw = debugwire_status()
        streams = []
        for s in _LOGGER_STREAMS:
            active = True
            if s["name"] == "debugwire":
                active = dw.get("enabled", False)
            elif s["name"] == "tool_telemetry":
                active = TOOL_TELEMETRY_PATH.exists() if TOOL_TELEMETRY_PATH else False
            elif s["name"] == "p5_diagnostic":
                active = False  # on demand only
            # Get last event time
            last_event = None
            try:
                p = Path(s["path"]) if s["path"] else None
                if p and p.is_file():
                    lines = p.read_text(encoding="utf-8").splitlines()
                    for line in reversed(lines[-20:]):
                        try:
                            obj = json.loads(line.strip())
                            ts = obj.get("ts_utc") or obj.get("timestamp")
                            if ts:
                                last_event = ts
                                break
                        except (json.JSONDecodeError, AttributeError):
                            continue
            except Exception:
                pass
            streams.append({
                "name": s["name"], "path": s["path"],
                "toggleable": s["toggleable"], "active": active,
                "last_event": last_event, "description": s["description"],
            })
        return {"streams": streams}

    @app.get("/api/control/loggers/{name}/tail")
    async def tail_logger(name: str, lines: int = 200):
        """Tail last N lines from a logger stream JSONL."""
        stream = next((s for s in _LOGGER_STREAMS if s["name"] == name), None)
        if not stream:
            raise HTTPException(404, "Logger stream not found")
        p = Path(stream["path"]) if stream["path"] else None
        if not p or not p.is_file():
            return {"lines": [], "stream": name}
        try:
            all_lines = p.read_text(encoding="utf-8").splitlines()
            tail = all_lines[-min(lines, len(all_lines)):]
            parsed = []
            for line in tail:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed.append(json.loads(line))
                except json.JSONDecodeError:
                    parsed.append(line)
            return {"lines": parsed, "stream": name, "total": len(all_lines)}
        except Exception as e:
            raise HTTPException(500, f"Failed to read log: {e}")

    @app.post("/api/control/loggers/{name}/toggle")
    async def toggle_logger(name: str, request: Request):
        """Toggle a logger stream on/off (only safe streams)."""
        stream = next((s for s in _LOGGER_STREAMS if s["name"] == name), None)
        if not stream:
            raise HTTPException(404, "Logger stream not found")
        if not stream["toggleable"]:
            raise HTTPException(403, f"Stream '{name}' cannot be toggled")
        body = await request.json()
        enabled = body.get("enabled", True)
        if name == "debugwire":
            from security.runtime_log import debugwire_set
            debugwire_set(enabled)
            from security.runtime_log import debugwire_status
            return debugwire_status()
        return {"name": name, "enabled": enabled}

    # ── Control Panel: Tool Policy ────────────────────────────

    @app.get("/api/control/tool-policy/{model:path}")
    async def get_tool_policy(model: str):
        """Get allowed tools for a model, plus full tool registry for UI."""
        from security.tool_profiles import get_allowed_tools, get_default_allowed
        from bridges.tool_defs import TOOL_REGISTRY
        allowed = get_allowed_tools(model)
        defaults = get_default_allowed()
        effective = allowed if allowed is not None else defaults
        tools = []
        for t in TOOL_REGISTRY:
            tools.append({
                "name": t["name"],
                "description": t.get("description", ""),
                "safety": t.get("safety", "read"),
                "allowed": t["name"] in effective,
            })
        return {
            "model": model,
            "allowed": allowed,
            "using_defaults": allowed is None,
            "defaults": defaults,
            "tools": tools,
        }

    @app.post("/api/control/tool-policy/{model:path}")
    async def save_tool_policy(model: str, request: Request):
        """Save allowed tools list for a model."""
        body = await request.json()
        allowed = body.get("allowed", [])
        from security.tool_profiles import save_tool_profile
        profile = save_tool_profile(model, allowed)
        return {"model": model, "profile": profile}

    # ── Control Panel: Tool Telemetry ─────────────────────────

    @app.get("/api/control/tool-telemetry")
    async def get_tool_telemetry():
        """Get aggregated tool telemetry stats."""
        from security.tool_telemetry import aggregate_stats
        return {"stats": aggregate_stats()}

    @app.get("/api/control/tool-telemetry/raw")
    async def get_tool_telemetry_raw(lines: int = 100):
        """Get raw tool telemetry records."""
        from security.tool_telemetry import tail_raw
        return {"records": tail_raw(lines)}

    # ── Action Ledger (History Queue events) ──────────────────

    @app.post("/api/history/queue/log")
    async def history_queue_log(request: Request):
        """Client-side queue events forwarded to server-side ledger."""
        from security.action_ledger import record as ledger_record
        body = await request.json()
        entry = ledger_record(
            event=body.get("event", "unknown"),
            session_id=body.get("session_id"),
            source_day=body.get("source_day"),
            source_msg_id=body.get("source_msg_id"),
            source_block_id=body.get("source_block_id"),
            action=body.get("action"),
            payload_preview=str(body.get("payload_preview", ""))[:128],
            status=body.get("status"),
            error=body.get("error"),
        )
        return {"ok": True, "seq": entry["seq"]}

    @app.get("/api/history/queue/ledger")
    async def history_queue_ledger(limit: int = 100):
        """Read last N ledger entries (read-only)."""
        import json as _json
        from security.action_ledger import ACTION_LEDGER_PATH
        if not ACTION_LEDGER_PATH.exists():
            return {"items": []}
        lines = ACTION_LEDGER_PATH.read_text(encoding="utf-8").splitlines()
        items = []
        for line in lines[-limit:]:
            try:
                items.append(_json.loads(line))
            except Exception:
                pass
        return {"items": items}

    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Forest Lexicon Bridge server")
    parser.add_argument("--config", type=Path, default=None, help="Path to forest.config.json (defaults to secure location)")
    parser.add_argument("--host", type=str, help="Override host")
    parser.add_argument("--port", type=int, help="Override port")
    parser.add_argument("--log-level", type=str, default="info")
    return parser.parse_args()


def _resolve_runtime_path(raw_path: str | Path) -> Path:
    try:
        from security.data_paths import SOURCE_ROOT as _SOURCE_ROOT
    except Exception:
        _SOURCE_ROOT = BASE_DIR
    p = Path(raw_path).expanduser()
    if p.is_absolute():
        return p
    return (_SOURCE_ROOT / p).resolve()


def _critical_config_fields(cfg: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "lexicon_root": cfg.get("lexicon_root"),
        "reports_root": cfg.get("reports_root"),
    }


def _startup_preflight(config_path: Path, *, explicit_config: bool) -> Dict[str, Any]:
    cfg = secure_json_load(config_path)
    critical_secure = _critical_config_fields(cfg)

    lexicon_abs = _resolve_runtime_path(str(critical_secure.get("lexicon_root") or ""))
    reports_abs = _resolve_runtime_path(str(critical_secure.get("reports_root") or ""))

    from security.data_paths import SOURCE_ROOT, FOREST_CONFIG_PATH
    workspace_cfg_path = SOURCE_ROOT / "forest.config.json"

    if (not explicit_config) and workspace_cfg_path.exists():
        try:
            with workspace_cfg_path.open("r", encoding="utf-8") as handle:
                workspace_cfg = json.load(handle)
            critical_workspace = _critical_config_fields(workspace_cfg)
            mismatches = []
            for key, secure_val in critical_secure.items():
                ws_val = critical_workspace.get(key)
                if ws_val != secure_val:
                    mismatches.append((key, secure_val, ws_val))
            if mismatches:
                details = "; ".join([f"{k}: secure={sv!r} workspace={wv!r}" for k, sv, wv in mismatches])
                raise RuntimeError(
                    "Split-brain config detected between secure and workspace forest.config.json. "
                    f"Mismatches: {details}"
                )
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Workspace config unreadable at {workspace_cfg_path}: {exc}") from exc

    if not lexicon_abs.exists():
        raise RuntimeError(f"Configured lexicon_root does not exist: {lexicon_abs}")

    LOGGER.info(
        "Preflight roots: config=%s secure_default=%s source=%s lexicon=%s reports=%s state=%s",
        config_path,
        FOREST_CONFIG_PATH,
        SOURCE_ROOT,
        lexicon_abs,
        reports_abs,
        STATE_DIR,
    )
    return cfg


def main():
    args = parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level.upper(), logging.INFO))
    config_path = args.config if args.config else _SEC_CONFIG
    config = _startup_preflight(config_path, explicit_config=bool(args.config))
    state = BridgeState(config_path)

    host = args.host or config.get("server", {}).get("host", "127.0.0.1")
    port = args.port or config.get("server", {}).get("port", 5050)

    app = create_app(state)

    # TLS: auto-generate self-signed cert if config says tls: true
    ssl_kw = {}
    if config.get("server", {}).get("tls", False):
        try:
            from security.tls import ensure_tls
            tls_result = ensure_tls()
            if tls_result:
                ssl_kw["ssl_certfile"] = tls_result[0]
                ssl_kw["ssl_keyfile"] = tls_result[1]
                LOGGER.info("TLS enabled: %s", tls_result[0])
        except Exception as e:
            LOGGER.warning("TLS setup failed, serving plain HTTP: %s", e)

    uvicorn.run(app, host=host, port=port, log_level=args.log_level, **ssl_kw)


if __name__ == "__main__":
    main()
