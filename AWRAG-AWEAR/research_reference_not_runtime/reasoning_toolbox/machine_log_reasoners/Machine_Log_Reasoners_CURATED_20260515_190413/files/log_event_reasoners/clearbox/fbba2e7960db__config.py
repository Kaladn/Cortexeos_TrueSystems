"""LakeSpeak configuration — reads from forest.config.json.

All config is optional with sensible defaults.
Adds a 'lakespeak' key to the main config if not present.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

# ── Defaults ─────────────────────────────────────────────────

DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "chunk_size": 512,          # tokens per chunk
    "chunk_overlap": 64,        # tokens overlap
    "bm25_topk": 20,            # BM25 candidates
    "census_topk": 20,          # Census candidates
    "final_topk": 5,            # Final results after rerank
    "bm25_weight": 0.4,         # RRF weight for BM25 (locked)
    "census_weight": 0.6,       # RRF weight for census — 6-1-6 adjacency counts (locked)
    "anchor_weight": 0.3,       # Reranker anchor contribution
    "min_score": 0.01,          # Quality Gate minimum score (scores normalized to [0,1])
}


def load_config(config_path: Path = None) -> Dict[str, Any]:
    """Load LakeSpeak config from forest.config.json.

    Returns merged config: file values override defaults.
    """
    secure_loader = None
    if config_path is None:
        try:
            from security.data_paths import FOREST_CONFIG_PATH
            from security.secure_storage import secure_json_load
            config_path = FOREST_CONFIG_PATH
            secure_loader = secure_json_load
        except ImportError:
            config_path = Path("forest.config.json")

    config = dict(DEFAULTS)

    try:
        if config_path.exists():
            if secure_loader is not None:
                full = secure_loader(config_path)
            else:
                with open(config_path, "r", encoding="utf-8") as f:
                    full = json.load(f)
            lakespeak_section = full.get("lakespeak", {})
            config.update(lakespeak_section)
    except Exception as e:
        logger.warning("Failed to load LakeSpeak config: %s", e)

    return config
