"""Lexicon browser, management, 616, spellcheck, and symbol routes."""
from __future__ import annotations
from typing import Callable

from fastapi import APIRouter, HTTPException, Request

from bridges.state import BridgeState
from bridges.models import (
    Get616Request, AnalyzeUnmappedRequest, LexiconAppendRequest,
    LexiconIgnoreRequest, AssignSymbolRequest, SetStatusRequest, LexiconImportRequest,
)
from bridges.services.lexicon_analysis import LexiconAnalysisService
from bridges.services.lexicon_616 import Lexicon616Service
from bridges.services.lexicon_browse import LexiconBrowseService
from bridges.services.lexicon_mutation import LexiconMutationService
from bridges.services.spellcheck_queue import SpellcheckQueueService
from bridges.services.spellcheck_assist import SpellcheckAssistService
from bridges.services.symbol_graph import SymbolGraphService
from bridges.ws_manager import WebSocketManager

# Module-level constants referenced from bridge_server
from pathlib import Path as _Path
_BASE_DIR = _Path(__file__).resolve().parent.parent.parent
VERSION = "clearbox-bridge-2.0.0"
DEFAULT_MODEL = None  # resolved lazily via state.config


def make_router(
    state: BridgeState,
    ws_manager: WebSocketManager,
    ensure_lexicon_loaded: Callable,
) -> APIRouter:
    router = APIRouter()
    from routing.config import DEFAULTS as _ROUTING_DEFAULTS
    assist_service = SpellcheckAssistService(
        state=state,
        default_model=_ROUTING_DEFAULTS["pipeline"][2]["config"]["model"],
    )
    analysis_service = LexiconAnalysisService(
        state=state,
        base_dir=_BASE_DIR,
        version=VERSION,
    )
    service_616 = Lexicon616Service(
        state=state,
        version=VERSION,
    )
    browse_service = LexiconBrowseService(
        state=state,
        version=VERSION,
    )
    mutation_service = LexiconMutationService(
        state=state,
        ws_manager=ws_manager,
        version=VERSION,
        base_dir=_BASE_DIR,
    )
    spellcheck_queue_service = SpellcheckQueueService(state=state)
    symbol_graph_service = SymbolGraphService()

    # ── Lexicon Browser ──────────────────────────────────────────

    @router.get("/api/search_lexicon")
    async def get_search_lexicon(query: str = ""):
        await ensure_lexicon_loaded("search_lexicon")
        return await browse_service.search_lexicon(query)

    @router.get("/api/lexicon/distribution")
    async def get_lexicon_distribution(pack: str = "all"):
        await ensure_lexicon_loaded("lexicon_distribution")
        return await browse_service.distribution(pack=pack)

    @router.get("/api/lexicon/browse")
    async def get_lexicon_browse(letter: str = "A", limit: int = 50, pack: str = "all"):
        await ensure_lexicon_loaded("lexicon_browse")
        return await browse_service.browse(letter=letter, limit=limit, pack=pack)

    @router.get("/api/lexicon/sample")
    async def get_lexicon_sample(count: int = 24, pack: str = "all"):
        await ensure_lexicon_loaded("lexicon_sample")
        return await browse_service.sample(count=count, pack=pack)

    @router.get("/api/lexicon/top")
    async def get_lexicon_top(count: int = 30, pack: str = "all"):
        await ensure_lexicon_loaded("lexicon_top")
        return await browse_service.top(count=count, pack=pack)

    @router.get("/api/lexicon/recent")
    async def get_lexicon_recent(count: int = 30, pack: str = "all"):
        await ensure_lexicon_loaded("lexicon_recent")
        return await browse_service.recent(count=count, pack=pack)

    @router.get("/api/lexicon/entry")
    async def get_lexicon_entry(word: str = ""):
        await ensure_lexicon_loaded("lexicon_entry")
        return await browse_service.entry(word=word)

    # ── Lexicon Unmatched Review Queue ───────────────────────────

    @router.get("/api/lexicon/unmatched")
    async def get_lexicon_unmatched(limit: int = 100, sort: str = "frequency", letter: str = ""):
        return await analysis_service.unmatched(limit=limit, sort=sort, letter=letter)

    @router.post("/api/lexicon/ignore")
    async def post_lexicon_ignore(body: LexiconIgnoreRequest):
        await ensure_lexicon_loaded("lexicon_ignore")
        return await mutation_service.ignore(body)

    @router.delete("/api/lexicon/ignore/{word}")
    async def delete_lexicon_ignore(word: str):
        await ensure_lexicon_loaded("lexicon_unignore")
        return await mutation_service.unignore(word)

    @router.get("/api/lexicon/ignored")
    async def get_lexicon_ignored(letter: str = ""):
        await ensure_lexicon_loaded("lexicon_ignored")
        return await browse_service.ignored(letter=letter)

    # ── Pending Review Queue ─────────────────────────────────────

    @router.post("/api/lexicon/approve")
    async def post_lexicon_approve(body: LexiconIgnoreRequest):
        """Stage 1: move unmatched word to pending list."""
        await ensure_lexicon_loaded("lexicon_approve")
        return await mutation_service.approve_to_pending(body.word)

    @router.get("/api/lexicon/pending")
    async def get_lexicon_pending():
        await ensure_lexicon_loaded("lexicon_pending")
        return await mutation_service.get_pending()

    @router.post("/api/lexicon/pending/assign")
    async def post_pending_assign(body: LexiconIgnoreRequest):
        """Stage 2: finalize a pending word — assign spare slot."""
        await ensure_lexicon_loaded("lexicon_finalize_pending")
        return await mutation_service.finalize_pending(body.word)

    @router.post("/api/lexicon/pending/assign-all")
    async def post_pending_assign_all():
        """Assign spare slots to ALL pending words."""
        await ensure_lexicon_loaded("lexicon_finalize_all_pending")
        return await mutation_service.finalize_all_pending()

    @router.delete("/api/lexicon/pending/{word}")
    async def delete_pending_word(word: str):
        """Remove word from pending (send back to unmatched)."""
        await ensure_lexicon_loaded("lexicon_remove_pending")
        return await mutation_service.remove_pending(word)

    # ── Bulk Unmatched Operations ────────────────────────────────

    @router.post("/api/lexicon/unmatched/approve-all")
    async def post_unmatched_approve_all(request: Request):
        """Move all currently visible unmatched words to pending."""
        body = await request.json()
        words = body.get("words", [])
        if not words:
            raise HTTPException(400, "words list required")
        await ensure_lexicon_loaded("lexicon_bulk_approve")
        return await mutation_service.bulk_approve_unmatched(words)

    @router.post("/api/lexicon/unmatched/deny-all")
    async def post_unmatched_deny_all(request: Request):
        """Ignore all currently visible unmatched words."""
        body = await request.json()
        words = body.get("words", [])
        if not words:
            raise HTTPException(400, "words list required")
        await ensure_lexicon_loaded("lexicon_bulk_deny")
        return await mutation_service.bulk_deny_unmatched(words)

    # ── 616 + Unmapped Analysis ──────────────────────────────────

    @router.post("/api/616")
    async def post_get_616(body: Get616Request):
        await ensure_lexicon_loaded("616")
        return service_616.get(body.word, body.topk)

    @router.post("/api/analyze_unmapped")
    async def post_analyze_unmapped(body: AnalyzeUnmappedRequest):
        return await analysis_service.analyze_unmapped(body)

    @router.post("/api/lexicon/append")
    async def post_lexicon_append(body: LexiconAppendRequest):
        await ensure_lexicon_loaded("lexicon_append")
        return await mutation_service.append(body)

    @router.post("/api/lexicon/assign-slot")
    async def post_lexicon_assign_slot(body: LexiconAppendRequest):
        await ensure_lexicon_loaded("lexicon_assign_slot")
        return await mutation_service.assign_slot(body)

    @router.post("/api/symbol/assign")
    async def post_assign_symbol(body: AssignSymbolRequest):
        await ensure_lexicon_loaded("symbol_assign")
        return await mutation_service.assign_symbol(body)

    @router.post("/api/lexicon/status")
    async def post_lexicon_status(body: SetStatusRequest):
        await ensure_lexicon_loaded("lexicon_status")
        return await mutation_service.set_status(body)

    @router.delete("/api/lexicon/canonical")
    async def delete_lexicon_canonical():
        await ensure_lexicon_loaded("lexicon_clear_canonical")
        return await mutation_service.clear_canonical()

    @router.post("/api/lexicon/return-to-pool")
    async def post_lexicon_return_to_pool():
        await ensure_lexicon_loaded("lexicon_return_to_pool")
        return await mutation_service.return_to_pool()

    @router.post("/api/lexicon/import")
    async def post_lexicon_import(body: LexiconImportRequest):
        await ensure_lexicon_loaded("lexicon_import")
        return await mutation_service.import_words(body)

    @router.post("/api/lexicon/unload")
    async def lexicon_unload():
        return await mutation_service.unload()

    # ── Temp Pool (ephemeral document symbolization) ──────────

    @router.post("/api/lexicon/temp/checkout")
    async def post_temp_checkout(request: Request):
        body = await request.json()
        word = body.get("word", "")
        doc_id = body.get("doc_id", "")
        if not word:
            raise HTTPException(400, "word required")
        await ensure_lexicon_loaded("temp_checkout")
        try:
            return state.bridge.checkout_temp_slot(word, doc_id)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @router.post("/api/lexicon/temp/return")
    async def post_temp_return(request: Request):
        body = await request.json()
        word = body.get("word", "")
        if not word:
            raise HTTPException(400, "word required")
        await ensure_lexicon_loaded("temp_return")
        return state.bridge.return_temp_slot(word)

    @router.post("/api/lexicon/temp/return-doc")
    async def post_temp_return_doc(request: Request):
        body = await request.json()
        doc_id = body.get("doc_id", "")
        if not doc_id:
            raise HTTPException(400, "doc_id required")
        await ensure_lexicon_loaded("temp_return_doc")
        return state.bridge.return_all_temp_by_doc(doc_id)

    @router.get("/api/lexicon/temp/stale")
    async def get_temp_stale(hours: int = 24):
        await ensure_lexicon_loaded("temp_stale")
        stale = state.bridge.get_stale_temp_checkouts(stale_hours=hours)
        return {"stale": stale, "total": len(stale)}

    @router.post("/api/lexicon/temp/promote")
    async def post_temp_promote(request: Request):
        """Promote a temp checkout to permanent canonical slot."""
        body = await request.json()
        word = body.get("word", "")
        if not word:
            raise HTTPException(400, "word required")
        await ensure_lexicon_loaded("temp_promote")
        try:
            return state.bridge.promote_temp_to_canonical(word)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @router.post("/api/lexicon/temp/resolve")
    async def post_temp_resolve(request: Request):
        """Resolve a stale temp checkout: keep (promote), return, or lake (return + note)."""
        body = await request.json()
        word = body.get("word", "")
        action = body.get("action", "")  # "keep" | "return" | "lake"
        if not word or not action:
            raise HTTPException(400, "word and action required")
        await ensure_lexicon_loaded("temp_resolve")
        if action == "keep":
            try:
                result = state.bridge.promote_temp_to_canonical(word)
                result["action"] = "promoted"
                return result
            except ValueError as exc:
                raise HTTPException(400, str(exc)) from exc
        elif action in ("return", "lake"):
            result = state.bridge.return_temp_slot(word)
            result["action"] = action
            return result
        else:
            raise HTTPException(400, f"Unknown action: {action}")

    # ── Spell-Check API ─────────────────────────────────────────
    # Prevents semantic duplication: misspellings → different symbol IDs
    # for the same concept.  SymSpell proposes, operator decides, alias map
    # enforces before symbolization.

    @router.post("/api/spellcheck/check")
    async def spellcheck_check(request: Request):
        body = await request.json()
        return await spellcheck_queue_service.check(body.get("tokens", []))

    @router.get("/api/spellcheck/queue")
    async def spellcheck_queue(limit: int = 50, offset: int = 0):
        return spellcheck_queue_service.queue(limit=limit, offset=offset)

    @router.post("/api/spellcheck/resolve")
    async def spellcheck_resolve(request: Request):
        body = await request.json()
        return spellcheck_queue_service.resolve(
            entry_id=body.get("id", ""),
            action=body.get("action", ""),
            final_token=body.get("final_token", ""),
        )

    @router.get("/api/spellcheck/stats")
    async def spellcheck_stats():
        return spellcheck_queue_service.stats()

    @router.post("/api/spellcheck/model-assist")
    async def spellcheck_model_assist(request: Request):
        """For unknown tokens: ask Ollama to suggest a correction."""
        body = await request.json()
        token = body.get("token", "")
        context = body.get("context", "")
        if not token:
            raise HTTPException(400, "token required")
        return await assist_service.suggest(token, context)

    # ── Symbols API ──────────────────────────────────────────────
    # Human-readable access to the symbolic graph. All symbol IDs are
    # resolved to readable tokens before reaching the UI.

    @router.post("/api/symbols/resolve")
    async def symbols_resolve(request: Request):
        body = await request.json()
        return symbol_graph_service.resolve(body.get("symbol_ids", []))

    @router.get("/api/symbols/search")
    async def symbols_search(q: str = "", limit: int = 20):
        return symbol_graph_service.search(q=q, limit=limit)

    @router.get("/api/symbols/top")
    async def symbols_top(limit: int = 20):
        return symbol_graph_service.top(limit=limit)

    return router
