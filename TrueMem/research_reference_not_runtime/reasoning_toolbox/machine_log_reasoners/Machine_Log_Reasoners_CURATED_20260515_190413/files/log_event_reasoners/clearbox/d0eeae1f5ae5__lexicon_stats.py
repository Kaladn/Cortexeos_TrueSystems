"""Lexicon disk and pack inventory statistics service."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class LexiconStatsService:
    def __init__(self) -> None:
        self._disk_stats_cache_sig: Optional[tuple] = None
        self._disk_stats_cache_values: Optional[Dict[str, Any]] = None
        self._pack_inventory_cache_sig: Optional[tuple] = None
        self._pack_inventory_cache_values: Optional[Dict[str, Any]] = None

    @staticmethod
    def _disk_stats_signature(bridge: Any) -> tuple:
        root = bridge.lexicon_root
        parts: List[tuple] = []
        for file_path in root.rglob("*.json"):
            if file_path.name == "enrichment_state.json":
                continue
            try:
                st = file_path.stat()
            except OSError:
                continue
            rel = str(file_path.relative_to(root))
            parts.append((rel, int(st.st_mtime_ns), int(st.st_size)))
        parts.sort()
        return tuple(parts)

    def compute_disk_stats(self, bridge: Any) -> Dict[str, Any]:
        sig = self._disk_stats_signature(bridge)
        if self._disk_stats_cache_sig == sig and self._disk_stats_cache_values:
            return dict(self._disk_stats_cache_values)

        entries = 0
        entries_with_frequency = 0
        entries_with_context = 0
        total_frequency = 0
        slots_total = 0
        slots_assigned = 0
        slots_available = 0

        for file_path in bridge.lexicon_root.rglob("*.json"):
            if file_path.name == "enrichment_state.json":
                continue
            try:
                with open(file_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except (OSError, json.JSONDecodeError):
                continue

            if isinstance(data, list) and data and isinstance(data[0], dict) and bridge._is_spare_slot(data[0]):
                slots_total += len(data)
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    status = str(item.get("status", "AVAILABLE")).upper()
                    word = item.get("word")
                    if status == "ASSIGNED" and isinstance(word, str) and word.strip():
                        slots_assigned += 1
                    else:
                        slots_available += 1
                continue

            if isinstance(data, dict):
                items = data.items()
            elif isinstance(data, list):
                hydrated: List[tuple] = []
                for entry in data:
                    if not isinstance(entry, dict):
                        continue
                    word = entry.get("word") or entry.get("token")
                    if isinstance(word, str) and word.strip():
                        hydrated.append((word.strip(), entry))
                items = hydrated
            else:
                continue

            for _, payload in items:
                entries += 1
                if isinstance(payload, dict):
                    freq = payload.get("frequency") or payload.get("freq") or 0
                    try:
                        freq_int = int(freq)
                    except (TypeError, ValueError):
                        freq_int = 0
                    total_frequency += freq_int
                    if freq_int > 0:
                        entries_with_frequency += 1
                    before = payload.get("context_before")
                    after = payload.get("context_after")
                    if (isinstance(before, dict) and before) or (isinstance(after, dict) and after):
                        entries_with_context += 1

        if slots_total > 0 and entries == 0:
            entries = slots_total

        computed = {
            "entries": entries,
            "entries_with_frequency": entries_with_frequency,
            "entries_with_context": entries_with_context,
            "total_frequency": total_frequency,
            "slots_total": slots_total,
            "slots_assigned": slots_assigned,
            "slots_available": slots_available,
        }
        self._disk_stats_cache_sig = sig
        self._disk_stats_cache_values = dict(computed)
        return computed

    @staticmethod
    def _lexical_base_dir(bridge: Any) -> Path:
        root = bridge.lexicon_root
        if root.name.lower() == "canonical":
            return root.parent
        return root

    @staticmethod
    def _count_entries_lightweight(path: Path) -> int:
        hex_key_re = re.compile(r'"hex"\s*:')
        count = 0
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as handle:
                for line in handle:
                    count += len(hex_key_re.findall(line))
            if count > 0:
                return count
        except OSError:
            return 0
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            if isinstance(data, list):
                return len(data)
            if isinstance(data, dict):
                return len(data)
        except Exception:
            return 0
        return 0

    def _pack_inventory_signature(self, bridge: Any) -> tuple:
        base = self._lexical_base_dir(bridge)
        targets = [
            ("Canonical", "canonical_[A-Z].json"),
            ("Medical", "med_[A-Z].json"),
            ("Spare_Slots", "pool_[A-Z].json"),
            ("Spare_Slots", "pool_ext_*.json"),
        ]
        parts: List[tuple] = []
        for folder, pattern in targets:
            dir_path = base / folder
            if not dir_path.exists():
                continue
            for file_path in sorted(dir_path.glob(pattern)):
                try:
                    st = file_path.stat()
                except OSError:
                    continue
                parts.append((folder, file_path.name, int(st.st_mtime_ns), int(st.st_size)))
        return tuple(parts)

    def compute_pack_inventory(self, bridge: Any) -> Dict[str, Any]:
        sig = self._pack_inventory_signature(bridge)
        if self._pack_inventory_cache_sig == sig and self._pack_inventory_cache_values:
            return dict(self._pack_inventory_cache_values)

        base = self._lexical_base_dir(bridge)
        canonical_dir = base / "Canonical"
        medical_dir = base / "Medical"
        pool_dir = base / "Spare_Slots"

        letters = {chr(i): 0 for i in range(ord("A"), ord("Z") + 1)}
        canonical_total = 0
        medical_total = 0
        pool_total = 0

        if canonical_dir.exists():
            for path in sorted(canonical_dir.glob("canonical_[A-Z].json")):
                n = self._count_entries_lightweight(path)
                canonical_total += n
                suffix = path.stem.split("_")[-1].upper()
                if len(suffix) == 1 and suffix in letters:
                    letters[suffix] = n

        if medical_dir.exists():
            for path in sorted(medical_dir.glob("med_[A-Z].json")):
                medical_total += self._count_entries_lightweight(path)

        if pool_dir.exists():
            for path in sorted(pool_dir.glob("pool_[A-Z].json")):
                pool_total += self._count_entries_lightweight(path)
            for path in sorted(pool_dir.glob("pool_ext_*.json")):
                pool_total += self._count_entries_lightweight(path)

        computed = {
            "canonical": int(canonical_total),
            "medical": int(medical_total),
            "spare_slots": int(pool_total),
            "total_indexed": int(canonical_total + medical_total),
            "letters": letters,
        }
        self._pack_inventory_cache_sig = sig
        self._pack_inventory_cache_values = dict(computed)
        return computed
