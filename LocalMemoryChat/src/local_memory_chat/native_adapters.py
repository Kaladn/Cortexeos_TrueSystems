from __future__ import annotations

import hashlib
import json
import mimetypes
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return repr(value)


@dataclass(frozen=True)
class NativeArtifact:
    native_id: str
    parent_native_id: str
    ordinal: int
    relationship: str
    media_type: str | None
    source_locator: str
    source_hash: str | None = None
    byte_size: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NativeObject:
    native_id: str
    parent_native_id: str | None
    object_type: str
    ordinal: int
    role: str | None = None
    timestamp: str | None = None
    text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdaptedChat:
    source_path: Path
    source_type: str
    source_hash: str
    size_bytes: int
    source_label: str
    conversation_native_id: str
    objects: tuple[NativeObject, ...]
    artifacts: tuple[NativeArtifact, ...] = ()


def adapt_native_chat(
    source_path: str | Path,
    *,
    source_type: str,
    conversation_id: str | None = None,
) -> AdaptedChat:
    path = Path(source_path).expanduser().resolve()
    if source_type == "codex":
        return adapt_codex(path)
    if source_type == "openai-export":
        return adapt_openai_export(path, conversation_id=conversation_id)
    if source_type == "lm-studio":
        if conversation_id is not None:
            raise ValueError("LM Studio files contain one conversation; omit conversation_id")
        return adapt_lm_studio(path)
    raise ValueError(f"unsupported source_type: {source_type}")


