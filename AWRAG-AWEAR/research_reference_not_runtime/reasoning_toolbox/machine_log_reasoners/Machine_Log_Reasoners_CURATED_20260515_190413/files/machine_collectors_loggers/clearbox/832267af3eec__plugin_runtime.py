"""Runtime plugin discovery and router mounting service."""
from __future__ import annotations

import ast
import importlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI


LOGGER = logging.getLogger("clearbox_bridge.plugins")


@dataclass(frozen=True)
class PluginDescriptor:
    """Filesystem + import metadata for one plugin package."""

    plugin_id: str
    package_dir: Path
    import_root: str
    name: str
    description: str
    version: str
    candidate_router_modules: tuple[str, ...]


class PluginRuntimeService:
    """Discovers installed plugins and mounts their routers."""

    def __init__(self, *, base_dir: Path) -> None:
        self.base_dir = base_dir
        self._mounted_routes: dict[str, list[str]] = {}

    @property
    def mounted_routes(self) -> dict[str, list[str]]:
        return self._mounted_routes

    def discover(self) -> list[PluginDescriptor]:
        discovered: dict[str, PluginDescriptor] = {}
        for entry in self._iter_plugin_package_dirs():
            if entry.name in discovered:
                continue
            plugin_id = entry.name
            name, description, version = self._parse_package_metadata(entry / "__init__.py", plugin_id)
            discovered[plugin_id] = PluginDescriptor(
                plugin_id=plugin_id,
                package_dir=entry,
                import_root=plugin_id,
                name=name,
                description=description,
                version=version,
                candidate_router_modules=tuple(self._discover_router_modules(entry, plugin_id)),
            )
        return [discovered[k] for k in sorted(discovered)]

    def mount_all(self, *, app: FastAPI, mounted_plugins: set[str]) -> dict[str, list[str]]:
        mounted_plugins.clear()
        mounted_routes: dict[str, list[str]] = {}
        for plugin in self.discover():
            routes_for_plugin: list[str] = []
            for module_name in plugin.candidate_router_modules:
                router = self._load_router(module_name)
                if router is None:
                    continue
                app.include_router(router)
                prefix = (getattr(router, "prefix", "") or "").strip()
                routes_for_plugin.append(prefix or module_name)
                LOGGER.info("Plugin router mounted: %s (%s)", plugin.plugin_id, module_name)

            if routes_for_plugin:
                mounted_plugins.add(plugin.plugin_id)
                mounted_routes[plugin.plugin_id] = routes_for_plugin
            else:
                mounted_routes[plugin.plugin_id] = []
                LOGGER.info("Plugin discovered but idle: %s", plugin.plugin_id)

        self._mounted_routes = mounted_routes
        return mounted_routes

    def _iter_plugin_package_dirs(self) -> list[Path]:
        out: list[Path] = []
        plugins_dir = self.base_dir / "plugins"
        if plugins_dir.is_dir():
            for path in sorted(plugins_dir.iterdir()):
                if self._is_package_dir(path):
                    out.append(path)

        # Support root-level plugin packages without hardcoding names.
        for path in sorted(self.base_dir.iterdir()):
            if not self._is_package_dir(path):
                continue
            if path.parent == plugins_dir:
                continue
            if (path / "router.py").exists() or (path / "api" / "router.py").exists():
                out.append(path)
        return out

    @staticmethod
    def _is_package_dir(path: Path) -> bool:
        return (
            path.is_dir()
            and not path.name.startswith((".", "_"))
            and (path / "__init__.py").exists()
        )

    @staticmethod
    def _parse_package_metadata(init_path: Path, plugin_id: str) -> tuple[str, str, str]:
        default_name = plugin_id.replace("_", " ").title()
        if not init_path.exists():
            return default_name, "", "unknown"
        try:
            src = init_path.read_text(encoding="utf-8")
            module = ast.parse(src, filename=str(init_path))
        except Exception:
            return default_name, "", "unknown"

        doc = (ast.get_docstring(module) or "").strip()
        first_line = doc.splitlines()[0].strip() if doc else ""
        title = first_line.split(" -- ")[0].split(" — ")[0].strip()
        name = title or default_name
        description = first_line if first_line else ""

        version = "unknown"
        for node in module.body:
            if not isinstance(node, ast.Assign):
                continue
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                continue
            key = node.targets[0].id
            if key not in {"VERSION", "PLUGIN_VERSION"}:
                continue
            value = PluginRuntimeService._const_str(node.value)
            if value:
                version = value
                break

        return name, description, version

    @staticmethod
    def _const_str(node: ast.AST) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def _discover_router_modules(self, package_dir: Path, import_root: str) -> list[str]:
        modules: list[str] = []
        api_dir = package_dir / "api"
        if (api_dir / "router.py").exists():
            modules.append(f"{import_root}.api.router")
        if (package_dir / "router.py").exists():
            modules.append(f"{import_root}.router")

        if api_dir.is_dir():
            for py_file in sorted(api_dir.glob("*.py")):
                if py_file.name in {"__init__.py", "router.py"}:
                    continue
                if not self._declares_router(py_file):
                    continue
                modules.append(f"{import_root}.api.{py_file.stem}")

        # Keep stable order while deduping.
        seen: set[str] = set()
        out: list[str] = []
        for name in modules:
            if name in seen:
                continue
            seen.add(name)
            out.append(name)
        return out

    @staticmethod
    def _declares_router(path: Path) -> bool:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            return False
        return "APIRouter" in text and ("router = APIRouter" in text or "@router." in text)

    @staticmethod
    def _load_router(module_name: str) -> APIRouter | None:
        try:
            module = importlib.import_module(module_name)
        except ImportError as exc:
            LOGGER.info("Plugin module unavailable: %s (%s)", module_name, exc)
            return None
        except Exception as exc:
            LOGGER.warning("Plugin module load failed: %s (%s)", module_name, exc)
            return None

        router: Any = getattr(module, "router", None)
        if isinstance(router, APIRouter):
            return router
        return None
