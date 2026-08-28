"""Chat Summarizer — daily, weekly, monthly, yearly rollups.

Daily:   Read day's JSONL → LLM → summaries/{date}.txt
Weekly:  Read 7 daily summaries → LLM → summaries/week/{year}-W{week}.txt
Monthly: Read month's daily summaries → LLM → summaries/month/{year}-{month}.txt
Yearly:  Read 12 monthly summaries → LLM → summaries/year/{year}.txt

Auto-trigger: daily_logger.py calls check_and_run_rollups() in a background
thread when a new day file is created. Non-blocking, non-fatal.
"""

import json
import logging
import httpx
from pathlib import Path
from datetime import date, timedelta
from typing import Optional, Any, List

logger = logging.getLogger(__name__)

# Secure data paths
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from security.data_paths import (
    CHAT_THREADS_DIR, CHAT_SUMMARIES_DIR,
    CHAT_SUMMARIES_WEEK_DIR, CHAT_SUMMARIES_MONTH_DIR, CHAT_SUMMARIES_YEAR_DIR,
)
from security.secure_storage import (
    secure_read_lines, secure_read_text, secure_write_text,
)

# ── Governed I/O: route writes through the gateway ────────────
try:
    from security.gateway import WriteZone, gateway as _gw
    _GOVERNED = True
except ImportError:
    _GOVERNED = False

import os as _os
ALLOW_LEGACY_WRITES = _os.environ.get("ALLOW_LEGACY_WRITES", "false").lower() in ("true", "1", "yes")

# Paths
THREAD_DIR = CHAT_THREADS_DIR
SUMMARY_DIR = CHAT_SUMMARIES_DIR
WEEK_DIR = CHAT_SUMMARIES_WEEK_DIR
MONTH_DIR = CHAT_SUMMARIES_MONTH_DIR
YEAR_DIR = CHAT_SUMMARIES_YEAR_DIR

# LLM config
LLM_ENDPOINT = "http://localhost:11435/api/generate"
# Model: use the routing default (single source of truth — routing/config.py)
from routing.config import DEFAULTS as _ROUTING_DEFAULTS
LLM_MODEL = _ROUTING_DEFAULTS["pipeline"][2]["config"]["model"]
TIMEOUT = 120  # 2 minutes max

# Context window management
CHARS_PER_TOKEN = 4  # Conservative estimate
MAX_CONVO_TOKENS = 3000  # Leave room for instruction + response
MAX_CONVO_CHARS = MAX_CONVO_TOKENS * CHARS_PER_TOKEN  # 12,000 chars


def _fmt_msg(msg: dict[str, Any]) -> str:
    """Format a single message for summary prompt."""
    sender = msg.get("sender", "unknown").upper()
    content = msg.get("content", "")
    return f"[{sender}]\n{content}\n\n"


def select_messages_for_summary(messages: list[dict[str, Any]], max_chars: int = MAX_CONVO_CHARS) -> str:
    """Select messages that fit within context window, preserving whole messages.
    
    Strategy:
    - Keep first message as anchor (context)
    - Fill from the end (most recent work)
    - Never split messages mid-content
    
    Args:
        messages: List of message dicts with 'sender' and 'content' keys
        max_chars: Maximum characters to include
        
    Returns:
        Formatted conversation string that fits in context
    """
    if not messages:
        return ""
    
    # Try to keep first message as anchor
    anchor = _fmt_msg(messages[0])
    
    # Build from end (most recent messages)
    tail_parts: list[str] = []
    total = 0
    
    for msg in reversed(messages[1:]):
        formatted = _fmt_msg(msg)
        if total + len(formatted) > max_chars:
            break
        tail_parts.append(formatted)
        total += len(formatted)
    
    tail_parts.reverse()
    tail = "".join(tail_parts)
    
    # If anchor + tail fits, use both
    sep = "\n--- (earlier messages) ---\n\n"
    if len(anchor) + len(sep) + len(tail) <= max_chars:
        return anchor + sep + tail
    
    # If only tail fits, return it
    if tail:
        return tail
    
    # Worst case: single huge message, hard truncate
    last = _fmt_msg(messages[-1])
    return last[-max_chars:]


