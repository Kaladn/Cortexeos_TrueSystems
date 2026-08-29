"""Forest AI Lexicon bridge integrating the production lexicon with 6-1-6 mapping."""
from __future__ import annotations

import json
import logging
import os
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from .forest_gpu import DeviceInfo, compute_window_counts, select_device

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from security.secure_storage import secure_json_load, secure_json_dump

try:
    from bridges.governed_io import (
        write_map_report as _governed_write_map,
        write_custom_entries as _governed_write_custom,
        read_custom_entries as _governed_read_custom,
        write_snapshot as _governed_write_snapshot,
    )
    _GOVERNED = True
except ImportError:
    _GOVERNED = False

# Kill switch: when False, legacy fallback paths hard-error instead of writing.
# Set to False once governed I/O is stable. Override via env var.
ALLOW_LEGACY_WRITES = os.environ.get("ALLOW_LEGACY_WRITES", "false").lower() in ("true", "1", "yes")

try:  # Local optional dependency; only used for stats metadata
    import torch  # type: ignore
except Exception:  # pragma: no cover - torch may not be present at import time
    torch = None

LOGGER = logging.getLogger(__name__)
DEFAULT_TOKEN_SPLIT = r"[^A-Za-z0-9']+"


@dataclass
class LexiconEntry:
    word: Optional[str]           # None for AVAILABLE slots
    symbol: Optional[str]          # hex address (canonical key)
    payload: Dict[str, Any]
    status: str = "AVAILABLE"      # AVAILABLE | ASSIGNED


def fnv1a_hex(value: str) -> str:
    """Return an 8-character uppercase hex using FNV-1a."""
    h = 0x811C9DC5
    for char in value:
        h ^= ord(char)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08X}"