def adapt_codex(path: Path) -> AdaptedChat:
    raw = path.read_bytes()
    rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
    meta = next((row.get("payload", {}) for row in rows if row.get("type") == "session_meta"), {})
    conversation_id = str(meta.get("session_id") or meta.get("id") or path.stem)
    objects: list[NativeObject] = [NativeObject(
        native_id=conversation_id,
        parent_native_id=None,
        object_type="conversation",
        ordinal=0,
        timestamp=_time(meta.get("timestamp")),
        metadata={"native_record_type": "session_meta", "cli_version": meta.get("cli_version")},
    )]
    artifacts: list[NativeArtifact] = []
    current_turn: str | None = None
    turn_ordinal = 0
    object_ordinal = 0
    for row_index, row in enumerate(rows, start=1):
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        record_type = str(row.get("type") or "")
        payload_type = str(payload.get("type") or "")
        timestamp = _time(row.get("timestamp") or payload.get("timestamp"))
        turn_hint = payload.get("turn_id")
        if payload_type == "task_started" or (record_type == "turn_context" and turn_hint):
            hinted = str(turn_hint or f"turn-{turn_ordinal + 1}")
            if hinted != current_turn:
                turn_ordinal += 1
                current_turn = hinted
                objects.append(NativeObject(
                    native_id=current_turn,
                    parent_native_id=conversation_id,
                    object_type="turn",
                    ordinal=turn_ordinal,
                    timestamp=timestamp,
                    metadata={"native_record_type": record_type, "native_payload_type": payload_type},
                ))
        if record_type != "response_item":
            continue
        object_type = {
            "message": "message",
            "function_call": "tool_call",
            "custom_tool_call": "tool_call",
            "function_call_output": "tool_result",
            "custom_tool_call_output": "tool_result",
        }.get(payload_type)
        if payload_type == "reasoning":
            native_id = str(payload.get("id") or f"reasoning-{row_index}")
            artifacts.append(NativeArtifact(
                native_id=native_id,
                parent_native_id=current_turn or conversation_id,
                ordinal=len(artifacts),
                relationship="raw_reasoning_record",
                media_type="application/json",
                source_locator=f"jsonl-line:{row_index}",
                source_hash=_sha(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")),
                byte_size=len(json.dumps(payload, ensure_ascii=False).encode("utf-8")),
                metadata={"raw_status": "RAW_UNINTERPRETED"},
            ))
            continue
        if object_type is None:
            continue
        if current_turn is None:
            turn_ordinal += 1
            current_turn = f"implicit-turn-{turn_ordinal}"
            objects.append(NativeObject(current_turn, conversation_id, "turn", turn_ordinal, timestamp=timestamp))
        object_ordinal += 1
        native_id = str(payload.get("id") or payload.get("call_id") or f"row-{row_index}")
        text = _codex_text(payload, object_type)
        metadata = {
            "native_record_type": record_type,
            "native_payload_type": payload_type,
            "call_id": payload.get("call_id"),
            "name": payload.get("name"),
            "status": payload.get("status"),
            "row": row_index,
        }
        objects.append(NativeObject(
            native_id=native_id,
            parent_native_id=current_turn,
            object_type=object_type,
            ordinal=object_ordinal,
            role=str(payload.get("role")) if payload.get("role") else None,
            timestamp=timestamp,
            text=text,
            metadata=metadata,
        ))
        if object_type == "message":
            for attachment_ordinal, attachment_path in enumerate(_codex_attachment_paths(text)):
                attachment_bytes = attachment_path.read_bytes() if attachment_path.is_file() else None
                artifacts.append(NativeArtifact(
                    native_id=str(attachment_path),
                    parent_native_id=native_id,
                    ordinal=attachment_ordinal,
                    relationship="codex_attachment",
                    media_type=mimetypes.guess_type(attachment_path.name)[0],
                    source_locator=f"path:{attachment_path}",
                    source_hash=_sha(attachment_bytes) if attachment_bytes is not None else None,
                    byte_size=len(attachment_bytes) if attachment_bytes is not None else None,
                    metadata={"raw_status": "RAW_UNINTERPRETED", "path_exists": attachment_bytes is not None},
                ))
        for part_index, part in enumerate(payload.get("content") or []):
            if not isinstance(part, dict) or part.get("type") in {"input_text", "output_text", "text"}:
                continue
            artifacts.append(_part_artifact(part, native_id, part_index, f"jsonl-line:{row_index}"))
    return AdaptedChat(path, "codex", _sha(raw), len(raw), path.name, conversation_id, tuple(objects), tuple(artifacts))


def adapt_openai_export(path: Path, *, conversation_id: str | None) -> AdaptedChat:
    raw = path.read_bytes()
    with zipfile.ZipFile(path) as archive:
        conversations = json.loads(archive.read("conversations.json"))
        if conversation_id is None:
            if len(conversations) != 1:
                raise ValueError("conversation_id is required when an OpenAI export contains multiple conversations")
            conversation = conversations[0]
        else:
            conversation = next((item for item in conversations if str(item.get("id") or item.get("conversation_id")) == conversation_id), None)
            if conversation is None:
                raise ValueError(f"conversation not found in export: {conversation_id}")
        members = {item.filename: item for item in archive.infolist()}
        member_names = set(members)
        conversation_native_id = str(conversation.get("id") or conversation.get("conversation_id"))
        objects: list[NativeObject] = [NativeObject(
            conversation_native_id, None, "conversation", 0,
            timestamp=_time(conversation.get("create_time")),
            metadata={"title": conversation.get("title"), "current_node": conversation.get("current_node")},
        )]
        artifacts: list[NativeArtifact] = []
        mapping = conversation.get("mapping") or {}
        ordered = sorted(mapping.values(), key=lambda node: (
            _number(((node.get("message") or {}).get("create_time"))), str(node.get("id") or "")
        ))
        turn_for_node: dict[str, str] = {}
        turn_ordinal = 0
        message_ordinal = 0
        for node in ordered:
            message = node.get("message")
            if not isinstance(message, dict):
                continue
            node_id = str(node.get("id") or message.get("id"))
            parent_node = str(node.get("parent") or "")
            role = str((message.get("author") or {}).get("role") or "") or None
            if role == "user" or not turn_for_node.get(parent_node):
                turn_ordinal += 1
                turn_id = f"turn:{node_id}"
                objects.append(NativeObject(turn_id, conversation_native_id, "turn", turn_ordinal, timestamp=_time(message.get("create_time")), metadata={"root_node": node_id}))
            else:
                turn_id = turn_for_node[parent_node]
            turn_for_node[node_id] = turn_id
            message_ordinal += 1
            content = message.get("content") if isinstance(message.get("content"), dict) else {}
            content_type = str(content.get("content_type") or "text")
            object_type = "message"
            if role == "tool" or content_type == "execution_output":
                object_type = "tool_result"
            text, part_artifacts = _openai_content(content, node_id, member_names, members, archive)
            objects.append(NativeObject(
                node_id, turn_id, object_type, message_ordinal, role,
                _time(message.get("create_time")), text,
                {"native_parent_node": node.get("parent"), "children": node.get("children") or [], "content_type": content_type, "message_id": message.get("id")},
            ))
            artifacts.extend(part_artifacts)
    return AdaptedChat(path, "openai-export", _sha(raw), len(raw), str(conversation.get("title") or path.name), conversation_native_id, tuple(objects), tuple(artifacts))


def adapt_lm_studio(path: Path) -> AdaptedChat:
    raw = path.read_bytes()
    data = json.loads(raw)
    conversation_id = str(data.get("conversationId") or path.name.split(".", 1)[0])
    objects: list[NativeObject] = [NativeObject(
        conversation_id, None, "conversation", 0,
        timestamp=_time_ms(data.get("createdAt")),
        metadata={"name": data.get("name"), "last_used_model": data.get("lastUsedModel")},
    )]
    artifacts: list[NativeArtifact] = []
    turn_ordinal = 0
    current_turn: str | None = None
    ordinal = 0
    for message_index, slot in enumerate(data.get("messages") or []):
        versions = slot.get("versions") or []
        selected_index = int(slot.get("currentlySelected") or 0)
        for version_index, version in enumerate(versions):
            role = str(version.get("role") or "") or None
            native_id = f"message:{message_index}:version:{version_index}"
            if version_index == selected_index:
                if role == "user" or current_turn is None:
                    turn_ordinal += 1
                    current_turn = f"turn:{message_index}"
                    objects.append(NativeObject(current_turn, conversation_id, "turn", turn_ordinal, timestamp=None, metadata={"message_index": message_index}))
                parent = current_turn
                object_type = "message"
            else:
                parent = f"message:{message_index}:version:{selected_index}"
                object_type = "message_variant"
            ordinal += 1
            text, found_artifacts = _lm_version(version, native_id, message_index)
            objects.append(NativeObject(
                native_id, parent, object_type, ordinal, role, None, text,
                {"message_index": message_index, "version_index": version_index, "selected": version_index == selected_index, "version_type": version.get("type")},
            ))
            artifacts.extend(found_artifacts)
    return AdaptedChat(path, "lm-studio", _sha(raw), len(raw), str(data.get("name") or path.name), conversation_id, tuple(objects), tuple(artifacts))



def _codex_attachment_paths(text: str) -> list[Path]:
    paths: list[Path] = []
    seen: set[str] = set()
    pattern = re.compile(r"/home/lamercey/\.codex/attachments/[^\s`\"<>]+")
    for match in pattern.finditer(text):
        value = match.group(0).rstrip(".,;:)]}")
        if value not in seen:
            seen.add(value)
            paths.append(Path(value))
    return paths


def _codex_text(payload: dict[str, Any], object_type: str) -> str:
    if object_type == "message":
        return "\n".join(str(part.get("text") or "") for part in payload.get("content") or [] if isinstance(part, dict) and part.get("type") in {"input_text", "output_text", "text"}).strip()
    value = payload.get("arguments") if object_type == "tool_call" else payload.get("output")
    if isinstance(value, str):
        return value
    return json.dumps(_json_safe(value), ensure_ascii=False, sort_keys=True) if value is not None else ""


def _openai_content(content: dict[str, Any], parent: str, member_names: set[str], members: dict[str, zipfile.ZipInfo], archive: zipfile.ZipFile) -> tuple[str, list[NativeArtifact]]:
    texts: list[str] = []
    artifacts: list[NativeArtifact] = []
    if isinstance(content.get("text"), str):
        texts.append(content["text"])
    for index, part in enumerate(content.get("parts") or []):
        if isinstance(part, str):
            texts.append(part)
            continue
        if not isinstance(part, dict):
            continue
        part_type = str(part.get("content_type") or part.get("type") or "artifact")
        if part_type in {"text", "input_text", "output_text"} and isinstance(part.get("text"), str):
            texts.append(part["text"])
            continue
        locator = str(part.get("asset_pointer") or part.get("file_id") or part.get("image_url") or f"embedded-part:{index}")
        member = _match_member(locator, member_names)
        info = members.get(member) if member else None
        artifacts.append(NativeArtifact(
            native_id=str(part.get("file_id") or part.get("asset_pointer") or f"{parent}:part:{index}"),
            parent_native_id=parent,
            ordinal=index,
            relationship=part_type,
            media_type=(mimetypes.guess_type(member)[0] if member else None),
            source_locator=(f"zip-member:{member}" if member else locator),
            source_hash=(_sha(archive.read(member)) if member else None),
            byte_size=(info.file_size if info else None),
            metadata={"raw_status": "RAW_UNINTERPRETED", "native_part": part},
        ))
    return "\n".join(value for value in texts if value).strip(), artifacts


def _lm_version(version: dict[str, Any], parent: str, message_index: int) -> tuple[str, list[NativeArtifact]]:
    texts: list[str] = []
    artifacts: list[NativeArtifact] = []
    items = list(version.get("content") or [])
    for step in version.get("steps") or []:
        if step.get("type") == "contentBlock":
            items.extend(step.get("content") or [])
        elif step.get("type") in {"debugInfoBlock", "citationBlock"}:
            raw = json.dumps(step, ensure_ascii=False, sort_keys=True).encode("utf-8")
            artifacts.append(NativeArtifact(
                str(step.get("stepIdentifier") or f"{parent}:step:{len(artifacts)}"), parent, len(artifacts),
                "raw_lm_studio_step", "application/json", f"message:{message_index}", _sha(raw), len(raw),
                {"raw_status": "RAW_UNINTERPRETED", "step_type": step.get("type")},
            ))
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            continue
        if item.get("type") == "text":
            texts.append(str(item.get("text") or ""))
        elif item.get("type") == "file":
            artifacts.append(NativeArtifact(
                str(item.get("fileIdentifier") or f"{parent}:file:{index}"), parent, index, "file",
                str(item.get("fileType") or "application/octet-stream"), str(item.get("fileIdentifier") or ""),
                byte_size=int(item.get("sizeBytes")) if item.get("sizeBytes") is not None else None,
                metadata={"raw_status": "RAW_UNINTERPRETED"},
            ))
    return "\n".join(value for value in texts if value).strip(), artifacts


def _part_artifact(part: dict[str, Any], parent: str, ordinal: int, locator: str) -> NativeArtifact:
    raw = json.dumps(part, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return NativeArtifact(
        str(part.get("id") or part.get("file_id") or f"{parent}:part:{ordinal}"), parent, ordinal,
        str(part.get("type") or "artifact"), str(part.get("mime_type") or "application/json"), locator,
        _sha(raw), len(raw), {"raw_status": "RAW_UNINTERPRETED", "native_part": part},
    )


def _match_member(locator: str, names: set[str]) -> str | None:
    value = locator.removeprefix("file-service://").removeprefix("sediment://")
    for name in names:
        if value == name or value in name or name in value:
            return name
    return None


def _time(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        from datetime import datetime, timezone
        return datetime.fromtimestamp(float(value), timezone.utc).isoformat().replace("+00:00", "Z")
    return str(value)


def _time_ms(value: Any) -> str | None:
    return _time(float(value) / 1000.0) if value is not None else None


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("inf")
