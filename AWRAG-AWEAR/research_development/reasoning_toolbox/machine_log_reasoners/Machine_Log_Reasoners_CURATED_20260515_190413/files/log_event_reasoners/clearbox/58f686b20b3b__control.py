"""Debug, tools, plugins, AI briefs, control, and history queue routes."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request

from bridges.services.ai_briefs import AIBriefService
from bridges.services.control_tools import ControlToolService
from bridges.services.history_queue import HistoryQueueService
from bridges.services.logger_streams import LoggerStreamService
from bridges.services.plugin_catalog import PluginCatalogService
from bridges.services.plugin_runtime import PluginRuntimeService
from bridges.state import BridgeState
from security.data_paths import DIAGNOSTIC_DIR
from security.runtime_log import RUNTIME_LOG_PATH
from security.tool_telemetry import TOOL_TELEMETRY_PATH


def make_router(
    state: BridgeState,
    mounted_plugins: set,
    base_dir: Path,
    plugin_runtime: PluginRuntimeService,
    mounted_plugin_routes: dict[str, list[str]],
) -> APIRouter:
    """Create the control router."""
    router = APIRouter()

    plugin_catalog = PluginCatalogService(
        state=state,
        mounted_plugins=mounted_plugins,
        base_dir=base_dir,
        plugin_runtime=plugin_runtime,
        mounted_plugin_routes=mounted_plugin_routes,
    )
    ai_briefs = AIBriefService(base_dir=base_dir)
    control_tools = ControlToolService()
    logger_streams = LoggerStreamService(
        runtime_log_path=RUNTIME_LOG_PATH,
        tool_telemetry_path=TOOL_TELEMETRY_PATH,
        diagnostic_dir=DIAGNOSTIC_DIR,
    )
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

    @router.get("/api/debugwire/status")
    async def debugwire_get_status():
        return control_tools.debugwire_status()

    @router.post("/api/debugwire/toggle")
    async def debugwire_toggle(request: Request):
        body = await request.json()
        return await control_tools.debugwire_toggle(
            enabled=bool(body.get("enabled", False)),
            components=body.get("components"),
        )

    @router.get("/api/plugins")
    async def list_plugins():
        return await plugin_catalog.list_plugins()

    @router.post("/api/plugins/{plugin_id}/connect")
    async def plugin_connect(plugin_id: str):
        return await plugin_catalog.connect(plugin_id)

    @router.post("/api/plugins/{plugin_id}/disconnect")
    async def plugin_disconnect(plugin_id: str):
        return await plugin_catalog.disconnect(plugin_id)

    @router.post("/api/plugins/reorder")
    async def plugin_reorder(order: list[str]):
        return await plugin_catalog.reorder(order)

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

    @router.get("/api/control/loggers")
    async def list_loggers():
        return logger_streams.list_streams()

    @router.get("/api/control/loggers/{name}/tail")
    async def tail_logger(name: str, lines: int = 200):
        return logger_streams.tail(name, lines)

    @router.post("/api/control/loggers/{name}/toggle")
    async def toggle_logger(name: str, request: Request):
        body = await request.json()
        return logger_streams.toggle(name, bool(body.get("enabled", True)))

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
