"""
Wolf Engine - Data Contracts (Canonical)
Symbol-First Architecture with Dual-Lane Persistence

Version: 1.0.0
Author: Shadow Wolf + GPT + Grok + Manus + Claude
"""

from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SymbolData:
    """Symbol data from genome lookup or dynamic generation."""
    symbol_hex: str
    symbol_id_64: int
    category: str
    priority: int
    visual_grid: str = ""


@dataclass
class RawAnchor:
    """Perception -> GNOME: raw token with 6-1-6 context."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    pulse_id: int = 0
    token: str = ""
    context_before: list[str] = field(default_factory=list)
    context_after: list[str] = field(default_factory=list)
    position: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class SymbolEvent:
    """GNOME -> Forge / SQL: symbolized event."""
    event_id: str = ""
    session_id: str = ""
    pulse_id: int = 0
    symbol_id: int = 0
    context_symbols: list[int] = field(default_factory=list)
    category: str = ""
    priority: int = 0
    integrity_hash: str = ""
    genome_version: str = ""
    position: int = 0
    timestamp: float = 0.0


@dataclass
class SessionData:
    """Session metadata."""
    session_id: str = ""
    started_at: float = 0.0
    ended_at: Optional[float] = None
    symbol_genome_version: str = ""
    config_hash: str = ""


@dataclass
class QueryResult:
    """Forge query result."""
    symbol_id: int = 0
    symbol_event: Optional[SymbolEvent] = None
    neighbors: dict[int, int] = field(default_factory=dict)
    resonance: float = 0.0
    chains: list[list[int]] = field(default_factory=list)


@dataclass
class ForgeStats:
    """Forge memory statistics."""
    total_symbols: int = 0
    total_chains: int = 0
    avg_resonance: float = 0.0
    window_size: int = 0
    current_size: int = 0