class ForestLexiconBridge:
    """Bridge responsible for loading the lexicon and computing 6-1-6 maps."""

    def __init__(
        self,
        lexicon_root: Path,
        reports_root: Path,
        config_path: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.lexicon_root = Path(lexicon_root)
        self.reports_root = Path(reports_root)
        self.reports_root.mkdir(parents=True, exist_ok=True)
        self.config_path = config_path

        config = config or {}
        self.config: Dict[str, Any] = {
            "window": int(config.get("window", config.get("win", 6))),
            "topK": int(config.get("topK", config.get("top_k", 10))),
            "min_len": int(config.get("min_len", 0)),
            "alpha_only": bool(config.get("alpha_only", False)),
            "regex_include": config.get("regex_include") or "",
            "regex_exclude": config.get("regex_exclude") or "",
            "gpu": config.get("gpu", "auto"),
        }

        self.window = int(self.config["window"])
        self.top_k = int(self.config["topK"])
        self.min_len = int(self.config["min_len"])
        try:
            self.device_info: DeviceInfo | None = select_device(self.config["gpu"])
        except RuntimeError as _gpu_err:
            LOGGER.warning("GPU unavailable at startup — GPU compute ops will fail: %s", _gpu_err)
            self.device_info = None

        self._regex_include = re.compile(self.config["regex_include"], re.IGNORECASE) if self.config["regex_include"] else None
        self._regex_exclude = re.compile(self.config["regex_exclude"], re.IGNORECASE) if self.config["regex_exclude"] else None

        self.entries: Dict[str, LexiconEntry] = {}
        self.frequency: Counter[str] = Counter()
        self.loaded = False
        self._last_load_time: Optional[float] = None
        self._vocab_index: Dict[str, int] = {}
        self._index_vocab: List[str] = []
        self.custom_entries_path = self.reports_root / "custom_entries.json"
        self.custom_entries: Dict[str, Dict[str, Any]] = {}
        self.last_map_result: Optional[Dict[str, Any]] = None
        self.enrichment_state: Dict[str, Any] = {}
        self.enrichment_state_path: Optional[Path] = None
        # Spare slot tracking
        self.word_index: Dict[str, str] = {}   # normalized_word -> hex
        self.slots_total: int = 0
        self.slots_assigned: int = 0
        self.slots_available: int = 0

    # ------------------------------------------------------------------
    # Lexicon loading & persistence
    # ------------------------------------------------------------------
    def _is_spare_slot(self, entry: Dict[str, Any]) -> bool:
        """Detect spare slot schema: has hex + status, may or may not have word."""
        return isinstance(entry.get("hex"), str) and isinstance(entry.get("status"), str)

    def _load_spare_slots(self, data: list, file_path: Path) -> int:
        """Load a spare slot file. Returns count of entries loaded."""
        count = 0
        for entry in data:
            if not isinstance(entry, dict):
                continue
            hex_addr = entry.get("hex")
            if not hex_addr:
                continue
            status = entry.get("status", "AVAILABLE")
            word = entry.get("word")
            norm_word = word.strip().lower() if isinstance(word, str) and word.strip() else None

            self.entries[hex_addr] = LexiconEntry(
                word=norm_word,
                symbol=hex_addr,
                payload=entry,
                status=status,
            )
            self.slots_total += 1
            if status == "ASSIGNED" and norm_word:
                self.slots_assigned += 1
                self.word_index[norm_word] = hex_addr
                self.frequency[norm_word] = int(entry.get("frequency", 0))
            else:
                self.slots_available += 1
            count += 1
        return count

    def load(self) -> Dict[str, int]:
        if not self.lexicon_root.exists():
            raise FileNotFoundError(f"Lexicon root '{self.lexicon_root}' does not exist.")

        start = time.time()
        count_files = 0
        count_entries = 0
        self.entries.clear()
        self.frequency.clear()
        self.word_index.clear()
        self.slots_total = 0
        self.slots_assigned = 0
        self.slots_available = 0
        self.enrichment_state = {}
        self.enrichment_state_path = None

        for file_path in self.lexicon_root.rglob("*.json"):
            if file_path.name == "enrichment_state.json":
                self._load_enrichment_state(file_path)
                continue
            count_files += 1
            try:
                with open(file_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except json.JSONDecodeError as exc:  # pragma: no cover
                LOGGER.error("Invalid JSON in %s: %s", file_path, exc)
                continue

            # ── Spare slot format (list with hex + status) ────
            if isinstance(data, list) and len(data) > 0 and self._is_spare_slot(data[0]):
                count_entries += self._load_spare_slots(data, file_path)
                LOGGER.info("Loaded spare slot file %s", file_path.name)
                continue

            # ── Legacy format (dict or word/token list) ───────
            if isinstance(data, dict):
                items = data.items()
            elif isinstance(data, list):
                hydrated: List[Tuple[str, Dict[str, Any]]] = []
                for entry in data:
                    if not isinstance(entry, dict):
                        continue
                    word = entry.get("word") or entry.get("token")
                    if isinstance(word, str) and word.strip():
                        hydrated.append((word.strip(), entry))
                items = hydrated
            else:
                LOGGER.warning("Skipping %s (unsupported JSON root)", file_path)
                continue

            for key, payload in items:
                if not key:
                    continue
                word = str(key).strip()
                if not word:
                    continue
                norm = word.lower()
                symbol = None
                if isinstance(payload, dict):
                    symbol = payload.get("symbol") or payload.get("hex")
                    frequency = payload.get("frequency") or payload.get("freq")
                    try:
                        freq_int = int(frequency)
                    except (TypeError, ValueError):
                        freq_int = 0
                    self.frequency[norm] = freq_int
                    if isinstance(payload.get("context_before"), dict) or isinstance(payload.get("context_after"), dict):
                        payload.setdefault("context_before", payload.get("context_before", {}))
                        payload.setdefault("context_after", payload.get("context_after", {}))
                entry_payload = payload if isinstance(payload, dict) else {"value": payload}
                self.entries[norm] = LexiconEntry(word=word, symbol=symbol, payload=entry_payload)
                self.word_index[norm] = symbol or norm
                count_entries += 1

        self._apply_custom_entries()
        self._rebuild_vocab()
        self.loaded = True
        self._last_load_time = time.time()
        elapsed = self._last_load_time - start
        LOGGER.info(
            "Lexicon loaded: %s slots from %s files in %.2fs  "
            "[total=%s  assigned=%s  available=%s]",
            count_entries, count_files, elapsed,
            self.slots_total, self.slots_assigned, self.slots_available,
        )
        return {"files": count_files, "entries": count_entries, "seconds": elapsed}

    def _load_enrichment_state(self, path: Path) -> None:
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover - diagnostics only
            LOGGER.warning("Failed to parse enrichment state %s: %s", path, exc)
            return
        if isinstance(data, dict):
            self.enrichment_state = data
            self.enrichment_state_path = path

    def _rebuild_vocab(self) -> None:
        self._vocab_index.clear()
        self._index_vocab = []

    def _apply_custom_entries(self) -> None:
        self.custom_entries = {}
        if not self.custom_entries_path.exists():
            return
        try:
            with open(self.custom_entries_path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except json.JSONDecodeError as exc:  # pragma: no cover
            LOGGER.error("Failed reading custom entries: %s", exc)
            return
        if not isinstance(data, dict):
            LOGGER.warning("Ignoring malformed custom entries file")
            return
        self.custom_entries = data
        for norm, payload in data.items():
            word = payload.get("word", norm)
            symbol = payload.get("symbol")
            entry_payload = payload.get("payload", {})
            self.entries[norm] = LexiconEntry(word=word, symbol=symbol, payload=entry_payload)
            if "frequency" in payload:
                try:
                    self.frequency[norm] = int(payload["frequency"])
                except (TypeError, ValueError):
                    pass

    def _persist_custom_entries(self) -> None:
        if not self.custom_entries:
            if self.custom_entries_path.exists():
                self.custom_entries_path.unlink()
            return
        # ── Governed path: write through gateway ──────────────
        if _GOVERNED:
            _governed_write_custom(self.custom_entries)
            return
        # ── Legacy fallback ───────────────────────────────────
        if not ALLOW_LEGACY_WRITES:
            raise RuntimeError("Legacy writes disabled. Set ALLOW_LEGACY_WRITES=true to bypass.")
        self.custom_entries_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.custom_entries_path, "w", encoding="utf-8") as handle:
            json.dump(self.custom_entries, handle, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Configuration management
    # ------------------------------------------------------------------
    def get_config(self) -> Dict[str, Any]:
        return dict(self.config)

    def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        changed = False
        config = dict(self.config)

        for key in ["min_len", "topK", "window", "alpha_only", "regex_include", "regex_exclude", "gpu"]:
            if key in updates and updates[key] is not None:
                value = updates[key]
                if key in {"min_len", "topK", "window"}:
                    value = int(value)
                config[key] = value
                changed = True

        if not changed:
            return config

        self.config = config
        self.window = int(config["window"])
        self.top_k = int(config["topK"])
        self.min_len = int(config["min_len"])
        self._regex_include = re.compile(config["regex_include"], re.IGNORECASE) if config.get("regex_include") else None
        self._regex_exclude = re.compile(config["regex_exclude"], re.IGNORECASE) if config.get("regex_exclude") else None

        try:
            self.device_info = select_device(config["gpu"])
        except RuntimeError as _gpu_err:
            LOGGER.warning("GPU unavailable on config reload: %s", _gpu_err)
            self.device_info = None
        self._persist_config()
        return dict(self.config)

    def _persist_config(self) -> None:
        if not self.config_path:
            return
        try:
            existing = secure_json_load(self.config_path)
        except FileNotFoundError:
            existing = {}
        except (json.JSONDecodeError, ValueError):
            existing = {}

        existing.update({
            "window": self.config["window"],
            "topK": self.config["topK"],
            "min_len": self.config["min_len"],
            "alpha_only": self.config["alpha_only"],
            "regex_include": self.config["regex_include"],
            "regex_exclude": self.config["regex_exclude"],
            "gpu": self.config["gpu"],
        })

        secure_json_dump(self.config_path, existing)

    # ------------------------------------------------------------------
    # Token helpers / filters
    # ------------------------------------------------------------------
    def normalise_token(self, token: str) -> str:
        return token.lower()

    def _ensure_vocab_index(self, token: str) -> int:
        norm = self.normalise_token(token)
        if norm not in self._vocab_index:
            self._vocab_index[norm] = len(self._index_vocab)
            self._index_vocab.append(norm)
        return self._vocab_index[norm]

    def _encode_tokens(self, tokens: Iterable[str]) -> List[int]:
        return [self._ensure_vocab_index(tok) for tok in tokens]

    def _decode_index(self, index: int) -> str:
        return self._index_vocab[index]

    def _passes_filters(self, token: str) -> bool:
        if self.config.get("alpha_only") and not token.isalpha():
            return False
        if self._regex_include and not self._regex_include.search(token):
            return False
        if self._regex_exclude and self._regex_exclude.search(token):
            return False
        return True

    def tokenize(self, text: str) -> List[str]:
        tokens = [tok for tok in re.split(DEFAULT_TOKEN_SPLIT, text) if tok]
        if self.min_len > 0:
            tokens = [tok for tok in tokens if len(tok) >= self.min_len]
        tokens = [tok for tok in tokens if self._passes_filters(tok)]
        return tokens

    # ------------------------------------------------------------------
    # Mapping logic
    # ------------------------------------------------------------------
    def _pack_side(self, side_map: Dict[str, Dict[int, Counter]]) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        """Pack raw counts — NO pruning.  TopK is a view, not storage."""
        packed: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        for focus_word, distance_buckets in side_map.items():
            focus_pack: Dict[str, List[Dict[str, Any]]] = {}
            for distance, counter in distance_buckets.items():
                # All counts survive, sorted by frequency (highest first)
                focus_pack[str(distance)] = [
                    {
                        "token": token,
                        "count": int(count),
                        "in_lexicon": token in self.word_index,
                        "symbol": self.entries[self.word_index[token]].symbol if token in self.word_index else None,
                    }
                    for token, count in counter.most_common()
                ]
            packed[focus_word] = focus_pack
        return packed

    def _attach_metadata(self, before_packed: Dict[str, Any], after_packed: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        merged: Dict[str, Dict[str, Any]] = {}
        focus_words = set(before_packed.keys()) | set(after_packed.keys())
        for focus_word in focus_words:
            hex_addr = self.word_index.get(focus_word)
            entry = self.entries.get(hex_addr) if hex_addr else None
            merged[focus_word] = {
                "before": before_packed.get(focus_word, {}),
                "after": after_packed.get(focus_word, {}),
                "symbol": entry.symbol if entry else None,
                "lexicon_payload": entry.payload if entry else None,
                "lexicon_word": entry.word if entry else focus_word,
                "frequency": int(self.frequency.get(focus_word, 0)),
            }
        return merged

    def _persist_last_map(self, report: Dict[str, Any]) -> None:
        self.last_map_result = report

    def map_tokens(self, tokens: List[str], source: str = "inline") -> Dict[str, Any]:
        if not self.loaded:
            raise RuntimeError("Lexicon not loaded. Call load() first.")
        if not tokens:
            report = {
                "source": source,
                "window": self.window,
                "topK": self.top_k,
                "device_used": self.device_info.type if self.device_info else "none",
                "items": {},
                "total_tokens": 0,
                "duration_ms": 0,
            }
            self._persist_last_map(report)
            return report

        # GPU via PyTorch is optional — Ollama provides GPU inference; map compute
        # falls back to CPU if no PyTorch GPU is available.
        _dev = self.device_info or DeviceInfo(type="cpu", name="CPU")
        token_ids = self._encode_tokens(tokens)
        start = time.time()
        counts = compute_window_counts(token_ids, self.window, _dev)
        elapsed = time.time() - start

        before_map: Dict[str, Dict[int, Counter]] = defaultdict(lambda: defaultdict(Counter))
        after_map: Dict[str, Dict[int, Counter]] = defaultdict(lambda: defaultdict(Counter))

        for offset, triples in counts.items():
            target = before_map if offset < 0 else after_map
            distance = abs(offset)
            for focus_idx, ctx_idx, value in triples:
                focus_word = self._decode_index(focus_idx)
                ctx_word = self._decode_index(ctx_idx)
                target[focus_word][distance][ctx_word] += value

        before_packed = self._pack_side(before_map)
        after_packed = self._pack_side(after_map)
        merged = self._attach_metadata(before_packed, after_packed)

        report = {
            "source": source,
            "window": self.window,
            "topK": self.top_k,
            "device_used": self.device_info.type,
            "device_name": self.device_info.name,
            "total_tokens": len(tokens),
            "duration_ms": int(elapsed * 1000),
            "items": merged,
        }
        self._persist_last_map(report)
        return report

    def map_text(self, text: str, source: str = "inline") -> Dict[str, Any]:
        """Map text with paragraph boundary enforcement.

        Double newline = wall.  No context crosses a paragraph break.
        Each paragraph is tokenized and windowed independently.
        Raw counters merge across paragraphs (safe — sealed universes).
        """
        if not self.loaded:
            raise RuntimeError("Lexicon not loaded. Call load() first.")

        # ── Split into paragraphs: double newline = wall ──────
        paragraphs = re.split(r'\n\s*\n', text)

        before_map: Dict[str, Dict[int, Counter]] = defaultdict(lambda: defaultdict(Counter))
        after_map: Dict[str, Dict[int, Counter]] = defaultdict(lambda: defaultdict(Counter))
        total_tokens = 0
        start = time.time()

        for para in paragraphs:
            tokens = self.tokenize(para)
            if not tokens:
                continue
            total_tokens += len(tokens)
            token_ids = self._encode_tokens(tokens)
            _dev = self.device_info or DeviceInfo(type="cpu", name="CPU")
            counts = compute_window_counts(token_ids, self.window, _dev)

            # Merge raw counts — each paragraph's windows are sealed
            for offset, triples in counts.items():
                target = before_map if offset < 0 else after_map
                distance = abs(offset)
                for focus_idx, ctx_idx, value in triples:
                    focus_word = self._decode_index(focus_idx)
                    ctx_word = self._decode_index(ctx_idx)
                    target[focus_word][distance][ctx_word] += value

        elapsed = time.time() - start

        if total_tokens == 0:
            report = {
                "source": source,
                "window": self.window,
                "topK": self.top_k,
                "device_used": self.device_info.type,
                "items": {},
                "total_tokens": 0,
                "duration_ms": 0,
            }
            self._persist_last_map(report)
            return report

        before_packed = self._pack_side(before_map)
        after_packed = self._pack_side(after_map)
        merged = self._attach_metadata(before_packed, after_packed)

        report = {
            "source": source,
            "window": self.window,
            "topK": self.top_k,
            "device_used": self.device_info.type,
            "device_name": self.device_info.name,
            "total_tokens": total_tokens,
            "duration_ms": int(elapsed * 1000),
            "items": merged,
        }
        self._persist_last_map(report)
        return report

    def map_file(self, path: Path) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
        return self.map_text(text, source=str(path))

    def map_files(
        self,
        paths: Iterable[Path],
        *,
        progress_cb: Optional[Callable[[int, int, Path, Dict[str, Any]], None]] = None,
        cancel_cb: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        start = time.time()
        aggregate: Dict[str, Dict[str, Any]] = {}
        total_tokens = 0
        cancelled = False
        paths = list(paths)
        total = len(paths)

        for idx, path in enumerate(paths, 1):
            if cancel_cb and cancel_cb():
                cancelled = True
                break
            result = self.map_file(path)
            total_tokens += result.get("total_tokens", 0)
            self._merge_aggregate(aggregate, result)
            if progress_cb:
                progress_cb(idx, total, path, result)

        report = self._collapse_aggregate(aggregate, total_tokens, start, cancelled)
        self._persist_last_map(report)
        return report

    def _merge_aggregate(self, aggregate: Dict[str, Dict[str, Any]], result: Dict[str, Any]) -> None:
        for focus, payload in result["items"].items():
            target = aggregate.setdefault(
                focus,
                {
                    "before": defaultdict(Counter),
                    "after": defaultdict(Counter),
                    "symbol": payload.get("symbol"),
                    "lexicon_payload": payload.get("lexicon_payload"),
                    "lexicon_word": payload.get("lexicon_word", focus),
                    "frequency": payload.get("frequency", 0),
                },
            )
            for distance, bucket in payload["before"].items():
                for item in bucket:
                    target["before"][distance][item["token"]] += item["count"]
            for distance, bucket in payload["after"].items():
                for item in bucket:
                    target["after"][distance][item["token"]] += item["count"]

    def _collapse_aggregate(
        self,
        aggregate: Dict[str, Dict[str, Any]],
        total_tokens: int,
        start_time: float,
        cancelled: bool,
    ) -> Dict[str, Any]:
        """Collapse batch aggregate — NO pruning.  TopK is a view, not storage."""
        collapsed: Dict[str, Dict[str, Any]] = {}
        for focus, payload in aggregate.items():
            collapsed[focus] = {
                "symbol": payload["symbol"],
                "lexicon_payload": payload["lexicon_payload"],
                "lexicon_word": payload["lexicon_word"],
                "frequency": payload["frequency"],
                "before": {
                    distance: [
                        {
                            "token": token,
                            "count": int(count),
                            "in_lexicon": token in self.word_index,
                            "symbol": self.entries[self.word_index[token]].symbol if token in self.word_index else None,
                        }
                        for token, count in counter.most_common()
                    ]
                    for distance, counter in payload["before"].items()
                },
                "after": {
                    distance: [
                        {
                            "token": token,
                            "count": int(count),
                            "in_lexicon": token in self.word_index,
                            "symbol": self.entries[self.word_index[token]].symbol if token in self.word_index else None,
                        }
                        for token, count in counter.most_common()
                    ]
                    for distance, counter in payload["after"].items()
                },
            }

        duration = time.time() - start_time
        return {
            "source": "batch",
            "window": self.window,
            "topK": self.top_k,
            "device_used": self.device_info.type,
            "device_name": self.device_info.name,
            "total_tokens": int(total_tokens),
            "duration_ms": int(duration * 1000),
            "items": collapsed,
            "cancelled": cancelled,
        }

    # ------------------------------------------------------------------
    # Lookup & analytics
    # ------------------------------------------------------------------
    def lookup(self, word: str) -> Dict[str, Any]:
        norm = self.normalise_token(word)
        hex_addr = self.word_index.get(norm)
        entry = self.entries.get(hex_addr) if hex_addr else None
        return {
            "query": word,
            "normalized": norm,
            "in_lexicon": bool(entry),
            "symbol": entry.symbol if entry else None,
            "status": entry.status if entry else None,
            "payload": entry.payload if entry else None,
            "frequency": int(self.frequency.get(norm, 0)),
        }

    def stats(self) -> Dict[str, Any]:
        entries_with_frequency = sum(1 for value in self.frequency.values() if value > 0)

        def _has_context(entry: LexiconEntry) -> bool:
            payload = entry.payload or {}
            before = payload.get("context_before") if isinstance(payload, dict) else {}
            after = payload.get("context_after") if isinstance(payload, dict) else {}
            return bool(before) or bool(after)

        entries_with_context = sum(1 for entry in self.entries.values() if _has_context(entry))

        enrichment_summary: Dict[str, Any] = {}
        history = []
        if isinstance(self.enrichment_state, dict):
            history = self.enrichment_state.get("history", []) if isinstance(self.enrichment_state.get("history"), list) else []
            if history:
                last_run = history[-1].get("run_at")
                enrichment_summary["last_run"] = last_run
                enrichment_summary["total_runs"] = len(history)
                enrichment_summary["reports"] = sum(len(entry.get("reports", [])) for entry in history if isinstance(entry, dict))
        if self.enrichment_state_path:
            enrichment_summary["state_path"] = str(self.enrichment_state_path)

        torch_version = getattr(torch, "__version__", None) if torch else None
        # Report both CUDA and ROCm/HIP version — ROCm builds set torch.version.hip
        _tv = getattr(torch, "version", None) if torch else None
        cuda_version = getattr(_tv, "cuda", None)
        hip_version  = getattr(_tv, "hip",  None)
        gpu_compute_version = f"ROCm {hip_version}" if hip_version else (f"CUDA {cuda_version}" if cuda_version else None)

        return {
            "loaded": self.loaded,
            "device_used": self.device_info.type if self.device_info else "none",
            "device_name": self.device_info.name if self.device_info else "none",
            "entries": len(self.entries),
            "entries_with_frequency": entries_with_frequency,
            "entries_with_context": entries_with_context,
            "total_frequency": int(sum(self.frequency.values())),
            "last_loaded_at": self._last_load_time,
            "config": self.get_config(),
            "torch_version": torch_version,
            "cuda_version": cuda_version,
            "hip_version": hip_version,
            "gpu_compute": gpu_compute_version,
            "enrichment": enrichment_summary,
            "slots_total": self.slots_total,
            "slots_assigned": self.slots_assigned,
            "slots_available": self.slots_available,
        }

    def get_616(self, word: str, topk: Optional[int] = None) -> Dict[str, Any]:
        if not self.last_map_result:
            return {"word": word, "before": {}, "after": {}, "total_windows": 0}
        norm = self.normalise_token(word)
        payload = self.last_map_result.get("items", {}).get(norm)
        if not payload:
            return {"word": word, "before": {}, "after": {}, "total_windows": 0}

        limit = topk or self.top_k

        def trim(buckets: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[List[Any]]]:
            output: Dict[str, List[List[Any]]] = {}
            for distance, items in buckets.items():
                output[distance] = [[item["token"], item["count"]] for item in items[:limit]]
            return output

        before = trim(payload.get("before", {}))
        after = trim(payload.get("after", {}))
        total = sum(count for buckets in before.values() for _, count in buckets)
        total += sum(count for buckets in after.values() for _, count in buckets)

        return {
            "word": payload.get("lexicon_word", word),
            "symbol": payload.get("symbol"),
            "before": before,
            "after": after,
            "total_windows": int(total),
        }

    # ------------------------------------------------------------------
    # Lexicon mutation helpers
    # ------------------------------------------------------------------
    def _ensure_entry(self, word: str) -> LexiconEntry:
        norm = self.normalise_token(word)
        hex_addr = self.word_index.get(norm)
        if hex_addr:
            return self.entries[hex_addr]
        # Word not bound yet — create via custom entries (no slot allocation)
        symbol = fnv1a_hex(norm)
        payload = {"word": word, "status": "CUSTOM"}
        entry = LexiconEntry(word=norm, symbol=symbol, payload=payload, status="CUSTOM")
        self.entries[symbol] = entry
        self.word_index[norm] = symbol
        self.custom_entries[norm] = {
            "word": word,
            "symbol": symbol,
            "payload": payload,
            "frequency": int(self.frequency.get(norm, 0)),
        }
        self._persist_custom_entries()
        return entry

    def append_word(self, word: str, status: Optional[str] = None) -> Dict[str, Any]:
        entry = self._ensure_entry(word)
        if status is not None:
            entry.payload["status"] = status
        norm = self.normalise_token(word)
        self.custom_entries[norm] = {
            "word": entry.word,
            "symbol": entry.symbol,
            "payload": entry.payload,
            "frequency": int(self.frequency.get(norm, 0)),
        }
        self._persist_custom_entries()
        return self.lookup(word)

    def assign_symbol(self, word: str, symbol: Optional[str], force: bool = False) -> Dict[str, Any]:
        entry = self._ensure_entry(word)
        if entry.symbol and not force and symbol:
            raise ValueError("Symbol already assigned; set force=true to override")
        entry.symbol = (symbol or fnv1a_hex(entry.word)).upper()
        norm = self.normalise_token(word)
        self.custom_entries.setdefault(norm, {})
        self.custom_entries[norm].update({
            "word": entry.word,
            "symbol": entry.symbol,
            "payload": entry.payload,
            "frequency": int(self.frequency.get(norm, 0)),
        })
        self._persist_custom_entries()
        return self.lookup(word)

    def set_status(self, word: str, status: Optional[str]) -> Dict[str, Any]:
        entry = self._ensure_entry(word)
        if status:
            entry.payload["status"] = status
        elif "status" in entry.payload:
            entry.payload.pop("status")
        norm = self.normalise_token(word)
        self.custom_entries.setdefault(norm, {})
        self.custom_entries[norm].update({
            "word": entry.word,
            "symbol": entry.symbol,
            "payload": entry.payload,
            "frequency": int(self.frequency.get(norm, 0)),
        })
        self._persist_custom_entries()
        return self.lookup(word)

    # ------------------------------------------------------------------
    # Canonical file persistence (write slot files back to disk)
    # ------------------------------------------------------------------
    def _write_canonical_files(self) -> int:
        """Write current in-memory slot entries back to canonical_X.json files.

        Groups entries by first letter of word (or hex prefix for unbound slots).
        Returns count of files written.
        """
        from collections import defaultdict
        by_letter: Dict[str, list] = defaultdict(list)
        for hex_addr, entry in self.entries.items():
            if not isinstance(entry.payload, dict) or "hex" not in entry.payload:
                continue
            # Determine letter bucket
            word = entry.word or entry.payload.get("word")
            if isinstance(word, str) and word.strip():
                letter = word.strip()[0].upper()
                if not letter.isalpha():
                    letter = "_"
            else:
                letter = "_"
            by_letter[letter].append(entry.payload)

        written = 0
        for letter, entries in by_letter.items():
            filename = f"canonical_{letter}.json"
            filepath = self.lexicon_root / filename
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
            written += 1
        return written

    # ------------------------------------------------------------------
    # Destructive lexicon operations (danger-gated in UI)
    # ------------------------------------------------------------------
    def clear_canonical(self) -> Dict[str, Any]:
        """Clear all canonical word bindings, returning slots to AVAILABLE.

        Preserves hex addresses, binary, font_symbol, tone_signature.
        Clears word, mapped_at, frequency. Sets status to AVAILABLE.
        """
        purged = 0
        for hex_addr, entry in self.entries.items():
            if entry.status == "ASSIGNED" and entry.word:
                purged += 1
                # Clear the word binding but keep the slot structure
                old_word = entry.word
                entry.word = None
                entry.status = "AVAILABLE"
                if isinstance(entry.payload, dict):
                    entry.payload["status"] = "AVAILABLE"
                    entry.payload["word"] = None
                    entry.payload.pop("mapped_at", None)
                    entry.payload.pop("frequency", None)
                # Remove from word index
                if old_word and old_word in self.word_index:
                    del self.word_index[old_word]
                if old_word and old_word in self.frequency:
                    del self.frequency[old_word]

        # Recount slots
        self.slots_assigned = sum(
            1 for e in self.entries.values()
            if e.status == "ASSIGNED" and e.word
        )
        self.slots_available = self.slots_total - self.slots_assigned

        # Persist
        self._write_canonical_files()
        self.custom_entries.clear()
        self._persist_custom_entries()

        LOGGER.info("clear_canonical: purged %d entries, %d slots now available",
                     purged, self.slots_available)
        return {
            "purged": purged,
            "slots_available": self.slots_available,
            "slots_reclaimed": purged,
        }

    def return_to_pool(self) -> Dict[str, Any]:
        """Move all ASSIGNED slots back to AVAILABLE (same as clear_canonical).

        Semantically identical but named differently for the UI flow.
        'Clear Canonical' emphasizes data loss; 'Return to Pool' emphasizes
        freeing address space.
        """
        result = self.clear_canonical()
        return {
            "moved": result["purged"],
            "pool_available": result["slots_available"],
        }

    def import_word_list(self, words_dir: Path) -> Dict[str, Any]:
        """Import verified word lists (verified_A.json ... verified_Z.json).

        Each file is a JSON array of strings (words). Words are bound to
        the first available slot alphabetically matching the word's first letter.

        Returns per-letter breakdown and totals.
        """
        words_dir = Path(words_dir)
        if not words_dir.exists():
            raise FileNotFoundError(f"Words directory not found: {words_dir}")
        if not words_dir.is_dir():
            raise ValueError(f"Not a directory: {words_dir}")

        total_imported = 0
        total_skipped = 0
        total_no_slots = 0
        letters_breakdown = []

        # Build index of available slots by letter
        from collections import defaultdict
        available_by_letter: Dict[str, list] = defaultdict(list)
        for hex_addr, entry in self.entries.items():
            if entry.status == "AVAILABLE" and not entry.word:
                # Determine which letter this slot belongs to by payload or hex
                available_by_letter["_"].append(hex_addr)

        # If slots are not letter-bucketed, just use a global pool
        global_pool = []
        for hex_addr, entry in self.entries.items():
            if entry.status == "AVAILABLE" and not entry.word:
                global_pool.append(hex_addr)

        pool_idx = 0

        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            filename = f"verified_{letter}.json"
            filepath = words_dir / filename
            if not filepath.exists():
                continue

            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    words = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                LOGGER.warning("Skipping %s: %s", filename, e)
                continue

            if not isinstance(words, list):
                LOGGER.warning("Skipping %s: not a list", filename)
                continue

            bound = 0
            skipped = 0
            overflow = 0

            for word in words:
                if not isinstance(word, str) or not word.strip():
                    continue
                norm = word.strip().lower()

                # Already bound?
                if norm in self.word_index:
                    skipped += 1
                    continue

                # Find an available slot
                if pool_idx >= len(global_pool):
                    overflow += 1
                    continue

                hex_addr = global_pool[pool_idx]
                pool_idx += 1
                entry = self.entries[hex_addr]

                # Bind word to slot
                entry.word = norm
                entry.status = "ASSIGNED"
                if isinstance(entry.payload, dict):
                    entry.payload["word"] = word.strip()
                    entry.payload["status"] = "ASSIGNED"
                    entry.payload["mapped_at"] = datetime.utcnow().isoformat() + "+00:00"
                    entry.payload["pack"] = "canonical"
                self.word_index[norm] = hex_addr
                self.frequency[norm] = 0
                bound += 1

            total_imported += bound
            total_skipped += skipped
            total_no_slots += overflow
            letters_breakdown.append({
                "letter": letter,
                "bound": bound,
                "skipped": skipped,
                "no_slots": overflow,
            })

        # Recount slots
        self.slots_assigned = sum(
            1 for e in self.entries.values()
            if e.status == "ASSIGNED" and e.word
        )
        self.slots_available = self.slots_total - self.slots_assigned

        # Persist to disk
        self._write_canonical_files()

        LOGGER.info(
            "import_word_list: imported=%d skipped=%d overflow=%d from %s",
            total_imported, total_skipped, total_no_slots, words_dir,
        )
        return {
            "imported": total_imported,
            "skipped": total_skipped,
            "no_slots": total_no_slots,
            "slots_available": self.slots_available,
            "letters": letters_breakdown,
        }

    # ------------------------------------------------------------------
    # Snapshot & rollback
    # ------------------------------------------------------------------
    def _snapshot_folder(self) -> Path:
        folder = self.reports_root / "snapshots"
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def create_snapshot(self, tag: Optional[str] = None) -> Path:
        lexicon_dump = {
            "entries": {
                norm: {
                    "word": entry.word,
                    "symbol": entry.symbol,
                    "payload": entry.payload,
                }
                for norm, entry in self.entries.items()
            },
            "frequency": dict(self.frequency),
            "config": self.get_config(),
            "custom_entries": self.custom_entries,
        }

        # ── Governed path: write through gateway ──────────────
        if _GOVERNED:
            snapshot_name = _governed_write_snapshot(tag or "", lexicon_dump)
            from security.storage_layout import STATE_DIR
            return STATE_DIR / "snapshots" / snapshot_name

        # ── Legacy fallback ───────────────────────────────────
        if not ALLOW_LEGACY_WRITES:
            raise RuntimeError("Legacy writes disabled. Set ALLOW_LEGACY_WRITES=true to bypass.")
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        safe_tag = f"_{tag}" if tag else ""
        folder = self._snapshot_folder() / f"snapshot{safe_tag}_{timestamp}"
        folder.mkdir(parents=True, exist_ok=True)

        with open(folder / "lexicon.json", "w", encoding="utf-8") as handle:
            json.dump(lexicon_dump, handle, ensure_ascii=False, indent=2)

        return folder

    def rollback(self, snapshot_path: Path) -> Dict[str, Any]:
        snapshot_path = snapshot_path if snapshot_path.is_absolute() else self._snapshot_folder() / snapshot_path
        lexicon_file = snapshot_path / "lexicon.json"
        if not lexicon_file.exists():
            raise FileNotFoundError(f"Snapshot file not found: {lexicon_file}")

        with open(lexicon_file, "r", encoding="utf-8") as handle:
            data = json.load(handle)

        entries = data.get("entries", {})
        frequency = data.get("frequency", {})
        config = data.get("config", {})
        custom = data.get("custom_entries", {})

        self.entries = {
            norm: LexiconEntry(word=payload["word"], symbol=payload.get("symbol"), payload=payload.get("payload", {}))
            for norm, payload in entries.items()
        }
        self.frequency = Counter({norm: int(freq) for norm, freq in frequency.items()})
        self.custom_entries = custom
        self.config.update(config)
        self.window = int(self.config["window"])
        self.top_k = int(self.config["topK"])
        self.min_len = int(self.config["min_len"])
        self._regex_include = re.compile(self.config["regex_include"], re.IGNORECASE) if self.config.get("regex_include") else None
        self._regex_exclude = re.compile(self.config["regex_exclude"], re.IGNORECASE) if self.config.get("regex_exclude") else None
        try:
            self.device_info = select_device(self.config["gpu"])
        except RuntimeError as _gpu_err:
            LOGGER.warning("GPU unavailable on reset: %s", _gpu_err)
            self.device_info = None
        self._persist_custom_entries()
        self._rebuild_vocab()
        self._persist_config()
        self.last_map_result = None
        return self.stats()

    # ------------------------------------------------------------------
    # Reporting helpers
    # ------------------------------------------------------------------
    def write_report(self, name: str, payload: Dict[str, Any]) -> Path:
        # ── Governed path: write through gateway ──────────────
        if _GOVERNED:
            result = _governed_write_map(
                report=payload,
                source=payload.get("source", "bridge"),
            )
            if result.get("success"):
                return Path(result["mapped_path"])
            LOGGER.error("Governed write failed: %s", result.get("error"))
            # Fall through to legacy path
        # ── Legacy fallback ───────────────────────────────────
        if not ALLOW_LEGACY_WRITES:
            raise RuntimeError("Legacy writes disabled. Set ALLOW_LEGACY_WRITES=true to bypass.")
        run_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        folder = self.reports_root / "forest_616" / run_id
        folder.mkdir(parents=True, exist_ok=True)
        file_path = folder / f"{name}.json"
        with open(file_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        return file_path

    def export_frequency_table(self) -> Path:
        table = {word: int(freq) for word, freq in self.frequency.items()}
        return self.write_report("frequency_table", table)


def load_bridge_from_config(config_path: Path, *, load_lexicon: bool = True) -> ForestLexiconBridge:
    config = secure_json_load(config_path)
    try:
        from security.data_paths import SOURCE_ROOT as _SOURCE_ROOT
    except Exception:
        _SOURCE_ROOT = Path(__file__).resolve().parents[1]

    def _resolve_runtime_path(raw_path: str | Path) -> Path:
        p = Path(raw_path).expanduser()
        if p.is_absolute():
            return p
        # Relative roots in config are workspace-relative, not cwd-relative.
        return (_SOURCE_ROOT / p).resolve()

    bridge = ForestLexiconBridge(
        lexicon_root=_resolve_runtime_path(config["lexicon_root"]),
        reports_root=_resolve_runtime_path(config["reports_root"]),
        config_path=config_path,
        config=config,
    )
    if load_lexicon:
        bridge.load()
    return bridge


__all__ = ["ForestLexiconBridge", "load_bridge_from_config"]
