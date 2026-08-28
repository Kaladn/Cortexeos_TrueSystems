"""Memory system admin endpoints — status, rollup, bootstrap."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from bridges.state import BridgeState
from security.data_paths import (
    CHAT_THREADS_DIR,
    CHAT_SUMMARIES_DIR,
    CHAT_MEMORY_DIR,
)

logger = logging.getLogger(__name__)


class RollupRequest(BaseModel):
    start_date: str                   # YYYY-MM-DD inclusive
    end_date: Optional[str] = None    # YYYY-MM-DD inclusive, default yesterday
    include_weekly: bool = True
    include_monthly: bool = True
    include_chat_ingest: bool = True  # 616 map + LakeSpeak ingest


class ChatIngestRequest(BaseModel):
    start_date: str
    end_date: Optional[str] = None
    skip_if_exists: bool = True


def make_router(state: BridgeState) -> APIRouter:
    router = APIRouter()

    # ── GET /api/memory/status ────────────────────────────────

    @router.get("/api/memory/status")
    async def memory_status():
        """Report what memory layers are populated vs empty."""
        chat_days = sorted(
            p.stem for p in CHAT_THREADS_DIR.glob("*.jsonl")
            if p.stem[:4].isdigit()
        )
        summaries = sorted(
            p.stem for p in CHAT_SUMMARIES_DIR.glob("*.txt")
            if p.stem[:4].isdigit()
        )
        lessons_dir = CHAT_MEMORY_DIR / "lessons"
        lessons = sorted(
            p.stem for p in lessons_dir.glob("*.jsonl")
        ) if lessons_dir.exists() else []

        reasoning_dir = CHAT_MEMORY_DIR / "reasoning"
        reasoning = sorted(
            p.stem for p in reasoning_dir.glob("*.jsonl")
        ) if reasoning_dir.exists() else []

        weekly_dir = CHAT_SUMMARIES_DIR / "week"
        weekly = sorted(
            p.stem for p in weekly_dir.glob("*.txt")
        ) if weekly_dir.exists() else []

        monthly_dir = CHAT_SUMMARIES_DIR / "month"
        monthly = sorted(
            p.stem for p in monthly_dir.glob("*.txt")
        ) if monthly_dir.exists() else []

        gaps = [d for d in chat_days if d not in summaries]

        # Check which days have been ingested (616 mapped) into the data lake
        ingested = []
        try:
            from Conversations.threads.map_manager import map_manager
            for ds in chat_days:
                import hashlib
                # Reconstruct cite_id the same way chat_ingest does
                # (via MapManager.create_citation content hash)
                cite = map_manager.get_citation(f"cite_chat_{ds}")
                if not cite:
                    # Check by filename pattern in DB
                    from security.data_paths import CITATION_DB_PATH
                    import sqlite3
                    with sqlite3.connect(CITATION_DB_PATH) as conn:
                        row = conn.execute(
                            "SELECT cite_id FROM citations WHERE filename = ?",
                            (f"chat_{ds}.jsonl",)
                        ).fetchone()
                        if row:
                            ingested.append(ds)
                else:
                    ingested.append(ds)
        except Exception:
            pass
        ingest_gaps = [d for d in chat_days if d not in ingested]

        return {
            "chat_days": chat_days,
            "summaries": summaries,
            "lessons": lessons,
            "reasoning": reasoning,
            "weekly": weekly,
            "monthly": monthly,
            "ingested": ingested,
            "gaps": gaps,
            "ingest_gaps": ingest_gaps,
        }

    # ── POST /api/memory/rollup ───────────────────────────────

    @router.post("/api/memory/rollup")
    async def trigger_rollup(body: RollupRequest):
        """Manually trigger summary rollups for a date range."""
        from Conversations.threads.summarizer import summarize_day, summarize_week, summarize_month
        from Conversations.threads.lessons import extract_lessons

        end = body.end_date or (date.today() - timedelta(days=1)).isoformat()
        start_d = date.fromisoformat(body.start_date)
        end_d = date.fromisoformat(end)

        results = {"daily": [], "lessons": [], "weekly": [], "monthly": [], "chat_ingest": []}
        current = start_d
        while current <= end_d:
            ds = current.isoformat()
            # Daily summary
            try:
                text = summarize_day(ds)
                results["daily"].append({"date": ds, "ok": bool(text), "chars": len(text or "")})
            except Exception as e:
                logger.warning("Rollup daily %s failed: %s", ds, e)
                results["daily"].append({"date": ds, "ok": False, "error": str(e)})

            # Lessons (requires daily summary to exist)
            try:
                les = extract_lessons(ds)
                results["lessons"].append({"date": ds, "ok": bool(les), "count": len(les)})
            except Exception as e:
                logger.warning("Rollup lessons %s failed: %s", ds, e)
                results["lessons"].append({"date": ds, "ok": False, "error": str(e)})

            # Chat ingest: 616 map + LakeSpeak
            if body.include_chat_ingest and state.bridge:
                try:
                    from Conversations.threads.chat_ingest import ingest_chat_day
                    r = ingest_chat_day(ds, state.bridge)
                    results["chat_ingest"].append(r)
                except Exception as e:
                    logger.warning("Rollup chat ingest %s failed: %s", ds, e)
                    results["chat_ingest"].append({"date": ds, "ok": False, "error": str(e)})

            current += timedelta(days=1)

        # Weekly rollups
        if body.include_weekly:
            weeks_seen = set()
            current = start_d
            while current <= end_d:
                yw = current.isocalendar()[:2]
                if yw not in weeks_seen:
                    weeks_seen.add(yw)
                    try:
                        text = summarize_week(yw[0], yw[1])
                        results["weekly"].append({"week": f"{yw[0]}-W{yw[1]:02d}", "ok": bool(text)})
                    except Exception as e:
                        results["weekly"].append({"week": f"{yw[0]}-W{yw[1]:02d}", "ok": False, "error": str(e)})
                current += timedelta(days=1)

        # Monthly rollups
        if body.include_monthly:
            months_seen = set()
            current = start_d
            while current <= end_d:
                ym = (current.year, current.month)
                if ym not in months_seen:
                    months_seen.add(ym)
                    try:
                        text = summarize_month(ym[0], ym[1])
                        results["monthly"].append({"month": f"{ym[0]}-{ym[1]:02d}", "ok": bool(text)})
                    except Exception as e:
                        results["monthly"].append({"month": f"{ym[0]}-{ym[1]:02d}", "ok": False, "error": str(e)})
                current += timedelta(days=1)

        return results

    # ── POST /api/memory/bootstrap ────────────────────────────

    @router.post("/api/memory/bootstrap")
    async def bootstrap_memory():
        """One-shot: generate all missing summaries and lessons for all chat days."""
        from Conversations.threads.summarizer import summarize_day, summarize_week, summarize_month
        from Conversations.threads.lessons import extract_lessons

        chat_days = sorted(
            p.stem for p in CHAT_THREADS_DIR.glob("*.jsonl")
            if p.stem[:4].isdigit()
        )
        existing_summaries = set(
            p.stem for p in CHAT_SUMMARIES_DIR.glob("*.txt")
            if p.stem[:4].isdigit()
        )
        existing_lessons = set()
        lessons_dir = CHAT_MEMORY_DIR / "lessons"
        if lessons_dir.exists():
            existing_lessons = set(p.stem for p in lessons_dir.glob("*.jsonl"))

        results = {"daily": [], "lessons": [], "weekly": [], "monthly": [], "chat_ingest": []}

        for ds in chat_days:
            # Daily summary
            if ds not in existing_summaries:
                try:
                    text = summarize_day(ds)
                    results["daily"].append({"date": ds, "ok": bool(text), "chars": len(text or "")})
                except Exception as e:
                    logger.warning("Bootstrap daily %s failed: %s", ds, e)
                    results["daily"].append({"date": ds, "ok": False, "error": str(e)})
            else:
                results["daily"].append({"date": ds, "ok": True, "skipped": True})

            # Lessons
            if ds not in existing_lessons:
                try:
                    les = extract_lessons(ds)
                    results["lessons"].append({"date": ds, "ok": bool(les), "count": len(les)})
                except Exception as e:
                    logger.warning("Bootstrap lessons %s failed: %s", ds, e)
                    results["lessons"].append({"date": ds, "ok": False, "error": str(e)})
            else:
                results["lessons"].append({"date": ds, "ok": True, "skipped": True})

            # Chat ingest: 616 map + LakeSpeak (skip_if_exists=True for idempotency)
            if state.bridge:
                try:
                    from Conversations.threads.chat_ingest import ingest_chat_day
                    r = ingest_chat_day(ds, state.bridge, skip_if_exists=True)
                    results["chat_ingest"].append(r)
                except Exception as e:
                    logger.warning("Bootstrap chat ingest %s failed: %s", ds, e)
                    results["chat_ingest"].append({"date": ds, "ok": False, "error": str(e)})

        # Weekly rollups for all weeks that have at least one daily summary
        weeks_seen = set()
        for ds in chat_days:
            d = date.fromisoformat(ds)
            yw = d.isocalendar()[:2]
            if yw not in weeks_seen:
                weeks_seen.add(yw)
                try:
                    text = summarize_week(yw[0], yw[1])
                    results["weekly"].append({"week": f"{yw[0]}-W{yw[1]:02d}", "ok": bool(text)})
                except Exception as e:
                    results["weekly"].append({"week": f"{yw[0]}-W{yw[1]:02d}", "ok": False, "error": str(e)})

        # Monthly rollups
        months_seen = set()
        for ds in chat_days:
            d = date.fromisoformat(ds)
            ym = (d.year, d.month)
            if ym not in months_seen:
                months_seen.add(ym)
                try:
                    text = summarize_month(d.year, d.month)
                    results["monthly"].append({"month": f"{d.year}-{d.month:02d}", "ok": bool(text)})
                except Exception as e:
                    results["monthly"].append({"month": f"{d.year}-{d.month:02d}", "ok": False, "error": str(e)})

        return results

    # ── POST /api/memory/ingest ──────────────────────────────

    @router.post("/api/memory/ingest")
    async def ingest_chats(body: ChatIngestRequest):
        """616 map + LakeSpeak ingest for chat logs in a date range.

        Unlike rollup/bootstrap, this ONLY does mapping and lake ingest —
        no summaries, no lessons, no weekly/monthly rollups.
        """
        if not state.bridge:
            return {"error": "Bridge not loaded — lexicon required for 616 mapping"}

        from Conversations.threads.chat_ingest import ingest_chat_range

        end = body.end_date or date.today().isoformat()
        results = ingest_chat_range(
            body.start_date, end, state.bridge,
            skip_if_exists=body.skip_if_exists,
        )
        return {"results": results}

    return router
