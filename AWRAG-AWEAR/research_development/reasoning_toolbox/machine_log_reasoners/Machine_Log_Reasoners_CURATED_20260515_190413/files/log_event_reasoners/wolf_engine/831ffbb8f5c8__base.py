"""Wolf Module — Abstract base class for all toggleable modules.

Every operator, logger, and reasoning engine extends this.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class WolfModule(ABC):
    """Base class for a toggleable Wolf Engine module."""

    key: str = ""           # e.g. "op_crosshair_lock"
    name: str = ""          # e.g. "Crosshair Lock Operator"
    category: str = ""      # "operator", "logger", "reasoning"
    description: str = ""   # One-line description

    def __init__(self, config: Dict[str, Any] | None = None):
        self._config = config or {}
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Start the module (for long-running modules like loggers)."""
        self._running = True

    def stop(self) -> None:
        """Stop the module."""
        self._running = False

    def status(self) -> Dict[str, Any]:
        """Return current module status."""
        return {
            "key": self.key,
            "name": self.name,
            "category": self.category,
            "running": self._running,
        }

    @abstractmethod
    def info(self) -> Dict[str, Any]:
        """Return module metadata for the registry listing."""
        ...
