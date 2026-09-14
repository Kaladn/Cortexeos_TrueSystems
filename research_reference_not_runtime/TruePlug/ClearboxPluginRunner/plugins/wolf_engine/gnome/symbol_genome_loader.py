"""
GNOME Symbol Genome Loader
Load Symbol Genome Phase 1 dictionary and provide symbol lookup.
"""

from __future__ import annotations

import json
import os
from typing import Optional

from wolf_engine.contracts import SymbolData


class SymbolGenomeLoader:
    """Loads and provides lookup for the Symbol Genome dictionary."""

    def __init__(self, genome_path: str):
        self._token_to_symbol: dict[str, SymbolData] = {}
        self._symbol_to_token: dict[int, str] = {}
        self._version: str = "v1.0"

        if os.path.exists(genome_path):
            with open(genome_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._version = data.get("metadata", {}).get("version", "v1.0")

            for token, entry in data.get("symbols", {}).items():
                symbol_data = SymbolData(
                    symbol_hex=entry.get("symbol_hex", ""),
                    symbol_id_64=entry.get("symbol_id_64", 0),
                    category=entry.get("category", "core"),
                    priority=entry.get("priority", 0),
                    visual_grid=entry.get("visual_grid", ""),
                )
                self._token_to_symbol[token.lower()] = symbol_data
                self._symbol_to_token[symbol_data.symbol_id_64] = token.lower()

    def get_symbol(self, token: str) -> Optional[SymbolData]:
        """Lookup token in genome dictionary."""
        return self._token_to_symbol.get(token.lower())

    def get_token(self, symbol_id: int) -> Optional[str]:
        """Reverse lookup: symbol_id -> token."""
        return self._symbol_to_token.get(symbol_id)

    def get_version(self) -> str:
        """Return genome version."""
        return self._version
