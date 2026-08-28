from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .base import sha1_text, utc_now, with_protected_notice


def stage_codex_sessions(
    sessions_root: str | Path,
    output_path: str | Path,
    *,
    session_index_path: str | Path | None = None,
    max_files: int | None = None,
) -> dict[str, Any]:
    """Convert Codex session JSONL files into AWEAR chat-turn markdown."""
    root = Path(sessions_root).expanduser().resolve()
    output = Path(output_path).expanduser().resolve()
    index = read_codex_session_index(session_index_path)
    files = sorted(root.rglob("*.jsonl"), key=lambda item: str(item))
    if max_files is not None:
        files = files[:max(0, int(max_files))]
    output.parent.mkdir(parents=True, exist_ok=True)

    turn_count = 0
    session_count = 0
    speaker_counts: Counter[str] = Counter()
    earliest: str | None = None
    latest: str | None = None

    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for file_path in files:
            session_id = ""
            source = "codex"
            title = file_path.stem
            session_had_turns = False
            for raw_line in file_path.read_text(encoding="utf-8", errors="replace").splitlines():
                if not raw_line.strip():
                    continue
                try:
                    row = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue
                if row.get("type") == "session_meta":
                    payload = row.get("payload") or {}
                    session_id = str(payload.get("id") or session_id or file_path.stem)
                    source = str(payload.get("source") or payload.get("originator") or source)
                    title = index.get(session_id, title)
                    continue
                speaker, text = codex_message_from_row(row)
                if not speaker or not text.strip():
                    continue
                turn_count += 1
                session_had_turns = True
                created_at = str(row.get("timestamp") or "")
                if created_at:
                    earliest = created_at if earliest is None else min(earliest, created_at)
                    latest = created_at if latest is None else max(latest, created_at)
                speaker_counts[speaker] += 1
                message_id = sha1_text(f"{file_path}:{turn_count}:{created_at}:{speaker}")[:16]
                handle.write(f"## CHAT_TURN_{turn_count}\n")
                handle.write(f"CHAT_SOURCE_EXPORT: codex_sessions\n")
                handle.write(f"CHAT_SOURCE_SCOPE: {source}\n")
                handle.write(f"CHAT_CONVERSATION_ID: {session_id or file_path.stem}\n")
                handle.write(f"CHAT_MESSAGE_ID: {message_id}\n")
                handle.write(f"CHAT_TITLE: {title}\n")
                handle.write(f"CHAT_CREATED_AT: {created_at}\n")
                handle.write(f"CHAT_SPEAKER: {speaker}\n")
                handle.write("CHAT_TRUTH_SCOPE: system_doctrine_not_world_truth\n")
                handle.write("CHAT_LIFETIME_ALLOWED: false\n")
                handle.write("CHAT_TEXT:\n")
                handle.write(text.strip() + "\n\n")
            if session_had_turns:
                session_count += 1

    return with_protected_notice({
        "schema": "awrag_codex_session_stage_receipt@1",
        "created_at": utc_now(),
        "sessions_root": str(root),
        "output_path": str(output),
        "source_file_count": len(files),
        "session_count": session_count,
        "turn_count": turn_count,
        "speaker_counts": dict(sorted(speaker_counts.items())),
        "earliest_timestamp": earliest,
        "latest_timestamp": latest,
        "scope": "staged_dataset_source",
        "lifetime_allowed": False,
    })


