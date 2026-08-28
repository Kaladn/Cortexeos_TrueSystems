"""Debug, tools, plugins, AI briefs, control, and history queue routes."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel
from bridges.helpers import RouteEngine, load_routing_profile

from bridges.helpers import DEFAULT_MODEL
from bridges.models import ChatSendRequest, ChatSendResponse
from bridges.services.chat_mode_executor import ChatModeExecutor
from bridges.services.ai_briefs import AIBriefService
from bridges.services.control_tools import ControlToolService
from bridges.services.history_queue import HistoryQueueService
from bridges.state import BridgeState
from core.tool_creation import record_factory_turn


_TOOL_FACTORY_CONTRACT = (
    "You are collaborating with the user to design a Clearbox tool. "
    "Stay strictly in design mode. Never call tools, never emit tool_call syntax, "
    "and never ask the runtime to execute commands on your behalf. "
    "Help the user refine the tool name, description, hint, params, safety level, "
    "runner shape, and test plan. Ask concise clarifying questions when needed."
)

_HELP_CHAT_CONTRACT = (
    "You are Clearbox Help Guide. "
    "Use only the provided HELP DATA CONTEXT. "
    "Do not invent UI panels, endpoints, routes, files, or behaviors that are not present in that context. "
    "Never call tools, never emit tool_call syntax, and never claim runtime state you were not given. "
    "If the answer is not supported by the provided help data, say that it is not documented yet. "
    "Prefer short, concrete answers with direct references to the relevant help ids when useful."
)


class HelpChatRequest(ChatSendRequest):
    focus_help_id: str | None = None


def _build_help_chat_context(message: str, focus_help_id: str | None) -> tuple[str, dict]:
    from core.help_system.api.router import get_engine

    engine = get_engine()
    bundle = engine.build_assistant_context(
        query=message,
        focus_help_id=(focus_help_id or "").strip() or None,
        limit=6,
    )
    contract = (
        f"{_HELP_CHAT_CONTRACT}\n\n"
        "HELP DATA CONTEXT (authoritative, deterministic):\n"
        f"{json.dumps(bundle, indent=2, ensure_ascii=False)}"
    )
    return contract, bundle


def make_router(
    state: BridgeState,
) -> APIRouter:
    """Create the control router."""
    router = APIRouter()

    ai_briefs = AIBriefService(base_dir=Path(__file__).resolve().parent.parent.parent)
    control_tools = ControlToolService()
    tool_factory_executor = ChatModeExecutor(state=state)
    help_chat_executor = ChatModeExecutor(state=state)
    history_queue = HistoryQueueService()

    @router.get("/api/tools")
    async def list_tools():
        return control_tools.list_tools()

    @router.get("/api/tools/{name}")
    async def get_tool(name: str):
        return control_tools.get_tool(name)

    @router.post("/api/tools")
    async def create_or_update_tool(request: Request):
        data = await request.json()
        return control_tools.save_tool(data)

    @router.delete("/api/tools/{name}")
    async def delete_tool(name: str):
        return control_tools.delete_tool(name)

    @router.post("/api/tools/{name}/test")
    async def test_tool(name: str, request: Request):
        body = await request.json()
        return await control_tools.test_tool(name, body.get("arguments", {}))

    @router.post("/api/tools/reload")
    async def reload_tools():
        return control_tools.reload_tools()

    @router.post("/api/tools/factory/chat", response_model=ChatSendResponse)
    async def tool_factory_chat(req: ChatSendRequest, request: Request):
        msg = (req.message or "").strip()
        if not msg:
            return ChatSendResponse(
                mode="llm",
                source="tool_factory",
                response="",
                error={"type": "bad_request", "message": "Empty message"},
            )

        req.mode = "llm"
        req.tools_enabled = False
        req.session_id = (req.session_id or "tool_factory").strip() or "tool_factory"

        extra_rules = (req.generation_contract or "").strip()
        req.generation_contract = (
            _TOOL_FACTORY_CONTRACT
            if not extra_rules
            else f"{_TOOL_FACTORY_CONTRACT}\n\nAdditional session rules:\n{extra_rules}"
        )

        route = RouteEngine(load_routing_profile(state.config.get("routing")))
        rctx = route.prepare(req.mode, msg)
        model_name = req.local_model or req.model or DEFAULT_MODEL

        try:
            resp = await tool_factory_executor.execute(
                req=req,
                msg=msg,
                request=request,
                route=route,
                rctx=rctx,
                original_mode="llm",
                model_name=model_name,
            )
        except Exception as exc:
            record_factory_turn(
                session_id=req.session_id,
                side_chat_id=req.side_chat_id,
                provider=req.hub_provider or "ollama",
                model=model_name,
                user_message=msg,
                response_text="",
                error_text=str(exc),
            )
            raise

        trace = dict(resp.reasoning_trace or {})
        trace["tool_factory"] = {
            "tools_forced_off": True,
            "session_id": req.session_id,
            "side_chat_id": req.side_chat_id,
            "provider": req.hub_provider or "ollama",
        }
        resp.reasoning_trace = trace
        record_factory_turn(
            session_id=req.session_id,
            side_chat_id=req.side_chat_id,
            provider=req.hub_provider or "ollama",
            model=model_name,
            user_message=msg,
            response_text=resp.response or "",
            error_text=(resp.error or {}).get("message") if resp.error else None,
            reasoning_trace=trace,
        )
        return resp

    @router.post("/api/help/chat", response_model=ChatSendResponse)
    async def help_chat(req: HelpChatRequest, request: Request):
        msg = (req.message or "").strip()
        if not msg:
            return ChatSendResponse(
                mode="llm",
                source="help_guide",
                response="",
                error={"type": "bad_request", "message": "Empty message"},
            )

        req.mode = "llm"
        req.tools_enabled = False
        req.session_id = (req.session_id or "help_guide").strip() or "help_guide"
        help_contract, help_bundle = _build_help_chat_context(msg, req.focus_help_id)
        extra_rules = (req.generation_contract or "").strip()
        req.generation_contract = (
            help_contract
            if not extra_rules
            else f"{help_contract}\n\nAdditional session rules:\n{extra_rules}"
        )

        route = RouteEngine(load_routing_profile(state.config.get("routing")))
        rctx = route.prepare(req.mode, msg)
        model_name = req.local_model or req.model or DEFAULT_MODEL

        resp = await help_chat_executor.execute(
            req=req,
            msg=msg,
            request=request,
            route=route,
            rctx=rctx,
            original_mode="llm",
            model_name=model_name,
        )

        trace = dict(resp.reasoning_trace or {})
        trace["help_assistant"] = {
            "tools_forced_off": True,
            "session_id": req.session_id,
            "side_chat_id": req.side_chat_id,
            "provider": req.hub_provider or "ollama",
            "focus_help_id": req.focus_help_id,
            "provided_help_ids": [entry.get("help_id") for entry in help_bundle.get("entries", [])],
        }
        resp.reasoning_trace = trace
        return resp

    # ── 6-1-6 Experimental Reasoning ────────────────────────────
    @router.post("/api/reasoning/616")
    async def reasoning_616(request: Request):
        body = await request.json()
        question = (body.get("question") or "").strip()
        if not question:
            return {"error": "question is required"}
        from bridges.services.reasoning_service import ReasoningService
        svc = ReasoningService()
        frame = await svc.query(question, top_k=body.get("top_k", 8))
        return {
            "subject": frame.subject,
            "intent": frame.intent,
            "clouds": frame.clouds,
            "predicates": frame.predicates,
            "causes": frame.causes,
            "relations": frame.relations,
            "cascade_paths": frame.cascade_paths,
            "lake_hits": frame.lake_hits,
            "confidence": frame.confidence,
            "surface_text": frame.surface_text,
            "trace": frame.trace,
        }

    @router.get("/api/ai-briefs")
    async def list_ai_briefs():
        return ai_briefs.list_briefs()

    @router.get("/api/ai-briefs/for-provider/{provider}")
    async def get_brief_for_provider(provider: str):
        return ai_briefs.get_for_provider(provider)

    @router.get("/api/ai-briefs/pin-status")
    async def brief_pin_status():
        return ai_briefs.pin_status()

    @router.post("/api/ai-briefs/pin")
    async def pin_brief_to_session(request: Request):
        body = await request.json()
        return ai_briefs.pin_for_provider(body.get("provider", ""))

    @router.get("/api/ai-briefs/{name}")
    async def get_ai_brief(name: str):
        return ai_briefs.get_brief(name)

    @router.get("/api/control/tool-policy/{model:path}")
    async def get_tool_policy(model: str):
        return control_tools.get_tool_policy(model)

    @router.post("/api/control/tool-policy/{model:path}")
    async def save_tool_policy(model: str, request: Request):
        body = await request.json()
        return control_tools.save_tool_policy(model, body.get("allowed", []))

    @router.get("/api/control/tool-telemetry")
    async def get_tool_telemetry():
        return control_tools.tool_telemetry()

    @router.get("/api/control/tool-telemetry/raw")
    async def get_tool_telemetry_raw(lines: int = 100):
        return control_tools.tool_telemetry_raw(lines)

    @router.post("/api/history/queue/log")
    async def history_queue_log(request: Request):
        body = await request.json()
        return history_queue.log_event(body)

    @router.get("/api/history/queue/ledger")
    async def history_queue_ledger(limit: int = 100):
        return history_queue.ledger(limit)

    return router
