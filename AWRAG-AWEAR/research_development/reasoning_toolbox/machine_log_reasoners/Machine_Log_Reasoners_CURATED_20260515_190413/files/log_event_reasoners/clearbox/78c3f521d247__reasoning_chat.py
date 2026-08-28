"""Reasoning mode service."""
from __future__ import annotations

import time
from typing import Any, Awaitable, Callable

from Conversations.threads import log_message as _log_message
from fastapi import HTTPException

from bridges.helpers import _safe_error
from bridges.models import ChatSendRequest, ChatSendResponse
from bridges.state import BridgeState, LOGGER


class ReasoningChatService:
    """Owns reasoning mode execution and fallback behavior."""

    def __init__(self, *, state: BridgeState) -> None:
        self.state = state

    async def execute(
        self,
        *,
        req: ChatSendRequest,
        msg: str,
        route: Any,
        rctx: Any,
        build_seat,
        ensure_lexicon_loaded: Callable[[str], Awaitable[None]],
    ) -> ChatSendResponse | None:
        if req.mode != "reasoning":
            return None

        if not route.enabled(rctx, "reasoning_engine"):
            route.record(rctx, "reasoning_engine", "reasoning_engine", False, ms=0, reason="stage_disabled")
            return ChatSendResponse(
                mode="reasoning",
                source="bridge_router",
                response="Reasoning engine is currently parked.",
                reasoning_trace={"routing": route.telemetry_block(rctx)},
                error={"type": "parked", "message": "Reasoning engine disabled in routing profile"},
            )

        t0_reasoning = time.time()
        try:
            answer = await self.state.reasoning_service.query_what_does_x_do(msg, req.topk)
            ms_reasoning = int((time.time() - t0_reasoning) * 1000)
            route.record(rctx, "plugin_chain", "plugin_chain", True, ms=ms_reasoning)
            surface = answer.surface_text
            reasoning_trace = answer.reasoning_trace or {}
        except HTTPException as http_exc:
            if http_exc.status_code == 404:
                await ensure_lexicon_loaded("reasoning-404-check")
                term_lower = msg.lower().strip()
                lexicon_present = term_lower in self.state.bridge.word_index
                msg_out = (
                    f"No map hits for '{msg}', although it does appear in the lexicon. Would you like to query the LLM?"
                    if lexicon_present
                    else "No map data for that term yet."
                )
                return ChatSendResponse(
                    mode="reasoning",
                    source="reasoning_engine",
                    response=msg_out,
                    answer_frame=None,
                    reasoning_trace={
                        "note": "anchor_not_found",
                        "lexicon_present": lexicon_present,
                        "suggested_next_mode": "llm" if lexicon_present else None,
                        "routing": route.telemetry_block(rctx),
                    },
                    error=None,
                )
            return ChatSendResponse(
                mode="reasoning",
                source="reasoning_engine",
                response=f"Reasoning engine error: {http_exc.detail}",
                reasoning_trace={"routing": route.telemetry_block(rctx)},
                error={"type": "engine_error", "message": str(http_exc.detail)},
            )
        except Exception as exc:
            LOGGER.exception("Reasoning engine query failed")
            return ChatSendResponse(
                mode="reasoning",
                source="reasoning_engine",
                response=f"Reasoning engine error: {exc}",
                reasoning_trace={"routing": route.telemetry_block(rctx)},
                error={"type": "engine_error", "message": _safe_error(exc)},
            )

        persist_warn = False
        try:
            _log_message(sender="user", content=msg)
        except Exception as exc:
            LOGGER.warning("Reasoning user log failed: %s", exc)
            persist_warn = True
        try:
            _log_message(
                sender="ai",
                content=surface,
                model_identity={"provider": "reasoning_engine", "model": "616", "engine": "reasoning"},
            )
        except Exception as exc:
            LOGGER.warning("Reasoning AI log failed: %s", exc)
            persist_warn = True

        reasoning_trace["routing"] = route.telemetry_block(rctx)
        if persist_warn:
            reasoning_trace["persistence_warning"] = "Message may not have been saved"
        return ChatSendResponse(
            mode="reasoning",
            source="reasoning_engine",
            response=surface,
            answer_frame=answer.__dict__,
            reasoning_trace=reasoning_trace,
            error=None,
            seat=build_seat("reasoning_engine", "616"),
        )

