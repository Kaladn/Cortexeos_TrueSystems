"""
GNOME Service
Main service that processes RawAnchors into SymbolEvents.
"""

from __future__ import annotations

import logging
from typing import Optional

from wolf_engine.contracts import RawAnchor, SymbolEvent
from wolf_engine.gnome.integrity import compute_integrity_hash
from wolf_engine.gnome.symbol_genome_loader import SymbolGenomeLoader
from wolf_engine.gnome.symbolizer import symbolize_context, symbolize_token

logger = logging.getLogger(__name__)


class GnomeFailure(Exception):
    """Raised when GNOME processing fails."""
    pass


class GnomeService:
    """Processes RawAnchors into SymbolEvents via the Symbol Genome."""

    def __init__(self, genome_path: str):
        try:
            self.genome = SymbolGenomeLoader(genome_path)
        except Exception as exc:
            raise GnomeFailure(f"Symbol Genome not found: {exc}") from exc
        self._collision_registry: dict[int, str] = {}

    def process_anchor(self, raw_anchor: RawAnchor) -> SymbolEvent:
        """Convert a RawAnchor into a SymbolEvent."""
        try:
            # 1. Symbolize token
            symbol_data = symbolize_token(raw_anchor.token, self.genome)

            # 2. Symbolize context
            context_before_symbols = symbolize_context(
                raw_anchor.context_before, self.genome
            )
            context_after_symbols = symbolize_context(
                raw_anchor.context_after, self.genome
            )
            context_symbols = context_before_symbols + context_after_symbols

            # 3. Compute integrity hash
            integrity_hash = compute_integrity_hash(raw_anchor.token)

            # 4. Build SymbolEvent
            symbol_event = SymbolEvent(
                event_id=raw_anchor.event_id,
                session_id=raw_anchor.session_id,
                pulse_id=raw_anchor.pulse_id,
                symbol_id=symbol_data.symbol_id_64,
                context_symbols=context_symbols,
                category=symbol_data.category,
                priority=symbol_data.priority,
                integrity_hash=integrity_hash,
                genome_version=self.genome.get_version(),
                position=raw_anchor.position,
                timestamp=raw_anchor.timestamp,
            )

            # 5. Collision detection
            if self._detect_collision(symbol_event, raw_anchor.token):
                logger.warning(
                    "Symbol collision detected: symbol_id=%s token=%s",
                    symbol_event.symbol_id,
                    raw_anchor.token,
                )

            return symbol_event

        except Exception as exc:
            raise GnomeFailure(f"Symbolization failed: {exc}") from exc

    def _detect_collision(self, symbol_event: SymbolEvent, token: str) -> bool:
        """Check if symbol_id already maps to a different token."""
        existing_token = self._collision_registry.get(symbol_event.symbol_id)
        if existing_token is not None and existing_token != token.lower():
            return True
        self._collision_registry[symbol_event.symbol_id] = token.lower()
        return False
