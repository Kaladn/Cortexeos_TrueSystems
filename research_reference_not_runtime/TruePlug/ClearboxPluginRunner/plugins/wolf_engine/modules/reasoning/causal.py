"""Causal Analyzer — WolfModule wrapper for wolf_engine.reasoning.causal_analyzer."""

from __future__ import annotations

from typing import Any, Dict

from wolf_engine.modules.base import WolfModule


class CausalAnalyzerModule(WolfModule):
    """WolfModule wrapper for CausalAnalyzer reasoning engine."""

    key = "rsn_causal"
    name = "Causal Analyzer"
    category = "reasoning"
    description = "Backward/forward causal validation on windows"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        self._analyzer = None

    def start(self):
        super().start()
        try:
            from wolf_engine.reasoning.causal_analyzer import CausalAnalyzer
            # CausalAnalyzer needs a forge instance — deferred to usage
            self._analyzer = CausalAnalyzer
        except ImportError:
            pass

    def get_analyzer(self, forge):
        """Get a CausalAnalyzer bound to a specific forge."""
        if self._analyzer is None:
            from wolf_engine.reasoning.causal_analyzer import CausalAnalyzer
            self._analyzer = CausalAnalyzer
        return self._analyzer(forge)

    def info(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "category": self.category,
            "description": self.description,
        }
