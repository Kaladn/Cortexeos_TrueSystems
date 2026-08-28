"""Chat chain executor and chat/load routes."""
from __future__ import annotations

from typing import Any, Dict, Set, cast

from fastapi import APIRouter, Request

from bridges.state import BridgeState, LOGGER, VERSION
from bridges.models import ChatSendRequest, ChatSendResponse, LoadRequest
from bridges.helpers import DEFAULT_MODEL
from bridges.services.chain_executor import ChainExecutor
from bridges.services.chat_mode_executor import ChatModeExecutor
from bridges.services.chat_routing_service import ChatRoutingService
from bridges.services.multi_llm_chat_service import MultiLlmChatService
from bridges.ws_manager import WebSocketManager
from bridges.helpers import RouteEngine, load_routing_profile


def make_router(
    state: BridgeState,
    ws_manager: WebSocketManager,
) -> APIRouter:
    router = APIRouter()

    chain_executor = ChainExecutor(
        state=state,
        ws_manager=ws_manager,
        inference_service=state.inference_service,
        reasoning_service=state.reasoning_service,
    )
    multi_llm_service = MultiLlmChatService(chain_executor=chain_executor)
    mode_executor = ChatModeExecutor(
        state=state,
        multi_llm_service=multi_llm_service,
    )
    chat_routing = ChatRoutingService()

    @router.post("/api/chat/send", response_model=ChatSendResponse)
    async def chat_send(req: ChatSendRequest, request: Request):
        """
        Unified chat router. All modes route through their owning server.
        LLM mode → local_llm_server (owns logging, history, citations, identity).
        """
        msg = (req.message or "").strip()
        if not msg:
            return ChatSendResponse(
                mode=req.mode, source="bridge_router", response="",
                error={"type": "bad_request", "message": "Empty message"}
            )

        normalized_mode, mapped_from, mode_error = chat_routing.normalize_mode(req.mode)
        if mode_error:
            return ChatSendResponse(
                mode=req.mode,
                source="bridge_router",
                response="",
                error=mode_error,
            )
        req.mode = normalized_mode

        # ── Routing telemetry (authority disarmed — hub model is sole source) ──
        _route_profile = load_routing_profile(state.config.get("routing"))
        route = RouteEngine(_route_profile)
        rctx = route.prepare(req.mode, msg)
        if mapped_from:
            route.record(
                rctx, "legacy_mode_map", "legacy_mode_map", True, ms=0,
                mapped_from=mapped_from, mapped_to=req.mode,
            )

        # ── Model resolution: Hub model is sole authority ──────────
        _original_mode = req.mode
        _model_name = req.local_model or req.model or DEFAULT_MODEL

        payload_error = chat_routing.validate_payload(req)
        if payload_error:
            return ChatSendResponse(
                mode=req.mode,
                source="bridge_router",
                response="",
                reasoning_trace={"routing": route.telemetry_block(rctx)},
                error=payload_error,
            )

        return await mode_executor.execute(
            req=req,
            msg=msg,
            request=request,
            route=route,
            rctx=rctx,
            original_mode=_original_mode,
            model_name=_model_name,
        )

    @router.post("/api/load")
    async def post_load(body: LoadRequest):
        overrides = cast(Dict[str, Any], body.dict(exclude_none=True))
        stats = await state.reload(overrides or None)
        await ws_manager.broadcast({
            "evt": "reload",
            "version": VERSION,
            "device": stats.get("device_name"),
            "entries": stats.get("entries"),
        })
        return stats

    return router
