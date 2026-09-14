"""6-1-6 Window Builder — sliding window co-occurrence analysis.

Ported from unzipped_cleanup/window_builder.py.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict

from wolf_engine.modules.base import WolfModule


class WindowBuilder:
    """Slides a 6-1-6 window over token streams and counts co-occurrences."""

    def __init__(self, window_size: int = 6):
        self.window_size = window_size
        self.lexicon_counts: Dict = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

    def process(self, tokens):
        """Slide 6-1-6 window over token stream and update counts."""
        token_list = list(tokens)
        for i, center_token in enumerate(token_list):
            center_norm = center_token["norm"]
            for j in range(1, self.window_size + 1):
                if i - j >= 0:
                    neighbor_norm = token_list[i - j]["norm"]
                    self.lexicon_counts[center_norm][-j][neighbor_norm] += 1
                if i + j < len(token_list):
                    neighbor_norm = token_list[i + j]["norm"]
                    self.lexicon_counts[center_norm][j][neighbor_norm] += 1

    def get_lexicon_counts(self):
        return self.lexicon_counts


class WindowBuilderModule(WolfModule):
    """WolfModule wrapper for 6-1-6 Window Builder."""

    key = "rsn_window_builder"
    name = "6-1-6 Window Builder"
    category = "reasoning"
    description = "Sliding 6-1-6 window co-occurrence analysis"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        ws = self._config.get("context_window_size", 6)
        self._builder = WindowBuilder(window_size=ws)

    def start(self):
        super().start()
        ws = self._config.get("context_window_size", 6)
        self._builder = WindowBuilder(window_size=ws)

    def process(self, tokens):
        """Delegate to the internal WindowBuilder."""
        return self._builder.process(tokens)

    def get_lexicon_counts(self):
        return self._builder.get_lexicon_counts()

    def info(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "window_size": self._builder.window_size,
        }
