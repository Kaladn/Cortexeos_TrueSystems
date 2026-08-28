"""Chat pack mode service."""
from __future__ import annotations

import time
from typing import Any

from Conversations.threads import log_message as _log_message
from bridges.helpers import _safe_error
from bridges.models import ChatSendRequest, ChatSendResponse
from bridges.state import BridgeState, LOGGER


class ChatPackService:
    """Owns chat-pack mode orchestration and response shaping."""

    def __init__(self, *, state: BridgeState) -> None:
        self.state = state

    async def execute(
        self,
        *,
        req: ChatSendRequest,
        msg: str,
        model_name: str,
        route: Any,
        rctx: Any,
        ollama_base: str,
        build_seat,
    ) -> ChatSendResponse | None:
        if req.mode != "chat_pack":
            return None

        try:
            from core.chat_packs.api.router import get_engine as _get_cp_engine

            cp_engine = _get_cp_engine()
            cp_session_id = req.session_id or ""
            if not cp_session_id:
                trace = {"routing": route.telemetry_block(rctx)}
                return ChatSendResponse(
                    mode="chat_pack",
                    source="chat_packs",
                    response="",
                    reasoning_trace=trace,
                    error={"type": "no_session", "message": "No pack session active. Start a pack first."},
                )

            cp_session = cp_engine.get_session(cp_session_id)
            if not cp_session:
                trace = {"routing": route.telemetry_block(rctx)}
                return ChatSendResponse(
                    mode="chat_pack",
                    source="chat_packs",
                    response="",
                    reasoning_trace=trace,
                    error={"type": "no_session", "message": f"Session {cp_session_id} not found."},
                )

            cp_messages = cp_engine.build_messages(cp_session_id, msg)
            if not cp_messages:
                trace = {"routing": route.telemetry_block(rctx)}
                return ChatSendResponse(
                    mode="chat_pack",
                    source="chat_packs",
                    response="",
                    reasoning_trace=trace,
                    error={"type": "build_error", "message": "Failed to build messages for pack session."},
                )

            cp_payload = {
                "model": model_name,
                "messages": cp_messages,
                "stream": False,
                "keep_alive": "5m",
            }

            cp_inference_keys = {
                "temperature",
                "top_p",
                "top_k",
                "repeat_penalty",
                "frequency_penalty",
                "presence_penalty",
                "seed",
                "mirostat_mode",
                "mirostat_tau",
                "mirostat_eta",
            }
            cp_opts = {"num_gpu": -1}
            if req.inference_params:
                for key, value in req.inference_params.items():
                    if key in cp_inference_keys:
                        cp_opts[key] = value
                if "max_tokens" in req.inference_params:
                    cp_opts["num_predict"] = req.inference_params["max_tokens"]
            cp_payload["options"] = cp_opts

            persist_warn = False
            try:
                cp_user_log = _log_message(sender="user", content=msg, conversation_id=cp_session_id)
            except Exception as exc:
                LOGGER.warning("Chat Pack user log failed: %s", exc)
                cp_user_log = {}
                persist_warn = True

            cp_t0 = time.time()
            client = await self.state.get_ollama_client()
            cp_resp = await client.post(f"{ollama_base}/api/chat", json=cp_payload)
            cp_model_ms = int((time.time() - cp_t0) * 1000)
            route.record(rctx, "model_call", "model_call", True, ms=cp_model_ms)

            if not cp_resp.is_success:
                trace = {"routing": route.telemetry_block(rctx)}
                return ChatSendResponse(
                    mode="chat_pack",
                    source="chat_packs",
                    response="",
                    reasoning_trace=trace,
                    error={"type": "ollama_error", "status": cp_resp.status_code, "detail": cp_resp.text[:500]},
                )

            cp_data = cp_resp.json()
            cp_reply = cp_data.get("message", {}).get("content", "")

            cp_eval_count = cp_data.get("eval_count", 0)
            cp_eval_dur_ns = cp_data.get("eval_duration", 0)
            cp_perf = {
                "eval_count": cp_eval_count,
                "prompt_eval_count": cp_data.get("prompt_eval_count", 0),
                "eval_duration_ms": cp_eval_dur_ns // 1_000_000,
                "load_duration_ms": cp_data.get("load_duration", 0) // 1_000_000,
                "total_duration_ms": cp_data.get("total_duration", 0) // 1_000_000,
                "tokens_per_second": round(cp_eval_count / max(cp_eval_dur_ns / 1e9, 0.001), 1) if cp_eval_dur_ns else None,
            }

            try:
                cp_ai_log = _log_message(
                    sender="ai",
                    content=cp_reply,
                    model_identity={"provider": "ollama", "model": model_name, "engine": "chat_pack"},
                    conversation_id=cp_session_id,
                )
            except Exception as exc:
                LOGGER.warning("Chat Pack AI log failed: %s", exc)
                cp_ai_log = {}
                persist_warn = True

            cp_pack_id = cp_session.get("pack_id", "")
            return ChatSendResponse(
                mode="chat_pack",
                source="chat_packs",
                response=cp_reply,
                reasoning_trace={
                    "user_message_id": cp_user_log.get("message_id"),
                    "ai_message_id": cp_ai_log.get("message_id"),
                    "routing": route.telemetry_block(rctx),
                    "ollama": cp_perf,
                    **({"persistence_warning": "Message may not have been saved"} if persist_warn else {}),
                    "pack_session": {
                        "session_id": cp_session_id,
                        "pack_id": cp_pack_id,
                        "phase": cp_session.get("phase"),
                        "section_index": cp_session.get("section_index"),
                        "total_sections": cp_session.get("total_sections"),
                        "question_index": cp_session.get("question_index"),
                        "total_questions": cp_session.get("total_questions"),
                    },
                },
                seat=build_seat("ollama", model_name, "local"),
            )
        except ImportError:
            return ChatSendResponse(
                mode="chat_pack",
                source="bridge_router",
                response="Chat Packs service is not available.",
                reasoning_trace={"routing": route.telemetry_block(rctx)},
                error={"type": "not_available", "message": "Chat Packs service is not available"},
            )
        except Exception as exc:
            LOGGER.exception("Chat Pack mode error")
            return ChatSendResponse(
                mode="chat_pack",
                source="chat_packs",
                response="",
                reasoning_trace={"routing": route.telemetry_block(rctx)},
                error={"type": "chat_pack_error", "message": _safe_error(exc)},
            )
