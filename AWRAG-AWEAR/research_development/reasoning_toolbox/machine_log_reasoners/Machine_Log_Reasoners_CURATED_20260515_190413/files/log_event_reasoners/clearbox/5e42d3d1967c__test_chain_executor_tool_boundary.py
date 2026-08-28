from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from bridges.models import ChainSlot, ChatSendRequest
from bridges.services.chain_executor import ChainExecutor


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
        self._count = 0

    async def post(self, url: str, json: dict) -> _FakeResponse:
        self.calls.append((url, json))
        self._count += 1
        if self._count == 1:
            return _FakeResponse({"message": {"content": "hub opening"}})
        return _FakeResponse({"message": {"content": "hub consolidated local-tool response"}})


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


class _FakeInference:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, list[dict]]] = []
        self.ollama_base_url = "http://127.0.0.1:11434"

    async def call(
        self,
        provider: str,
        api_key: str,
        model: str,
        messages: list[dict],
        inference_params: dict | None = None,
    ) -> tuple[str, dict, int]:
        _ = (api_key, inference_params)
        self.calls.append((provider, model, messages))
        # Slot requests tool once; executor must not re-call slot with tool results.
        return "REQUEST_TOOL_FROM_SLOT", {}, 20


class _FakeRequest:
    headers = {}


def test_chain_slot_tool_requests_are_executed_only_by_local_hub(monkeypatch) -> None:
    async def _run() -> None:
        state = _FakeState()
        ws = _FakeWsManager()
        route = _FakeRoute()
        inference = _FakeInference()

        async def _fake_execute_tool(name: str, arguments: dict, **kwargs: Any) -> str:
            _ = (name, arguments, kwargs)
            return "tool-ok"

        monkeypatch.setattr("bridges.tool_defs.execute_tool", _fake_execute_tool)

        executor = ChainExecutor(
            state=state,
            ws_manager=ws,
            mounted_plugins=set(),
            inference_service=inference,  # type: ignore[arg-type]
            provider_key_getter=lambda _provider: "test-key",
            tool_request_parser=lambda reply: [{"name": "echo", "arguments": {"x": 1}}]
            if "REQUEST_TOOL_FROM_SLOT" in reply
            else None,
            chat_messages_builder=lambda msg: [{"role": "user", "content": msg}],
            log_message_fn=lambda **_kwargs: None,
        )

        req = ChatSendRequest(
            message="hello chain",
            mode="llm",
            tools_enabled=True,
            plugins_enabled=False,
            chain_slots=[ChainSlot(slot_id=1, enabled=True, provider="openai", model="gpt-4o-mini")],
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

        # Exactly one cloud slot call: no second "tool result" round-trip to cloud.
        assert len(inference.calls) == 1
        assert inference.calls[0][0] == "openai"
        # Local hub called at least twice: initial + local synthesis with tool results.
        assert len(state.ollama_client.calls) >= 2
        assert response.response == "hub consolidated local-tool response"
        assert response.contributions is not None
        assert any(c.get("tool_delegations") for c in response.contributions if c.get("author") == "hub")

    asyncio.run(_run())
