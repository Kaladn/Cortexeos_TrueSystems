"""Pattern Detector — WolfModule wrapper for wolf_engine.reasoning.pattern_detector."""

from __future__ import annotations

from typing import Any, Dict

from wolf_engine.modules.base import WolfModule


class PatternDetectorModule(WolfModule):
    """WolfModule wrapper for PatternDetector reasoning engine."""

    key = "rsn_pattern"
    name = "Pattern Detector"
    category = "reasoning"
    description = "Z-score pattern breaks, consistency chains, anomalies"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        self._detector = None

    def start(self):
        super().start()
        try:
            from wolf_engine.reasoning.pattern_detector import PatternDetector
            self._detector = PatternDetector()
        except ImportError:
            pass

    @property
    def detector(self):
        if self._detector is None:
            from wolf_engine.reasoning.pattern_detector import PatternDetector
            self._detector = PatternDetector()
        return self._detector

    def info(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "category": self.category,
            "description": self.description,
        }
