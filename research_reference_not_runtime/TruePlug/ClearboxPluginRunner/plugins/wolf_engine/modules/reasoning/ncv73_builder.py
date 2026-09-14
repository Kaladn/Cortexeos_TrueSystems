"""NCV-73 Builder — 73-dimensional neighbor context vectors.

Ported from unzipped_cleanup/ncv73_builder.py.
"""

from __future__ import annotations

from typing import Any, Dict

from wolf_engine.modules.base import WolfModule

try:
    import numpy as np
except ImportError:
    np = None


class NCV73Builder:
    """Constructs 73-dimensional neighbor context vectors from lexicon counts."""

    def __init__(self, window_size: int = 6, max_possibilities: int = 50):
        self.window_size = window_size
        self.max_possibilities = max_possibilities

    def build_lexicon(self, lexicon_counts):
        """Build final lexicon with top-k neighbors per offset."""
        lexicon = {}
        for word, offsets in lexicon_counts.items():
            lexicon[word] = {}
            for offset, neighbors in offsets.items():
                sorted_neighbors = sorted(neighbors.items(), key=lambda item: item[1], reverse=True)
                lexicon[word][offset] = sorted_neighbors[: self.max_possibilities]
        return lexicon

    def build_ncv(self, word, lexicon):
        """Build a single NCV-73 vector for a word."""
        if np is None:
            return [0.0] * 73
        ncv = np.zeros(73)
        if word in lexicon:
            for offset in range(-self.window_size, self.window_size + 1):
                idx = 36 + offset
                if offset == 0:
                    ncv[idx] = 1  # Anchor
                elif offset in lexicon[word]:
                    ncv[idx] = 1
        return ncv


class Ncv73Module(WolfModule):
    """WolfModule wrapper for NCV-73 Builder."""

    key = "rsn_ncv73"
    name = "NCV-73 Builder"
    category = "reasoning"
    description = "73-dimensional neighbor context vectors"

    def __init__(self, config: Dict[str, Any] | None = None):
        super().__init__(config)
        ws = self._config.get("context_window_size", 6)
        mp = self._config.get("max_possibilities_per_slot", 50)
        self._builder = NCV73Builder(window_size=ws, max_possibilities=mp)

    def build_lexicon(self, lexicon_counts):
        return self._builder.build_lexicon(lexicon_counts)

    def build_ncv(self, word, lexicon):
        return self._builder.build_ncv(word, lexicon)

    def info(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "window_size": self._builder.window_size,
            "numpy_available": np is not None,
        }
