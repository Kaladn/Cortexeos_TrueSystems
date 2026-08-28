"""Chat mode dispatcher service."""
from __future__ import annotations

from typing import Any, Set

from fastapi import Request

from bridges.models import ChatSendRequest, ChatSendResponse
from bridges.state import BridgeState, LOGGER
from bridges.services.llm_chat_service import LlmChatService
from bridges.services.multi_llm_chat_service import MultiLlmChatService
from bridges.services.reasoning_chat import ReasoningChatService


class ChatModeExecutor:
    """Dispatch chat requests to mode-owned services only."""

    def __init__(
        self,
        *,
        state: BridgeState,
        llm_service: LlmChatService | None = None,
        multi_llm_service: MultiLlmChatService | None = None,
        reasoning_service: ReasoningChatService | None = None,
    ) -> None:
        self.state = state
        self.llm_service = llm_service or LlmChatService(state=state)
        self.multi_llm_service = multi_llm_service
        self.reasoning_service = reasoning_service or ReasoningChatService(state=state)

    @staticmethod
    def _trace_id(request: Request) -> str | None:
        try:
            return request.headers.get("X-Trace-Id")
        except Exception:
            return None

    @staticmethod
    def _build_seat(provider: str, model: str, seat_id: str | None = None, node_id: str = "server") -> dict:
        return {"provider": provider, "model": model, "seat_id": seat_id, "node_id": node_id}

    async def _ensure_lexicon_loaded(self, reason: str) -> None:
        ensure_loaded = getattr(self.state, "ensure_bridge_loaded", None)
        if ensure_loaded is None:
            return
        await ensure_loaded(reason)

    async def execute(
        self,
        *,
        req: ChatSendRequest,
        msg: str,
        request: Request,
        route: Any,
        rctx: Any,
        original_mode: str,
        model_name: str,
    ) -> ChatSendResponse:
        trace_id = self._trace_id(request)
        branch = (req.side_chat_id or "").strip() or "main"

        if req.mode == "llm":
            return await self.llm_service.execute(
                req=req,
                msg=msg,
                model_name=model_name,
                route=route,
                rctx=rctx,
                original_mode=original_mode,
                trace_id=trace_id,
                branch=branch,
                build_seat=self._build_seat,
            )

        if req.mode == "reasoning":
            resp = await self.reasoning_service.execute(
                req=req,
                msg=msg,
                route=route,
                rctx=rctx,
                branch=branch,
                build_seat=self._build_seat,
                ensure_lexicon_loaded=self._ensure_lexicon_loaded,
            )
            if resp is not None:
                return resp

        if req.mode == "multi_llm":
            if not self.multi_llm_service:
                return ChatSendResponse(
                    mode=req.mode,
                    source="bridge_router",
                    response="",
                    reasoning_trace={"routing": route.telemetry_block(rctx)},
                    error={
                        "type": "misconfigured",
                        "message": "multi_llm service is not configured.",
                    },
                )
            return await self.multi_llm_service.execute(
                req=req,
                msg=msg,
                request=request,
                route=route,
                rctx=rctx,
            )

        LOGGER.warning("Unknown chat mode: %s", req.mode)
        return ChatSendResponse(
            mode=req.mode,
            source="bridge_router",
            response="",
            reasoning_trace={"routing": route.telemetry_block(rctx)},
            error={
                "type": "unknown_mode",
                "message": (
                    f"Unknown mode: {req.mode}. "
                    "Allowed base modes: llm, reasoning, multi_llm."
                ),
            },
        )
