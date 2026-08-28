"""Wolf Module Registry — discover, toggle, and query modules.

Config-driven: reads enabled state from config["modules"] dict.
Modules are lazy-loaded on first access.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from wolf_engine.modules.base import WolfModule

logger = logging.getLogger(__name__)


# ── Module Catalog ───────────────────────────────────────────
# Static catalog of all known modules. Each entry maps a key to
# (import_path, class_name, display_name, category, description).
# Actual import happens lazily in _load_module().

_CATALOG: List[Dict[str, str]] = [
    # Operators (TrueVision frame analysis)
    {
        "key": "op_crosshair_lock",
        "name": "Crosshair Lock",
        "category": "operator",
        "module_path": "wolf_engine.modules.operators.crosshair_lock",
        "class_name": "CrosshairLockModule",
        "description": "Detects crosshair lock-on patterns in frame sequences",
    },
    {
        "key": "op_edge_entry",
        "name": "Edge Entry",
        "category": "operator",
        "module_path": "wolf_engine.modules.operators.edge_entry",
        "class_name": "EdgeEntryModule",
        "description": "Detects enemy spawn/entry patterns at screen edges",
    },
    {
        "key": "op_thermal_hitbox",
        "name": "Thermal Hitbox",
        "category": "operator",
        "module_path": "wolf_engine.modules.operators.thermal_hitbox",
        "class_name": "ThermalHitboxModule",
        "description": "Analyzes thermal buffer for hitbox manipulation",
    },
    {
        "key": "op_eomm",
        "name": "EOMM Compositor",
        "category": "operator",
        "module_path": "wolf_engine.modules.operators.eomm_compositor",
        "class_name": "EommModule",
        "description": "Aggregates operator results into unified telemetry window",
    },
    # Loggers (evidence capture)
    {
        "key": "log_system_perf",
        "name": "System Perf",
        "category": "logger",
        "module_path": "wolf_engine.modules.loggers.system_perf",
        "class_name": "SystemPerfModule",
        "description": "CPU/RAM/GPU metrics via psutil",
    },
    {
        "key": "log_network",
        "name": "Network Logger",
        "category": "logger",
        "module_path": "wolf_engine.modules.loggers.network",
        "class_name": "NetworkModule",
        "description": "Inter-node ping and packet loss",
    },
    {
        "key": "log_process",
        "name": "Process Logger",
        "category": "logger",
        "module_path": "wolf_engine.modules.loggers.process",
        "class_name": "ProcessModule",
        "description": "Running processes and suspicious flags",
    },
    {
        "key": "log_input",
        "name": "Input Logger",
        "category": "logger",
        "module_path": "wolf_engine.modules.loggers.input_logger",
        "class_name": "InputModule",
        "description": "Aggregate input patterns",
    },
    {
        "key": "log_camera_movement",
        "name": "Camera Movement",
        "category": "logger",
        "module_path": "wolf_engine.modules.loggers.camera_movement",
        "class_name": "CameraMovementModule",
        "description": "Camera direction, speed, snap detection",
    },
    {
        "key": "log_ads_detector",
        "name": "ADS Detector",
        "category": "logger",
        "module_path": "wolf_engine.modules.loggers.ads_detector",
        "class_name": "AdsDetectorModule",
        "description": "FOV ratio and scope state tracking",
    },
    {
        "key": "log_trigger_pull",
        "name": "Trigger Pull",
        "category": "logger",
        "module_path": "wolf_engine.modules.loggers.trigger_pull",
        "class_name": "TriggerPullModule",
        "description": "Muzzle flash and trigger event logging",
    },
    {
        "key": "log_movement_state",
        "name": "Movement State",
        "category": "logger",
        "module_path": "wolf_engine.modules.loggers.movement_state",
        "class_name": "MovementStateModule",
        "description": "Velocity, stance, and movement state tracking",
    },
    # Reasoning engines
    {
        "key": "rsn_window_builder",
        "name": "6-1-6 Window Builder",
        "category": "reasoning",
        "module_path": "wolf_engine.modules.reasoning.window_builder",
        "class_name": "WindowBuilderModule",
        "description": "Sliding 6-1-6 window co-occurrence analysis",
    },
    {
        "key": "rsn_ncv73",
        "name": "NCV-73 Builder",
        "category": "reasoning",
        "module_path": "wolf_engine.modules.reasoning.ncv73_builder",
        "class_name": "Ncv73Module",
        "description": "73-dimensional neighbor context vectors",
    },
    {
        "key": "rsn_arc",
        "name": "ARC Frame Grid",
        "category": "reasoning",
        "module_path": "wolf_engine.modules.reasoning.frame_to_grid",
        "class_name": "ArcModule",
        "description": "Frame to 32x32 quantized grid (ARC reasoning)",
    },
    {
        "key": "rsn_causal",
        "name": "Causal Analyzer",
        "category": "reasoning",
        "module_path": "wolf_engine.modules.reasoning.causal",
        "class_name": "CausalAnalyzerModule",
        "description": "Backward/forward causal validation on windows",
    },
    {
        "key": "rsn_pattern",
        "name": "Pattern Detector",
        "category": "reasoning",
        "module_path": "wolf_engine.modules.reasoning.pattern",
        "class_name": "PatternDetectorModule",
        "description": "Z-score pattern breaks, consistency chains, anomalies",
    },
    {
        "key": "rsn_cascade",
        "name": "Cascade Engine",
        "category": "reasoning",
        "module_path": "wolf_engine.modules.reasoning.cascade",
        "class_name": "CascadeEngineModule",
        "description": "BFS trace on co-occurrence graph",
    },
]


class ModuleRegistry:
    """Manages the catalog of toggleable Wolf Engine modules."""

    def __init__(self, config: Dict[str, Any] | None = None):
        self._config = config or {}
        self._module_config = self._config.get("modules", {})
        self._instances: Dict[str, WolfModule] = {}

    def list_modules(self) -> List[Dict[str, Any]]:
        """Return all modules with their enabled state."""
        result = []
        for entry in _CATALOG:
            key = entry["key"]
            result.append({
                "key": key,
                "name": entry["name"],
                "category": entry["category"],
                "description": entry["description"],
                "enabled": self._module_config.get(key, False),
                "loaded": key in self._instances,
            })
        return result

    def toggle(self, key: str, enabled: bool) -> Dict[str, Any]:
        """Enable or disable a module by key."""
        entry = self._find_entry(key)
        if entry is None:
            return {"error": f"Unknown module: {key}"}

        self._module_config[key] = enabled

        if not enabled and key in self._instances:
            try:
                self._instances[key].stop()
            except Exception:
                pass
            del self._instances[key]

        return {
            "key": key,
            "enabled": enabled,
            "name": entry["name"],
        }

    def get_enabled(self, category: str | None = None) -> List[Dict[str, str]]:
        """Get list of enabled module entries, optionally filtered by category."""
        result = []
        for entry in _CATALOG:
            if self._module_config.get(entry["key"], False):
                if category is None or entry["category"] == category:
                    result.append(entry)
        return result

    def get_instance(self, key: str) -> Optional[WolfModule]:
        """Get or lazy-load a module instance."""
        if key in self._instances:
            return self._instances[key]

        entry = self._find_entry(key)
        if entry is None:
            return None

        if not self._module_config.get(key, False):
            return None  # Not enabled

        instance = self._load_module(entry)
        if instance is not None:
            self._instances[key] = instance
        return instance

    def _find_entry(self, key: str) -> Optional[Dict[str, str]]:
        for entry in _CATALOG:
            if entry["key"] == key:
                return entry
        return None

    def _load_module(self, entry: Dict[str, str]) -> Optional[WolfModule]:
        """Lazy-import and instantiate a module."""
        try:
            import importlib
            mod = importlib.import_module(entry["module_path"])
            cls = getattr(mod, entry["class_name"])
            return cls(config=self._config)
        except (ImportError, AttributeError) as e:
            logger.warning(
                "Failed to load module %s (%s.%s): %s",
                entry["key"], entry["module_path"], entry["class_name"], e,
            )
            return None
