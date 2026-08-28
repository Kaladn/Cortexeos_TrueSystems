"""Standalone Citation & Notes Server — port 5052.

Owns all /api/citations/* and /api/notes/* endpoints.
Reads/writes day-sharded JSON sidecars via CitationStore and NoteStore.
No dependency on Ollama or the LLM server.
"""
from __future__ import annotations

import json
import logging
import re
import sys
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# ── Project root on sys.path ──────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# ── Windows console UTF-8 fix ─────────────────────────────────
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from security.data_paths import (
    CHAT_THREADS_DIR,
    CITATION_FLAGS_PATH as _SEC_CITATION_FLAGS,
)
from security.secure_storage import secure_read_lines, secure_append_line
from Conversations.threads.citation_store import CitationStore
from Conversations.threads.note_store import NoteStore

# ── Logging ────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [CIT] %(message)s")
logger = logging.getLogger("citation_server")

# ── Stores ─────────────────────────────────────────────────────
citation_store = CitationStore(max_cached_days=14)
note_store = NoteStore(max_cached_days=14)


def now_utc_iso() -> str:
    dt = datetime.now(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


# ── FastAPI app ────────────────────────────────────────────────
app = FastAPI(title="Clearbox Citation Server", version="2.5.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5050", "http://127.0.0.1:5050",
        "https://localhost:5050", "https://127.0.0.1:5050",
        "http://localhost:8080", "http://127.0.0.1:8080",
        "https://localhost:8080", "https://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Clearbox-CSRF", "X-Trace-Id"],
)


# ══════════════════════════════════════════════════════════════
#  CITATION ENDPOINTS
# ══════════════════════════════════════════════════════════════


class CitationAttachRequest(BaseModel):
    day: str
    message_id: str
    block_id: str
    block_ordinal: int
    canonical: str
    subject: Optional[str] = None
    note: Optional[str] = None
    source: str = "manual"


class CitationDetachRequest(BaseModel):
    day: str
    message_id: str
    block_id: str
    cite_id: str


class CitationEditRequest(BaseModel):
    cite_id: str
    subject: Optional[str] = None
    note: Optional[str] = None
    coord: Optional[str] = None


class CitationDeleteRequest(BaseModel):
    cite_id: str
    hard: bool = False


class CitationSearchRequest(BaseModel):
    query: str
    limit: int = 5


class CitationFlagRequest(BaseModel):
    cite: str
    reason: str
    note: Optional[str] = None
    citation_meta: Optional[dict] = None


@app.post("/api/citations/attach")
async def attach_citation(req: CitationAttachRequest):
    try:
        record = citation_store.attach(
            day=req.day,
            message_id=req.message_id,
            block_id=req.block_id,
            block_ordinal=req.block_ordinal,
            canonical=req.canonical,
            subject=req.subject,
            note=req.note,
            source=req.source,
        )
        logger.info(f"Citation attached: {req.canonical} -> {req.message_id}:{req.block_id}")
        return {"ok": True, "cite": record}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.exception("Citation attach failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/citations/detach")
