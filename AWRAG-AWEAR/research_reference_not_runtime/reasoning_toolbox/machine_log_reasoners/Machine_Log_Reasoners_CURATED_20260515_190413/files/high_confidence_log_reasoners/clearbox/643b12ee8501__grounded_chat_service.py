"""Grounded chat service (LakeSpeak retrieval + evidence synthesis)."""
from __future__ import annotations

import asyncio
import re
import time
from typing import Any, Callable

from Conversations.threads import log_message as _log_message
from bridges.helpers import _safe_error
from bridges.models import ChatSendRequest, ChatSendResponse
from bridges.services.plugin_gateway import PluginGatewayService
from bridges.state import BridgeState, LOGGER


class GroundedChatService:
    """Owns grounded mode execution and evidence-bound response shaping."""

    def __init__(self, *, state: BridgeState, plugin_gateway: PluginGatewayService | None = None) -> None:
        self.state = state
        self.plugin_gateway = plugin_gateway or PluginGatewayService(state=state)

    async def execute(
        self,
        *,
        req: ChatSendRequest,
        msg: str,
        model_name: str,
        route: Any,
        rctx: Any,
        branch: str,
        build_seat: Callable[[str, str, str | None, str], dict[str, Any]],
    ) -> ChatSendResponse:
        state = self.state
        OLLAMA_BASE = state.get_ollama_base_url()
        try:
            engine = self.plugin_gateway.get_lakespeak_engine()

            # Step 1: Retrieve evidence from LakeSpeak
            t0_retrieval = time.time()
            ls_result = await asyncio.to_thread(
                engine.query,
                query=msg,
                mode="grounded",
                topk=req.topk,
                session_id=req.session_id,
            )
            route.record(rctx, "plugin_chain", "plugin_chain", True, ms=int((time.time() - t0_retrieval) * 1000))

            citations = ls_result.citations or []
            trace = ls_result.trace or {}
            verdict = ls_result.verdict

            # If verdict is trash (no usable evidence), return miss template directly
            if verdict == "trash" or not citations:
                _miss = (
                    "This is not represented in the current data. "
                    "No relevant evidence was found in the selected corpus."
                )
                trace["routing"] = route.telemetry_block(rctx)
                return ChatSendResponse(
                    mode="grounded",
                    source="lakespeak",
                    response=_miss,
                    reasoning_trace=trace,
                    citations=[],
                    grounded=False,
                    verdict="no_representation",
                    error=None,
                )

            # Step 2: Build evidence block for LLM
            # Guard: suppress directive-heavy chunks on short queries
            _DIRECTIVE_STARTS = re.compile(
                r"^\s*("
                r"you\s+(must|should|are|will)|always\s|never\s|"
                r"respond\s+as|format:|style:|rule:|story[_ ]|"
                r"instructions?:|system\s*prompt|do\s+not\b"
                r")",
                re.IGNORECASE,
            )
            _short_query = len(msg.split()) < 8

            evidence_lines = []
            for c in citations[: req.topk]:
                snippet = c.get("snippet", c.get("text", ""))[:600]
                # On short queries, skip chunks that look like directives
                if _short_query and _DIRECTIVE_STARTS.search(snippet):
                    continue
                score = c.get("score", 0)
                evidence_lines.append(f"[{len(evidence_lines) + 1}] (score: {score:.3f}) {snippet}")
            evidence_block = "\n\n".join(evidence_lines)

            # Step 3: Send to Ollama /api/chat with tool results pre-filled
            system_prompt = (
                "You are a grounded research assistant. You MUST answer using ONLY "
                "the evidence provided below. Cite evidence by number [1], [2], etc. "
                "If the evidence does not contain the answer, say so explicitly. "
                "Do NOT make up facts beyond what the evidence states."
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": msg},
                {"role": "system", "content": f"EVIDENCE FROM ARCHIVE:\n\n{evidence_block}"},
            ]

            # Tool definition for search_archive (model can request additional searches)
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "search_archive",
                        "description": "Search the Clearbox AI Studio knowledge archive for grounded evidence on a topic. Use this when you need more evidence or a different angle on the question.",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Search query for the archive",
                                }
                            },
                            "required": ["query"],
                        },
                    },
                }
            ]

            ollama_payload = {
                "model": model_name,
                "messages": messages,
                "tools": tools,
                "stream": False,
                "keep_alive": "5m",
                "options": {"num_gpu": -1},
            }

            # Stage: model_call
            t0_model = time.time()
            client = await state.get_ollama_client()
            r = await client.post(f"{OLLAMA_BASE}/api/chat", json=ollama_payload)

            if not r.is_success:
                # Fallback: return raw evidence if Ollama fails
                route.record(rctx, "model_call", "model_call", True, ms=int((time.time() - t0_model) * 1000))
                trace["routing"] = route.telemetry_block(rctx)
                return ChatSendResponse(
                    mode="grounded",
                    source="lakespeak",
                    response=ls_result.answer_text,
                    reasoning_trace=trace,
                    citations=citations,
                    grounded=ls_result.grounded,
                    verdict=verdict,
                    error={"type": "ollama_error", "status": r.status_code, "detail": r.text[:500]},
                )

            data = r.json()
            resp_message = data.get("message", {})

            # Step 4: Handle tool calls (one round of follow-up search)
            tool_calls = resp_message.get("tool_calls")
            if tool_calls:
                # Append the assistant's tool-call message ONCE (before the loop)
                messages.append(resp_message)
                _tool_results_added = 0

                # Execute each tool call
                for tc in tool_calls[:2]:  # Max 2 follow-up searches
                    fn = tc.get("function", {})
                    if fn.get("name") == "search_archive":
                        follow_query = fn.get("arguments", {}).get("query", msg)

                        follow_result = await asyncio.to_thread(
                            engine.query,
                            query=follow_query,
                            mode="grounded",
                            topk=req.topk,
                            session_id=req.session_id,
                        )

                        # Add follow-up citations (dedup by chunk_id)
                        existing_ids = {c.get("chunk_id") for c in citations}
                        for fc in (follow_result.citations or []):
                            if fc.get("chunk_id") not in existing_ids:
                                citations.append(fc)
                                existing_ids.add(fc.get("chunk_id"))

                        # Build follow-up evidence
                        follow_lines = []
                        for i, c in enumerate(follow_result.citations or []):
                            snippet = c.get("snippet", c.get("text", ""))[:600]
                            score = c.get("score", 0)
                            follow_lines.append(f"[{len(evidence_lines) + i + 1}] (score: {score:.3f}) {snippet}")

                        # Append tool result to messages
                        messages.append(
                            {
                                "role": "tool",
                                "content": "\n\n".join(follow_lines) if follow_lines else "No additional results found.",
                            }
                        )
                        _tool_results_added += 1

                # Second LLM call — only if at least one tool result was actually added
                if _tool_results_added > 0:
                    ollama_payload["messages"] = messages
                    del ollama_payload["tools"]  # No more tool calls in round 2
                    client = await state.get_ollama_client()
                    r2 = await client.post(f"{OLLAMA_BASE}/api/chat", json=ollama_payload)

                    if r2.is_success:
                        data = r2.json()
                        resp_message = data.get("message", {})

            reply = resp_message.get("content", "")

            # Extract Ollama performance metadata (grounded)
            _eval_count = data.get("eval_count", 0)
            _eval_dur_ns = data.get("eval_duration", 0)
            _prompt_count = data.get("prompt_eval_count", 0)
            _load_dur_ns = data.get("load_duration", 0)
            _total_dur_ns = data.get("total_duration", 0)
            trace["ollama"] = {
                "eval_count": _eval_count,
                "prompt_eval_count": _prompt_count,
                "eval_duration_ms": _eval_dur_ns // 1_000_000,
                "load_duration_ms": _load_dur_ns // 1_000_000,
                "total_duration_ms": _total_dur_ns // 1_000_000,
                "tokens_per_second": round(_eval_count / max(_eval_dur_ns / 1e9, 0.001), 1) if _eval_dur_ns else None,
            }

            route.record(rctx, "model_call", "model_call", True, ms=int((time.time() - t0_model) * 1000))

            # Log grounded exchange to thread
            _grounded_reply = reply or ls_result.answer_text
            _persist_warn = False
            try:
                _log_message(sender="user", content=msg, branch=branch)
            except Exception as e:
                LOGGER.warning(f"Grounded user log failed: {e}")
                _persist_warn = True
            _grounded_ai_log = {}
            try:
                _grounded_ai_log = _log_message(
                    sender="ai",
                    content=_grounded_reply,
                    branch=branch,
                    model_identity={"provider": "ollama", "model": model_name, "engine": "grounded"},
                )
            except Exception as e:
                LOGGER.warning(f"Grounded AI log failed: {e}")
                _persist_warn = True

            # Auto-persist citations to sidecar store
            if citations and _grounded_ai_log.get("message_id") is not None:
                _cite_day = _grounded_ai_log.get("date", "")
                _cite_msg_id = str(_grounded_ai_log["message_id"])
                try:
                    from Conversations.threads.citation_store import CitationStore

                    _cs = CitationStore()
                    for _ci, _cite in enumerate(citations):
                        _coord = _cite.get("coord", "")
                        if not _coord:
                            continue
                        try:
                            _cs.attach(
                                day=_cite_day,
                                message_id=_cite_msg_id,
                                block_id=f"b{_ci}",
                                block_ordinal=_ci,
                                canonical=_coord,
                                subject=_cite.get("text", "")[:200] if _cite.get("text") else None,
                                source="lakespeak",
                            )
                        except ValueError:
                            pass  # Dedup — already attached
                        except Exception as ce:
                            LOGGER.warning(f"Citation auto-persist failed: {ce}")
                except Exception as ce:
                    LOGGER.warning(f"Citation store init failed: {ce}")

            trace["routing"] = route.telemetry_block(rctx)
            if _persist_warn:
                trace["persistence_warning"] = "Message may not have been saved"
            return ChatSendResponse(
                mode="grounded",
                source="lakespeak",
                response=_grounded_reply,
                reasoning_trace=trace,
                citations=citations,
                grounded=ls_result.grounded,
                verdict=verdict,
                error=None,
                seat=build_seat("ollama", model_name, "local", "server"),
            )

        except ImportError:
            return ChatSendResponse(
                mode="grounded",
                source="bridge_router",
                response="LakeSpeak plugin not installed.",
                reasoning_trace={"routing": route.telemetry_block(rctx)},
                error={"type": "not_available", "message": "LakeSpeak plugin not installed"},
            )
        except Exception as e:
            LOGGER.exception("Grounded mode error")
            return ChatSendResponse(
                mode="grounded",
                source="lakespeak",
                response="",
                reasoning_trace={"routing": route.telemetry_block(rctx)},
                error={"type": "lakespeak_error", "message": _safe_error(e)},
            )
