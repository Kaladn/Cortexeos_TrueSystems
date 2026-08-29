from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from bridges.models import ChatSendRequest, ChatSendResponse
from bridges.services.chat_mode_executor import ChatModeExecutor


@dataclass
class _FakeRoute:
    def telemetry_block(self, _ctx: Any) -> dict[str, str]:
        return {"route": "ok"}


class _FakeRequest:
    headers = {}


class _FakeLlmService:
    def __init__(self) -> None:
        self.calls = 0

    async def execute(self, **kwargs: Any) -> ChatSendResponse:
        self.calls += 1
        return ChatSendResponse(mode=kwargs["original_mode"], source="llm", response="llm-ok")


class _FakeGroundedService:
    def __init__(self) -> None:
        self.calls = 0

    async def execute(self, **_kwargs: Any) -> ChatSendResponse:
        self.calls += 1
        return ChatSendResponse(mode="grounded", source="grounded", response="grounded-ok")


class _FakeMultiService:
    def __init__(self) -> None:
        self.calls = 0

    async def execute(self, **_kwargs: Any) -> ChatSendResponse:
        self.calls += 1
        return ChatSendResponse(mode="multi_llm", source="multi", response="multi-ok")


class _FakeReasoningService:
    def __init__(self) -> None:
        self.calls = 0

    async def execute(self, **_kwargs: Any) -> ChatSendResponse:
        self.calls += 1
        return ChatSendResponse(mode="reasoning", source="reasoning_engine", response="reasoning-ok")


def test_dispatches_to_mode_owned_services() -> None:
    async def _run() -> None:
        llm = _FakeLlmService()
        grounded = _FakeGroundedService()
        multi = _FakeMultiService()
        reasoning = _FakeReasoningService()

        exec_svc = ChatModeExecutor(
            state=object(),  # type: ignore[arg-type]
            llm_service=llm,  # type: ignore[arg-type]
            grounded_service=grounded,  # type: ignore[arg-type]
            multi_llm_service=multi,  # type: ignore[arg-type]
            reasoning_service=reasoning,  # type: ignore[arg-type]
        )
        route = _FakeRoute()
        request = _FakeRequest()

        r1 = await exec_svc.execute(
            req=ChatSendRequest(message="m1", mode="llm"),
            msg="m1",
            request=request,  # type: ignore[arg-type]
            route=route,
            rctx={},
            original_mode="llm",
            model_name="gpt-oss:20b",
        )
        assert r1.response == "llm-ok"

        r2 = await exec_svc.execute(
            req=ChatSendRequest(message="m2", mode="grounded"),
            msg="m2",
            request=request,  # type: ignore[arg-type]
            route=route,
            rctx={},
            original_mode="grounded",
            model_name="gpt-oss:20b",
        )
        assert r2.response == "grounded-ok"

        r3 = await exec_svc.execute(
            req=ChatSendRequest(message="m3", mode="multi_llm"),
            msg="m3",
            request=request,  # type: ignore[arg-type]
            route=route,
            rctx={},
            original_mode="multi_llm",
            model_name="gpt-oss:20b",
        )
        assert r3.response == "multi-ok"

        r4 = await exec_svc.execute(
            req=ChatSendRequest(message="m4", mode="reasoning"),
            msg="m4",
            request=request,  # type: ignore[arg-type]
            route=route,
            rctx={},
            original_mode="reasoning",
            model_name="gpt-oss:20b",
        )
        assert r4.response == "reasoning-ok"

        assert llm.calls == 1
        assert grounded.calls == 1
        assert multi.calls == 1
        assert reasoning.calls == 1

    asyncio.run(_run())


def test_unknown_mode_returns_contract_error() -> None:
    async def _run() -> None:
        exec_svc = ChatModeExecutor(
            state=object(),  # type: ignore[arg-type]
            llm_service=_FakeLlmService(),  # type: ignore[arg-type]
            grounded_service=_FakeGroundedService(),  # type: ignore[arg-type]
            multi_llm_service=_FakeMultiService(),  # type: ignore[arg-type]
            reasoning_service=_FakeReasoningService(),  # type: ignore[arg-type]
        )
        route = _FakeRoute()
        request = _FakeRequest()

        resp = await exec_svc.execute(
            req=ChatSendRequest(message="m", mode="invalid_mode"),
            msg="m",
            request=request,  # type: ignore[arg-type]
            route=route,
            rctx={},
            original_mode="invalid_mode",
            model_name="gpt-oss:20b",
        )
        assert resp.error is not None
        assert resp.error["type"] == "unknown_mode"

    asyncio.run(_run())