def stage_codex_markdown_export(
    input_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    """Convert a visible Codex Markdown chat export into AWEAR chat-turn markdown."""
    source_path = Path(input_path).expanduser().resolve()
    output = Path(output_path).expanduser().resolve()
    text = source_path.read_text(encoding="utf-8", errors="replace")
    metadata = _codex_markdown_metadata(text)
    title = _codex_markdown_title(text) or source_path.stem
    session_id = str(metadata.get("session_id") or source_path.stem)
    source = str(metadata.get("originator") or "codex_markdown_export")

    output.parent.mkdir(parents=True, exist_ok=True)
    turn_count = 0
    speaker_counts: Counter[str] = Counter()
    earliest: str | None = None
    latest: str | None = None

    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for turn in _iter_codex_markdown_turns(text):
            speaker = turn["speaker"]
            body = str(turn["text"]).strip()
            if not body:
                continue
            turn_count += 1
            created_at = str(turn.get("timestamp") or "")
            if created_at:
                earliest = created_at if earliest is None else min(earliest, created_at)
                latest = created_at if latest is None else max(latest, created_at)
            speaker_counts[speaker] += 1
            message_id = sha1_text(f"{source_path}:{turn_count}:{created_at}:{speaker}")[:16]
            handle.write(f"## CHAT_TURN_{turn_count}\n")
            handle.write("CHAT_SOURCE_EXPORT: codex_markdown_export\n")
            handle.write(f"CHAT_SOURCE_SCOPE: {source}\n")
            handle.write(f"CHAT_CONVERSATION_ID: {session_id}\n")
            handle.write(f"CHAT_MESSAGE_ID: {message_id}\n")
            handle.write(f"CHAT_TITLE: {title}\n")
            handle.write(f"CHAT_CREATED_AT: {created_at}\n")
            handle.write(f"CHAT_SPEAKER: {speaker}\n")
            handle.write("CHAT_TRUTH_SCOPE: system_doctrine_not_world_truth\n")
            handle.write("CHAT_LIFETIME_ALLOWED: false\n")
            handle.write("CHAT_TEXT:\n")
            handle.write(body + "\n\n")

    return with_protected_notice({
        "schema": "awrag_codex_markdown_stage_receipt@1",
        "created_at": utc_now(),
        "input_path": str(source_path),
        "output_path": str(output),
        "turn_count": turn_count,
        "speaker_counts": dict(sorted(speaker_counts.items())),
        "earliest_timestamp": earliest,
        "latest_timestamp": latest,
        "source_session_id": session_id,
        "source_scope": source,
        "scope": "staged_dataset_source",
        "lifetime_allowed": False,
    })


def stage_chatgpt_export(
    export_root: str | Path,
    output_path: str | Path,
    *,
    max_conversations: int | None = None,
) -> dict[str, Any]:
    """Convert ChatGPT data-export conversations JSON into AWEAR chat-turn markdown."""
    root = Path(export_root).expanduser().resolve()
    output = Path(output_path).expanduser().resolve()
    files = sorted(root.glob("conversations-*.json"), key=lambda item: str(item))
    output.parent.mkdir(parents=True, exist_ok=True)

    turn_count = 0
    conversation_count = 0
    source_file_count = 0
    speaker_counts: Counter[str] = Counter()
    model_counts: Counter[str] = Counter()
    earliest: str | None = None
    latest: str | None = None
    limit = max(0, int(max_conversations)) if max_conversations is not None else None

    with output.open("w", encoding="utf-8", newline="\n") as handle:
        for file_path in files:
            if limit is not None and conversation_count >= limit:
                break
            source_file_count += 1
            conversations = _read_chatgpt_conversation_file(file_path)
            for conversation in conversations:
                if limit is not None and conversation_count >= limit:
                    break
                turns = _chatgpt_conversation_turns(conversation)
                if not turns:
                    continue
                conversation_count += 1
                conversation_id = str(conversation.get("conversation_id") or conversation.get("id") or file_path.stem)
                title = str(conversation.get("title") or conversation.get("conversation_template_id") or conversation_id)
                default_model = str(conversation.get("default_model_slug") or "")
                if default_model:
                    model_counts[default_model] += 1

                for turn in turns:
                    turn_count += 1
                    speaker = turn["speaker"]
                    created_at = turn["created_at"]
                    model = turn["model_slug"] or default_model
                    if model:
                        model_counts[model] += 1
                    if created_at:
                        earliest = created_at if earliest is None else min(earliest, created_at)
                        latest = created_at if latest is None else max(latest, created_at)
                    speaker_counts[speaker] += 1
                    message_id = str(turn["message_id"]) or sha1_text(f"{conversation_id}:{turn_count}:{created_at}:{speaker}")[:16]
                    handle.write(f"## CHAT_TURN_{turn_count}\n")
                    handle.write("CHAT_SOURCE_EXPORT: chatgpt_data_export\n")
                    handle.write("CHAT_SOURCE_SCOPE: chatgpt_conversations\n")
                    handle.write(f"CHAT_CONVERSATION_ID: {conversation_id}\n")
                    handle.write(f"CHAT_MESSAGE_ID: {message_id}\n")
                    handle.write(f"CHAT_TITLE: {_one_line(title)}\n")
                    handle.write(f"CHAT_CREATED_AT: {created_at}\n")
                    handle.write(f"CHAT_SPEAKER: {speaker}\n")
                    if model:
                        handle.write(f"CHAT_MODEL: {_one_line(model)}\n")
                    handle.write("CHAT_TRUTH_SCOPE: system_doctrine_not_world_truth\n")
                    handle.write("CHAT_LIFETIME_ALLOWED: false\n")
                    handle.write("CHAT_TEXT:\n")
                    handle.write(turn["text"].strip() + "\n\n")

    return with_protected_notice({
        "schema": "awrag_chatgpt_export_stage_receipt@1",
        "created_at": utc_now(),
        "export_root": str(root),
        "output_path": str(output),
        "source_file_count": source_file_count,
        "conversation_count": conversation_count,
        "turn_count": turn_count,
        "speaker_counts": dict(sorted(speaker_counts.items())),
        "model_counts": dict(sorted(model_counts.items())),
        "earliest_timestamp": earliest,
        "latest_timestamp": latest,
        "scope": "staged_dataset_source",
        "lifetime_allowed": False,
    })

def read_codex_session_index(session_index_path: str | Path | None) -> dict[str, str]:
    if not session_index_path:
        return {}
    path = Path(session_index_path).expanduser()
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        session_id = str(row.get("id") or "")
        title = str(row.get("thread_name") or "")
        if session_id and title:
            out[session_id] = title
    return out


def _read_chatgpt_conversation_file(file_path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(file_path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        conversations = data.get("conversations")
        if isinstance(conversations, list):
            return [row for row in conversations if isinstance(row, dict)]
    return []


def _chatgpt_conversation_turns(conversation: dict[str, Any]) -> list[dict[str, str]]:
    mapping = conversation.get("mapping")
    if not isinstance(mapping, dict):
        return []
    rows: list[dict[str, str]] = []
    for node_id, node in mapping.items():
        if not isinstance(node, dict):
            continue
        message = node.get("message")
        if not isinstance(message, dict):
            continue
        author = message.get("author") if isinstance(message.get("author"), dict) else {}
        speaker = str(author.get("role") or "").casefold()
        if speaker not in {"user", "assistant"}:
            continue
        text = _chatgpt_message_text(message)
        if not text.strip():
            continue
        created_at = _chatgpt_timestamp(message.get("create_time"))
        metadata = message.get("metadata") if isinstance(message.get("metadata"), dict) else {}
        model = str(metadata.get("model_slug") or "")
        message_id = str(message.get("id") or node.get("id") or node_id)
        rows.append({
            "speaker": speaker,
            "text": text.strip(),
            "created_at": created_at,
            "model_slug": model,
            "message_id": message_id,
        })
    return sorted(rows, key=lambda row: (row["created_at"], row["message_id"]))


def _chatgpt_message_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if not isinstance(content, dict):
        return ""
    content_type = str(content.get("content_type") or "")
    if content_type == "thoughts":
        return ""
    parts = content.get("parts")
    if isinstance(parts, list):
        texts = [_chatgpt_part_text(part) for part in parts]
        return "\n".join(text for text in texts if text)
    text = content.get("text")
    if text is not None:
        return str(text)
    return ""


def _chatgpt_part_text(part: Any) -> str:
    if isinstance(part, str):
        return part
    if isinstance(part, dict):
        for key in ("text", "value", "content"):
            value = part.get(key)
            if value is not None:
                return str(value)
    return ""


def _chatgpt_timestamp(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, (int, float)):
        from datetime import datetime, timezone

        return datetime.fromtimestamp(float(value), tz=timezone.utc).isoformat().replace("+00:00", "Z")
    return str(value)


def _one_line(value: str) -> str:
    return " ".join(str(value).split())

def codex_message_from_row(row: dict[str, Any]) -> tuple[str | None, str]:
    payload = row.get("payload") or {}
    if row.get("type") != "response_item" or payload.get("type") != "message":
        return None, ""
    role = str(payload.get("role") or "").casefold()
    if role not in {"user", "assistant"}:
        return None, ""
    parts = payload.get("content") or []
    texts: list[str] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        value = part.get("text")
        if value is None:
            value = part.get("value")
        if value is not None:
            texts.append(str(value))
    return role, "\n".join(texts).strip()


def _codex_markdown_title(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip() or None
    return None


def _codex_markdown_metadata(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    aliases = {
        "session id": "session_id",
        "originator": "originator",
        "session started utc": "session_started_utc",
        "source jsonl last write": "source_jsonl_last_write",
        "exported local time": "exported_local_time",
        "source path": "source_path",
    }
    in_metadata = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line == "## Source Metadata":
            in_metadata = True
            continue
        if in_metadata and line.startswith("## "):
            break
        if not in_metadata or not line.startswith("- ") or ":" not in line:
            continue
        key, value = line[2:].split(":", 1)
        normalized_key = aliases.get(key.strip().casefold())
        if not normalized_key:
            continue
        out[normalized_key] = value.strip().strip("`")
    return out


def _iter_codex_markdown_turns(text: str) -> list[dict[str, str]]:
    import re

    header_re = re.compile(r"^###\s+([0-9]+)\.\s+(User|Assistant)\s*$", flags=re.MULTILINE)
    matches = list(header_re.finditer(text))
    turns: list[dict[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        segment = text[start:end]
        timestamp = ""
        body_lines = segment.splitlines()
        content_start = 0
        for line_index, raw_line in enumerate(body_lines):
            line = raw_line.strip()
            if line.startswith("Timestamp:"):
                timestamp = line.split(":", 1)[1].strip().strip("`")
                content_start = line_index + 1
                break
        while content_start < len(body_lines) and not body_lines[content_start].strip():
            content_start += 1
        content_lines = body_lines[content_start:]
        while content_lines and not content_lines[-1].strip():
            content_lines.pop()
        if content_lines and content_lines[-1].strip() == "---":
            content_lines.pop()
        while content_lines and not content_lines[-1].strip():
            content_lines.pop()
        turns.append({
            "turn_number": match.group(1),
            "speaker": match.group(2).casefold(),
            "timestamp": timestamp,
            "text": "\n".join(content_lines).strip(),
        })
    return turns

