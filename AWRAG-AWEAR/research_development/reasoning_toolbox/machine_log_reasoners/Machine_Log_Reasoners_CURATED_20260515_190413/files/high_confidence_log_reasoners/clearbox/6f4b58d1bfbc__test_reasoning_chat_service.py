from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi import HTTPException

import bridges.services.reasoning_chat as reasoning_chat_module
from bridges.services.reasoning_chat import ReasoningChatService
from bridges.services.reasoning_service import ReasoningService
from bridges.models import ChatSendRequest


@dataclass
class _FakeRoute:
    enabled_value: bool = True

    def enabled(self, _ctx: Any, _stage: str) -> bool:
        return self.enabled_value

    def record(self, *args: Any, **kwargs: Any) -> None:
        _ = (args, kwargs)

    def telemetry_block(self, _ctx: Any) -> dict[str, str]:
        return {"route": "ok"}


@dataclass
class _FakeBridge:
    word_index: dict[str, str]


@dataclass
class _FakeState:
    reasoning_service: Any
    bridge: Any
    config: dict[str, Any]


@dataclass
class _FakeAnswer:
    subject: str
    predicates: list[dict[str, Any]]
    confidence: float
    reasoning_trace: dict[str, Any]
    surface_text: str


class _MissingReasoning:
    def __init__(self, *, subject: str, status_code: int = 404) -> None:
        self.subject = subject
        self.status_code = status_code

    def extract_subject(self, _question: str) -> str:
        return self.subject

    async def query_what_does_x_do(self, _question: str, _topk: int) -> Any:
        raise HTTPException(status_code=self.status_code, detail="not found")


class _AnsweringReasoning:
    def __init__(self, answer: _FakeAnswer) -> None:
        self.answer = answer

    def extract_subject(self, _question: str) -> str:
        return self.answer.subject

    async def query_what_does_x_do(self, _question: str, _topk: int) -> _FakeAnswer:
        return self.answer


def _build_seat(provider: str, model: str, seat_id: str | None = None, node_id: str = "server") -> dict[str, Any]:
    return {"provider": provider, "model": model, "seat_id": seat_id, "node_id": node_id}


async def _noop_ensure(_label: str) -> None:
    return None


def test_extract_subject_handles_articles_and_question_forms() -> None:
    assert ReasoningService.extract_subject("What does the forest do?") == "forest"
    assert ReasoningService.extract_subject("What is a river?") == "river"
    assert ReasoningService.extract_subject("What are these systems?") == "systems"


