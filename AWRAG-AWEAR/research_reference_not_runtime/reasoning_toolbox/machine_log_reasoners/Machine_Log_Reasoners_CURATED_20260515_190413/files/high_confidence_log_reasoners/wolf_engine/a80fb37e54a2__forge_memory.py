"""
Forge Memory (Refactored)
RAM-only working memory for symbols. No persistence, no lexicons, no strings.

Constraints:
  - Forge MUST NOT load Symbol Genome dictionary
  - Forge MUST NOT hash strings or tokens
  - Forge MUST NOT touch raw tokens (only symbol_id)
  - Forge MUST NOT write to disk (RAM-only)
  - Forge MUST NOT expand meaning or cascades

  - Forge MUST accept only SymbolEvent objects
  - Forge MUST use uint64 symbol_id as primary key
  - Forge MUST maintain bounded window (evict old events)
  - Forge MUST provide fast query by symbol_id
"""

from __future__ import annotations

import hashlib
import threading
from collections import Counter, defaultdict, deque
from typing import Optional

from wolf_engine.contracts import ForgeStats, QueryResult, SymbolEvent


class ForgeMemory:
    """RAM-only working memory for symbols with bounded window."""

    def __init__(self, window_size: int = 10000):
        self._lock = threading.RLock()

        # All keyed by uint64 symbol_id
        self.symbols: dict[int, SymbolEvent] = {}
        self.co_occurrence: dict[int, Counter] = defaultdict(Counter)
        self.resonance: dict[int, float] = defaultdict(float)
        self.chains: dict[str, list[int]] = {}

        # Bounded window
        self.window_size = window_size
        self.event_queue: deque[int] = deque()

    def ingest(self, symbol_event: SymbolEvent) -> None:
        """Ingest a symbol event into working memory."""
        with self._lock:
            symbol_id = symbol_event.symbol_id

            # 1. Store symbol event
            self.symbols[symbol_id] = symbol_event

            # 2. Update resonance
            self.resonance[symbol_id] += 1.0

            # 3. Update co-occurrence
            for context_symbol_id in symbol_event.context_symbols:
                self.co_occurrence[symbol_id][context_symbol_id] += 1

            # 4. Add to event queue
            self.event_queue.append(symbol_id)

            # 5. Evict if window exceeded
            if len(self.event_queue) > self.window_size:
                evicted_symbol_id = self.event_queue.popleft()
                # LOCKED POLICY: Evict full event, keep resonance/co-occurrence
                # Forge is thinking, not forgetting history
                if evicted_symbol_id in self.symbols:
                    del self.symbols[evicted_symbol_id]
                # DO NOT decrement resonance or co_occurrence

    def build_chains(self, top_k: int = 10) -> None:
        """Build co-occurrence chains from symbol neighbors."""
        with self._lock:
            self.chains.clear()
            for symbol_id, neighbors in self.co_occurrence.items():
                top_neighbors = neighbors.most_common(top_k)
                chain = [symbol_id] + [neighbor_id for neighbor_id, _ in top_neighbors]
                chain_key = hashlib.md5(
                    str(tuple(chain)).encode("utf-8")
                ).hexdigest()
                self.chains[chain_key] = chain

    def query(self, symbol_id: int) -> Optional[QueryResult]:
        """Query working memory by symbol_id."""
        with self._lock:
            symbol_event = self.symbols.get(symbol_id)
            if symbol_event is None:
                return None

            neighbors = self.co_occurrence.get(symbol_id, Counter())
            resonance_score = self.resonance.get(symbol_id, 0.0)
            chains = [chain for chain in self.chains.values() if symbol_id in chain]

            return QueryResult(
                symbol_id=symbol_id,
                symbol_event=symbol_event,
                neighbors=dict(neighbors),
                resonance=resonance_score,
                chains=chains,
            )

    def reload_from_events(self, events: list[SymbolEvent]) -> None:
        """Clear all state and rebuild from a list of symbol events."""
        with self._lock:
            self.symbols.clear()
            self.co_occurrence.clear()
            self.resonance.clear()
            self.chains.clear()
            self.event_queue.clear()
        # Ingest each event (ingest() acquires lock internally via RLock)
        for event in events:
            self.ingest(event)

    def stats(self) -> ForgeStats:
        """Return current Forge statistics."""
        with self._lock:
            avg_resonance = 0.0
            if self.resonance:
                avg_resonance = sum(self.resonance.values()) / len(self.resonance)

            return ForgeStats(
                total_symbols=len(self.symbols),
                total_chains=len(self.chains),
                avg_resonance=avg_resonance,
                window_size=self.window_size,
                current_size=len(self.event_queue),
            )
