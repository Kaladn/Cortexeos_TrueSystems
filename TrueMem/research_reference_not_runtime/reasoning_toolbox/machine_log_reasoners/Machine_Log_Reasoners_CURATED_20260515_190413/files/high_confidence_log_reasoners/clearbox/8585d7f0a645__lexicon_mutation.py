"""Lexicon mutation/update service."""
from __future__ import annotations

import gc as _gc
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from bridges.helpers import _safe_error, _validate_path_within
from bridges.models import (
    AssignSymbolRequest,
    LexiconAppendRequest,
    LexiconIgnoreRequest,
    LexiconImportRequest,
    SetStatusRequest,
)
from bridges.state import BridgeState, LOGGER
from bridges.ws_manager import WebSocketManager


class LexiconMutationService:
    """Owns mutating lexicon operations and their broadcast side effects."""

    def __init__(
        self,
        *,
        state: BridgeState,
        ws_manager: WebSocketManager,
        version: str,
        base_dir: Path,
    ) -> None:
        self.state = state
        self.ws_manager = ws_manager
        self.version = version
        self.base_dir = base_dir

    async def ignore(self, body: LexiconIgnoreRequest) -> dict[str, Any]:
        word = body.word.strip()
        if not word:
            raise HTTPException(400, "word is required")
        self.state.bridge.ignore_word(word)
        # Also remove from pending if it was there
        self.state.bridge.remove_pending_word(word)
        await self.ws_manager.broadcast({"evt": "lexicon-ignore", "word": word})
        return {"word": word, "ignored": True}

    async def unignore(self, word: str) -> dict[str, Any]:
        self.state.bridge.unignore_word(word)
        await self.ws_manager.broadcast({"evt": "lexicon-unignore", "word": word})
        return {"word": word, "ignored": False}

    async def append(self, body: LexiconAppendRequest) -> dict[str, Any]:
        if not body.word:
            raise HTTPException(status_code=400, detail="word is required")
        result = self.state.bridge.append_word(body.word, body.status)
        result["version"] = self.version
        await self.ws_manager.broadcast({"evt": "lexicon-append", "word": body.word, "version": self.version})
        return result

    async def assign_slot(self, body: LexiconAppendRequest) -> dict[str, Any]:
        if not body.word:
            raise HTTPException(status_code=400, detail="word is required")
        try:
            result = self.state.bridge.assign_to_canonical_slot(body.word)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        result["version"] = self.version
        await self.ws_manager.broadcast(
            {
                "evt": "lexicon-assign-slot",
                "word": body.word,
                "symbol": result.get("symbol"),
                "version": self.version,
            }
        )
        return result

    async def assign_symbol(self, body: AssignSymbolRequest) -> dict[str, Any]:
        if not body.word:
            raise HTTPException(status_code=400, detail="word is required")
        try:
            result = self.state.bridge.assign_symbol(body.word, body.symbol, body.force or False)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=_safe_error(exc)) from exc
        result["version"] = self.version
        await self.ws_manager.broadcast(
            {
                "evt": "symbol-assign",
                "word": body.word,
                "symbol": result.get("symbol"),
                "version": self.version,
            }
        )
        return result

    async def set_status(self, body: SetStatusRequest) -> dict[str, Any]:
        if not body.word:
            raise HTTPException(status_code=400, detail="word is required")
        result = self.state.bridge.set_status(body.word, body.status)
        result["version"] = self.version
        await self.ws_manager.broadcast(
            {
                "evt": "lexicon-status",
                "word": body.word,
                "status": body.status,
                "version": self.version,
            }
        )
        return result

    async def clear_canonical(self) -> dict[str, Any]:
        result = self.state.bridge.clear_canonical()
        result["version"] = self.version
        await self.ws_manager.broadcast(
            {
                "evt": "lexicon-cleared",
                "purged": result["purged"],
                "version": self.version,
            }
        )
        return result

    async def return_to_pool(self) -> dict[str, Any]:
        result = self.state.bridge.return_to_pool()
        result["version"] = self.version
        await self.ws_manager.broadcast(
            {
                "evt": "lexicon-pool-reset",
                "moved": result["moved"],
                "version": self.version,
            }
        )
        return result

    async def import_words(self, body: LexiconImportRequest) -> dict[str, Any]:
        from security.data_paths import CLEARBOX_DATA_ROOT

        words_dir = Path(body.words_dir)
        try:
            safe_words_dir = _validate_path_within(words_dir, self.base_dir, "words_dir")
        except HTTPException:
            safe_words_dir = _validate_path_within(words_dir, CLEARBOX_DATA_ROOT, "words_dir")
        try:
            result = self.state.bridge.import_word_list(safe_words_dir)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=_safe_error(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=_safe_error(exc)) from exc

        result["version"] = self.version
        await self.ws_manager.broadcast(
            {
                "evt": "lexicon-imported",
                "imported": result["imported"],
                "version": self.version,
            }
        )
        return result

    # ── Pending review queue ──────────────────────────────────

    async def approve_to_pending(self, word: str) -> dict[str, Any]:
        """Move unmatched word to pending list (stage 1 — no slot assigned yet)."""
        word = word.strip()
        if not word:
            raise HTTPException(400, "word is required")
        result = self.state.bridge.add_pending_word(word)
        await self.ws_manager.broadcast({"evt": "lexicon-pending-add", "word": word})
        return result

    async def get_pending(self) -> dict[str, Any]:
        words = self.state.bridge.get_pending_words()
        return {"words": words, "total": len(words)}

    async def finalize_pending(self, word: str) -> dict[str, Any]:
        """Stage 2: assign a spare slot to a pending word. Returns proof."""
        word = word.strip()
        if not word:
            raise HTTPException(400, "word is required")
        try:
            result = self.state.bridge.assign_to_canonical_slot(word)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        # Remove from pending list now that it's slotted
        self.state.bridge.remove_pending_word(word)
        result["version"] = self.version
        await self.ws_manager.broadcast(
            {
                "evt": "lexicon-assign-slot",
                "word": word,
                "symbol": result.get("symbol"),
                "hex": result.get("hex"),
                "version": self.version,
            }
        )
        return result

    async def finalize_all_pending(self) -> dict[str, Any]:
        """Assign slots to ALL pending words in one batch."""
        pending = self.state.bridge.get_pending_words()
        results = []
        for entry in pending:
            w = entry.get("display") or entry.get("word", "")
            try:
                r = self.state.bridge.assign_to_canonical_slot(w)
                self.state.bridge.remove_pending_word(w)
                results.append({"word": w, "ok": True, "hex": r.get("hex"), "symbol": r.get("symbol")})
            except ValueError as exc:
                results.append({"word": w, "ok": False, "error": str(exc)})
        await self.ws_manager.broadcast({"evt": "lexicon-assign-batch", "count": len([r for r in results if r["ok"]])})
        return {"results": results, "assigned": sum(1 for r in results if r["ok"]), "failed": sum(1 for r in results if not r["ok"])}

    async def remove_pending(self, word: str) -> dict[str, Any]:
        """Remove a word from pending list (send back to unmatched)."""
        word = word.strip()
        if not word:
            raise HTTPException(400, "word is required")
        self.state.bridge.remove_pending_word(word)
        await self.ws_manager.broadcast({"evt": "lexicon-pending-remove", "word": word})
        return {"word": word, "removed": True}

    # ── Bulk unmatched operations ──────────────────────────────

    async def bulk_approve_unmatched(self, words: list[str]) -> dict[str, Any]:
        """Move multiple unmatched words to pending in one call."""
        results = []
        for w in words:
            w = w.strip()
            if not w:
                continue
            r = self.state.bridge.add_pending_word(w)
            results.append(r)
        await self.ws_manager.broadcast({"evt": "lexicon-pending-bulk", "count": len(results)})
        return {"results": results, "moved": sum(1 for r in results if r.get("pending"))}

    async def bulk_deny_unmatched(self, words: list[str]) -> dict[str, Any]:
        """Ignore multiple unmatched words in one call."""
        count = 0
        for w in words:
            w = w.strip()
            if not w:
                continue
            self.state.bridge.ignore_word(w)
            self.state.bridge.remove_pending_word(w)
            count += 1
        await self.ws_manager.broadcast({"evt": "lexicon-ignore-bulk", "count": count})
        return {"ignored": count}

    async def unload(self) -> dict[str, Any]:
        async with self.state.lock:
            count = len(self.state.bridge.entries)
            if not self.state.bridge.loaded:
                return {"ok": True, "was_loaded": False, "entries_freed": 0}
            self.state.bridge.entries.clear()
            self.state.bridge.loaded = False
        _gc.collect()
        LOGGER.info("Lexicon unloaded on request - %d entries freed", count)
        return {"ok": True, "was_loaded": True, "entries_freed": count}
