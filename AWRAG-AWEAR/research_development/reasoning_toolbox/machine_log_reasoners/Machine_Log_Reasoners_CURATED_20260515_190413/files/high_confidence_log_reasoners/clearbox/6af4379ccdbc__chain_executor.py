"""Chain orchestration service extracted from chat router."""
from __future__ import annotations

import re
import time
from typing import Any, Callable, Optional, Set

from Conversations.threads import log_message as _log_message
from security.identity_profiles import load_profile as _load_identity
from security.inference_profiles import load_profile as _load_inference
from security.provider_keys import get_provider_key as _prov_get_key

from bridges.helpers import DEFAULT_MODEL, _build_chat_messages, _parse_tool_request
from bridges.models import ChatSendRequest, ChatSendResponse
from bridges.state import LOGGER
from bridges.ws_manager import WebSocketManager
from .inference import InferenceService
from .reasoning_service import ReasoningService


class ChainExecutor:
    """Executes hub -> slots chain flow with optional tool bounce-backs."""

    def __init__(
        self,
        *,
        state: Any,
        ws_manager: WebSocketManager,
        mounted_plugins: Set[str] | None = None,
        inference_service: InferenceService,
        reasoning_service: ReasoningService | None = None,
        provider_key_getter: Optional[Callable[[str], str]] = None,
        chat_messages_builder: Optional[Callable[..., list[dict]]] = None,
        tool_request_parser: Optional[Callable[[str], list[dict] | None]] = None,
        log_message_fn: Optional[Callable[..., Any]] = None,
        default_model: str = DEFAULT_MODEL,
    ) -> None:
        self.state = state
        self.ws_manager = ws_manager
        self._mounted_plugins: Set[str] = mounted_plugins if mounted_plugins is not None else set()
        self.inference_service = inference_service
        self.reasoning_service = reasoning_service
        self._provider_key_getter = provider_key_getter or _prov_get_key
        self._build_chat_messages = chat_messages_builder or _build_chat_messages
        self._parse_tool_request = tool_request_parser or _parse_tool_request
        self._log_message = log_message_fn or _log_message
        self._default_model = default_model

    @staticmethod
    def _trace_id(request: Any) -> str | None:
        try:
            return request.headers.get("X-Trace-Id")
        except Exception:
            return None

    def _build_seat(
        self,
        provider: str,
        model: str,
        seat_id: str | None = None,
        node_id: str = "server",
    ) -> dict:
        return {"provider": provider, "model": model, "seat_id": seat_id, "node_id": node_id}

    def _build_messages(self, prompt: str, branch: str) -> list[dict]:
        # Test doubles may provide a 1-arg builder. Production builder accepts branch.
        try:
            return self._build_chat_messages(prompt, branch=branch)
        except TypeError:
            return self._build_chat_messages(prompt)

    async def _call_hub(self, payload: dict) -> tuple[dict, int]:
        """Legacy Ollama-only hub call. Use _call_hub_provider for provider-aware calls."""
        t0_hub = time.time()
        client = await self.state.get_ollama_client()
        r = await client.post(f"{self.inference_service.ollama_base_url}/api/chat", json=payload)
        ms = int((time.time() - t0_hub) * 1000)
        if not r.is_success:
            return {"error": f"Ollama returned {r.status_code}"}, ms
        return r.json(), ms

    async def _call_hub_provider(
        self, provider: str, model: str, messages: list[dict], inference_params: dict | None = None
    ) -> tuple[str, dict, int]:
        """Provider-aware hub call. Routes through inference service for any provider."""
        if provider in ("ollama", ""):
            # Legacy path: direct Ollama call
            payload = {"model": model, "messages": messages, "stream": False}
            if inference_params:
                opts = {}
                if "temperature" in inference_params:
                    opts["temperature"] = inference_params["temperature"]
                if "top_p" in inference_params:
                    opts["top_p"] = inference_params["top_p"]
                if opts:
                    payload["options"] = opts
            data, ms = await self._call_hub(payload)
            if data.get("error"):
                return f"[Hub error: {data['error']}]", {}, ms
            reply = data.get("message", {}).get("content", "")
            usage = {
                "eval_count": data.get("eval_count", 0),
                "prompt_eval_count": data.get("prompt_eval_count", 0),
            }
            return reply, usage, ms
        else:
            # Route through inference service (OpenAI, Claude, Gemini, Grok)
            api_key = self._provider_key_getter(provider)
            if not api_key:
                return f"[Hub error: {provider} API key not configured]", {}, 0
            return await self.inference_service.call(
                provider, api_key, model, messages, inference_params
            )

    async def execute(self, request_data: dict[str, Any]) -> ChatSendResponse:
        req: ChatSendRequest = request_data["request"]
        msg: str = request_data["message"]
        route = request_data["route"]
        rctx = request_data["routing_context"]
        request = request_data.get("http_request")

        _tid = self._trace_id(request)
        contributions: list[dict] = []
        _hub_model = req.local_model or req.model or self._default_model
        _hub_provider = req.hub_provider or "ollama"
        _hub_enabled = req.hub_enabled
        _branch = (req.side_chat_id or "").strip() or "main"

        try:
            await self.ws_manager.broadcast(
                {
                    "evt": "chain-start",
                    "trace_id": _tid,
                    "mode": "multi_llm",
                    "hub_model": _hub_model,
                    "hub_enabled": _hub_enabled,
                }
            )
        except Exception:
            pass

        _server_tools_allowed = self.state.config.get("tools_enabled", True)
        _tools_active = req.tools_enabled and _server_tools_allowed
        _tool_trace: list[dict] = []

        # Log user message
        try:
            self._log_message(sender="user", content=msg, branch=_branch)
        except Exception:
            pass

        hub_reply = ""
        hub_usage = {}
        hub_ms = 0

        if _hub_enabled:
            hub_messages = self._build_messages(msg, _branch)
            if _tools_active:
                from bridges.tool_defs import TOOL_SYSTEM_PROMPT

                hub_messages.insert(0, {"role": "system", "content": TOOL_SYSTEM_PROMPT})

            if req.plugins_enabled and req.enabled_plugins:
                from bridges.plugin_hooks import run_pre_hooks

                _pre_ctx = await run_pre_hooks(
                    enabled_plugins=req.enabled_plugins,
                    mounted_plugins=self._mounted_plugins,
                    request_ctx={
                        "user_message": msg,
                        "hub_model": _hub_model,
                        "tools_enabled": _tools_active,
                        "hub_messages": hub_messages,
                        "extra": {},
                    },
                )
                hub_messages = _pre_ctx.get("hub_messages", hub_messages)

            try:
                hub_reply, hub_usage, hub_ms = await self._call_hub_provider(
                    _hub_provider, _hub_model, hub_messages, req.inference_params
                )

                if _tools_active and hub_reply and _hub_provider in ("ollama", ""):
                    # Tool calling only supported for local hub (tools execute locally)
                    from bridges.tool_defs import execute_tool, parse_tool_calls, strip_tool_calls

                    _parsed_tools = parse_tool_calls(hub_reply)
                    if _parsed_tools:
                        _parsed_tools = _parsed_tools[:1]
                        _clean = strip_tool_calls(hub_reply)
                        hub_messages.append({"role": "assistant", "content": _clean or "(calling tool)"})
                        for tc in _parsed_tools:
                            t0_tool = time.time()
                            result_str = await execute_tool(
                                tc["name"],
                                tc["arguments"],
                                session_id=req.session_id,
                                model_name=_hub_model,
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
                            hub_messages.append(
                                {
                                    "role": "system",
                                    "content": (
                                        f"[TOOL RESULT — {tc['name']}]\n{result_str}\n[END TOOL RESULT]\n"
                                        "Now summarize this result for the user. Do NOT call another tool."
                                    ),
                                }
                            )
                        _reply2, _, _ = await self._call_hub_provider(
                            _hub_provider, _hub_model, hub_messages, req.inference_params
                        )
                        hub_reply = _reply2 if _reply2.strip() else _clean

                if hub_reply and ("tool_call" in hub_reply or "<tool_call>" in hub_reply):
                    from bridges.tool_defs import strip_tool_calls

                    hub_reply = strip_tool_calls(hub_reply)
            except Exception as e:
                hub_ms = 0
                hub_reply = f"[Hub error: {e}]"

            _provider_label = {"openai": "openai", "claude": "anthropic", "gemini": "google", "grok": "xai"}
            _hub_prov_label = _provider_label.get(_hub_provider, _hub_provider)

            try:
                self._log_message(
                    sender="ai",
                    content=hub_reply,
                    branch=_branch,
                    model_identity={"provider": _hub_prov_label, "model": _hub_model, "engine": "chat"},
                )
            except Exception:
                pass

            contributions.append(
                {
                    "author": "hub",
                    "provider": _hub_prov_label,
                    "model": _hub_model,
                    "content": hub_reply,
                    "tools_used": _tool_trace,
                    "ms": hub_ms,
                    "usage": hub_usage,
                }
            )

        if req.plugins_enabled and req.enabled_plugins:
            from bridges.plugin_hooks import run_post_hooks

            _post_ctx = await run_post_hooks(
                enabled_plugins=req.enabled_plugins,
                mounted_plugins=self._mounted_plugins,
                response_ctx={
                    "user_message": msg,
                    "hub_model": _hub_model,
                    "hub_reply": hub_reply,
                    "tools_used": _tool_trace,
                    "contributions": contributions,
                    "extra": {},
                },
            )
            contributions = _post_ctx.get("contributions", contributions)

        _tool_results_text = ""
        if _tool_trace:
            _tool_results_text = "\n".join(f"[Tool: {t['tool']}] {t['result_preview']}" for t in _tool_trace)

        _active_slots = [s for s in (req.chain_slots or []) if s.enabled and s.provider and s.model]

        # Load identity profiles for all participants
        _slot_profiles: dict[int, dict | None] = {}
        for s in _active_slots:
            _slot_profiles[s.slot_id] = _load_identity(s.model)
        _hub_profile = _load_identity(_hub_model) if _hub_enabled else None

        # Build roster with identity roles
        _roster_lines = []
        if _hub_enabled:
            _hub_role = (_hub_profile or {}).get("identity_role", "")
            _hub_label = f"- HUB ({_hub_model}): {_hub_role}" if _hub_role else f"- HUB: {_hub_model} (local)"
            _roster_lines.append(_hub_label)
        for s in _active_slots:
            _sp = _slot_profiles.get(s.slot_id) or {}
            _sr = _sp.get("identity_role", "")
            _sl = f"- SLOT {s.slot_id} ({s.model}): {_sr}" if _sr else f"- SLOT {s.slot_id}: {s.model} ({s.provider})"
            _roster_lines.append(_sl)
        _roster_block = "## Lab Participants\n" + "\n".join(_roster_lines)

        _lab_protocol = (
            "\n\n## Lab Protocol\n"
            "You are a colleague in a working lab. The user brought a problem to the table.\n"
            "Everyone here is working toward resolving it together.\n"
            "Read the Prior Work above carefully. Your job is to BUILD ON IT:\n"
            "- Quote or reference specific points from prior outputs (use short snippets).\n"
            "- Don't restate the problem. Don't summarize what's been said. Move the work forward.\n"
            "- If the prior output has a gap, fill it. If it has an error, fix it in place.\n"
            "- If it's solid, take the next logical step — refine, extend, or produce the deliverable.\n"
            "- When you reference prior work, cite the author: \"As @slot_1 noted…\" or \"Building on @hub's point…\"\n"
            "Each person adds to the whiteboard, nobody erases it to start over.\n"
            "Address people directly when needed: @hub, @slot_1, @slot_2, @user.\n"
            "The goal is resolution — a finished artifact, a working answer, a closed question.\n"
            "Keep going until the problem is solved, not until you've had your say."
        )

        prior_outputs: list[str] = []
        _slot_identity_map: dict[str, dict] = {}
        _slot_tool_delegations: list[dict[str, Any]] = []

        # ── Resume from interrupt: restore prior state ──
        _resume = req.chain_resume
        _resume_after_slot = 0
        if _resume:
            prior_outputs = _resume.get("prior_outputs", [])
            contributions = _resume.get("contributions", contributions)
            hub_reply = _resume.get("hub_reply", hub_reply)
            _resume_after_slot = _resume.get("interrupted_after_slot", 0)
            _user_steering = _resume.get("user_steering", "")
            if _user_steering:
                prior_outputs.append(f"[USER INTERRUPT] {_user_steering}")
                contributions.append({
                    "author": "user",
                    "provider": "human",
                    "model": "user",
                    "content": _user_steering,
                    "ms": 0,
                })
            LOGGER.info("Chain resume after slot %s with %d prior outputs", _resume_after_slot, len(prior_outputs))

        for slot in _active_slots:
            # Skip slots already completed in a resumed chain
            if _resume and slot.slot_id <= _resume_after_slot:
                continue

            if slot.provider not in ("ollama", "openai", "claude", "gemini", "grok", "grounded", "reasoning"):
                contributions.append(
                    {
                        "author": f"slot_{slot.slot_id}",
                        "provider": slot.provider,
                        "model": slot.model,
                        "content": f"[Unknown provider: {slot.provider}]",
                        "ms": 0,
                    }
                )
                continue

            _local_providers = {"ollama", "grounded", "reasoning"}
            api_key = "" if slot.provider in _local_providers else self._provider_key_getter(slot.provider)
            if not api_key and slot.provider not in _local_providers:
                contributions.append(
                    {
                        "author": f"slot_{slot.slot_id}",
                        "provider": slot.provider,
                        "model": slot.model,
                        "content": f"[{slot.provider} API key not configured]",
                        "ms": 0,
                    }
                )
                continue

            _slot_identity_map[f"slot_{slot.slot_id}"] = {
                "provider": slot.provider,
                "model": slot.model,
                "api_key": api_key,
            }

            # Build slot identity from its per-model profile
            _profile = _slot_profiles.get(slot.slot_id) or {}
            _identity_role = _profile.get("identity_role", "")
            if _identity_role:
                slot_context = f"## Your Identity\n{_identity_role}\n\n"
                slot_context += f"You are SLOT {slot.slot_id} ({slot.model}) in this lab.\n\n"
            else:
                slot_context = f"## You are SLOT {slot.slot_id}: {slot.model} ({slot.provider})\n\n"

            # Session memory (summary + lessons) — keeps slots grounded
            from bridges.helpers import build_slot_memory_context
            _slot_memory = build_slot_memory_context()
            slot_context += f"\n\n## Session Memory\n{_slot_memory}\n\n"

            slot_context += _roster_block
            slot_context += f"\n\n## User Message\n{msg}"
            if _hub_enabled and hub_reply:
                _hub_id = (_hub_profile or {}).get("identity_role", _hub_model)
                slot_context += f"\n\n## HUB ({_hub_id}) Output\n{hub_reply}"
            if _tool_results_text:
                slot_context += f"\n\n## Tool Results\n{_tool_results_text}"
            if prior_outputs:
                slot_context += "\n\n## Prior Work (build on this — don't repeat it)\n"
                for i, prior in enumerate(prior_outputs):
                    _prior_slot = _active_slots[i] if i < len(_active_slots) else None
                    if _prior_slot:
                        _pp = (_slot_profiles.get(_prior_slot.slot_id) or {}).get("identity_role", "")
                        _prior_label = f"SLOT {_prior_slot.slot_id} ({_pp or _prior_slot.model})"
                    elif prior.startswith("[USER INTERRUPT]"):
                        _prior_label = "USER STEERING"
                    else:
                        _prior_label = f"Prior Slot {i + 1}"
                    # Full text for last output (the one to directly build on),
                    # snippets for earlier ones to keep context lean
                    if i == len(prior_outputs) - 1:
                        slot_context += f"\n### {_prior_label} (latest — extend this)\n{prior}"
                    else:
                        _snippet = prior[:600].rstrip()
                        _truncated = "…" if len(prior) > 600 else ""
                        slot_context += f"\n### {_prior_label}\n{_snippet}{_truncated}\n"
            slot_context += _lab_protocol

            # Generation contract rules (from Inference page)
            if req.generation_contract:
                slot_context += f"\n\n## Generation Rules\n{req.generation_contract}"

            slot_messages = [{"role": "user", "content": slot_context}]

            # Per-model inference params: saved profile → request override
            _inf_profile = _load_inference(slot.model) or {}
            _slot_params = {**_inf_profile, **(req.inference_params or {})} if _inf_profile else req.inference_params

            try:
                reply, usage, slot_ms = await self.inference_service.call(
                    slot.provider,
                    api_key,
                    slot.model,
                    slot_messages,
                    _slot_params,
                )
                # Surface API errors: inference returns ("", {"error": "..."}, ms) on failure
                if not reply and isinstance(usage, dict) and usage.get("error"):
                    reply = f"[{slot.provider} error: {usage['error']}]"
            except Exception as e:
                reply, usage, slot_ms = f"[Error: {e}]", {}, 0

            _bounce_trace: list[dict] = []
            if _tools_active and reply:
                _tool_req = self._parse_tool_request(reply)
                if _tool_req:
                    from bridges.tool_defs import execute_tool, strip_tool_calls

                    _clean_slot_reply = strip_tool_calls(reply)
                    if _clean_slot_reply.strip():
                        reply = _clean_slot_reply
                    else:
                        reply = f"[Tool request delegated to local hub by slot_{slot.slot_id}]"

                    _bounce_results: list[str] = []
                    for tr in _tool_req[:2]:
                        t0_bounce = time.time()
                        _br = await execute_tool(
                            tr["name"],
                            tr.get("arguments", {}),
                            session_id=req.session_id,
                            model_name=_hub_model,
                        )
                        _bounce_ms = int((time.time() - t0_bounce) * 1000)
                        _bounce_trace.append(
                            {
                                "tool": tr["name"],
                                "args": tr.get("arguments", {}),
                                "requested_by": f"slot_{slot.slot_id}",
                                "ms": _bounce_ms,
                                "result_preview": _br[:200],
                            }
                        )
                        _bounce_results.append(f"[Tool: {tr['name']}] {_br}")
                    if _bounce_results:
                        _slot_tool_delegations.append(
                            {
                                "requester": f"slot_{slot.slot_id}",
                                "provider": slot.provider,
                                "model": slot.model,
                                "tool_results": _bounce_results,
                            }
                        )

            _provider_map = {"openai": "openai", "claude": "anthropic", "gemini": "google", "grok": "xai"}
            try:
                self._log_message(
                    sender="ai",
                    content=reply,
                    branch=_branch,
                    model_identity={
                        "provider": _provider_map.get(slot.provider, slot.provider),
                        "model": slot.model,
                        "engine": "chain_slot",
                    },
                )
            except Exception:
                pass

            # L4: persist chain contribution as reasoning trace
            try:
                from Conversations.threads.reasoning_log import log_chain_contribution
                log_chain_contribution(slot.slot_id, slot.provider, slot.model, reply[:500], slot_ms)
            except Exception:
                pass

            contributions.append(
                {
                    "author": f"slot_{slot.slot_id}",
                    "provider": _provider_map.get(slot.provider, slot.provider),
                    "model": slot.model,
                    "content": reply,
                    "ms": slot_ms,
                    "usage": usage,
                    "bounce_tools": _bounce_trace if _bounce_trace else None,
                }
            )
            prior_outputs.append(reply)

            # ── Interrupt check: pause chain if this slot has interrupt_after ──
            if slot.interrupt_after:
                _remaining_slots = [s for s in _active_slots if s.slot_id > slot.slot_id]
                if _remaining_slots:
                    LOGGER.info("Chain interrupted after slot %s — awaiting user input", slot.slot_id)
                    _interrupt_state = {
                        "interrupted_after_slot": slot.slot_id,
                        "prior_outputs": prior_outputs,
                        "contributions": contributions,
                        "hub_reply": hub_reply,
                        "remaining_slot_ids": [s.slot_id for s in _remaining_slots],
                    }
                    return ChatSendResponse(
                        mode="multi_llm",
                        source="chain_interrupted",
                        response=reply,
                        contributions=contributions,
                        chain_state=_interrupt_state,
                        seat=self._build_seat(
                            _provider_map.get(slot.provider, slot.provider),
                            slot.model,
                        ),
                    )

        # Local-hub-only tool boundary: slot models can request tools, but only the hub
        # receives the executed tool results and synthesizes them.
        if _slot_tool_delegations:
            _tool_blocks: list[str] = []
            for d in _slot_tool_delegations:
                _tool_blocks.append(
                    f"Requester: {d['requester']} ({d['provider']}:{d['model']})\n"
                    + "\n".join(d["tool_results"])
                )
            _hub_tool_prompt = (
                "Chain slots requested tools. You are the local hub and the only tool authority.\n"
                "Use the executed tool results below to provide a consolidated response for the user.\n\n"
                + "\n\n---\n\n".join(_tool_blocks)
            )
            _hub_tool_messages = self._build_messages(_hub_tool_prompt, _branch)
            try:
                t0_hub_tool = time.time()
                _hub_tool_data, _ = await self._call_hub(
                    {"model": _hub_model, "messages": _hub_tool_messages, "stream": False}
                )
                _hub_tool_ms = int((time.time() - t0_hub_tool) * 1000)
                if _hub_tool_data.get("error"):
                    _hub_tool_reply = "(local hub tool synthesis failed)"
                else:
                    _hub_tool_reply = _hub_tool_data.get("message", {}).get("content", "")
            except Exception as e:
                _hub_tool_reply, _hub_tool_ms = f"[Hub tool synthesis error: {e}]", 0

            contributions.append(
                {
                    "author": "hub",
                    "provider": "ollama",
                    "model": _hub_model,
                    "content": _hub_tool_reply,
                    "ms": _hub_tool_ms,
                    "tool_delegations": _slot_tool_delegations,
                }
            )

        _followup_pattern = re.compile(r"@(hub|slot_(?:[1-9]|10))\s*:\s*(.+?)(?:\n|$)", re.IGNORECASE)
        _followup_targets: dict[str, tuple[str, str]] = {}
        for contrib in contributions:
            if contrib["author"] == "hub":
                continue
            for m in _followup_pattern.finditer(contrib["content"]):
                target = m.group(1).lower()
                question = m.group(2).strip()
                if target not in _followup_targets and question:
                    _followup_targets[target] = (question, contrib["author"])

        for target, (question, from_author) in _followup_targets.items():
            if target == "hub":
                _fup_messages = self._build_messages(
                    f"A chain participant ({from_author}) asks you: {question}\n\n"
                    f"Original user message: {msg}\nYour prior analysis: {hub_reply}\n\n"
                    "Answer concisely.",
                    _branch,
                )
                try:
                    t0_fup = time.time()
                    fup_data, _ = await self._call_hub(
                        {"model": _hub_model, "messages": _fup_messages, "stream": False}
                    )
                    fup_ms = int((time.time() - t0_fup) * 1000)
                    if fup_data.get("error"):
                        fup_reply = "(hub followup failed)"
                    else:
                        fup_reply = fup_data.get("message", {}).get("content", "")
                except Exception as e:
                    fup_reply, fup_ms = f"[Hub followup error: {e}]", 0
                contributions.append(
                    {
                        "author": "hub",
                        "provider": "ollama",
                        "model": _hub_model,
                        "content": fup_reply,
                        "ms": fup_ms,
                        "followup_to": from_author,
                    }
                )
            elif target in _slot_identity_map:
                _si = _slot_identity_map[target]
                _fup_context = (
                    f"A chain participant ({from_author}) asks you directly:\n{question}\n\n"
                    f"Original user message: {msg}\n\n"
                    "Answer concisely. One response only."
                )
                try:
                    fup_reply, _, fup_ms = await self.inference_service.call(
                        _si["provider"],
                        _si["api_key"],
                        _si["model"],
                        [{"role": "user", "content": _fup_context}],
                        req.inference_params,
                    )
                except Exception as e:
                    fup_reply, fup_ms = f"[Followup error: {e}]", 0
                contributions.append(
                    {
                        "author": target,
                        "provider": _si["provider"],
                        "model": _si["model"],
                        "content": fup_reply,
                        "ms": fup_ms,
                        "followup_to": from_author,
                    }
                )

        # ── Resolver slot: final synthesis after all chain slots ──
        if req.resolver_enabled and req.resolver_provider and req.resolver_model:
            _resolver_provider = req.resolver_provider
            _resolver_model = req.resolver_model
            _resolver_key = "" if _resolver_provider in ("ollama", "grounded", "reasoning") else self._provider_key_getter(_resolver_provider)

            if _resolver_key or _resolver_provider in ("ollama", "grounded", "reasoning"):
                # Build resolver context with all prior work
                resolver_context = f"## You are the RESOLVER — final synthesis\n\n"
                resolver_context += f"## User Message\n{msg}\n\n"
                if hub_reply:
                    resolver_context += f"## Hub Output\n{hub_reply}\n\n"
                for c in contributions:
                    if c["author"] == "hub":
                        continue
                    resolver_context += f"## {c['author'].upper()} ({c.get('provider','')}/{c.get('model','')}) Output\n"
                    resolver_context += f"{c['content']}\n\n"
                resolver_context += (
                    "## Your Task\n"
                    "You have read everyone's contributions above. Now produce the FINAL resolved answer.\n"
                    "Synthesize the best points. Resolve any contradictions. Fill any gaps.\n"
                    "Deliver a clean, complete answer as if only one person responded.\n"
                    "Do not summarize what others said — produce the deliverable."
                )

                resolver_messages = [{"role": "user", "content": resolver_context}]

                try:
                    r_reply, r_usage, r_ms = await self.inference_service.call(
                        _resolver_provider, _resolver_key, _resolver_model,
                        resolver_messages, req.inference_params,
                    )
                except Exception as e:
                    r_reply, r_usage, r_ms = f"[Resolver error: {e}]", {}, 0

                _rprov_map = {"openai": "openai", "claude": "anthropic", "gemini": "google", "grok": "xai"}
                contributions.append({
                    "author": "resolver",
                    "provider": _rprov_map.get(_resolver_provider, _resolver_provider),
                    "model": _resolver_model,
                    "content": r_reply,
                    "ms": r_ms,
                    "usage": r_usage,
                })

                try:
                    self._log_message(
                        sender="ai", content=r_reply, branch=_branch,
                        model_identity={
                            "provider": _rprov_map.get(_resolver_provider, _resolver_provider),
                            "model": _resolver_model, "engine": "resolver",
                        },
                    )
                except Exception:
                    pass

                LOGGER.info("Resolver completed: %s/%s in %dms", _resolver_provider, _resolver_model, r_ms)
            else:
                contributions.append({
                    "author": "resolver",
                    "provider": _resolver_provider,
                    "model": _resolver_model,
                    "content": f"[{_resolver_provider} API key not configured]",
                    "ms": 0,
                })

        final_response = contributions[-1]["content"] if contributions else hub_reply
        final_seat = self._build_seat(
            contributions[-1].get("provider", "ollama"),
            contributions[-1].get("model", _hub_model),
        )

        total_ms = sum(c.get("ms", 0) for c in contributions)
        route.record(
            rctx,
            "chain_executor",
            "chain",
            True,
            ms=total_ms,
            slots_run=len([c for c in contributions if c["author"] != "hub"]),
        )

        if _tid:
            LOGGER.info("[%s] chain complete slots=%s ms=%s", _tid, len(_active_slots), total_ms)

        try:
            await self.ws_manager.broadcast(
                {
                    "evt": "chain-complete",
                    "trace_id": _tid,
                    "mode": "multi_llm",
                    "latency_ms": total_ms,
                    "slots_run": len([c for c in contributions if c["author"] != "hub"]),
                }
            )
        except Exception:
            pass

        return ChatSendResponse(
            mode="multi_llm",
            source="chain",
            response=final_response,
            contributions=contributions,
            reasoning_trace={
                "chain": {
                    "contributions": contributions,
                    "hub_model": _hub_model,
                    "slots_run": len(contributions) - 1,
                    "tools": {"enabled": _tools_active, "calls": _tool_trace},
                    "latency_ms_total": total_ms,
                },
                "routing": route.telemetry_block(rctx),
            },
            seat=final_seat,
        )
