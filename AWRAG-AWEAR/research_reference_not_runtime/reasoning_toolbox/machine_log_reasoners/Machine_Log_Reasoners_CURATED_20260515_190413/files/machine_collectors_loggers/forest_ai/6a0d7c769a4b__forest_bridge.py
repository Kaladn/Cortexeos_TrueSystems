"""Forest AI Lexicon bridge integrating the production lexicon with 6-1-6 mapping."""
from __future__ import annotations

import json
import logging
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from .forest_gpu import DeviceInfo, compute_window_counts, select_device

LOGGER = logging.getLogger(__name__)
DEFAULT_TOKEN_SPLIT = r"[^A-Za-z0-9']+"


@dataclass
class LexiconEntry:
    word: str
    symbol: Optional[str]
    payload: Dict[str, Any]


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
            "star_policy": config.get("star_policy", "off"),
            "batch_size": int(config.get("batch_size", 0)),
            "workers": int(config.get("workers", 1)),
            "rate_limit": config.get("rate_limit"),
            "gpu": config.get("gpu", "auto"),
        }

        self.window = int(self.config["window"])
        self.top_k = int(self.config["topK"])
        self.min_len = int(self.config["min_len"])
        self.device_info: DeviceInfo = select_device(self.config["gpu"])

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

    # ------------------------------------------------------------------
    # Lexicon loading & persistence
    # ------------------------------------------------------------------
    def load(self) -> Dict[str, int]:
        if not self.lexicon_root.exists():
            raise FileNotFoundError(f"Lexicon root '{self.lexicon_root}' does not exist.")

        start = time.time()
        count_files = 0
        count_entries = 0
        self.entries.clear()
        self.frequency.clear()

        for file_path in self.lexicon_root.rglob("*.json"):
            count_files += 1
            try:
                with open(file_path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except json.JSONDecodeError as exc:  # pragma: no cover
                LOGGER.error("Invalid JSON in %s: %s", file_path, exc)
                continue

            if isinstance(data, dict):
                items = data.items()
            elif isinstance(data, list):
                items = ((entry.get("word"), entry) for entry in data)
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
                    if frequency:
                        try:
                            self.frequency[norm] += int(frequency)
                        except (ValueError, TypeError):
                            pass
                entry_payload = payload if isinstance(payload, dict) else {"value": payload}
                self.entries[norm] = LexiconEntry(word=word, symbol=symbol, payload=entry_payload)
                count_entries += 1

        self._apply_custom_entries()
        self._rebuild_vocab()
        self.loaded = True
        self._last_load_time = time.time()
        elapsed = self._last_load_time - start
        LOGGER.info("Lexicon loaded: %s entries from %s files in %.2fs", count_entries, count_files, elapsed)
        return {"files": count_files, "entries": count_entries, "seconds": elapsed}

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

        for key in ["min_len", "topK", "window", "alpha_only", "regex_include", "regex_exclude", "star_policy", "batch_size", "workers", "rate_limit", "gpu"]:
            if key in updates and updates[key] is not None:
                value = updates[key]
                if key in {"min_len", "topK", "window", "batch_size", "workers"}:
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

        self.device_info = select_device(config["gpu"])
        self._persist_config()
        return dict(self.config)

    def _persist_config(self) -> None:
        if not self.config_path:
            return
        try:
            with open(self.config_path, "r", encoding="utf-8") as handle:
                existing = json.load(handle)
        except FileNotFoundError:
            existing = {}
        except json.JSONDecodeError:
            existing = {}

        existing.update({
            "window": self.config["window"],
            "topK": self.config["topK"],
            "min_len": self.config["min_len"],
            "alpha_only": self.config["alpha_only"],
            "regex_include": self.config["regex_include"],
            "regex_exclude": self.config["regex_exclude"],
            "star_policy": self.config["star_policy"],
            "batch_size": self.config["batch_size"],
            "workers": self.config["workers"],
            "rate_limit": self.config.get("rate_limit"),
            "gpu": self.config["gpu"],
        })

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as handle:
            json.dump(existing, handle, ensure_ascii=False, indent=2)

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
        packed: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        for focus_word, distance_buckets in side_map.items():
            focus_pack: Dict[str, List[Dict[str, Any]]] = {}
            for distance, counter in distance_buckets.items():
                top_items = counter.most_common(self.top_k)
                focus_pack[str(distance)] = [
                    {
                        "token": token,
                        "count": int(count),
                        "in_lexicon": token in self.entries,
                        "symbol": self.entries[token].symbol if token in self.entries else None,
                    }
                    for token, count in top_items
                ]
            packed[focus_word] = focus_pack
        return packed

    def _attach_metadata(self, before_packed: Dict[str, Any], after_packed: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        merged: Dict[str, Dict[str, Any]] = {}
        focus_words = set(before_packed.keys()) | set(after_packed.keys())
        for focus_word in focus_words:
            entry = self.entries.get(focus_word)
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
                "device_used": self.device_info.type,
                "items": {},
                "total_tokens": 0,
                "duration_ms": 0,
            }
            self._persist_last_map(report)
            return report

        token_ids = self._encode_tokens(tokens)
        start = time.time()
        counts = compute_window_counts(token_ids, self.window, self.device_info)
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
        tokens = self.tokenize(text)
        return self.map_tokens(tokens, source=source)

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
                            "in_lexicon": token in self.entries,
                            "symbol": self.entries[token].symbol if token in self.entries else None,
                        }
                        for token, count in counter.most_common(self.top_k)
                    ]
                    for distance, counter in payload["before"].items()
                },
                "after": {
                    distance: [
                        {
                            "token": token,
                            "count": int(count),
                            "in_lexicon": token in self.entries,
                            "symbol": self.entries[token].symbol if token in self.entries else None,
                        }
                        for token, count in counter.most_common(self.top_k)
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
        entry = self.entries.get(norm)
        return {
            "query": word,
            "normalized": norm,
            "in_lexicon": bool(entry),
            "symbol": entry.symbol if entry else None,
            "payload": entry.payload if entry else None,
            "frequency": int(self.frequency.get(norm, 0)),
        }

    def stats(self) -> Dict[str, Any]:
        return {
            "loaded": self.loaded,
            "device_used": self.device_info.type,
            "device_name": self.device_info.name,
            "entries": len(self.entries),
            "total_frequency": int(sum(self.frequency.values())),
            "last_loaded_at": self._last_load_time,
            "config": self.get_config(),
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
        entry = self.entries.get(norm)
        if entry:
            return entry
        symbol = fnv1a_hex(norm)
        payload = {"word": word, "status": self.config.get("star_policy", "off")}
        entry = LexiconEntry(word=word, symbol=symbol, payload=payload)
        self.entries[norm] = entry
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
    # Snapshot & rollback
    # ------------------------------------------------------------------
    def _snapshot_folder(self) -> Path:
        folder = self.reports_root / "snapshots"
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def create_snapshot(self, tag: Optional[str] = None) -> Path:
        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        safe_tag = f"_{tag}" if tag else ""
        folder = self._snapshot_folder() / f"snapshot{safe_tag}_{timestamp}"
        folder.mkdir(parents=True, exist_ok=True)

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
        self.device_info = select_device(self.config["gpu"])
        self._persist_custom_entries()
        self._rebuild_vocab()
        self._persist_config()
        self.last_map_result = None
        return self.stats()

    # ------------------------------------------------------------------
    # Reporting helpers
    # ------------------------------------------------------------------
    def write_report(self, name: str, payload: Dict[str, Any]) -> Path:
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


def load_bridge_from_config(config_path: Path) -> ForestLexiconBridge:
    with open(config_path, "r", encoding="utf-8") as handle:
        config = json.load(handle)
    bridge = ForestLexiconBridge(
        lexicon_root=Path(config["lexicon_root"]),
        reports_root=Path(config["reports_root"]),
        config_path=config_path,
        config=config,
    )
    bridge.load()
    return bridge


__all__ = ["ForestLexiconBridge", "load_bridge_from_config"]