async def detach_citation(req: CitationDetachRequest):
    try:
        removed = citation_store.detach(
            day=req.day,
            message_id=req.message_id,
            block_id=req.block_id,
            cite_id=req.cite_id,
        )
        if not removed:
            raise HTTPException(status_code=404, detail="Citation not found on that block")
        return {"ok": True, "cite_id": req.cite_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Citation detach failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/citations/block")
async def get_block_citations(
    day: str = Query(...),
    message_id: str = Query(...),
    block_id: str = Query(...),
):
    try:
        cites = citation_store.get_block_cites(day, message_id, block_id)
        return {"cites": cites, "count": len(cites)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/citations/id/{cite_id}")
async def get_citation_by_id(cite_id: str):
    record = citation_store.get_citation(cite_id)
    if not record:
        raise HTTPException(status_code=404, detail="cite_id not found")
    return {"cite": record}


@app.post("/api/citations/search")
async def search_citations(req: CitationSearchRequest):
    query_lower = req.query.lower().split()
    if not query_lower:
        return {"results": [], "count": 0}

    results = []
    try:
        all_days = list(reversed(citation_store.list_days()))[:14]
        for day in all_days:
            sc = citation_store.load_day(day)
            for cid, rec in sc.by_id.items():
                haystack = " ".join(filter(None, [
                    rec.get("subject", ""),
                    rec.get("note", ""),
                    rec.get("coord", ""),
                ])).lower()
                score = sum(1 for t in query_lower if t in haystack)
                if score > 0:
                    results.append({
                        "cite_id": cid,
                        "coord": rec.get("coord"),
                        "subject": rec.get("subject"),
                        "note": rec.get("note"),
                        "snippet": (rec.get("subject") or rec.get("note") or rec.get("coord", ""))[:120],
                        "day": day,
                        "score": score,
                    })
        results.sort(key=lambda x: -x["score"])
        results = results[:req.limit]
    except Exception as e:
        logger.exception("Citation search failed")
        raise HTTPException(status_code=500, detail=str(e))

    return {"results": results, "count": len(results)}


@app.post("/api/citations/flag")
async def flag_citation(req: CitationFlagRequest):
    _SEC_CITATION_FLAGS.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "flagged_at": now_utc_iso(),
        "cite": req.cite,
        "reason": req.reason,
        "note": req.note,
        "citation_meta": req.citation_meta,
    }
    try:
        secure_append_line(_SEC_CITATION_FLAGS, json.dumps(record, ensure_ascii=False))
        logger.info(f"Citation flagged: {req.cite} ({req.reason})")
        return {"ok": True, "cite": req.cite}
    except Exception as e:
        logger.exception("Citation flag write failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/citations/resolve")
async def resolve_citation(cite: Optional[str] = None, day: Optional[str] = None):
    threads_dir = CHAT_THREADS_DIR

    if cite:
        block_match = re.match(r"^(\d{4}-\d{2}-\d{2}):SID:(\d+):BLK:(\d+)$", cite)
        sid_match = re.match(r"^SID:(\d+):BLK:(\d+)$", cite) if not block_match else None

        if block_match or sid_match:
            if block_match:
                target_day = block_match.group(1)
                server_id = int(block_match.group(2))
                blk_idx = int(block_match.group(3))
                search_days = [target_day]
            else:
                server_id = int(sid_match.group(1))
                blk_idx = int(sid_match.group(2))
                today = datetime.now()
                search_days = [(today - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(7)]

            for check_day in search_days:
                fp = threads_dir / f"{check_day}.jsonl"
                if not fp.exists():
                    continue
                try:
                    lines = secure_read_lines(fp)
                    for raw in lines:
                        raw = raw.strip()
                        if not raw:
                            continue
                        try:
                            obj = json.loads(raw)
                            msg_server_id = obj.get("serverId") or obj.get("server_id") or obj.get("id")
                            if msg_server_id == server_id:
                                blocks = obj.get("blocks", [])
                                if blk_idx < len(blocks):
                                    block = blocks[blk_idx]
                                    content = block.get("text") or block.get("content", "")
                                    return {
                                        "cite": cite,
                                        "found": True,
                                        "content": content,
                                        "sender": obj.get("sender"),
                                        "branch": obj.get("branch"),
                                        "timestamp": obj.get("timestamp"),
                                    }
                        except json.JSONDecodeError:
                            continue
                except Exception:
                    continue

            return {"cite": cite, "found": False, "content": None}

        m = re.match(r"^(\d{4}-\d{2}-\d{2}):L(\d+)$", cite)
        if not m:
            raise HTTPException(status_code=400, detail=f"Invalid citation format: {cite}")

        cite_day = m.group(1)
        cite_line = int(m.group(2))
        fp = threads_dir / f"{cite_day}.jsonl"
        if not fp.exists():
            return {"cite": cite, "found": False, "content": None}
        try:
            lines = secure_read_lines(fp)
            for i, raw in enumerate(lines, start=1):
                if i == cite_line:
                    obj = json.loads(raw.strip())
                    return {
                        "cite": cite, "found": True,
                        "content": obj.get("content", ""),
                        "sender": obj.get("sender"),
                        "branch": obj.get("branch"),
                        "timestamp": obj.get("timestamp"),
                    }
            return {"cite": cite, "found": False, "content": None}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    if day:
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", day):
            raise HTTPException(status_code=400, detail=f"Invalid day format: {day}")
        fp = threads_dir / f"{day}.jsonl"
        if not fp.exists():
            return {"day": day, "found": False, "messages": []}
        messages = []
        try:
            lines = secure_read_lines(fp)
            for raw in lines:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    obj = json.loads(raw)
                    messages.append({
                        "sender": obj.get("sender", "unknown"),
                        "content": obj.get("content", ""),
                        "branch": obj.get("branch", "main"),
                        "timestamp": obj.get("timestamp"),
                        "id": obj.get("id"),
                    })
                except json.JSONDecodeError:
                    continue
            return {"day": day, "found": True, "messages": messages, "count": len(messages)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    raise HTTPException(status_code=400, detail="Provide ?cite= or ?day= parameter")


@app.get("/api/citations/day/{day}")
async def get_day_citations(day: str):
    try:
        by_block = citation_store.get_day_cites_by_block(day)
        return {"day": day, "by_block": by_block, "count": sum(len(v) for v in by_block.values())}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/citations/all")
async def get_all_citations(cursor: Optional[str] = None, limit: int = 5):
    try:
        return citation_store.get_all_paginated(cursor=cursor, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/citations/distribution")
async def citations_distribution():
    try:
        return citation_store.distribution()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/citations/health")
async def citations_health(days: Optional[int] = None):
    try:
        return citation_store.health_check(days=days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/citations/edit")
async def edit_citation(req: CitationEditRequest):
    fields = {}
    if req.subject is not None:
        fields["subject"] = req.subject
    if req.note is not None:
        fields["note"] = req.note
    if req.coord is not None:
        fields["coord"] = req.coord
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    try:
        updated = citation_store.update_cite(req.cite_id, fields)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Citation not found: {req.cite_id}")
        return {"ok": True, "cite": updated}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Citation edit failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/citations/delete")
async def delete_citation(req: CitationDeleteRequest):
    try:
        if req.hard:
            removed = citation_store.hard_delete(req.cite_id)
        else:
            rec = citation_store.get_citation(req.cite_id)
            if not rec:
                raise HTTPException(status_code=404, detail=f"Citation not found: {req.cite_id}")
            day = rec.get("day", "")
            msg_id = rec.get("message_id", "")
            block_id = rec.get("block_id", "")
            removed = citation_store.detach(day, msg_id, block_id, req.cite_id)
        if not removed:
            raise HTTPException(status_code=404, detail=f"Citation not found: {req.cite_id}")
        return {"ok": True, "cite_id": req.cite_id, "hard": req.hard}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Citation delete failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════
#  NOTE ENDPOINTS
# ══════════════════════════════════════════════════════════════


class NoteAttachRequest(BaseModel):
    day: str
    message_id: str
    block_id: str
    block_ordinal: int
    note: str


class NoteDetachRequest(BaseModel):
    day: str
    message_id: str
    block_id: str
    note_id: str


class NoteEditRequest(BaseModel):
    note_id: str
    note: str


class NoteDeleteRequest(BaseModel):
    note_id: str


@app.post("/api/notes/attach")
async def attach_note(req: NoteAttachRequest):
    try:
        record = note_store.attach(
            day=req.day,
            message_id=req.message_id,
            block_id=req.block_id,
            block_ordinal=req.block_ordinal,
            note_text=req.note,
        )
        logger.info(f"Note attached: {req.message_id}:{req.block_id}")
        return {"ok": True, "note": record}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.exception("Note attach failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notes/detach")
async def detach_note(req: NoteDetachRequest):
    try:
        removed = note_store.detach(
            day=req.day,
            message_id=req.message_id,
            block_id=req.block_id,
            note_id=req.note_id,
        )
        if not removed:
            raise HTTPException(status_code=404, detail="Note not found on that block")
        return {"ok": True, "note_id": req.note_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Note detach failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notes/block")
async def get_block_notes(
    day: str = Query(...),
    message_id: str = Query(...),
    block_id: str = Query(...),
):
    try:
        notes = note_store.get_block_notes(day, message_id, block_id)
        return {"notes": notes, "count": len(notes)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/notes/all")
async def get_all_notes(
    cursor: Optional[str] = Query(None),
    limit: int = Query(5, ge=1, le=50),
):
    return note_store.get_all_paginated(cursor=cursor, limit=limit)


@app.get("/api/notes/distribution")
async def note_distribution():
    return note_store.distribution()


@app.post("/api/notes/edit")
async def edit_note(req: NoteEditRequest):
    try:
        rec = note_store.update_note(req.note_id, req.note)
        if not rec:
            raise HTTPException(status_code=404, detail="Note not found")
        return {"ok": True, "note": rec}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Note edit failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notes/delete")
async def delete_note(req: NoteDeleteRequest):
    try:
        removed = note_store.hard_delete(req.note_id)
        if not removed:
            raise HTTPException(status_code=404, detail="Note not found")
        return {"ok": True, "note_id": req.note_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Note delete failed")
        raise HTTPException(status_code=500, detail=str(e))


# ── Health / status ───────────────────────────────────────────

@app.get("/api/status")
async def status():
    cit_dist = citation_store.distribution()
    note_dist = note_store.distribution()
    return {
        "service": "citation_server",
        "version": "2.5.0",
        "citations": {"total": cit_dist["total"], "days": len(cit_dist["days"])},
        "notes": {"total": note_dist["total"], "days": len(note_dist["days"])},
    }


# ── Main ──────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Clearbox Citation & Notes Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind")
    parser.add_argument("--port", default=5052, type=int, help="Port (default 5052)")
    args = parser.parse_args()

    print(f"\n  Citation Server v2.5.0")
    print(f"  Listening: http://{args.host}:{args.port}")
    print(f"  Citations: {citation_store.distribution()['total']} across {len(citation_store.list_days())} days")
    print(f"  Notes:     {note_store.distribution()['total']} across {len(note_store.list_days())} days\n")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