def test_reasoning_returns_no_data_contract_when_term_exists_in_lexicon(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        monkeypatch.setattr(reasoning_chat_module, "_log_message", lambda **_kwargs: {"message_id": "1"})
        state = _FakeState(
            reasoning_service=_MissingReasoning(subject="forest"),
            bridge=_FakeBridge(word_index={"forest": "0x1"}),
            config={"user_profile": {"display_name": "Alex"}},
        )
        svc = ReasoningChatService(state=state)  # type: ignore[arg-type]

        resp = await svc.execute(
            req=ChatSendRequest(message="What does the forest do?", mode="reasoning"),
            msg="What does the forest do?",
            route=_FakeRoute(),
            rctx={},
            build_seat=_build_seat,
            ensure_lexicon_loaded=_noop_ensure,
        )

        assert resp is not None
        assert resp.answer_frame is not None
        assert resp.answer_frame["status"] == "no_data"
        assert resp.answer_frame["subject"] == "forest"
        assert resp.answer_frame["suggested_next_mode"] == "llm"
        assert "Alex" in resp.response

    asyncio.run(_run())


def test_reasoning_returns_no_anchor_contract_when_term_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        monkeypatch.setattr(reasoning_chat_module, "_log_message", lambda **_kwargs: {"message_id": "1"})
        state = _FakeState(
            reasoning_service=_MissingReasoning(subject="unknownthing"),
            bridge=_FakeBridge(word_index={}),
            config={},
        )
        svc = ReasoningChatService(state=state)  # type: ignore[arg-type]

        resp = await svc.execute(
            req=ChatSendRequest(message="What does unknownthing do?", mode="reasoning"),
            msg="What does unknownthing do?",
            route=_FakeRoute(),
            rctx={},
            build_seat=_build_seat,
            ensure_lexicon_loaded=_noop_ensure,
        )

        assert resp is not None
        assert resp.answer_frame is not None
        assert resp.answer_frame["status"] == "no_anchor"
        assert resp.answer_frame["subject"] == "unknownthing"
        assert resp.answer_frame["suggested_next_mode"] is None

    asyncio.run(_run())


def test_reasoning_returns_stable_answer_frame_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        monkeypatch.setattr(reasoning_chat_module, "_log_message", lambda **_kwargs: {"message_id": "1"})
        answer = _FakeAnswer(
            subject="forest",
            predicates=[{"verb": "store", "object": "carbon", "confidence": 0.9}],
            confidence=0.9,
            reasoning_trace={"anchors_used": ["forest"]},
            surface_text="Forest: store carbon.",
        )
        state = _FakeState(
            reasoning_service=_AnsweringReasoning(answer),
            bridge=_FakeBridge(word_index={"forest": "0x1"}),
            config={},
        )
        svc = ReasoningChatService(state=state)  # type: ignore[arg-type]

        resp = await svc.execute(
            req=ChatSendRequest(message="What does forest do?", mode="reasoning"),
            msg="What does forest do?",
            route=_FakeRoute(),
            rctx={},
            build_seat=_build_seat,
            ensure_lexicon_loaded=_noop_ensure,
        )

        assert resp is not None
        assert resp.answer_frame == {
            "status": "ok",
            "subject": "forest",
            "predicates": [{"verb": "store", "object": "carbon", "confidence": 0.9}],
            "confidence": 0.9,
            "surface_text": "Forest: store carbon.",
            "query_mode": "what_does_x_do",
            "suggested_next_mode": None,
        }

    asyncio.run(_run())


def test_reasoning_returns_no_predicates_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _run() -> None:
        monkeypatch.setattr(reasoning_chat_module, "_log_message", lambda **_kwargs: {"message_id": "1"})
        answer = _FakeAnswer(
            subject="forest",
            predicates=[],
            confidence=0.0,
            reasoning_trace={},
            surface_text="No verb-like predicates found for forest.",
        )
        state = _FakeState(
            reasoning_service=_AnsweringReasoning(answer),
            bridge=_FakeBridge(word_index={"forest": "0x1"}),
            config={},
        )
        svc = ReasoningChatService(state=state)  # type: ignore[arg-type]

        resp = await svc.execute(
            req=ChatSendRequest(message="What does forest do?", mode="reasoning"),
            msg="What does forest do?",
            route=_FakeRoute(),
            rctx={},
            build_seat=_build_seat,
            ensure_lexicon_loaded=_noop_ensure,
        )

        assert resp is not None
        assert resp.answer_frame is not None
        assert resp.answer_frame["status"] == "no_predicates"
        assert resp.answer_frame["predicates"] == []
        assert resp.answer_frame["subject"] == "forest"
        assert "reliable action frame" in resp.response

    asyncio.run(_run())


def test_reasoning_returns_parked_contract() -> None:
    async def _run() -> None:
        state = _FakeState(
            reasoning_service=_MissingReasoning(subject="forest"),
            bridge=_FakeBridge(word_index={}),
            config={},
        )
        svc = ReasoningChatService(state=state)  # type: ignore[arg-type]

        resp = await svc.execute(
            req=ChatSendRequest(message="What does forest do?", mode="reasoning"),
            msg="What does forest do?",
            route=_FakeRoute(enabled_value=False),
            rctx={},
            build_seat=_build_seat,
            ensure_lexicon_loaded=_noop_ensure,
        )

        assert resp is not None
        assert resp.answer_frame is not None
        assert resp.answer_frame["status"] == "parked"
        assert resp.error is not None
        assert resp.error["type"] == "parked"

    asyncio.run(_run())
