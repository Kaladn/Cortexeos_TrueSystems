"""
GNOME Symbolizer
Convert tokens to 64-bit symbols using SHA-256 truncation.
"""

from __future__ import annotations

import hashlib

from wolf_engine.contracts import SymbolData
from wolf_engine.gnome.symbol_genome_loader import SymbolGenomeLoader


def generate_symbol_id(token: str) -> int:
    """
    Compute SHA-256 hash of token (lowercase, UTF-8).
    Truncate to first 64 bits. Return as uint64.
    """
    hash_bytes = hashlib.sha256(token.lower().encode("utf-8")).digest()
    symbol_id = int.from_bytes(hash_bytes[:8], "big")
    return symbol_id


def symbolize_token(token: str, genome: SymbolGenomeLoader) -> SymbolData:
    """
    Look up token in genome dictionary.
    If not found, generate a dynamic symbol via SHA-256.
    """
    symbol_data = genome.get_symbol(token.lower())
    if symbol_data is not None:
        return symbol_data

    symbol_id_64 = generate_symbol_id(token)
    return SymbolData(
        symbol_hex="UNKNOWN",
        symbol_id_64=symbol_id_64,
        category="unreviewed",
        priority=7,
        visual_grid="",
    )


def symbolize_context(tokens: list[str], genome: SymbolGenomeLoader) -> list[int]:
    """Symbolize a list of context tokens into symbol IDs."""
    return [symbolize_token(token, genome).symbol_id_64 for token in tokens]