def _load_messages(target_date: str) -> list[dict[str, Any]]:
    """Load all messages from a day's JSONL file.

    Returns list of message dicts (empty on missing file or total failure).
    Each dict gets an injected '_line' key (1-indexed JSONL line number)
    for citation coord tracing.
    """
    thread_path = THREAD_DIR / f"{target_date}.jsonl"
    if not thread_path.exists():
        logger.info("No chat file for %s", target_date)
        return []

    messages = []
    corrupted = 0
    lines = secure_read_lines(thread_path)
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            obj["_line"] = line_num  # citation coord reference
            messages.append(obj)
        except json.JSONDecodeError:
            corrupted += 1

    if corrupted:
        logger.warning("Skipped %d corrupted lines in %s", corrupted, target_date)
    return messages


def _fmt_msg_with_coord(msg: dict[str, Any], target_date: str) -> str:
    """Format a message for the debrief prompt, including its citation coord."""
    sender = msg.get("sender", "unknown").upper()
    content = msg.get("content", "")
    line = msg.get("_line", 0)
    coord = f"{target_date}:L{line}"
    return f"[{sender}] (ref {coord})\n{content}\n\n"


def generate_debrief(target_date: str) -> str:
    """Generate a structured session debrief for a specific date.

    Output format (plain text, LLM-generated):
        SESSION DEBRIEF — {date}

        TOPICS COVERED
        • topic [ref YYYY-MM-DD:L##]

        COMPLETED
        • item [ref YYYY-MM-DD:L##]

        UNFINISHED
        • item — last state: description [ref YYYY-MM-DD:L##]

        STATUS: Clean | In-progress | Blocked

        NEXT MOVE: what to do next

    Saved to summaries/{date}.txt (replaces old prose summary).
    Returns debrief text (empty string on failure).
    """
    messages = _load_messages(target_date)
    if not messages:
        return ""

    logger.info("Loaded %d messages from %s for debrief", len(messages), target_date)

    # Build conversation text with coords for the LLM
    total_chars = 0
    # Keep first message as anchor, fill from end
    anchor = _fmt_msg_with_coord(messages[0], target_date)
    tail_parts: list[str] = []
    for msg in reversed(messages[1:]):
        part = _fmt_msg_with_coord(msg, target_date)
        if total_chars + len(part) > MAX_CONVO_CHARS:
            break
        tail_parts.append(part)
        total_chars += len(part)
    tail_parts.reverse()

    sep = "\n--- (earlier messages) ---\n\n"
    if len(anchor) + len(sep) + total_chars <= MAX_CONVO_CHARS:
        conversation_text = anchor + sep + "".join(tail_parts)
    elif tail_parts:
        conversation_text = "".join(tail_parts)
    else:
        conversation_text = anchor[-MAX_CONVO_CHARS:]

    system_instruction = (
        "You are a session debrief extractor. Read the transcript below and produce "
        "a structured debrief. Do NOT write prose. Do NOT answer questions from the "
        "transcript. Extract facts only.\n\n"
        "Output format (use exactly these headings):\n\n"
        f"SESSION DEBRIEF — {target_date}\n\n"
        "TOPICS COVERED\n"
        "• topic description [ref YYYY-MM-DD:L##]\n\n"
        "COMPLETED\n"
        "• what was finished [ref YYYY-MM-DD:L##]\n\n"
        "UNFINISHED\n"
        "• what is incomplete — last state: where it was left off [ref YYYY-MM-DD:L##]\n\n"
        "STATUS: one of Clean | In-progress | Blocked\n\n"
        "NEXT MOVE: single sentence, what to do next\n\n"
        "Rules:\n"
        "- Each bullet MUST include a [ref ...] citation coord from the transcript\n"
        "- Use the (ref YYYY-MM-DD:L##) markers from the transcript messages\n"
        "- Keep bullets short (one line each)\n"
        "- If nothing is unfinished, write UNFINISHED: None\n"
        "- Do not invent details not in the transcript"
    )

    prompt = (
        f"Extract a structured debrief from this session transcript ({target_date}):\n\n"
        f"{conversation_text}\n\n"
        "Debrief:"
    )

    debrief_text = _call_llm(system_instruction, prompt, max_tokens=600)
    if not debrief_text:
        logger.warning("Debrief LLM returned empty for %s", target_date)
        return ""

    # Ensure header is present (LLM may or may not include it)
    if not debrief_text.startswith("SESSION DEBRIEF"):
        debrief_text = f"SESSION DEBRIEF — {target_date}\n\n{debrief_text}"

    logger.info("Debrief generated for %s (%d chars)", target_date, len(debrief_text))

    # Save
    if not _save_summary(SUMMARY_DIR, f"{target_date}.txt", debrief_text):
        logger.warning("Failed to save debrief for %s", target_date)
        return ""

    logger.info("Debrief saved: %s/%s.txt", SUMMARY_DIR, target_date)
    return debrief_text


