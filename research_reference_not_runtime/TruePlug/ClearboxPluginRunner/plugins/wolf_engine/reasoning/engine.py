"""
6-1-6 Reasoning Engine — Two-pass streaming analysis over SymbolEvents.

Adapted from unzipped_cleanup/engine.py (UnifiedEngine). Rewired to use
wolf_engine contracts (uint64 symbol_id) instead of string symbols.

Pass 1: Build lifetime co-occurrence counts from the event stream.
Pass 2: Build 6-1-6 windows and compute position-weighted resonance.

The engine reads from ForgeMemory (or a list of SymbolEvents) and produces
Window objects that downstream analyzers consume.
"""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from wolf_engine.contracts import SymbolEvent
from wolf_engine.forge.forge_memory import ForgeMemory

logger = logging.getLogger(__name__)

WINDOW_SIZE = 6  # 6-1-6


@dataclass(slots=True)
class Window:
    """A 6-1-6 context window around an anchor symbol."""

    anchor_id: int = 0
    anchor_index: int = 0
    preceding: list[int] = field(default_factory=list)   # up to 6 symbol_ids before
    following: list[int] = field(default_factory=list)    # up to 6 symbol_ids after
    resonance: dict[int, float] = field(default_factory=dict)  # symbol_id → resonance score

    def all_context_ids(self) -> list[int]:
        return self.preceding + self.following


@dataclass(slots=True)
class EngineResult:
    """Output of the reasoning engine for a session analysis."""

    windows: list[Window] = field(default_factory=list)
    lifetime_counts: dict[int, Counter] = field(default_factory=dict)
    resonance_map: dict[int, float] = field(default_factory=dict)
    total_events: int = 0


class ReasoningEngine:
    """
    Two-pass 6-1-6 streaming reasoning engine.

    Processes a sequence of SymbolEvents, building co-occurrence
    lifetime counts (pass 1) and 6-1-6 windows with resonance (pass 2).
    """

    def __init__(self, window_size: int = WINDOW_SIZE, top_k: int = 10):
        self.window_size = window_size
        self.top_k = top_k

    def analyze(self, events: list[SymbolEvent]) -> EngineResult:
        """
        Run full two-pass analysis on a list of SymbolEvents.

        Returns an EngineResult with windows, lifetime counts, and resonance.
        """
        if not events:
            return EngineResult()

        symbol_ids = [e.symbol_id for e in events]

        # Pass 1: lifetime co-occurrence counts
        lifetime_counts = self._build_lifetime_counts(symbol_ids)

        # Pass 2: build windows and compute resonance
        windows = self._build_windows(symbol_ids, lifetime_counts)

        # Aggregate resonance map
        resonance_map: dict[int, float] = defaultdict(float)
        for w in windows:
            for sid, score in w.resonance.items():
                resonance_map[sid] = max(resonance_map[sid], score)

        result = EngineResult(
            windows=windows,
            lifetime_counts=lifetime_counts,
            resonance_map=dict(resonance_map),
            total_events=len(events),
        )

        logger.info(
            "ReasoningEngine: %d events → %d windows, %d unique resonance entries",
            len(events), len(windows), len(resonance_map),
        )
        return result

    def analyze_from_forge(self, forge: ForgeMemory) -> EngineResult:
        """
        Analyze events currently in Forge's working memory.

        Extracts the event stream from forge.symbols and forge.event_queue.
        """
        # Reconstruct event order from the event_queue (deque of symbol_ids)
        events = []
        for sid in forge.event_queue:
            se = forge.symbols.get(sid)
            if se is not None:
                events.append(se)
        return self.analyze(events)

    def _build_lifetime_counts(self, symbol_ids: list[int]) -> dict[int, Counter]:
        """Pass 1: count co-occurrences at each offset within the window."""
        counts: dict[int, Counter] = defaultdict(Counter)
        n = len(symbol_ids)

        for i in range(n):
            focus = symbol_ids[i]
            # Forward window
            for j in range(i + 1, min(i + self.window_size + 1, n)):
                counts[focus][symbol_ids[j]] += 1
            # Backward window
            for j in range(max(0, i - self.window_size), i):
                counts[focus][symbol_ids[j]] += 1

        return dict(counts)

    def _build_windows(
        self,
        symbol_ids: list[int],
        lifetime_counts: dict[int, Counter],
    ) -> list[Window]:
        """Pass 2: build 6-1-6 windows with position-weighted resonance."""
        n = len(symbol_ids)
        windows = []

        for i in range(n):
            anchor = symbol_ids[i]
            preceding = symbol_ids[max(0, i - self.window_size): i]
            following = symbol_ids[i + 1: i + 1 + self.window_size]

            # Compute resonance for each context symbol
            resonance: dict[int, float] = {}
            for offset, sid in enumerate(reversed(preceding), 1):
                weight = 1.0 - 0.8 * (offset / self.window_size)
                co_count = lifetime_counts.get(anchor, Counter()).get(sid, 0)
                resonance[sid] = co_count * weight

            for offset, sid in enumerate(following, 1):
                weight = 1.0 - 0.8 * (offset / self.window_size)
                co_count = lifetime_counts.get(anchor, Counter()).get(sid, 0)
                existing = resonance.get(sid, 0.0)
                resonance[sid] = max(existing, co_count * weight)

            windows.append(Window(
                anchor_id=anchor,
                anchor_index=i,
                preceding=preceding,
                following=following,
                resonance=resonance,
            ))

        return windows

    def get_statistics(self, result: EngineResult) -> dict[str, Any]:
        """Return summary statistics for an analysis result."""
        if not result.windows:
            return {"total_events": 0, "total_windows": 0}

        avg_context = sum(
            len(w.preceding) + len(w.following) for w in result.windows
        ) / len(result.windows)

        return {
            "total_events": result.total_events,
            "total_windows": len(result.windows),
            "unique_symbols": len(result.lifetime_counts),
            "avg_context_size": round(avg_context, 2),
            "top_resonance": sorted(
                result.resonance_map.items(), key=lambda x: x[1], reverse=True
            )[:self.top_k],
        }
