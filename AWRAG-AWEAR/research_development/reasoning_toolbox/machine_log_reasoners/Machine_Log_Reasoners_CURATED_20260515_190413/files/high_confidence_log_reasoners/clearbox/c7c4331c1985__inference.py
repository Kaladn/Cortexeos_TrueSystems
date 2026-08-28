"""Provider and local inference service."""
from __future__ import annotations

import asyncio
import logging
import re as _re
import time
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException

from .lakespeak_service import LakeSpeakService
from .reasoning_service import ReasoningService


LOGGER = logging.getLogger("clearbox_bridge_server")

# Single source of truth for fallback model name.
DEFAULT_MODEL = "current model"


class InferenceService:
    """State-aware provider callers used by routers and orchestration services."""

    def __init__(
        self,
        *,
        state: Any | None = None,
        reasoning_service: ReasoningService | None = None,
        lakespeak_service: LakeSpeakService | None = None,
        ollama_base_url: str | None = None,
    ) -> None:
        self._state = state
        self._reasoning_service = reasoning_service or ReasoningService()
        self._lakespeak_service = lakespeak_service or LakeSpeakService()
        self._explicit_ollama_base_url = ollama_base_url
        self._callers = {
            "ollama": self.call_ollama,
            "openai": self.call_openai,
            "claude": self.call_claude,
            "gemini": self.call_gemini,
            "grok": self.call_grok,
            "reasoning": self.call_reasoning,
        }
        # Persistent HTTP clients — one per provider, reused across all calls.
        # Eliminates per-call TCP handshake + TLS negotiation overhead.
        # Each client holds a connection pool; connections are reused automatically.
        self._openai_client = httpx.AsyncClient(
            timeout=120.0,
            headers={"Content-Type": "application/json"},
        )
        self._claude_client = httpx.AsyncClient(
            timeout=120.0,
            headers={
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )
        self._gemini_client = httpx.AsyncClient(
            timeout=120.0,
            headers={"Content-Type": "application/json"},
        )
        self._grok_client = httpx.AsyncClient(
            timeout=120.0,
            headers={"Content-Type": "application/json"},
        )
        self._ollama_client = httpx.AsyncClient(
            timeout=120.0,
            headers={"Content-Type": "application/json"},
        )

    async def aclose(self) -> None:
        """Close all persistent HTTP clients. Call on server shutdown."""
        for client in (
            self._openai_client,
            self._claude_client,
            self._gemini_client,
            self._grok_client,
            self._ollama_client,
        ):
            try:
                await client.aclose()
            except Exception:
                pass

    @property
    def reasoning_service(self) -> ReasoningService:
        return self._reasoning_service

    @property
    def ollama_base_url(self) -> str:
        if self._explicit_ollama_base_url:
            return self._explicit_ollama_base_url.rstrip("/")
        if self._state is not None and hasattr(self._state, "get_ollama_base_url"):
            return str(self._state.get_ollama_base_url()).rstrip("/")
        return "http://127.0.0.1:11434"

    @staticmethod
    def _strip_tool_calls(text: str) -> str:
        if not text or ("tool_call" not in text and "<tool_call>" not in text):
            return text
        from bridges.tool_defs import strip_tool_calls

        return strip_tool_calls(text)

    async def call(
        self,
        provider: str,
        api_key: str,
        model: str,
        messages: list[dict],
        inference_params: dict | None = None,
    ) -> tuple[str, dict, int]:
        caller = self._callers.get(provider)
        if caller is None:
            raise ValueError(f"Unknown provider: {provider}")
        return await caller(api_key, model, messages, inference_params)

    async def call_openai(
        self,
        api_key: str,
        model: str,
        messages: list[dict],
        inference_params: dict | None = None,
    ) -> tuple[str, dict, int]:
        payload: dict = {"model": model, "input": messages}
        if inference_params:
            if "temperature" in inference_params:
                payload["temperature"] = inference_params["temperature"]
            if "top_p" in inference_params:
                payload["top_p"] = inference_params["top_p"]
            if "max_tokens" in inference_params:
                payload["max_output_tokens"] = inference_params["max_tokens"]
        t0 = time.time()
        r = await self._openai_client.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {api_key}"},
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
        return self._strip_tool_calls(reply), data.get("usage", {}), ms

    async def call_claude(
        self,
        api_key: str,
        model: str,
        messages: list[dict],
        inference_params: dict | None = None,
    ) -> tuple[str, dict, int]:
        from bridges.helpers import _merge_consecutive_roles

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
        r = await self._claude_client.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api_key},
            json=payload,
        )
        ms = int((time.time() - t0) * 1000)
        if not r.is_success:
            return "", {"error": f"HTTP {r.status_code}: {r.text[:300]}"}, ms
        data = r.json()
        reply = "".join(
            block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
        )
        return self._strip_tool_calls(reply), data.get("usage", {}), ms

    async def call_gemini(
        self,
        api_key: str,
        model: str,
        messages: list[dict],
        inference_params: dict | None = None,
    ) -> tuple[str, dict, int]:
        _gemini_role = {"user": "user", "assistant": "model", "system": "user"}
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        chat_msgs = [m for m in messages if m["role"] != "system"]
        payload: dict = {
            "contents": [
                {"role": _gemini_role.get(m["role"], "user"), "parts": [{"text": m["content"]}]}
                for m in chat_msgs
            ],
        }
        if system_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n".join(system_parts)}]}
        gen_config: dict = {}
        if inference_params:
            if "temperature" in inference_params:
                gen_config["temperature"] = inference_params["temperature"]
            if "top_p" in inference_params:
                gen_config["topP"] = inference_params["top_p"]
            if "top_k" in inference_params:
                gen_config["topK"] = inference_params["top_k"]
            if "max_tokens" in inference_params:
                gen_config["maxOutputTokens"] = inference_params["max_tokens"]
        if gen_config:
            payload["generationConfig"] = gen_config
        t0 = time.time()
        r = await self._gemini_client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": api_key},
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
        return self._strip_tool_calls(reply), data.get("usageMetadata", {}), ms

    async def call_grok(
        self,
        api_key: str,
        model: str,
        messages: list[dict],
        inference_params: dict | None = None,
    ) -> tuple[str, dict, int]:
        payload: dict = {"model": model, "messages": messages, "stream": False}
        if inference_params:
            if "temperature" in inference_params:
                payload["temperature"] = inference_params["temperature"]
            if "top_p" in inference_params:
                payload["top_p"] = inference_params["top_p"]
            if "max_tokens" in inference_params:
                payload["max_tokens"] = inference_params["max_tokens"]
        t0 = time.time()
        r = await self._grok_client.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
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
        return self._strip_tool_calls(reply), data.get("usage", {}), ms

    async def call_ollama(
        self,
        api_key: str,
        model: str,
        messages: list[dict],
        inference_params: dict | None = None,
    ) -> tuple[str, dict, int]:
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
            r = await self._ollama_client.post(f"{self.ollama_base_url}/api/chat", json=payload)
            ms = int((time.time() - t0) * 1000)
            if not r.is_success:
                return "", {"error": f"HTTP {r.status_code}: {r.text[:300]}"}, ms
            data = r.json()
            reply = self._strip_tool_calls(data.get("message", {}).get("content", ""))
            usage = {
                "prompt_eval_count": data.get("prompt_eval_count"),
                "eval_count": data.get("eval_count"),
            }
            return reply, usage, ms
        except Exception as e:
            return f"[Ollama error: {e}]", {}, int((time.time() - t0) * 1000)

    async def call_reasoning(
        self,
        api_key: str,
        model: str,
        messages: list[dict],
        inference_params: dict | None = None,
    ) -> tuple[str, dict, int]:
        _ = (api_key, model, inference_params)
        user_msg = messages[-1].get("content", "") if messages else ""
        t0 = time.time()
        try:
            answer = await self._reasoning_service.query_what_does_x_do(user_msg, 8)
            ms = int((time.time() - t0) * 1000)
            return answer.surface_text, answer.reasoning_trace or {}, ms
        except HTTPException as he:
            ms = int((time.time() - t0) * 1000)
            if he.status_code == 404:
                return "No map data for that term.", {"note": "anchor_not_found"}, ms
            return f"[Reasoning error: {he.detail}]", {}, ms
        except Exception as e:
            return f"[Reasoning engine error: {e}]", {}, int((time.time() - t0) * 1000)