def summarize_day(target_date: str) -> str:
    """Generate debrief for a specific date (delegates to generate_debrief).

    Kept as the public API so rollup triggers and CLI still work.
    """
    return generate_debrief(target_date)


# ── Shared LLM Helper ─────────────────────────────────────────

def _call_llm(system_instruction: str, prompt: str, max_tokens: int = 300) -> str:
    """Call the local LLM and return response text. Empty string on failure."""
    try:
        payload = {
            "model": LLM_MODEL,
            "prompt": prompt,
            "system_prompt": system_instruction,
            "stream": False,
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
        response = httpx.post(LLM_ENDPOINT, json=payload, timeout=TIMEOUT)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except httpx.ConnectError:
        logger.warning("Summarizer: cannot connect to LLM at %s", LLM_ENDPOINT)
        return ""
    except httpx.TimeoutException:
        logger.warning("Summarizer: LLM timeout after %ds", TIMEOUT)
        return ""
    except Exception as e:
        logger.warning("Summarizer: LLM error: %s", e)
        return ""


def _save_summary(directory: Path, filename: str, text: str) -> bool:
    """Save summary text through gateway. Returns True on success."""
    directory.mkdir(parents=True, exist_ok=True)

    if _GOVERNED:
        # Build relative path from CHAT_SUMMARIES_DIR
        try:
            rel = (directory / filename).relative_to(SUMMARY_DIR)
            result = _gw.write("system", WriteZone.CHAT_SUMMARIES, str(rel), text)
            if not result.success:
                logger.warning("Summarizer: gateway write failed: %s", result.error)
                return False
            return True
        except Exception as e:
            logger.warning("Summarizer: gateway write error: %s", e)
            return False
    else:
        if not ALLOW_LEGACY_WRITES:
            logger.warning("Summarizer: legacy writes disabled")
            return False
        secure_write_text(directory / filename, text)
        return True


# ── Rollup: Weekly ────────────────────────────────────────────

def summarize_week(year: int, week: int) -> str:
    """Summarize a week by reading that week's daily summaries.

    Args:
        year: ISO year
        week: ISO week number (1-53)

    Returns:
        Weekly summary text (empty on failure)
    """
    filename = f"{year}-W{week:02d}.txt"
    output_path = WEEK_DIR / filename

    if output_path.exists():
        logger.info("Weekly summary already exists: %s", filename)
        return secure_read_text(output_path).strip()

    # Collect daily summaries for this ISO week
    daily_texts: List[str] = []
    # Monday of the given ISO week
    monday = date.fromisocalendar(year, week, 1)
    for i in range(7):
        day = monday + timedelta(days=i)
        day_file = SUMMARY_DIR / f"{day.isoformat()}.txt"
        if day_file.exists():
            try:
                text = secure_read_text(day_file).strip()
                if text:
                    daily_texts.append(f"[{day.isoformat()}]\n{text}")
            except Exception:
                pass

    if not daily_texts:
        logger.info("No daily summaries for week %s-W%02d", year, week)
        return ""

    combined = "\n\n---\n\n".join(daily_texts)

    system_instruction = (
        "You are a concise summarizer. Read the daily summaries below and write "
        "a 5-8 sentence weekly roundup. Focus on: key accomplishments, decisions "
        "made, problems solved, and what's next. Do not invent details."
    )
    prompt = (
        f"Weekly roundup for {year}-W{week:02d} "
        f"({monday.isoformat()} to {(monday + timedelta(days=6)).isoformat()}):\n\n"
        f"{combined}\n\n"
        "Weekly Summary:"
    )

    summary = _call_llm(system_instruction, prompt, max_tokens=500)
    if not summary:
        return ""

    _save_summary(WEEK_DIR, filename, summary)
    logger.info("Weekly summary saved: %s", filename)
    return summary


# ── Rollup: Monthly ──────────────────────────────────────────

def summarize_month(year: int, month: int) -> str:
    """Summarize a month by reading that month's daily summaries.

    Args:
        year: Calendar year
        month: Calendar month (1-12)

    Returns:
        Monthly summary text (empty on failure)
    """
    filename = f"{year}-{month:02d}.txt"
    output_path = MONTH_DIR / filename

    if output_path.exists():
        logger.info("Monthly summary already exists: %s", filename)
        return secure_read_text(output_path).strip()

    # Collect daily summaries for this month
    daily_texts: List[str] = []
    day = date(year, month, 1)
    while day.month == month:
        day_file = SUMMARY_DIR / f"{day.isoformat()}.txt"
        if day_file.exists():
            try:
                text = secure_read_text(day_file).strip()
                if text:
                    daily_texts.append(f"[{day.isoformat()}]\n{text}")
            except Exception:
                pass
        day += timedelta(days=1)

    if not daily_texts:
        logger.info("No daily summaries for %04d-%02d", year, month)
        return ""

    combined = "\n\n---\n\n".join(daily_texts)

    month_name = date(year, month, 1).strftime("%B %Y")
    system_instruction = (
        "You are a concise summarizer. Read the daily summaries below and write "
        "a 1-2 paragraph monthly report. Cover: major features built, architecture "
        "changes, recurring themes, and trajectory. Do not invent details."
    )
    prompt = (
        f"Monthly report for {month_name}:\n\n"
        f"{combined}\n\n"
        "Monthly Summary:"
    )

    summary = _call_llm(system_instruction, prompt, max_tokens=600)
    if not summary:
        return ""

    _save_summary(MONTH_DIR, filename, summary)
    logger.info("Monthly summary saved: %s", filename)
    return summary


# ── Rollup: Yearly ───────────────────────────────────────────

def summarize_year(year: int) -> str:
    """Summarize a year by reading that year's monthly summaries.

    Args:
        year: Calendar year

    Returns:
        Yearly summary text (empty on failure)
    """
    filename = f"{year}.txt"
    output_path = YEAR_DIR / filename

    if output_path.exists():
        logger.info("Yearly summary already exists: %s", filename)
        return secure_read_text(output_path).strip()

    # Collect monthly summaries for this year
    monthly_texts: List[str] = []
    for month in range(1, 13):
        month_file = MONTH_DIR / f"{year}-{month:02d}.txt"
        if month_file.exists():
            try:
                text = secure_read_text(month_file).strip()
                if text:
                    month_name = date(year, month, 1).strftime("%B")
                    monthly_texts.append(f"[{month_name}]\n{text}")
            except Exception:
                pass

    if not monthly_texts:
        logger.info("No monthly summaries for %d", year)
        return ""

    combined = "\n\n---\n\n".join(monthly_texts)

    system_instruction = (
        "You are a concise summarizer. Read the monthly summaries below and write "
        "a 2-3 paragraph annual review. Cover: the arc of the year, major milestones, "
        "how the system evolved, and where things stand. Do not invent details."
    )
    prompt = (
        f"Annual review for {year}:\n\n"
        f"{combined}\n\n"
        "Annual Summary:"
    )

    summary = _call_llm(system_instruction, prompt, max_tokens=800)
    if not summary:
        return ""

    _save_summary(YEAR_DIR, filename, summary)
    logger.info("Yearly summary saved: %s", filename)
    return summary


# ── Auto-Trigger Orchestrator ─────────────────────────────────

def check_and_run_rollups(today: Optional[date] = None) -> dict:
    """Check what summaries are due and run them.

    Called from daily_logger.py in a background thread on new-day detection.
    Non-fatal: logs warnings on failure, never raises.

    Returns:
        Dict of what was attempted and results.
    """
    if today is None:
        today = date.today()

    yesterday = today - timedelta(days=1)
    results = {}

    # Always: summarize yesterday
    try:
        day_summary = summarize_day(yesterday.isoformat())
        results["daily"] = {"date": yesterday.isoformat(), "ok": bool(day_summary)}
    except Exception as e:
        logger.warning("Auto-summary daily failed: %s", e)
        results["daily"] = {"date": yesterday.isoformat(), "ok": False, "error": str(e)}

    # L3: Extract lessons from yesterday's debrief (runs after summary exists)
    try:
        from .lessons import extract_lessons
        lessons = extract_lessons(yesterday.isoformat())
        results["lessons"] = {"date": yesterday.isoformat(), "ok": bool(lessons), "count": len(lessons)}
    except Exception as e:
        logger.warning("Auto-lessons extraction failed: %s", e)
        results["lessons"] = {"date": yesterday.isoformat(), "ok": False, "error": str(e)}

    # Sunday: summarize last week (the week that just ended on Saturday)
    if today.weekday() == 6:  # Sunday
        last_week = yesterday  # Saturday
        iso_year, iso_week, _ = last_week.isocalendar()
        try:
            week_summary = summarize_week(iso_year, iso_week)
            results["weekly"] = {"week": f"{iso_year}-W{iso_week:02d}", "ok": bool(week_summary)}
        except Exception as e:
            logger.warning("Auto-summary weekly failed: %s", e)
            results["weekly"] = {"week": f"{iso_year}-W{iso_week:02d}", "ok": False, "error": str(e)}

    # 1st of month: summarize previous month
    if today.day == 1:
        prev_month = yesterday  # Last day of previous month
        try:
            month_summary = summarize_month(prev_month.year, prev_month.month)
            results["monthly"] = {
                "month": f"{prev_month.year}-{prev_month.month:02d}",
                "ok": bool(month_summary),
            }
        except Exception as e:
            logger.warning("Auto-summary monthly failed: %s", e)
            results["monthly"] = {
                "month": f"{prev_month.year}-{prev_month.month:02d}",
                "ok": False, "error": str(e),
            }

    # Jan 1: summarize previous year
    if today.month == 1 and today.day == 1:
        prev_year = yesterday.year
        try:
            year_summary = summarize_year(prev_year)
            results["yearly"] = {"year": prev_year, "ok": bool(year_summary)}
        except Exception as e:
            logger.warning("Auto-summary yearly failed: %s", e)
            results["yearly"] = {"year": prev_year, "ok": False, "error": str(e)}

    logger.info("Auto-summary results: %s", results)
    return results


def get_latest_summary() -> Optional[tuple[str, str]]:
    """Find and load the most recent summary.
    
    Returns:
        Tuple of (date_string, summary_text) or None if no summaries exist
    """
    if not SUMMARY_DIR.exists():
        return None
    
    summary_files = sorted(SUMMARY_DIR.glob("*.txt"))
    
    if not summary_files:
        return None
    
    latest_file = summary_files[-1]
    date_str = latest_file.stem  # Filename without .txt
    
    try:
        summary_text = secure_read_text(latest_file).strip()
        return (date_str, summary_text)
    except Exception as e:
        print(f"⚠️  Could not read summary {latest_file}: {e}")
        return None


def summarize_yesterday() -> str:
    """Convenience function to summarize yesterday's chat.
    
    Returns:
        Summary text
    """
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    return summarize_day(yesterday)


if __name__ == "__main__":
    # Quick test
    import sys
    
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = (date.today() - timedelta(days=1)).isoformat()
    
    print(f"\n{'='*60}")
    print(f"  CHAT SUMMARIZER")
    print(f"{'='*60}\n")
    
    result = summarize_day(target)
    
    if result:
        print(f"\n{'='*60}")
        print("SUMMARY:")
        print(f"{'='*60}")
        print(result)
        print(f"{'='*60}\n")
    else:
        print("\n❌ Summary failed\n")
