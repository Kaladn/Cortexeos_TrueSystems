from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import pytest

from bridges.models import ChatSendRequest
from bridges.services.chain_executor import ChainExecutor
from bridges.services.inference import InferenceService
from bridges.services.reasoning_service import ReasoningService


class _FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code
        self.is_success = status_code < 400

    def json(self) -> dict:
        return self._payload


class _FakeOllamaClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def post(self, url: str, json: dict) -> _FakeResponse:
        self.calls.append((url, json))
        return _FakeResponse(
            {
                "message": {"content": "hub simple reply"},
                "eval_count": 12,
                "prompt_eval_count": 8,
            }
        )


@dataclass
class _FakeState:
    config: dict = field(default_factory=lambda: {"tools_enabled": True})
    ollama_client: _FakeOllamaClient = field(default_factory=_FakeOllamaClient)

    async def get_ollama_client(self) -> _FakeOllamaClient:
        return self.ollama_client

    def get_ollama_base_url(self) -> str:
        return "http://127.0.0.1:11434"


@dataclass
class _FakeWsManager:
    broadcasts: list[dict] = field(default_factory=list)

    async def broadcast(self, payload: dict) -> None:
        self.broadcasts.append(payload)


@dataclass
class _FakeRoute:
    records: list[tuple] = field(default_factory=list)

    def record(self, *args: Any, **kwargs: Any) -> None:
        self.records.append((args, kwargs))

    def telemetry_block(self, _ctx: Any) -> dict:
        return {"route": "ok"}


class _FakeRequest:
    headers = {}


def test_chain_executor_simple_path_runs_hub_only() -> None:
    async def _run() -> None:
        state = _FakeState()
        ws = _FakeWsManager()
        route = _FakeRoute()
        inference = InferenceService(state=state, reasoning_service=ReasoningService())
        executor = ChainExecutor(
            state=state,
            ws_manager=ws,
            mounted_plugins=set(),
            inference_service=inference,
            reasoning_service=ReasoningService(),
            chat_messages_builder=lambda msg: [{"role": "user", "content": msg}],
            log_message_fn=lambda **_kwargs: None,
        )

        req = ChatSendRequest(
            message="hello chain",
            mode="llm",
            tools_enabled=False,
            chain_slots=[],
            plugins_enabled=False,
        )
        response = await executor.execute(
            {
                "request": req,
                "message": req.message,
                "route": route,
                "routing_context": {},
                "http_request": _FakeRequest(),
            }
        )

        assert response.response == "hub simple reply"
        assert response.contributions is not None
        assert len(response.contributions) == 1
        assert response.contributions[0]["author"] == "hub"
        assert response.contributions[0]["tools_used"] == []
        assert len(state.ollama_client.calls) == 1
        assert [evt.get("evt") for evt in ws.broadcasts] == ["chain-start", "chain-complete"]
        assert route.records, "Expected routing record from chain executor"

    asyncio.run(_run())
