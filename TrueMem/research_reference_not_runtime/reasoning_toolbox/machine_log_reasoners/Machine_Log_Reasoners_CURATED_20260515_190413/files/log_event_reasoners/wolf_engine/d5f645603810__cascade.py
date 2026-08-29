"""Cascade Engine — WolfModule wrapper for wolf_engine.reasoning.cascade_engine."""

from __future__ import annotations

from typing import Any, Dict

from wolf_engine.modules.base import WolfModule


class CascadeEngineModule(WolfModule):
    """WolfModule wrapper for CascadeEngine reasoning engine."""

    key = "rsn_cascade"
    name = "Cascade Engine"
    category = "reasoning"
    description = "BFS trace on co-occurrence graph"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        self._engine_cls = None

    def start(self):
        super().start()
        try:
            from wolf_engine.reasoning.cascade_engine import CascadeEngine
            self._engine_cls = CascadeEngine
        except ImportError:
            pass

    def get_engine(self, forge, max_depth: int = 5):
        """Get a CascadeEngine bound to a specific forge."""
        if self._engine_cls is None:
            from wolf_engine.reasoning.cascade_engine import CascadeEngine
            self._engine_cls = CascadeEngine
        return self._engine_cls(forge, max_depth=max_depth)

    def info(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "category": self.category,
            "description": self.description,
        }
