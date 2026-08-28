"""Tool registry, debugwire bridge, and tool policy services."""
from __future__ import annotations

from typing import Any

import httpx
from fastapi import HTTPException

from bridges.state import LOGGER


class ControlToolService:
    """Owns tool catalog operations and debugwire/tool policy endpoints."""

    def __init__(self, *, llm_debugwire_url: str = "http://127.0.0.1:11435/api/debugwire/toggle") -> None:
        self._llm_debugwire_url = llm_debugwire_url

    @staticmethod
    def list_tools() -> dict[str, Any]:
        from bridges.tool_defs import tool_directory

        return {"tools": tool_directory()}

    @staticmethod
    def get_tool(name: str) -> dict[str, Any]:
        from bridges.tool_defs import _BUILTIN_NAMES, get_custom_tool_json, tool_directory

        for tool in tool_directory():
            if tool["name"] == name:
                result = dict(tool)
                if name not in _BUILTIN_NAMES:
                    raw = get_custom_tool_json(name)
                    if raw:
                        result["runner"] = raw.get("runner", {})
                        result["params"] = raw.get("params", {})
                return result
        raise HTTPException(status_code=404, detail=f"Tool not found: {name}")

    @staticmethod
    def save_tool(data: dict[str, Any]) -> dict[str, Any]:
        from bridges.tool_defs import save_custom_tool

        err = save_custom_tool(data)
        if err:
            raise HTTPException(status_code=400, detail=err)
        LOGGER.info("Tool saved: %s", data.get("name"))
        return {"ok": True, "name": data["name"]}

    @staticmethod
    def delete_tool(name: str) -> dict[str, Any]:
        from bridges.tool_defs import delete_custom_tool

        err = delete_custom_tool(name)
        if err:
            raise HTTPException(status_code=400, detail=err)
        LOGGER.info("Tool deleted: %s", name)
        return {"ok": True}

    @staticmethod
    async def test_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        from bridges.tool_defs import execute_tool

        result = await execute_tool(name, arguments, session_id="tool_workshop_test")
        return {"name": name, "result": result}

    @staticmethod
    def reload_tools() -> dict[str, Any]:
        from bridges.tool_defs import reload_custom_tools

        count = reload_custom_tools()
        return {"ok": True, "custom_tools_loaded": count}

    @staticmethod
    def debugwire_status() -> dict[str, Any]:
        from security.runtime_log import debugwire_status

        return debugwire_status()

    async def debugwire_toggle(
        self,
        *,
        enabled: bool,
        components: list[str] | None,
    ) -> dict[str, Any]:
        from security.runtime_log import debugwire_set, debugwire_status

        debugwire_set(enabled, components)
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self._llm_debugwire_url,
                    json={"enabled": enabled, "components": components},
                    timeout=3.0,
                )
        except Exception:
            pass
        return debugwire_status()

    @staticmethod
    def get_tool_policy(model: str) -> dict[str, Any]:
        from bridges.tool_defs import TOOL_REGISTRY
        from security.tool_profiles import get_allowed_tools, get_default_allowed

        allowed = get_allowed_tools(model)
        defaults = get_default_allowed()
        effective = allowed if allowed is not None else defaults
        tools = [
            {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "safety": tool.get("safety", "read"),
                "allowed": tool["name"] in effective,
            }
            for tool in TOOL_REGISTRY
        ]
        return {
            "model": model,
            "allowed": allowed,
            "using_defaults": allowed is None,
            "defaults": defaults,
            "tools": tools,
        }

    @staticmethod
    def save_tool_policy(model: str, allowed: list[str]) -> dict[str, Any]:
        from security.tool_profiles import save_tool_profile

        profile = save_tool_profile(model, allowed)
        return {"model": model, "profile": profile}

    @staticmethod
    def tool_telemetry() -> dict[str, Any]:
        from security.tool_telemetry import aggregate_stats

        return {"stats": aggregate_stats()}

    @staticmethod
    def tool_telemetry_raw(lines: int = 100) -> dict[str, Any]:
        from security.tool_telemetry import tail_raw

        return {"records": tail_raw(lines)}

