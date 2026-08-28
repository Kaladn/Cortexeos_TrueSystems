from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from bridges.models import ChatSendRequest
from bridges.services.grounded_chat_service import GroundedChatService


@dataclass
class _FakeRoute:
    def telemetry_block(self, _ctx: Any) -> dict[str, str]:
        return {"route": "ok"}

    def record(self, *args: Any, **kwargs: Any) -> None:
        _ = (args, kwargs)


@dataclass
class _FakeState:
    config: dict

    def get_ollama_base_url(self) -> str:
        return "http://127.0.0.1:11434"


class _MissingLakeSpeak:
    def get_engine(self) -> Any:
        raise ImportError("lakespeak missing")


def test_grounded_returns_not_available_when_plugin_missing() -> None:
    async def _run() -> None:
        state = _FakeState(config={})
        svc = GroundedChatService(
            state=state,  # type: ignore[arg-type]
            lakespeak_service=_MissingLakeSpeak(),  # type: ignore[arg-type]
        )
        resp = await svc.execute(
            req=ChatSendRequest(message="where is x", mode="grounded"),
            msg="where is x",
            model_name="gpt-oss:20b",
            route=_FakeRoute(),
            rctx={},
            branch="main",
            build_seat=lambda provider, model, seat_id=None, node_id="server": {
                "provider": provider,
                "model": model,
                "seat_id": seat_id,
                "node_id": node_id,
            },
        )
        assert resp.error is not None
        assert resp.error["type"] == "not_available"
        assert "LakeSpeak is unavailable" in resp.response

    asyncio.run(_run())
