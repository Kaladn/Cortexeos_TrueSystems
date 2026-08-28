"""Provider cloud chat mode service."""
from __future__ import annotations

from typing import Any

from Conversations.threads import log_message as _log_message
from bridges.helpers import _build_chat_messages
from bridges.models import ChatSendRequest, ChatSendResponse
from bridges.state import BridgeState
from security.provider_keys import get_provider_key as _prov_get_key


class ProviderChatService:
    """Owns OpenAI/Claude/Gemini/Grok mode execution."""

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
    ) -> ChatSendResponse | None:
        if req.mode == "openai":
            api_key = _prov_get_key("openai")
            if not api_key:
                return ChatSendResponse(
                    mode="openai",
                    source="bridge_router",
                    response="",
                    error={
                        "type": "not_configured",
                        "message": "OpenAI API key not configured. Add it in Connections.",
                    },
                )

            openai_model = "gpt-5"
            if req.model and req.model not in ("", "default") and req.model.startswith(("gpt-5", "o1", "o3", "o4")):
                openai_model = req.model

            try:
                reply, usage, latency_ms = await self.state.inference_service.call_openai(
                    api_key,
                    openai_model,
                    _build_chat_messages(msg),
                    req.inference_params,
                )
                if usage.get("error"):
                    return ChatSendResponse(
                        mode="openai",
                        source="openai_api",
                        response="",
                        error={
                            "type": "openai_error",
                            "message": f"OpenAI ({openai_model}) rejected request: {usage['error']}",
                        },
                    )

                persist_warn = False
                try:
                    user_log = _log_message(sender="user", content=msg)
                except Exception:
                    user_log = {}
                    persist_warn = True
                try:
                    ai_log = _log_message(
                        sender="ai",
                        content=reply,
                        model_identity={"provider": "openai", "model": openai_model, "engine": "responses"},
                    )
                except Exception:
                    ai_log = {}
                    persist_warn = True

                return ChatSendResponse(
                    mode="openai",
                    source="openai_api",
                    response=reply,
                    reasoning_trace={
                        "user_message_id": user_log.get("message_id"),
                        "ai_message_id": ai_log.get("message_id"),
                        "model": openai_model,
                        "usage": usage,
                        "latency_ms": latency_ms,
                        **({"persistence_warning": "Message may not have been saved"} if persist_warn else {}),
                    },
                    seat=build_seat("openai", openai_model),
                )
            except Exception as exc:
                return ChatSendResponse(
                    mode="openai",
                    source="openai_api",
                    response="",
                    error={"type": "connection_error", "message": f"OpenAI ({openai_model}): {exc}"},
                )

        if req.mode == "claude":
            api_key = _prov_get_key("claude")
            if not api_key:
                return ChatSendResponse(
                    mode="claude",
                    source="bridge_router",
                    response="",
                    error={
                        "type": "not_configured",
                        "message": "Claude API key not configured. Add it in Connections.",
                    },
                )

            claude_model = (
                req.model
                if (req.model and req.model not in ("", "default") and req.model.startswith("claude"))
                else "claude-sonnet-4-20250514"
            )

            try:
                reply, usage, latency_ms = await self.state.inference_service.call_claude(
                    api_key,
                    claude_model,
                    _build_chat_messages(msg),
                    req.inference_params,
                )
                if usage.get("error"):
                    return ChatSendResponse(
                        mode="claude",
                        source="anthropic_api",
                        response="",
                        error={
                            "type": "claude_error",
                            "message": f"Claude ({claude_model}) rejected request: {usage['error']}",
                        },
                    )

                persist_warn = False
                try:
                    user_log = _log_message(sender="user", content=msg)
                except Exception:
                    user_log = {}
                    persist_warn = True
                try:
                    ai_log = _log_message(
                        sender="ai",
                        content=reply,
                        model_identity={"provider": "anthropic", "model": claude_model, "engine": "messages"},
                    )
                except Exception:
                    ai_log = {}
                    persist_warn = True

                return ChatSendResponse(
                    mode="claude",
                    source="anthropic_api",
                    response=reply,
                    reasoning_trace={
                        "user_message_id": user_log.get("message_id"),
                        "ai_message_id": ai_log.get("message_id"),
                        "model": claude_model,
                        "usage": usage,
                        "latency_ms": latency_ms,
                        **({"persistence_warning": "Message may not have been saved"} if persist_warn else {}),
                    },
                    seat=build_seat("anthropic", claude_model),
                )
            except Exception as exc:
                return ChatSendResponse(
                    mode="claude",
                    source="anthropic_api",
                    response="",
                    error={"type": "connection_error", "message": f"Claude ({claude_model}): {exc}"},
                )

        if req.mode == "gemini":
            api_key = _prov_get_key("gemini")
            if not api_key:
                return ChatSendResponse(
                    mode="gemini",
                    source="bridge_router",
                    response="",
                    error={
                        "type": "not_configured",
                        "message": "Gemini API key not configured. Add it in Connections.",
                    },
                )

            gemini_default = route.config(rctx, "model_call", "gemini_model", "gemini-2.5-flash")
            gemini_model = req.model if (req.model and req.model not in ("", "default")) else gemini_default

            try:
                reply, usage, latency_ms = await self.state.inference_service.call_gemini(
                    api_key,
                    gemini_model,
                    _build_chat_messages(msg),
                    req.inference_params,
                )
                if usage.get("error"):
                    return ChatSendResponse(
                        mode="gemini",
                        source="gemini_api",
                        response="",
                        error={
                            "type": "gemini_error",
                            "message": f"Gemini ({gemini_model}) rejected request: {usage['error']}",
                        },
                    )

                persist_warn = False
                try:
                    user_log = _log_message(sender="user", content=msg)
                except Exception:
                    user_log = {}
                    persist_warn = True
                try:
                    ai_log = _log_message(
                        sender="ai",
                        content=reply,
                        model_identity={"provider": "google", "model": gemini_model, "engine": "generateContent"},
                    )
                except Exception:
                    ai_log = {}
                    persist_warn = True

                return ChatSendResponse(
                    mode="gemini",
                    source="gemini_api",
                    response=reply,
                    reasoning_trace={
                        "user_message_id": user_log.get("message_id"),
                        "ai_message_id": ai_log.get("message_id"),
                        "model": gemini_model,
                        "usage": usage,
                        "latency_ms": latency_ms,
                        "routing": route.telemetry_block(rctx),
                        **({"persistence_warning": "Message may not have been saved"} if persist_warn else {}),
                    },
                    seat=build_seat("google", gemini_model),
                )
            except Exception as exc:
                return ChatSendResponse(
                    mode="gemini",
                    source="gemini_api",
                    response="",
                    error={"type": "connection_error", "message": f"Gemini ({gemini_model}): {exc}"},
                )

        if req.mode == "grok":
            api_key = _prov_get_key("grok")
            if not api_key:
                return ChatSendResponse(
                    mode="grok",
                    source="bridge_router",
                    response="",
                    error={
                        "type": "not_configured",
                        "message": "xAI API key not configured. Add it in Connections.",
                    },
                )

            grok_model = "grok-3-fast"
            if req.model and req.model not in ("", "default") and req.model.startswith("grok"):
                grok_model = req.model

            try:
                reply, usage, latency_ms = await self.state.inference_service.call_grok(
                    api_key,
                    grok_model,
                    _build_chat_messages(msg),
                    req.inference_params,
                )
                if usage.get("error"):
                    return ChatSendResponse(
                        mode="grok",
                        source="xai_api",
                        response="",
                        error={
                            "type": "xai_error",
                            "message": f"Grok ({grok_model}) rejected request: {usage['error']}",
                        },
                    )

                persist_warn = False
                try:
                    user_log = _log_message(sender="user", content=msg)
                except Exception:
                    user_log = {}
                    persist_warn = True
                try:
                    ai_log = _log_message(
                        sender="ai",
                        content=reply,
                        model_identity={"provider": "xai", "model": grok_model, "engine": "chat_completions"},
                    )
                except Exception:
                    ai_log = {}
                    persist_warn = True

                return ChatSendResponse(
                    mode="grok",
                    source="xai_api",
                    response=reply,
                    reasoning_trace={
                        "user_message_id": user_log.get("message_id"),
                        "ai_message_id": ai_log.get("message_id"),
                        "model": grok_model,
                        "usage": usage,
                        "latency_ms": latency_ms,
                        "routing": route.telemetry_block(rctx),
                        **({"persistence_warning": "Message may not have been saved"} if persist_warn else {}),
                    },
                    seat=build_seat("xai", grok_model),
                )
            except Exception as exc:
                return ChatSendResponse(
                    mode="grok",
                    source="xai_api",
                    response="",
                    error={"type": "connection_error", "message": f"Grok ({grok_model}): {exc}"},
                )

        return None

