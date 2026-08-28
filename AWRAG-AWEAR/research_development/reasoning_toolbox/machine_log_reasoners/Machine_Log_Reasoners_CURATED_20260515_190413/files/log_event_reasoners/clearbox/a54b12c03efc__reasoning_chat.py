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

    def _user_display_name(self) -> str | None:
        cfg = getattr(self.state, "config", {}) or {}
        profile = cfg.get("user_profile") or {}
        name = (profile.get("display_name") or "").strip()
        return name or None

    def _friendly_prefix(self) -> str:
        name = self._user_display_name()
        return f"Hey {name}, " if name else ""

    def _answer_frame(
        self,
        *,
        status: str,
        subject: str,
        response: str,
        predicates: list[dict] | None = None,
        confidence: float = 0.0,
        suggested_next_mode: str | None = None,
    ) -> dict[str, Any]:
        return {
            "status": status,
            "subject": subject,
            "predicates": predicates or [],
            "confidence": confidence,
            "surface_text": response,
            "query_mode": "what_does_x_do",
            "suggested_next_mode": suggested_next_mode,
        }

    async def execute(
        self,
        *,
        req: ChatSendRequest,
        msg: str,
        route: Any,
        rctx: Any,
        branch: str = "",
        build_seat,
        ensure_lexicon_loaded: Callable[[str], Awaitable[None]],
    ) -> ChatSendResponse | None:
        if req.mode != "reasoning":
            return None
        subject = self.state.reasoning_service.extract_subject(msg)

        if not route.enabled(rctx, "reasoning_engine"):
            route.record(rctx, "reasoning_engine", "reasoning_engine", False, ms=0, reason="stage_disabled")
            response = f"{self._friendly_prefix()}I'm glad you're interested. Reasoning mode is currently under development and may not be active yet."
            return ChatSendResponse(
                mode="reasoning",
                source="bridge_router",
                response=response,
                answer_frame=self._answer_frame(status="parked", subject=subject, response=response),
                reasoning_trace={"status": "parked", "routing": route.telemetry_block(rctx)},
                error={"type": "parked", "message": "Reasoning engine disabled in routing profile"},
            )

        t0_reasoning = time.time()
        try:
            answer = await self.state.reasoning_service.query_what_does_x_do(msg, req.topk)
            ms_reasoning = int((time.time() - t0_reasoning) * 1000)
            route.record(rctx, "reasoning_engine", "reasoning_engine", True, ms=ms_reasoning)
            reasoning_trace = answer.reasoning_trace or {}
            predicates = list(getattr(answer, "predicates", []) or [])
            contract_status = "ok" if predicates else "no_predicates"
            subject = getattr(answer, "subject", subject)
            if contract_status == "ok":
                surface = getattr(answer, "surface_text", "") or f"{subject.capitalize()}."
            else:
                surface = (
                    f"{self._friendly_prefix()}I found '{subject}', but I couldn't build a reliable action frame for it yet."
                )
            answer_frame = self._answer_frame(
                status=contract_status,
                subject=subject,
                response=surface,
                predicates=predicates,
                confidence=float(getattr(answer, "confidence", 0.0) or 0.0),
            )
            reasoning_trace["status"] = contract_status
        except HTTPException as http_exc:
            if http_exc.status_code == 404:
                await ensure_lexicon_loaded("reasoning-404-check")
                subject_lower = subject.lower().strip()
                lexicon_present = subject_lower in self.state.bridge.word_index
                status = "no_data" if lexicon_present else "no_anchor"
                suggested_next_mode = "llm" if lexicon_present else None
                msg_out = (
                    f"{self._friendly_prefix()}I'm glad you're interested. '{subject}' appears in the lexicon, but I don't have active reasoning map data for it yet."
                    if lexicon_present
                    else f"{self._friendly_prefix()}I'm glad you're interested. I don't have reasoning data for '{subject}' yet."
                )
                return ChatSendResponse(
                    mode="reasoning",
                    source="reasoning_engine",
                    response=msg_out,
                    answer_frame=self._answer_frame(
                        status=status,
                        subject=subject,
                        response=msg_out,
                        suggested_next_mode=suggested_next_mode,
                    ),
                    reasoning_trace={
                        "status": status,
                        "note": "anchor_not_found",
                        "subject": subject,
                        "lexicon_present": lexicon_present,
                        "suggested_next_mode": suggested_next_mode,
                        "routing": route.telemetry_block(rctx),
                    },
                    error=None,
                )
            error_message = f"Reasoning engine error: {http_exc.detail}"
            return ChatSendResponse(
                mode="reasoning",
                source="reasoning_engine",
                response=error_message,
                answer_frame=self._answer_frame(status="error", subject=subject, response=error_message),
                reasoning_trace={"status": "error", "routing": route.telemetry_block(rctx)},
                error={"type": "engine_error", "message": str(http_exc.detail)},
            )
        except Exception as exc:
            LOGGER.exception("Reasoning engine query failed")
            error_message = f"Reasoning engine error: {exc}"
            return ChatSendResponse(
                mode="reasoning",
                source="reasoning_engine",
                response=error_message,
                answer_frame=self._answer_frame(status="error", subject=subject, response=error_message),
                reasoning_trace={"status": "error", "routing": route.telemetry_block(rctx)},
                error={"type": "engine_error", "message": _safe_error(exc)},
            )

        persist_warn = False
        user_log: dict[str, Any] = {}
        ai_log: dict[str, Any] = {}
        try:
            user_log = _log_message(sender="user", content=msg, branch=branch)
        except Exception as exc:
            LOGGER.warning("Reasoning user log failed: %s", exc)
            persist_warn = True
        try:
            ai_log = _log_message(
                sender="ai",
                content=surface,
                branch=branch,
                model_identity={"provider": "reasoning_engine", "model": "616", "engine": "reasoning"},
            )
        except Exception as exc:
            LOGGER.warning("Reasoning AI log failed: %s", exc)
            persist_warn = True

        reasoning_trace["user_message_id"] = user_log.get("message_id")
        reasoning_trace["ai_message_id"] = ai_log.get("message_id")
        reasoning_trace["routing"] = route.telemetry_block(rctx)
        if persist_warn:
            reasoning_trace["persistence_warning"] = "Message may not have been saved"
        return ChatSendResponse(
            mode="reasoning",
            source="reasoning_engine",
            response=surface,
            answer_frame=answer_frame,
            reasoning_trace=reasoning_trace,
            error=None,
            seat=build_seat("reasoning_engine", "616"),
        )
