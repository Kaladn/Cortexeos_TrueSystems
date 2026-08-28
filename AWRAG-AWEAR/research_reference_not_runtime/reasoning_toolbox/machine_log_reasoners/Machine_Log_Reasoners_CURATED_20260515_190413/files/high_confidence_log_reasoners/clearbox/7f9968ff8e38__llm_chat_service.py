"""Single-model local LLM chat service."""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Callable

from Conversations.threads import log_message as _log_message
from bridges.helpers import _build_chat_messages, _get_todays_pinned_digest, _safe_error
from bridges.models import ChatSendRequest, ChatSendResponse
from bridges.state import BridgeState, LOGGER
from security.runtime_log import debug_enter
from security.data_paths import CLEARBOX_CONFIG_PATH

_DEFAULT_ARCHIVE_INSTRUCTION = (
    "The user may include retrieved messages from their personal chat archive. "
    "Use these as supporting context when relevant. "
    "Answer using your full reasoning and general knowledge. "
    "Only say you don't know when the question is genuinely unknowable."
)


def _load_global_config() -> dict:
    """Load identity, user_profile, archive_instruction from clearbox.config.json."""
    if not CLEARBOX_CONFIG_PATH.exists():
        return {}
    try:
        with open(CLEARBOX_CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _build_system_prompt(model_name: str) -> str:
    """Build system prompt: per-model identity → global identity → default.

    Mirrors the reference implementation in local_llm_server.py.
    """
    cfg = _load_global_config()

    # Per-model identity profile (encrypted, takes precedence)
    per_model = None
    try:
        from security.identity_profiles import load_profile as _load_ident
        per_model = _load_ident(model_name)
    except Exception:
        pass

    parts = []

    # Identity role
    if per_model and per_model.get("identity_role"):
        parts.append(per_model["identity_role"])
    elif cfg.get("identity", {}).get("role"):
        parts.append(cfg["identity"]["role"])
    else:
        parts.append("You are a helpful assistant.")

    # User profile
    user_profile = cfg.get("user_profile")
    if user_profile:
        profile_lines = []
        for key in ("display_name", "role", "context", "style", "level", "notes"):
            val = user_profile.get(key)
            if val:
                profile_lines.append(f"{key.replace('_', ' ').title()}: {val}")
        if profile_lines:
            parts.append("USER PROFILE:\n" + "\n".join(profile_lines))

    # Archive instruction
    if per_model and per_model.get("archive_instruction"):
        parts.append(per_model["archive_instruction"])
    else:
        parts.append(cfg.get("archive_instruction") or _DEFAULT_ARCHIVE_INSTRUCTION)

    # Clock
    parts.append(f"Current time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    return "\n\n".join(parts)


class LlmChatService:
    """Owns local `llm` mode execution without routing concerns."""

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
        original_mode: str,
        trace_id: str | None,
        branch: str,
        build_seat: Callable[[str, str, str | None, str], dict[str, Any]],
    ) -> ChatSendResponse:
        state = self.state
        _persist_warn = False

        # ── Non-Ollama hub provider: route through InferenceService ──
        _hub_provider = (req.hub_provider or "ollama").strip()
        if _hub_provider and _hub_provider != "ollama":
            return await self._execute_api_provider(
                req=req, msg=msg, model_name=model_name,
                provider=_hub_provider, route=route, rctx=rctx,
                original_mode=original_mode, trace_id=trace_id,
                branch=branch, build_seat=build_seat,
            )

        OLLAMA_BASE = state.get_ollama_base_url()

        # Log user message
        try:
            user_log = _log_message(sender="user", content=msg, branch=branch)
        except Exception as e:
            LOGGER.warning(f"User log failed: {e}")
            user_log = {}
            _persist_warn = True

        retrieval_hits = None  # LLM mode has no retrieval

        # Build messages with system prompt (identity + user profile)
        messages = _build_chat_messages(msg, branch=branch)
        system_prompt = _build_system_prompt(model_name)
        # Append generation contract rules if present
        if req.generation_contract:
            system_prompt += f"\n\n## Generation Rules\n{req.generation_contract}"
        # Insert system prompt as first message (before AI_BRIEF if present)
        messages.insert(0, {"role": "system", "content": system_prompt})

        ollama_payload = {
            "model": model_name,
            "messages": messages,
            "stream": False,
            "keep_alive": "5m",
        }

        # Resolve inference params: request → per-model profile → defaults
        _INFERENCE_KEYS = {
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
        # GPU offload: -1 = all layers to GPU (avoid CPU/GPU blend)
        _opts = {"num_gpu": -1}

        # Layer 1: per-model saved profile (fallback)
        _saved_profile = None
        try:
            from security.inference_profiles import load_profile as _load_inf
            _saved_profile = _load_inf(model_name)
        except Exception:
            pass
        if _saved_profile:
            for k, v in _saved_profile.items():
                if k in _INFERENCE_KEYS:
                    _opts[k] = v
                if k == "max_tokens":
                    _opts["num_predict"] = v

        # Layer 2: request params override saved profile
        if req.inference_params:
            for k, v in req.inference_params.items():
                if k in _INFERENCE_KEYS:
                    _opts[k] = v
            if "max_tokens" in req.inference_params:
                _opts["num_predict"] = req.inference_params["max_tokens"]
        ollama_payload["options"] = _opts

        # Server-side tools policy: config can disable tools regardless of client flag
        _server_tools_allowed = state.config.get("tools_enabled", True)
        _tools_active = req.tools_enabled and _server_tools_allowed
        if req.tools_enabled and not _server_tools_allowed:
            LOGGER.info(f"[{trace_id}] tools_enabled overridden by server policy")

        # Use native Ollama tools API — avoids prompt injection conflicts
        # with models (e.g. qwen2.5) that have built-in tool templates.
        # Path B in the response handler picks up tool_calls from the response.
        _tool_trace = []
        if _tools_active:
            from bridges.tool_defs import TOOL_DEFINITIONS

            if TOOL_DEFINITIONS:
                ollama_payload["tools"] = TOOL_DEFINITIONS

        # Non-injection receipt: log AI brief status (proves brief is NOT in prompt prefix)
        _pinned_digest = _get_todays_pinned_digest()
        _brief_pinned = _pinned_digest is not None
        debug_enter(
            "http",
            "chat/brief_receipt",
            extra={  # DEBUGWIRE:HTTP
                "ai_brief_pinned": _brief_pinned,
                "ai_brief_source": "thread_note" if _brief_pinned else "none",
                "ai_brief_chars": len(_pinned_digest) if _pinned_digest else 0,
            },
        )

        try:
            # Stage: model_call
            t0_model = time.time()
            client = await state.get_ollama_client()
            r = await client.post(f"{OLLAMA_BASE}/api/chat", json=ollama_payload)
            _model_ms = int((time.time() - t0_model) * 1000)

            if not r.is_success:
                route.record(rctx, "model_call", "model_call", True, ms=_model_ms)
                return ChatSendResponse(
                    mode=original_mode,
                    source="ollama",
                    response="",
                    reasoning_trace={"routing": route.telemetry_block(rctx)},
                    error={"type": "ollama_error", "status": r.status_code, "detail": r.text[:500]},
                )

            route.record(rctx, "model_call", "model_call", True, ms=_model_ms)

            data = r.json()
            resp_message = data.get("message", {})
            reply = resp_message.get("content", "")

            # Handle tool calls when tools are enabled
            # Path A: prompt-based (any format in content — gemma3, etc.)
            # Path B: native tool_calls array (thinking models — gpt-oss)
            _parsed_tools = []
            if _tools_active:
                from bridges.tool_defs import execute_tool, parse_tool_calls, strip_tool_calls

                # Path A: parse all known formats from content
                if reply:
                    _parsed_tools = parse_tool_calls(reply)

                # Path B: native tool_calls (thinking models emit these)
                if not _parsed_tools and resp_message.get("tool_calls"):
                    for tc in resp_message["tool_calls"][:3]:
                        fn = tc.get("function", {})
                        fn_name = fn.get("name", "")
                        # Strip "tool." prefix (gpt-oss quirk)
                        if fn_name.startswith("tool."):
                            fn_name = fn_name[5:]
                        fn_args = fn.get("arguments", {})
                        if fn_name:
                            _parsed_tools.append(
                                {
                                    "name": fn_name,
                                    "arguments": fn_args if isinstance(fn_args, dict) else {},
                                }
                            )

            # Execute at most ONE tool per round
            if _parsed_tools:
                _parsed_tools = _parsed_tools[:1]

            if _parsed_tools:
                from bridges.tool_defs import strip_tool_calls

                # Save the prose portion (without tags) as fallback
                _first_reply_clean = strip_tool_calls(reply) if reply else ""

                messages = ollama_payload["messages"]
                # Append the CLEAN assistant text (no raw tags in context)
                messages.append({"role": "assistant", "content": _first_reply_clean or "(calling tool)"})

                for tc in _parsed_tools:
                    t0_tool = time.time()
                    result_str = await execute_tool(
                        tc["name"],
                        tc["arguments"],
                        session_id=req.session_id,
                        model_name=model_name,
                    )
                    _tool_ms = int((time.time() - t0_tool) * 1000)
                    _tool_trace.append(
                        {
                            "tool": tc["name"],
                            "args": tc["arguments"],
                            "ms": _tool_ms,
                            "result_preview": result_str[:200],
                        }
                    )
                    # L4: persist reasoning trace
                    try:
                        from Conversations.threads.reasoning_log import log_tool_call
                        log_tool_call(model_name, tc["name"], tc["arguments"], result_str[:200], _tool_ms)
                    except Exception:
                        pass
                    messages.append(
                        {
                            "role": "system",
                            "content": f"[TOOL RESULT — {tc['name']}]\n{result_str}\n[END TOOL RESULT]\nNow summarize this result for the user. Do NOT call another tool.",
                        }
                    )

                # Second LLM call — model summarizes tool results
                # Remove tools from payload: summary call must not trigger another tool round
                _summary_payload = {k: v for k, v in ollama_payload.items() if k != "tools"}
                _summary_payload["messages"] = messages
                client = await state.get_ollama_client()
                r2 = await client.post(f"{OLLAMA_BASE}/api/chat", json=_summary_payload)
                if r2.is_success:
                    data = r2.json()
                    _second_reply = data.get("message", {}).get("content", "")
                    # Use second call if it produced content, else fallback to stripped first
                    reply = _second_reply if _second_reply.strip() else _first_reply_clean
                else:
                    reply = _first_reply_clean

            # Always strip any tool call artifacts from final reply
            # (covers <tool_call> tags, ```tool_call=```, bare tool_call=, etc.)
            if reply and ("tool_call" in reply or "<tool_call>" in reply):
                from bridges.tool_defs import strip_tool_calls

                reply = strip_tool_calls(reply)

            # Extract Ollama performance metadata
            _eval_count = data.get("eval_count", 0)
            _eval_dur_ns = data.get("eval_duration", 0)
            _prompt_count = data.get("prompt_eval_count", 0)
            _load_dur_ns = data.get("load_duration", 0)
            _total_dur_ns = data.get("total_duration", 0)
            _ollama_perf = {
                "eval_count": _eval_count,
                "prompt_eval_count": _prompt_count,
                "eval_duration_ms": _eval_dur_ns // 1_000_000,
                "load_duration_ms": _load_dur_ns // 1_000_000,
                "total_duration_ms": _total_dur_ns // 1_000_000,
                "tokens_per_second": round(_eval_count / max(_eval_dur_ns / 1e9, 0.001), 1) if _eval_dur_ns else None,
            }

            # Log AI response
            try:
                ai_log = _log_message(
                    sender="ai",
                    content=reply,
                    branch=branch,
                    model_identity={
                        "provider": "ollama",
                        "model": model_name,
                        "engine": "generate",
                    },
                )
            except Exception as e:
                LOGGER.warning(f"AI log failed: {e}")
                ai_log = {}
                _persist_warn = True

            return ChatSendResponse(
                mode=original_mode,
                source="ollama",
                response=reply,
                answer_frame=None,
                reasoning_trace={
                    "user_message_id": user_log.get("message_id"),
                    "ai_message_id": ai_log.get("message_id"),
                    "routing": route.telemetry_block(rctx),
                    "ollama": _ollama_perf,
                    **({"tool_calls": _tool_trace} if _tool_trace else {}),
                    **({"persistence_warning": "Message may not have been saved"} if _persist_warn else {}),
                },
                citations=retrieval_hits or None,
                grounded=bool(retrieval_hits),
                error=None,
                seat=build_seat("ollama", model_name, "local", "server"),
            )

        except Exception as e:
            return ChatSendResponse(
                mode=original_mode,
                source="ollama",
                response="",
                reasoning_trace={"routing": route.telemetry_block(rctx)},
                error={"type": "connection_error", "message": _safe_error(e)},
            )

    async def _execute_api_provider(
        self,
        *,
        req: ChatSendRequest,
        msg: str,
        model_name: str,
        provider: str,
        route: Any,
        rctx: Any,
        original_mode: str,
        trace_id: str | None,
        branch: str,
        build_seat: Callable[[str, str, str | None, str], dict[str, Any]],
    ) -> ChatSendResponse:
        """Route single-model LLM mode through a non-Ollama API provider."""
        state = self.state
        _persist_warn = False

        # Log user message
        try:
            user_log = _log_message(sender="user", content=msg, branch=branch)
        except Exception as e:
            LOGGER.warning(f"User log failed: {e}")
            user_log = {}
            _persist_warn = True

        # Build messages with system prompt
        messages = _build_chat_messages(msg, branch=branch)
        system_prompt = _build_system_prompt(model_name)
        if req.generation_contract:
            system_prompt += f"\n\n## Generation Rules\n{req.generation_contract}"
        messages.insert(0, {"role": "system", "content": system_prompt})

        # Route through InferenceService
        try:
            from bridges.services.inference import InferenceService
            inference_svc = InferenceService(state=state)

            # Get API key for provider
            api_key = ""
            try:
                from security.provider_keys import get_provider_key
                api_key = get_provider_key(provider) or ""
            except Exception:
                pass

            t0 = time.time()
            reply, usage, ms = await inference_svc.call(
                provider, api_key, model_name, messages, req.inference_params
            )
            route.record(rctx, "model_call", "model_call", True, ms=ms)

            # Log AI response
            try:
                ai_log = _log_message(
                    sender="ai",
                    content=reply,
                    branch=branch,
                    model_identity={
                        "provider": provider,
                        "model": model_name,
                        "engine": "api",
                    },
                )
            except Exception as e:
                LOGGER.warning(f"AI log failed: {e}")
                ai_log = {}
                _persist_warn = True

            return ChatSendResponse(
                mode=original_mode,
                source=provider,
                response=reply,
                answer_frame=None,
                reasoning_trace={
                    "user_message_id": user_log.get("message_id"),
                    "ai_message_id": ai_log.get("message_id"),
                    "routing": route.telemetry_block(rctx),
                    "provider": provider,
                    "model": model_name,
                    "ms": ms,
                    **({"persistence_warning": "Message may not have been saved"} if _persist_warn else {}),
                },
                citations=None,
                grounded=False,
                error=None,
                seat=build_seat(provider, model_name, None, "server"),
            )

        except Exception as e:
            return ChatSendResponse(
                mode=original_mode,
                source=provider,
                response="",
                reasoning_trace={"routing": route.telemetry_block(rctx)},
                error={"type": "api_error", "message": _safe_error(e)},
            )
