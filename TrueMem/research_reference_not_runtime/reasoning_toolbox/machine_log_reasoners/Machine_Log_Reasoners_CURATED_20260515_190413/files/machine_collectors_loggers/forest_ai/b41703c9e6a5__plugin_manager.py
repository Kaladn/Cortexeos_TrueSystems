"""
Core module for discovering, loading, and managing plugins.
"""

import importlib
import json
from pathlib import Path

from core.events import event_stream

class PluginManager:
    """
    Manages the lifecycle of plugins within the Forest AI system.
    """

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.plugins_path = project_root / "plugins"
        self.plugins = {}
        self._discover_and_load_plugins()

    def _discover_and_load_plugins(self):
        """
        Scans the plugins directory, validates, and loads all found plugins.
        """
        event_stream.publish("plugin_manager.scan.start", "PluginManager", details={"path": str(self.plugins_path)})

        for plugin_dir in self.plugins_path.iterdir():
            if plugin_dir.is_dir() and (plugin_dir / "manifest.json").exists():
                self._load_plugin(plugin_dir)

        event_stream.publish("plugin_manager.scan.finish", "PluginManager", details={"loaded_count": len(self.plugins)})

    def _load_plugin(self, plugin_path: Path):
        """
        Loads a single plugin from its directory.
        """
        manifest_path = plugin_path / "manifest.json"
        plugin_name = plugin_path.name

        try:
            with open(manifest_path, "r") as f:
                manifest = json.load(f)

            # Validate manifest basic structure
            if "name" not in manifest or "version" not in manifest or "entry_point" not in manifest:
                raise ValueError("Manifest is missing required keys (name, version, entry_point).")

            entry_point_file = manifest["entry_point"]
            module_name = f"plugins.{plugin_name}.{entry_point_file.replace('.py', '')}"

            # Import the plugin module
            module = importlib.import_module(module_name)

            self.plugins[plugin_name] = {
                "manifest": manifest,
                "module": module,
                "path": plugin_path
            }

            event_stream.publish(
                "plugin.load.success", 
                "PluginManager", 
                details={"plugin": plugin_name, "version": manifest['version']}
            )

        except Exception as e:
            event_stream.publish(
                "plugin.load.failure", 
                "PluginManager", 
                level="ERROR", 
                details={"plugin": plugin_name, "error": str(e)}
            )

    def get_all_plugins(self):
        return self.plugins

    def get_plugin(self, name: str):
        return self.plugins.get(name)

