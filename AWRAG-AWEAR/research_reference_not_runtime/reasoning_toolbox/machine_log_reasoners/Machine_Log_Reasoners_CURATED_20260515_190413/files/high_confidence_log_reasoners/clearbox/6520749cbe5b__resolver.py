"""Intent-based query resolver: maps natural language questions to sensor IDs.

V1 uses keyword matching. Expandable to LLM-assisted resolution later.
"""
from __future__ import annotations

import fnmatch
import re
from typing import Any

from core.observe.policy import is_allowed

# ── Intent → sensor ID mapping ─────────────────────────────────
INTENT_MAP: dict[str, list[str]] = {
    # Hardware categories
    "cpu": ["cpu.percent", "cpu.core.*"],
    "processor": ["cpu.percent", "cpu.core.*"],
    "gpu": ["gpu.util_percent", "gpu.temp_c", "gpu.mem_used_mb", "gpu.mem_total_mb"],
    "graphics": ["gpu.util_percent", "gpu.temp_c", "gpu.mem_used_mb"],
    "vram": ["gpu.mem_used_mb", "gpu.mem_total_mb"],
    "memory": ["ram.percent", "ram.used_gb", "ram.total_gb"],
    "ram": ["ram.percent", "ram.used_gb", "ram.total_gb"],
    "disk": ["disk.percent", "disk.read_bytes", "disk.write_bytes"],
    "storage": ["disk.percent", "disk.used_gb", "disk.total_gb"],
    "network": ["net.bytes_sent", "net.bytes_recv"],
    "bandwidth": ["net.bytes_sent", "net.bytes_recv"],

    # Composite intents
    "throttling": ["cpu.percent", "gpu.util_percent", "gpu.temp_c", "gpu.power_w"],
    "throttle": ["cpu.percent", "gpu.util_percent", "gpu.temp_c", "gpu.power_w"],
    "pressure": ["ram.percent", "cpu.percent", "disk.percent"],
    "bottleneck": ["cpu.percent", "ram.percent", "gpu.util_percent", "disk.percent"],
    "performance": ["cpu.percent", "ram.percent", "gpu.util_percent", "gpu.temp_c"],
    "health": ["cpu.percent", "ram.percent", "disk.percent", "gpu.temp_c"],
    "temperature": ["gpu.temp_c"],
    "temp": ["gpu.temp_c"],
    "hot": ["gpu.temp_c"],
    "power": ["gpu.power_w"],
    "watt": ["gpu.power_w"],

    # Process
    "process": ["proc.count", "proc.top_cpu.*"],
    "processes": ["proc.count", "proc.top_cpu.*", "proc.top_mem.*"],
    "task": ["proc.count", "proc.top_cpu.*"],

    # System
    "uptime": ["os.uptime_sec"],
    "system": ["cpu.percent", "ram.percent", "disk.percent", "gpu.util_percent", "os.uptime_sec"],
    "overview": ["cpu.percent", "ram.percent", "disk.percent", "gpu.util_percent", "gpu.temp_c"],
    "status": ["cpu.percent", "ram.percent", "disk.percent", "gpu.util_percent"],

    # Latency / IO
    "latency": ["disk.read_bytes", "disk.write_bytes", "net.bytes_sent"],
    "io": ["disk.read_bytes", "disk.write_bytes", "net.bytes_sent", "net.bytes_recv"],
    "slow": ["cpu.percent", "ram.percent", "disk.percent", "gpu.util_percent"],
}


def _expand_wildcards(patterns: list[str], catalog: list[dict]) -> list[str]:
    """Expand wildcard patterns against the catalog."""
    expanded: list[str] = []
    catalog_ids = [s["id"] for s in catalog]
    for pat in patterns:
        if "*" in pat or "?" in pat:
            for sid in catalog_ids:
                if fnmatch.fnmatch(sid, pat) and sid not in expanded:
                    expanded.append(sid)
        elif pat not in expanded:
            expanded.append(pat)
    return expanded


def _tokenize(question: str) -> list[str]:
    """Extract lowercase tokens from a question."""
    return re.findall(r"[a-z0-9]+", question.lower())


def resolve(
    question: str,
    catalog: list[dict],
    policy: dict,
) -> dict[str, Any]:
    """Map a natural language question to sensor IDs.

    Returns:
        {
            "requested": [sensor IDs matched],
            "allowed": [IDs passing policy],
            "blocked": [IDs blocked by policy],
            "keywords_matched": [keywords that hit],
        }
    """
    tokens = _tokenize(question)
    catalog_map = {s["id"]: s for s in catalog}

    matched_patterns: list[str] = []
    keywords_hit: list[str] = []

    for token in tokens:
        if token in INTENT_MAP:
            keywords_hit.append(token)
            for pat in INTENT_MAP[token]:
                if pat not in matched_patterns:
                    matched_patterns.append(pat)

    # If no keywords matched, return a general overview
    if not matched_patterns:
        matched_patterns = list(INTENT_MAP.get("overview", []))
        keywords_hit = ["(fallback: overview)"]

    # Expand wildcards
    requested = _expand_wildcards(matched_patterns, catalog)

    # Filter by policy
    allowed = []
    blocked = []
    for sid in requested:
        sensor = catalog_map.get(sid)
        if sensor and is_allowed(sensor, policy):
            allowed.append(sid)
        else:
            blocked.append(sid)

    return {
        "requested": requested,
        "allowed": allowed,
        "blocked": blocked,
        "keywords_matched": keywords_hit,
    }
