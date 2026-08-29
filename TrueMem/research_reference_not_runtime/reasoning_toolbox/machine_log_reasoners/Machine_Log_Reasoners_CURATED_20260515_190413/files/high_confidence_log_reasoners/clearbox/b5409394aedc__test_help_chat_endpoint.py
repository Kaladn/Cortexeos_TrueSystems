from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from bridges.models import ChatSendResponse
from bridges.routers.control import make_router
from core.help_system.api.router import router as help_router


class _DummyState:
    def __init__(self) -> None:
        self.config = {}

    async def write_config(self, updates: dict) -> None:
        self.config.update(updates)


class _DummyPluginRuntime:
    def discover(self) -> list:
        return []


def test_help_chat_forces_help_only_context(monkeypatch, tmp_path: Path) -> None:
    captured: dict = {}

    async def _fake_execute(self, *, req, msg, request, route, rctx, original_mode, model_name):
        captured["mode"] = req.mode
        captured["tools_enabled"] = req.tools_enabled
        captured["session_id"] = req.session_id
        captured["generation_contract"] = req.generation_contract
        captured["focus_help_id"] = req.focus_help_id
        captured["hub_provider"] = req.hub_provider
        return ChatSendResponse(
            mode="llm",
            source="ollama",
            response="help draft",
            reasoning_trace={},
        )

    monkeypatch.setattr("bridges.routers.control.ChatModeExecutor.execute", _fake_execute)
    monkeypatch.setattr(
        "bridges.routers.control._build_help_chat_context",
        lambda message, focus_help_id: (
            "Use only the provided HELP DATA CONTEXT.\n\n{\"entries\":[{\"help_id\":\"nav.lexicon\"}]}",
            {"entries": [{"help_id": "nav.lexicon"}]},
        ),
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
        "/api/help/chat",
        json={
            "message": "How do I use the lexicon browser?",
            "mode": "grounded",
            "tools_enabled": True,
            "hub_provider": "openai",
            "local_model": "gpt-4.1-mini",
            "focus_help_id": "nav.lexicon",
            "side_chat_id": "side_20260315_180000_deadbeef",
            "generation_contract": "Keep it concise.",
        },
    )

    assert resp.status_code == 200
    assert captured["mode"] == "llm"
    assert captured["tools_enabled"] is False
    assert captured["session_id"] == "help_guide"
    assert captured["focus_help_id"] == "nav.lexicon"
    assert captured["hub_provider"] == "openai"
    assert "Use only the provided HELP DATA CONTEXT" in captured["generation_contract"]
    assert "Keep it concise." in captured["generation_contract"]

    data = resp.json()
    assert data["response"] == "help draft"
    assert data["reasoning_trace"]["help_assistant"]["tools_forced_off"] is True
    assert data["reasoning_trace"]["help_assistant"]["provided_help_ids"] == ["nav.lexicon"]


def test_help_ids_accepts_rich_catalog_rows(monkeypatch) -> None:
    class _DummyHelpEngine:
        def list_ids(self):
            return [
                {
                    "help_id": "nav.lexicon",
                    "label": "Lexicon Browser",
                    "category": "Navigation",
                    "icon": "book",
                    "snippet": "Browse canonical and mutable lexicon entries.",
                    "difficulty": "easy",
                    "tutorial_available": False,
                    "has_layer2": True,
                    "has_layer3": False,
                }
            ]

    monkeypatch.setattr("core.help_system.api.router.get_engine", lambda: _DummyHelpEngine())

    app = FastAPI()
    app.include_router(help_router)
    client = TestClient(app)

    resp = client.get("/api/help/ids")

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["ids"][0]["help_id"] == "nav.lexicon"
    assert data["ids"][0]["tutorial_available"] is False
    assert data["ids"][0]["has_layer2"] is True
    assert data["ids"][0]["has_layer3"] is False
