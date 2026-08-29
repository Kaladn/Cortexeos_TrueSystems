"""L3 — Lessons-learned extraction from daily session debriefs.

Reads daily summary debriefs and extracts structured lessons:
  - Decisions made (architectural, design, policy)
  - Corrections applied (bugs fixed, mistakes caught)
  - Key facts learned (domain knowledge, system behavior)

Storage: CHAT_MEMORY_DIR/lessons/{YYYY-MM-DD}.jsonl
  Each line: {"type": "decision|correction|fact", "text": "...", "ref": "YYYY-MM-DD:L##"}

Retrieval: load_recent_lessons(days=7) returns formatted context block
for injection into LLM system prompt.

Auto-triggered alongside daily summary in check_and_run_rollups().
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from security.data_paths import CHAT_MEMORY_DIR, CHAT_SUMMARIES_DIR
from security.secure_storage import secure_read_text

# ── Governed I/O ──────────────────────────────────────────────
try:
    from security.gateway import WriteZone, gateway as _gw
    _GOVERNED = True
except ImportError:
    _GOVERNED = False

import os as _os
ALLOW_LEGACY_WRITES = _os.environ.get("ALLOW_LEGACY_WRITES", "false").lower() in ("true", "1", "yes")

LESSONS_DIR = CHAT_MEMORY_DIR / "lessons"

# LLM config (same as summarizer)
import httpx
LLM_ENDPOINT = "http://localhost:11435/api/generate"
from routing.config import DEFAULTS as _ROUTING_DEFAULTS
LLM_MODEL = _ROUTING_DEFAULTS["pipeline"][2]["config"]["model"]
LLM_TIMEOUT = 120


def _call_llm(system_instruction: str, prompt: str, max_tokens: int = 400) -> str:
    """Call local LLM. Empty string on failure."""
    try:
        payload = {
            "model": LLM_MODEL,
            "prompt": prompt,
            "system_prompt": system_instruction,
            "stream": False,
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }
        r = httpx.post(LLM_ENDPOINT, json=payload, timeout=LLM_TIMEOUT)
        r.raise_for_status()
        return r.json().get("response", "").strip()
    except Exception as e:
        logger.warning("Lessons LLM error: %s", e)
        return ""


def _save_lessons(target_date: str, lessons: list[dict]) -> bool:
    """Write lessons JSONL for a given date."""
    LESSONS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{target_date}.jsonl"
    text = "\n".join(json.dumps(l, ensure_ascii=False) for l in lessons) + "\n"

    if _GOVERNED:
        try:
            rel = Path("lessons") / filename
            result = _gw.write("system", WriteZone.CHAT_MEMORY, str(rel), text)
            if not result.success:
                logger.warning("Lessons gateway write failed: %s", result.error)
                return False
            return True
        except Exception as e:
            logger.warning("Lessons gateway error: %s", e)
            return False
    else:
        if not ALLOW_LEGACY_WRITES:
            logger.warning("Lessons: legacy writes disabled")
            return False
        (LESSONS_DIR / filename).write_text(text, encoding="utf-8")
        return True


def extract_lessons(target_date: str) -> list[dict]:
    """Extract structured lessons from a daily debrief summary.

    Reads summaries/{target_date}.txt, sends to LLM for extraction,
    parses JSON output into lesson records.

    Returns list of {"type": str, "text": str, "ref": str} dicts.
    """
    lessons_path = LESSONS_DIR / f"{target_date}.jsonl"
    if lessons_path.exists():
        logger.info("Lessons already extracted for %s", target_date)
        return _load_day_lessons(target_date)

    summary_path = CHAT_SUMMARIES_DIR / f"{target_date}.txt"
    if not summary_path.exists():
        return []

    try:
        debrief = secure_read_text(summary_path).strip()
    except Exception:
        return []

    if not debrief or len(debrief) < 50:
        return []

    system_instruction = (
        "You are a lessons-learned extractor. Read the session debrief below "
        "and extract structured lessons. Output ONLY a JSON array.\n\n"
        "Each lesson is an object with exactly 3 fields:\n"
        '  "type": one of "decision", "correction", "fact"\n'
        '  "text": one sentence describing the lesson\n'
        '  "ref": the citation coord [ref YYYY-MM-DD:L##] if present, else ""\n\n'
        "Types:\n"
        '  "decision" — an architectural, design, or policy choice that was made\n'
        '  "correction" — a bug fix, mistake caught, or wrong approach abandoned\n'
        '  "fact" — domain knowledge or system behavior learned\n\n'
        "Rules:\n"
        "- Extract 3-8 lessons per session (fewer if session was light)\n"
        "- Each lesson must be one clear sentence\n"
        "- Do not invent details not in the debrief\n"
        "- Output ONLY the JSON array, nothing else"
    )

    prompt = f"Extract lessons from this debrief:\n\n{debrief}\n\nJSON:"

    raw = _call_llm(system_instruction, prompt, max_tokens=600)
    if not raw:
        return []

    # Parse JSON — handle LLM wrapping it in markdown fences
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw[:-3].strip()

    try:
        lessons = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Lessons: LLM returned invalid JSON for %s", target_date)
        return []

    if not isinstance(lessons, list):
        return []

    # Validate and normalize
    valid = []
    for l in lessons:
        if not isinstance(l, dict):
            continue
        ltype = l.get("type", "")
        text = l.get("text", "")
        ref = l.get("ref", "")
        if ltype in ("decision", "correction", "fact") and text:
            valid.append({"type": ltype, "text": text.strip(), "ref": str(ref).strip()})

    if valid:
        _save_lessons(target_date, valid)
        logger.info("Extracted %d lessons for %s", len(valid), target_date)

    return valid


def _load_day_lessons(target_date: str) -> list[dict]:
    """Load lessons JSONL for a specific date."""
    path = LESSONS_DIR / f"{target_date}.jsonl"
    if not path.exists():
        return []
    lessons = []
    try:
        for line in path.read_text(encoding="utf-8").strip().split("\n"):
            if line.strip():
                lessons.append(json.loads(line))
    except Exception:
        pass
    return lessons


def load_recent_lessons(days: int = 7) -> str | None:
    """Load lessons from the last N days, formatted for LLM context injection.

    Returns a formatted string block or None if no lessons found.
    """
    today = date.today()
    all_lessons: list[tuple[str, dict]] = []

    for i in range(1, days + 1):
        day = (today - timedelta(days=i)).isoformat()
        for l in _load_day_lessons(day):
            all_lessons.append((day, l))

    if not all_lessons:
        return None

    # Group by type
    decisions = [(d, l) for d, l in all_lessons if l["type"] == "decision"]
    corrections = [(d, l) for d, l in all_lessons if l["type"] == "correction"]
    facts = [(d, l) for d, l in all_lessons if l["type"] == "fact"]

    parts = ["LESSONS LEARNED (from recent sessions):"]

    if decisions:
        parts.append("\nDecisions:")
        for day, l in decisions:
            ref = f" {l['ref']}" if l.get("ref") else ""
            parts.append(f"  • {l['text']}{ref}")

    if corrections:
        parts.append("\nCorrections:")
        for day, l in corrections:
            ref = f" {l['ref']}" if l.get("ref") else ""
            parts.append(f"  • {l['text']}{ref}")

    if facts:
        parts.append("\nFacts:")
        for day, l in facts:
            ref = f" {l['ref']}" if l.get("ref") else ""
            parts.append(f"  • {l['text']}{ref}")

    return "\n".join(parts)
