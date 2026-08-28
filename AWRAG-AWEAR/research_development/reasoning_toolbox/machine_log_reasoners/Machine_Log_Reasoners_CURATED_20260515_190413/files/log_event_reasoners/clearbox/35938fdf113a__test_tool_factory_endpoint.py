from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from bridges.models import ChatSendResponse
from bridges.routers.control import make_router


class _DummyState:
    def __init__(self) -> None:
        self.config = {}

    async def write_config(self, updates: dict) -> None:
        self.config.update(updates)


class _DummyPluginRuntime:
    def discover(self) -> list:
        return []


def test_tool_factory_chat_forces_tools_off(monkeypatch, tmp_path: Path) -> None:
    captured: dict = {}
    recorded: list[dict] = []

    async def _fake_execute(self, *, req, msg, request, route, rctx, original_mode, model_name):
        captured["mode"] = req.mode
        captured["tools_enabled"] = req.tools_enabled
        captured["session_id"] = req.session_id
        captured["generation_contract"] = req.generation_contract
        captured["hub_provider"] = req.hub_provider
        captured["side_chat_id"] = req.side_chat_id
        return ChatSendResponse(
            mode="llm",
            source="ollama",
            response="factory draft",
            reasoning_trace={},
        )

    monkeypatch.setattr("bridges.routers.control.ChatModeExecutor.execute", _fake_execute)
    monkeypatch.setattr(
        "bridges.routers.control.record_factory_turn",
        lambda **kwargs: recorded.append(kwargs),
    )

    app = FastAPI()
    app.include_router(
        make_router(
            state=_DummyState(),
            mounted_plugins=set(),
            base_dir=tmp_path,
            plugin_runtime=_DummyPluginRuntime(),
            mounted_plugin_routes={},
        )
    )
    client = TestClient(app)

    resp = client.post(
        "/api/tools/factory/chat",
        json={
            "message": "Help me build a read-only market data tool.",
            "mode": "grounded",
            "tools_enabled": True,
            "hub_provider": "openai",
            "local_model": "gpt-4.1-mini",
            "side_chat_id": "side_20260315_120000_deadbeef",
            "generation_contract": "Keep the output concise.",
        },
    )

    assert resp.status_code == 200
    assert captured["mode"] == "llm"
    assert captured["tools_enabled"] is False
    assert captured["session_id"] == "tool_factory"
    assert captured["hub_provider"] == "openai"
    assert captured["side_chat_id"] == "side_20260315_120000_deadbeef"
    assert "Never call tools" in captured["generation_contract"]
    assert "Keep the output concise." in captured["generation_contract"]

    data = resp.json()
    assert data["response"] == "factory draft"
    assert data["reasoning_trace"]["tool_factory"]["tools_forced_off"] is True
    assert len(recorded) == 1
    assert recorded[0]["session_id"] == "tool_factory"
    assert recorded[0]["side_chat_id"] == "side_20260315_120000_deadbeef"
    assert recorded[0]["provider"] == "openai"
    assert recorded[0]["model"] == "gpt-4.1-mini"
