"""System info/boot payload/warmup service."""
from __future__ import annotations

import platform
import subprocess as _sp
import time as _time
from pathlib import Path
from typing import Any

from bridges.services.plugin_runtime import PluginRuntimeService
from bridges.state import BridgeState
from bridges.ws_manager import WebSocketManager
from core.lakespeak.storage import iter_receipt_dirs


class SystemInfoService:
    """Owns system metadata shaping and boot payload assembly."""

    def __init__(
        self,
        *,
        state: BridgeState,
        ws_manager: WebSocketManager,
        metrics: dict[str, Any],
        mounted_plugins: set[str],
        base_dir: Path,
        version: str,
        plugin_runtime: PluginRuntimeService,
        mounted_plugin_routes: dict[str, list[str]],
    ) -> None:
        self.state = state
        self.ws_manager = ws_manager
        self.metrics = metrics
        self.mounted_plugins = mounted_plugins
        self.base_dir = base_dir
        self.version = version
        self.plugin_runtime = plugin_runtime
        self.mounted_plugin_routes = mounted_plugin_routes

    def metrics_snapshot(self) -> dict[str, Any]:
        out: dict[str, Any] = {"started_at": self.metrics["started_at"], "by_path": {}}
        for path, row in self.metrics["by_path"].items():
            count = row["count"] or 1
            out["by_path"][path] = {
                "count": row["count"],
                "errors": row["errors"],
                "avg_latency_ms": round(row["latency_ms_sum"] / count, 2),
            }
        return out

    async def warmup_ollama(self) -> dict[str, str]:
        from routing.config import DEFAULTS as _ROUTING_DEFAULTS

        default_model = _ROUTING_DEFAULTS["pipeline"][2]["config"]["model"]
        ollama_base = self.state.get_ollama_base_url()
        try:
            model_name = self.state.config.get("model", default_model)
            client = await self.state.get_ollama_client()
            resp = await client.post(
                f"{ollama_base}/api/generate",
                json={
                    "model": model_name,
                    "prompt": ".",
                    "stream": False,
                    "keep_alive": "5m",
                    "options": {"num_predict": 1},
                },
            )
            return {"status": "ready" if resp.is_success else "error"}
        except Exception:
            return {"status": "warming"}

    async def system_info(self) -> dict[str, Any]:
        stats = await self.state.stats_snapshot()
        bridge_dev = self.state.bridge.device_info
        device_type = stats.get("device_used") or (bridge_dev.type if bridge_dev else "none")
        device_name = stats.get("device_name") or (bridge_dev.name if bridge_dev else "none")

        info = {
            "version": self.version,
            "platform": platform.system(),
            "python_version": platform.python_version(),
            "lexicon_loaded": bool(stats.get("loaded")),
            "lexicon_entries": int(stats.get("entries", 0)),
            "device_type": device_type,
            "device_name": device_name,
        }
        try:
            import psutil

            mem = psutil.virtual_memory()
            info["memory_percent"] = mem.percent
            info["memory_available_gb"] = round(mem.available / (1024**3), 2)
        except ImportError:
            pass
        return info

    def _plugin_flags(self) -> dict[str, bool]:
        installed = {p.plugin_id for p in self.plugin_runtime.discover()}
        keys = sorted(installed | set(self.mounted_plugins))
        return {pid: pid in self.mounted_plugins for pid in keys}

    @staticmethod
    def _health_aliases(plugin_id: str) -> set[str]:
        aliases = {plugin_id}
        parts = plugin_id.split("_")
        if len(parts) > 1 and parts[-1] in {"engine", "plugin", "service"}:
            aliases.add("_".join(parts[:-1]))
        if plugin_id.startswith("clearbox_"):
            aliases.add(plugin_id.removeprefix("clearbox_"))
        if plugin_id.endswith("node"):
            aliases.add("nodes")
        return {a for a in aliases if a}

    async def boot_payload(self) -> dict[str, Any]:
        stats = await self.state.stats_snapshot()
        stats["version"] = self.version
        system = await self.system_info()

        try:
            import psutil

            system["os_boot_time"] = psutil.boot_time()
        except ImportError:
            pass
        system["bridge_started_at"] = self.metrics.get("started_at", _time.time())

        plugin_flags = self._plugin_flags()
        health: dict[str, Any] = {
            "bridge": True,
            "reasoning": self.state.reasoning_service.is_available(),
        }
        for pid, is_mounted in plugin_flags.items():
            for alias in self._health_aliases(pid):
                health[alias] = is_mounted

        active_ws = len(self.ws_manager.active)
        data_lake_files = 0
        try:
            data_lake_files = sum(1 for _corpus_id, path in iter_receipt_dirs() if (path / "chunks.jsonl").exists())
        except Exception:
            data_lake_files = 0

        origin = {"workspace": str(self.base_dir)}
        try:
            commit = _sp.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=str(self.base_dir),
                stderr=_sp.DEVNULL,
                timeout=2,
            ).decode().strip()
            origin["commit"] = commit
            commit_date = _sp.check_output(
                ["git", "log", "-1", "--format=%ci", "--short"],
                cwd=str(self.base_dir),
                stderr=_sp.DEVNULL,
                timeout=2,
            ).decode().strip()
            origin["commit_date"] = commit_date
        except Exception:
            origin["commit"] = origin.get("commit", "unknown")

        return {
            "stats": stats,
            "system": system,
            "health": health,
            "services": health,
            "plugins": plugin_flags,
            "active_ws": active_ws,
            "ws_connections": active_ws,
            "data_lake_files": data_lake_files,
            "origin": origin,
        }
