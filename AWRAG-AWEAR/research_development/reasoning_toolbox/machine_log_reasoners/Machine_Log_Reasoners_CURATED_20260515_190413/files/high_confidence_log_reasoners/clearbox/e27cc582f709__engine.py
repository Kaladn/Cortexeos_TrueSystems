"""Help System Engine -- loads and serves contextual help content.

Reads help_content.json at startup, provides lookup, search, and stats.
No heavy deps. No database. Pure JSON + in-memory index.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class HelpSystemEngine:
    """Singleton that holds the help content and provides lookup/search."""

    def __init__(self):
        self._content: Dict[str, Dict[str, Any]] = {}
        self._search_index: List[Dict[str, Any]] = []
        self._load_content()

    def _load_content(self) -> None:
        """Load help_content.json from the plugin's content directory."""
        from help_system.config import load_config

        config = load_config()
        content_path = Path(config["content_path"])

        if not content_path.exists():
            logger.warning("Help content file not found: %s", content_path)
            return

        try:
            with open(content_path, "r", encoding="utf-8") as f:
                self._content = json.load(f)
            self._build_search_index()
            logger.info(
                "Help System loaded %d entries from %s",
                len(self._content),
                content_path,
            )
        except Exception as e:
            logger.error("Failed to load help content: %s", e, exc_info=True)

    def _build_search_index(self) -> None:
        """Build a flat search index from all content for text search."""
        self._search_index = []
        for help_id, entry in self._content.items():
            layer1 = entry.get("layer1", {})
            searchable = " ".join([
                help_id,
                entry.get("label", ""),
                entry.get("category", ""),
                layer1.get("what", ""),
                layer1.get("why", ""),
                layer1.get("consequence", ""),
                layer1.get("avoid", ""),
            ]).lower()
            self._search_index.append({
                "help_id": help_id,
                "label": entry.get("label", ""),
                "category": entry.get("category", ""),
                "searchable": searchable,
            })

    def get_entry(self, help_id: str) -> Optional[Dict[str, Any]]:
        """Return the full help entry for a given ID, or None."""
        return self._content.get(help_id)

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search help content. Returns list of {help_id, label, category, snippet}."""
        q = query.lower()
        results = []
        for item in self._search_index:
            if q in item["searchable"]:
                entry = self._content.get(item["help_id"], {})
                layer1 = entry.get("layer1", {})
                snippet = layer1.get("what", "")[:120]
                results.append({
                    "help_id": item["help_id"],
                    "label": item["label"],
                    "category": item["category"],
                    "snippet": snippet,
                })
        return results

    def list_ids(self) -> List[Dict[str, str]]:
        """Return all help IDs with label and category."""
        return [
            {
                "help_id": hid,
                "label": entry.get("label", ""),
                "category": entry.get("category", ""),
            }
            for hid, entry in sorted(self._content.items())
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Return stats about the loaded content."""
        categories: Dict[str, int] = {}
        layers = {"layer1": 0, "layer2": 0, "layer3": 0}

        for entry in self._content.values():
            cat = entry.get("category", "Uncategorized")
            categories[cat] = categories.get(cat, 0) + 1
            for layer_key in ("layer1", "layer2", "layer3"):
                if entry.get(layer_key):
                    layers[layer_key] += 1

        return {
            "total_ids": len(self._content),
            "categories": categories,
            "layers_coverage": layers,
        }
