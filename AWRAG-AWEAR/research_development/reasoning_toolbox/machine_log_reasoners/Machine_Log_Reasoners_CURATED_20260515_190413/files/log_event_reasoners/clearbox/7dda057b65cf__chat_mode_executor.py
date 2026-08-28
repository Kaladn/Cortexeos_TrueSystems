"""Chat mode dispatcher service."""
from __future__ import annotations

from typing import Any, Set

from fastapi import Request

from bridges.models import ChatSendRequest, ChatSendResponse
from bridges.services.plugin_gateway import PluginGatewayService
from bridges.state import BridgeState, LOGGER
from bridges.services.grounded_chat_service import GroundedChatService
from bridges.services.llm_chat_service import LlmChatService
from bridges.services.multi_llm_chat_service import MultiLlmChatService


class ChatModeExecutor:
    """Dispatch chat requests to mode-owned services only."""

    def __init__(
        self,
        *,
        state: BridgeState,
        mounted_plugins: Set[str] | None = None,
        llm_service: LlmChatService | None = None,
        grounded_service: GroundedChatService | None = None,
        multi_llm_service: MultiLlmChatService | None = None,
        plugin_gateway: PluginGatewayService | None = None,
    ) -> None:
        self.state = state
        self._mounted_plugins = mounted_plugins if mounted_plugins is not None else set()
        self.plugin_gateway = plugin_gateway or PluginGatewayService(
            state=state,
            mounted_plugins=self._mounted_plugins,
        )
        self.llm_service = llm_service or LlmChatService(state=state)
        self.grounded_service = grounded_service or GroundedChatService(
            state=state,
            plugin_gateway=self.plugin_gateway,
        )
        self.multi_llm_service = multi_llm_service

    @staticmethod
    def _trace_id(request: Request) -> str | None:
        try:
            return request.headers.get("X-Trace-Id")
        except Exception:
            return None

    @staticmethod
    def _build_seat(provider: str, model: str, seat_id: str | None = None, node_id: str = "server") -> dict:
        return {"provider": provider, "model": model, "seat_id": seat_id, "node_id": node_id}

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

        if req.mode == "grounded":
            return await self.grounded_service.execute(
                req=req,
                msg=msg,
                model_name=model_name,
                route=route,
                rctx=rctx,
                branch=branch,
                build_seat=self._build_seat,
            )

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
                    "Allowed base modes: llm, grounded, multi_llm."
                ),
            },
        )
