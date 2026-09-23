from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .native_adapters import AdaptedChat, adapt_native_chat

WORD_RE = re.compile(r"[^\W_][\w'’-]*|[^\s\w]", re.UNICODE)
STOP = {
    "a", "an", "and", "are", "as", "at", "be", "by", "did", "do", "for",
    "from", "in", "is", "it", "of", "on", "or", "that", "the", "to", "we",
    "what", "with",
}

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS sources(
 source_id TEXT PRIMARY KEY, source_path TEXT NOT NULL, source_type TEXT NOT NULL,
 source_hash TEXT NOT NULL, size_bytes INTEGER NOT NULL, source_label TEXT NOT NULL,
 admitted_at TEXT NOT NULL, status TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS objects(
 object_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, parent_id TEXT,
 object_type TEXT NOT NULL, ordinal INTEGER NOT NULL, role TEXT, speaker TEXT,
 timestamp TEXT, line_start INTEGER NOT NULL, line_end INTEGER NOT NULL,
 char_start INTEGER NOT NULL, char_end INTEGER NOT NULL,
 byte_start INTEGER NOT NULL, byte_end INTEGER NOT NULL,
 exact_text_hash TEXT NOT NULL, text TEXT NOT NULL, metadata_json TEXT NOT NULL,
 UNIQUE(source_id, object_id));
CREATE TABLE IF NOT EXISTS object_edges(
 parent_id TEXT NOT NULL, child_id TEXT NOT NULL, edge_type TEXT NOT NULL,
 ordinal INTEGER NOT NULL, PRIMARY KEY(parent_id, child_id, edge_type));
CREATE TABLE IF NOT EXISTS anchors(
 anchor_id INTEGER PRIMARY KEY AUTOINCREMENT, surface TEXT NOT NULL UNIQUE,
 kind TEXT NOT NULL, symbol TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS occurrences(
 occurrence_id TEXT PRIMARY KEY, object_id TEXT NOT NULL, anchor_id INTEGER NOT NULL,
 ordinal INTEGER NOT NULL, char_start INTEGER NOT NULL, char_end INTEGER NOT NULL,
 byte_start INTEGER NOT NULL, byte_end INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS relations(
 relation_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, object_id TEXT NOT NULL,
 center_anchor_id INTEGER NOT NULL, neighbor_anchor_id INTEGER NOT NULL,
 dimension TEXT NOT NULL, signed_distance INTEGER NOT NULL, count INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS occurrences_anchor ON occurrences(anchor_id);
CREATE INDEX IF NOT EXISTS objects_source ON objects(source_id);
CREATE TABLE IF NOT EXISTS source_occurrences(
 occurrence_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, source_path TEXT NOT NULL,
 observed_hash TEXT NOT NULL, observed_at TEXT NOT NULL,
 UNIQUE(source_id, source_path, observed_hash));
CREATE TABLE IF NOT EXISTS artifacts(
 artifact_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, parent_id TEXT NOT NULL,
 ordinal INTEGER NOT NULL, relationship TEXT NOT NULL, media_type TEXT,
 source_locator TEXT NOT NULL, source_hash TEXT, byte_size INTEGER,
 raw_status TEXT NOT NULL, metadata_json TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS immutable_source_update
BEFORE UPDATE ON sources WHEN OLD.status='historical_immutable'
BEGIN SELECT RAISE(ABORT, 'historical source is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_source_delete
BEFORE DELETE ON sources WHEN OLD.status='historical_immutable'
BEGIN SELECT RAISE(ABORT, 'historical source is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_object_insert
BEFORE INSERT ON objects WHEN EXISTS(
 SELECT 1 FROM sources WHERE source_id=NEW.source_id AND status='historical_immutable')
BEGIN SELECT RAISE(ABORT, 'historical object is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_object_update
BEFORE UPDATE ON objects WHEN EXISTS(
 SELECT 1 FROM sources WHERE source_id=OLD.source_id AND status='historical_immutable')
BEGIN SELECT RAISE(ABORT, 'historical object is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_object_delete
BEFORE DELETE ON objects WHEN EXISTS(
 SELECT 1 FROM sources WHERE source_id=OLD.source_id AND status='historical_immutable')
BEGIN SELECT RAISE(ABORT, 'historical object is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_artifact_insert
BEFORE INSERT ON artifacts WHEN EXISTS(
 SELECT 1 FROM sources WHERE source_id=NEW.source_id AND status='historical_immutable')
BEGIN SELECT RAISE(ABORT, 'historical artifact is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_artifact_update
BEFORE UPDATE ON artifacts WHEN EXISTS(
 SELECT 1 FROM sources WHERE source_id=OLD.source_id AND status='historical_immutable')
BEGIN SELECT RAISE(ABORT, 'historical artifact is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_artifact_delete
BEFORE DELETE ON artifacts WHEN EXISTS(
 SELECT 1 FROM sources WHERE source_id=OLD.source_id AND status='historical_immutable')
BEGIN SELECT RAISE(ABORT, 'historical artifact is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_edge_insert
BEFORE INSERT ON object_edges WHEN EXISTS(
 SELECT 1 FROM objects o JOIN sources s ON s.source_id=o.source_id
 WHERE o.object_id=NEW.parent_id AND s.status='historical_immutable')
BEGIN SELECT RAISE(ABORT, 'historical edge is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_edge_update
BEFORE UPDATE ON object_edges WHEN EXISTS(
 SELECT 1 FROM objects o JOIN sources s ON s.source_id=o.source_id
 WHERE o.object_id=OLD.parent_id AND s.status='historical_immutable')
BEGIN SELECT RAISE(ABORT, 'historical edge is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_edge_delete
BEFORE DELETE ON object_edges WHEN EXISTS(
 SELECT 1 FROM objects o JOIN sources s ON s.source_id=o.source_id
 WHERE o.object_id=OLD.parent_id AND s.status='historical_immutable')
BEGIN SELECT RAISE(ABORT, 'historical edge is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_occurrence_insert
BEFORE INSERT ON occurrences WHEN EXISTS(
 SELECT 1 FROM objects o JOIN sources s ON s.source_id=o.source_id
 WHERE o.object_id=NEW.object_id AND s.status='historical_immutable')
BEGIN SELECT RAISE(ABORT, 'historical occurrence is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_occurrence_update
BEFORE UPDATE ON occurrences WHEN EXISTS(
 SELECT 1 FROM objects o JOIN sources s ON s.source_id=o.source_id
 WHERE o.object_id=OLD.object_id AND s.status='historical_immutable')
BEGIN SELECT RAISE(ABORT, 'historical occurrence is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_occurrence_delete
BEFORE DELETE ON occurrences WHEN EXISTS(
 SELECT 1 FROM objects o JOIN sources s ON s.source_id=o.source_id
 WHERE o.object_id=OLD.object_id AND s.status='historical_immutable')
BEGIN SELECT RAISE(ABORT, 'historical occurrence is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_relation_insert
BEFORE INSERT ON relations WHEN EXISTS(
 SELECT 1 FROM sources WHERE source_id=NEW.source_id AND status='historical_immutable')
BEGIN SELECT RAISE(ABORT, 'historical relation is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_relation_update
BEFORE UPDATE ON relations WHEN EXISTS(
 SELECT 1 FROM sources WHERE source_id=OLD.source_id AND status='historical_immutable')
BEGIN SELECT RAISE(ABORT, 'historical relation is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_relation_delete
BEFORE DELETE ON relations WHEN EXISTS(
 SELECT 1 FROM sources WHERE source_id=OLD.source_id AND status='historical_immutable')
BEGIN SELECT RAISE(ABORT, 'historical relation is immutable'); END;
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha(value: bytes | str) -> str:
    raw = value if isinstance(value, bytes) else value.encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _symbol(surface: str) -> str:
    return "0x" + hashlib.sha1(surface.encode("utf-8")).hexdigest()[:12].upper()


def _anchors(text: str) -> list[tuple[str, int, int]]:
    return [
        (match.group(0), match.start(), match.end())
        for match in WORD_RE.finditer(text)
        if match.group(0).strip()
    ]


def _source_id(path: Path, source_hash: str) -> str:
    return "SRC2-" + _sha(f"{path}|{source_hash}")[:20]


def _object_id(source_id: str, kind: str, ordinal: int, text: str) -> str:
    return f"OBJ2-{_sha(f'{source_id}|{kind}|{ordinal}|{_sha(text)}')[:20]}"


def _read_jsonl(path: Path) -> Iterable[tuple[int, int, str, dict[str, Any]]]:
    raw = path.read_bytes()
    offset = 0
    for line_no, line in enumerate(raw.splitlines(keepends=True), start=1):
        decoded = line.decode("utf-8", errors="strict")
        body = decoded.rstrip("\r\n")
        if body.strip():
            yield line_no, offset, body, json.loads(body)
        offset += len(line)


def _event_text(row: dict[str, Any]) -> tuple[str, str | None]:
    message = row.get("message")
    if not isinstance(message, dict):
        return "", None
    role = str(message.get("role") or row.get("type") or "")
    content = message.get("content")
    if isinstance(content, str):
        return content, role
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text") or ""))
        return "\n".join(part for part in parts if part), role
    return "", role


def init_v2(runtime_root: str | Path) -> Path:
    root = Path(runtime_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(root / "relational_v2.sqlite3") as db:
        db.executescript(SCHEMA)
    return root


def ingest_chat_jsonl(
    source_path: str | Path,
    *,
    runtime_root: str | Path,
    source_label: str | None = None,
) -> dict[str, Any]:
    path = Path(source_path).expanduser().resolve()
    raw = path.read_bytes()
    source_hash = _sha(raw)
    source_id = _source_id(path, source_hash)
    root = init_v2(runtime_root)
    rows = list(_read_jsonl(path))
    events = [(line, offset, body, row) for line, offset, body, row in rows]
    session_ids = [str(row.get("sessionId") or "") for _, _, _, row in events if row.get("sessionId")]
    conversation_value = session_ids[0] if session_ids else "UNKNOWN"
    conversation_id = f"CONV2-{_sha(conversation_value)[:20]}"
    objects: list[dict[str, Any]] = []
    parent_for = {"conversation": None, "turn": conversation_id}
    turn_ordinal = 0
    message_ordinal = 0
    block_ordinal = 0
    objects.append({
        "object_id": conversation_id, "source_id": source_id, "parent_id": None,
        "object_type": "conversation", "ordinal": 0, "role": None,
        "speaker": None, "timestamp": None, "line_start": 1, "line_end": 1,
        "char_start": 0, "char_end": 0, "byte_start": 0, "byte_end": 0,
        "exact_text_hash": _sha(""), "text": "",
        "metadata_json": json.dumps({"session_id": conversation_value}, sort_keys=True),
    })
    for line_no, byte_start, body, row in events:
        text, role = _event_text(row)
        if not text:
            continue
        kind = str(row.get("type") or "event")
        if kind == "user":
            turn_ordinal += 1
            turn_id = _object_id(source_id, "turn", turn_ordinal, text)
            parent_for["turn"] = turn_id
            objects.append(_object(source_id, turn_id, conversation_id, "turn", turn_ordinal, row, text, role, line_no, byte_start, body))
        else:
            turn_id = str(parent_for.get("turn") or conversation_id)
        message_ordinal += 1
        message_id = _object_id(source_id, "message", message_ordinal, text)
        objects.append(_object(source_id, message_id, turn_id, "message", message_ordinal, row, text, role, line_no, byte_start, body))
        block_ordinal += 1
        block_id = _object_id(source_id, "block", block_ordinal, text)
        objects.append(_object(source_id, block_id, message_id, "block", block_ordinal, row, text, role, line_no, byte_start, body))

    with sqlite3.connect(root / "relational_v2.sqlite3") as db:
        db.execute(
            "INSERT OR IGNORE INTO sources VALUES(?,?,?,?,?,?,?,?)",
            (source_id, str(path), "chat-jsonl", source_hash, len(raw), source_label or path.name, _now(), "admitted"),
        )
        for obj in objects:
            db.execute(
                "INSERT OR IGNORE INTO objects VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                tuple(obj[key] for key in (
                    "object_id", "source_id", "parent_id", "object_type", "ordinal",
                    "role", "speaker", "timestamp", "line_start", "line_end",
                    "char_start", "char_end", "byte_start", "byte_end",
                    "exact_text_hash", "text", "metadata_json",
                )),
            )
            if obj["parent_id"]:
                db.execute(
                    "INSERT OR IGNORE INTO object_edges VALUES(?,?,?,?)",
                    (obj["parent_id"], obj["object_id"], "contains", obj["ordinal"]),
                )
            anchor_rows = _anchors(obj["text"])
            for ordinal, (surface, start, end) in enumerate(anchor_rows):
                db.execute("INSERT OR IGNORE INTO anchors(surface,kind,symbol) VALUES(?,?,?)", (surface, "content", _symbol(surface)))
                anchor_id = db.execute("SELECT anchor_id FROM anchors WHERE surface=?", (surface,)).fetchone()[0]
                occurrence_key = f"{obj['object_id']}|{ordinal}|{surface}"
                occurrence_id = f"OCC2-{_sha(occurrence_key)[:20]}"
                db.execute(
                    "INSERT OR IGNORE INTO occurrences VALUES(?,?,?,?,?,?,?,?)",
                    (occurrence_id, obj["object_id"], anchor_id, ordinal, start, end, obj["byte_start"] + len(obj["text"][:start].encode("utf-8")), obj["byte_start"] + len(obj["text"][:end].encode("utf-8"))),
                )
            for center_index, (center, _, _) in enumerate(anchor_rows):
                center_id = db.execute("SELECT anchor_id FROM anchors WHERE surface=?", (center,)).fetchone()[0]
                # The 6-1-6 neighborhood is an ephemeral calculation window.
                # Persist only its measured signed relationships.
                for neighbor_index in range(max(0, center_index - 6), min(len(anchor_rows), center_index + 7)):
                    if neighbor_index == center_index:
                        continue
                    neighbor = anchor_rows[neighbor_index][0]
                    neighbor_id = db.execute("SELECT anchor_id FROM anchors WHERE surface=?", (neighbor,)).fetchone()[0]
                    distance = neighbor_index - center_index
                    relation_key = f"{source_id}|{obj['object_id']}|{center_id}|{neighbor_id}|{distance}"
                    relation_id = f"REL2-{_sha(relation_key)[:20]}"
                    db.execute(
                        "INSERT INTO relations VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(relation_id) DO UPDATE SET count=count+1",
                        (relation_id, source_id, obj["object_id"], center_id, neighbor_id, "message", distance, 1),
                    )
        db.commit()
    return {
        "schema": "local_memory_relational_v2_intake@1",
        "source_id": source_id,
        "source_path": str(path),
        "source_hash": source_hash,
        "object_count": len(objects),
        "conversation_id": conversation_id,
        "turn_count": sum(1 for item in objects if item["object_type"] == "turn"),
        "message_count": sum(1 for item in objects if item["object_type"] == "message"),
        "block_count": sum(1 for item in objects if item["object_type"] == "block"),
        "runtime_db": str(root / "relational_v2.sqlite3"),
    }



def ingest_native_chat(
    source_path: str | Path,
    *,
    source_type: str,
    runtime_root: str | Path,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    """Adapt and immutably admit exactly one native historical chat."""
    adapted = adapt_native_chat(
        source_path, source_type=source_type, conversation_id=conversation_id
    )
    return _admit_adapted_chat(adapted, runtime_root=runtime_root)


def _admit_adapted_chat(adapted: AdaptedChat, *, runtime_root: str | Path) -> dict[str, Any]:
    root = init_v2(runtime_root)
    source_id = "NATSRC2-" + _sha(
        f"{adapted.source_type}|{adapted.source_hash}|{adapted.conversation_native_id}"
    )[:20]
    occurrence_id = "CUST2-" + _sha(f"{source_id}|{adapted.source_path}|{adapted.source_hash}")[:20]
    with sqlite3.connect(root / "relational_v2.sqlite3") as db:
        prior = db.execute("SELECT status FROM sources WHERE source_id=?", (source_id,)).fetchone()
        db.execute(
            "INSERT OR IGNORE INTO source_occurrences VALUES(?,?,?,?,?)",
            (occurrence_id, source_id, str(adapted.source_path), adapted.source_hash, _now()),
        )
        if prior:
            db.commit()
            counts = {
                kind: db.execute("SELECT COUNT(*) FROM objects WHERE source_id=? AND object_type=?", (source_id, kind)).fetchone()[0]
                for kind in ("conversation", "turn", "message", "message_variant", "block", "tool_call", "tool_result")
            }
            return _native_receipt(adapted, source_id, root, counts, duplicate=True)

        db.execute(
            "INSERT INTO sources VALUES(?,?,?,?,?,?,?,?)",
            (source_id, str(adapted.source_path), adapted.source_type, adapted.source_hash,
             adapted.size_bytes, adapted.source_label, _now(), "staging"),
        )
        id_map: dict[str, str] = {}
        for item in adapted.objects:
            id_map.setdefault(item.native_id, f"NATOBJ2-{_sha(f'{source_id}|{item.object_type}|{item.native_id}')[:20]}")
        stored: list[dict[str, Any]] = []
        for item in adapted.objects:
            object_id = id_map[item.native_id]
            parent_id = id_map.get(item.parent_native_id or "")
            metadata = dict(item.metadata)
            metadata["native_id"] = item.native_id
            metadata["native_parent_id"] = item.parent_native_id
            stored.append({
                "object_id": object_id, "source_id": source_id, "parent_id": parent_id,
                "object_type": item.object_type, "ordinal": item.ordinal,
                "role": item.role, "speaker": item.role, "timestamp": item.timestamp,
                "line_start": 0, "line_end": 0, "char_start": 0,
                "char_end": len(item.text), "byte_start": 0,
                "byte_end": len(item.text.encode("utf-8")),
                "exact_text_hash": _sha(item.text), "text": item.text,
                "metadata_json": json.dumps(metadata, ensure_ascii=True, sort_keys=True),
            })
            if item.object_type in {"message", "message_variant"} and item.text:
                for paragraph_ordinal, (start, end, paragraph) in enumerate(_paragraphs(item.text)):
                    block_id = f"NATBLK2-{_sha(f'{object_id}|{paragraph_ordinal}|{_sha(paragraph)}')[:20]}"
                    stored.append({
                        "object_id": block_id, "source_id": source_id, "parent_id": object_id,
                        "object_type": "block", "ordinal": paragraph_ordinal,
                        "role": item.role, "speaker": item.role, "timestamp": item.timestamp,
                        "line_start": 0, "line_end": 0, "char_start": start,
                        "char_end": end, "byte_start": len(item.text[:start].encode("utf-8")),
                        "byte_end": len(item.text[:end].encode("utf-8")),
                        "exact_text_hash": _sha(paragraph), "text": paragraph,
                        "metadata_json": json.dumps({"paragraph_ordinal": paragraph_ordinal, "native_message_id": item.native_id}, sort_keys=True),
                    })

        for obj in stored:
            db.execute(
                "INSERT INTO objects VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                tuple(obj[key] for key in (
                    "object_id", "source_id", "parent_id", "object_type", "ordinal",
                    "role", "speaker", "timestamp", "line_start", "line_end",
                    "char_start", "char_end", "byte_start", "byte_end",
                    "exact_text_hash", "text", "metadata_json",
                )),
            )
            if obj["parent_id"]:
                db.execute(
                    "INSERT OR IGNORE INTO object_edges VALUES(?,?,?,?)",
                    (obj["parent_id"], obj["object_id"], "contains", obj["ordinal"]),
                )
            if obj["object_type"] == "block":
                _index_block(db, source_id, obj)

        for artifact in adapted.artifacts:
            parent_id = id_map.get(artifact.parent_native_id)
            if parent_id is None:
                raise ValueError(f"artifact parent is absent: {artifact.parent_native_id}")
            artifact_id = "ART2-" + _sha(f"{source_id}|{artifact.native_id}|{artifact.ordinal}")[:20]
            metadata = dict(artifact.metadata)
            metadata["native_id"] = artifact.native_id
            db.execute(
                "INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (artifact_id, source_id, parent_id, artifact.ordinal, artifact.relationship,
                 artifact.media_type, artifact.source_locator, artifact.source_hash,
                 artifact.byte_size, "RAW_UNINTERPRETED",
                 json.dumps(metadata, ensure_ascii=True, sort_keys=True)),
            )
        db.execute("UPDATE sources SET status='historical_immutable' WHERE source_id=?", (source_id,))
        db.commit()
        counts = Counter(obj["object_type"] for obj in stored)
    return _native_receipt(adapted, source_id, root, counts, duplicate=False)


def _paragraphs(text: str) -> Iterable[tuple[int, int, str]]:
    cursor = 0
    for separator in re.finditer(r"(?:\r?\n){2,}", text):
        if separator.start() > cursor:
            yield cursor, separator.start(), text[cursor:separator.start()]
        cursor = separator.end()
    if cursor < len(text):
        yield cursor, len(text), text[cursor:]


def _index_block(db: sqlite3.Connection, source_id: str, obj: dict[str, Any]) -> None:
    anchor_rows = _anchors(obj["text"])
    anchor_ids: list[int] = []
    for ordinal, (surface, start, end) in enumerate(anchor_rows):
        # Chat lexicon values are exact observed surfaces. No hash symbolization.
        db.execute("INSERT OR IGNORE INTO anchors(surface,kind,symbol) VALUES(?,?,?)", (surface, "word_surface", surface))
        anchor_id = db.execute("SELECT anchor_id FROM anchors WHERE surface=?", (surface,)).fetchone()[0]
        anchor_ids.append(anchor_id)
        occurrence_id = "OCC2-" + _sha(f"{obj['object_id']}|{ordinal}|{surface}")[:20]
        db.execute(
            "INSERT INTO occurrences VALUES(?,?,?,?,?,?,?,?)",
            (occurrence_id, obj["object_id"], anchor_id, ordinal, start, end,
             obj["byte_start"] + len(obj["text"][:start].encode("utf-8")),
             obj["byte_start"] + len(obj["text"][:end].encode("utf-8"))),
        )
    for center_index, center_id in enumerate(anchor_ids):
        # Calculate ±6 temporarily; persist only collapsed measured counts.
        for neighbor_index in range(max(0, center_index - 6), min(len(anchor_ids), center_index + 7)):
            neighbor_id = anchor_ids[neighbor_index]
            if center_index == neighbor_index:
                continue
            distance = neighbor_index - center_index
            relation_id = "REL2-" + _sha(f"{source_id}|{obj['object_id']}|{center_id}|{neighbor_id}|{distance}")[:20]
            db.execute(
                "INSERT INTO relations VALUES(?,?,?,?,?,?,?,?) "
                "ON CONFLICT(relation_id) DO UPDATE SET count=count+1",
                (relation_id, source_id, obj["object_id"], center_id, neighbor_id, "paragraph", distance, 1),
            )


def _native_receipt(adapted: AdaptedChat, source_id: str, root: Path, counts: dict[str, int], *, duplicate: bool) -> dict[str, Any]:
    return {
        "schema": "local_memory_native_chat_intake@1",
        "source_id": source_id,
        "source_type": adapted.source_type,
        "source_path": str(adapted.source_path),
        "source_hash": adapted.source_hash,
        "source_size_bytes": adapted.size_bytes,
        "conversation_native_id": adapted.conversation_native_id,
        "conversation_count": int(counts.get("conversation", 0)),
        "turn_count": int(counts.get("turn", 0)),
        "message_count": int(counts.get("message", 0)),
        "message_variant_count": int(counts.get("message_variant", 0)),
        "block_count": int(counts.get("block", 0)),
        "tool_call_count": int(counts.get("tool_call", 0)),
        "tool_result_count": int(counts.get("tool_result", 0)),
        "artifact_count": len(adapted.artifacts),
        "status": "historical_immutable",
        "duplicate_logical_source": duplicate,
        "runtime_db": str(root / "relational_v2.sqlite3"),
    }


def retrieve_v2(
    question: str,
    *,
    runtime_root: str | Path,
    limit: int = 6,
    max_chars: int = 24000,
) -> dict[str, Any]:
    root = init_v2(runtime_root)
    query = [surface for surface, _, _ in _anchors(question) if surface.casefold() not in STOP]
    with sqlite3.connect(root / "relational_v2.sqlite3") as db:
        db.row_factory = sqlite3.Row
        evidence: list[dict[str, Any]] = []
        for row in db.execute("SELECT * FROM objects WHERE object_type IN ('message','block') ORDER BY source_id, line_start, ordinal"):
            surfaces = [value for value, _, _ in _anchors(row["text"])]
            direct = sorted(set(query) & set(surfaces))
            if not direct:
                continue
            placeholders = ",".join("?" for _ in direct)
            counts = db.execute(
                f"SELECT COUNT(*) FROM occurrences o JOIN anchors a ON a.anchor_id=o.anchor_id WHERE o.object_id=? AND a.surface IN ({placeholders})",
                [row["object_id"], *direct],
            ).fetchone()[0]
            relation_support = db.execute(
                "SELECT COALESCE(SUM(count),0) FROM relations WHERE object_id=?",
                (row["object_id"],),
            ).fetchone()[0]
            citation = "MEMCIT2-" + _sha(row["object_id"])[:12]
            evidence.append({
                "object_id": row["object_id"],
                "object_type": row["object_type"],
                "parent_id": row["parent_id"],
                "source_id": row["source_id"],
                "coordinates": {
                    "line_start": row["line_start"], "line_end": row["line_end"],
                    "byte_start": row["byte_start"], "byte_end": row["byte_end"],
                },
                "text": row["text"],
                "citation": citation,
                "retrieval": {
                    "direct_anchors": direct,
                    "query_coverage": len(direct),
                    "direct_occurrences": int(counts),
                    "relationship_support": int(relation_support),
                    "reason": "direct anchor match plus measured message-local relations",
                },
            })
    evidence.sort(key=lambda item: (
        -item["retrieval"]["query_coverage"], -item["retrieval"]["direct_occurrences"],
        -item["retrieval"]["relationship_support"], item["coordinates"]["byte_start"],
        item["object_id"],
    ))
    selected = []
    used = 0
    for item in evidence:
        remaining = max_chars - used
        if remaining <= 0 or len(selected) >= max(1, int(limit)):
            break
        text = item["text"][:remaining]
        if len(text) < len(item["text"]):
            text += " ...[packet-truncated]"
        selected.append({**item, "text": text})
        used += len(text)
    packet = {
        "schema": "local_memory_packet@2",
        "query": question,
        "query_anchors": query,
        "evidence": selected,
        "unknowns": [] if selected else ["No admitted object matched the query anchors."],
        "bounds": {"max_items": max(1, int(limit)), "max_chars": max_chars, "actual_chars": used},
        "model_authority": "renderer_only",
    }
    packet_path = root / f"memory_packet_v2_{_sha(question)[:16]}.json"
    packet_path.write_text(json.dumps(packet, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    return {"packet": packet, "packet_path": str(packet_path), "candidate_count": len(evidence)}


def _object(source_id: str, object_id: str, parent_id: str, kind: str, ordinal: int,
            row: dict[str, Any], text: str, role: str | None, line_no: int,
            byte_start: int, body: str) -> dict[str, Any]:
    timestamp = row.get("timestamp")
    return {
        "object_id": object_id, "source_id": source_id, "parent_id": parent_id,
        "object_type": kind, "ordinal": ordinal, "role": role,
        "speaker": role, "timestamp": str(timestamp) if timestamp else None,
        "line_start": line_no, "line_end": line_no, "char_start": 0,
        "char_end": len(body), "byte_start": byte_start,
        "byte_end": byte_start + len(body.encode("utf-8")),
        "exact_text_hash": _sha(text), "text": text,
        "metadata_json": json.dumps({
            "uuid": row.get("uuid"), "parent_uuid": row.get("parentUuid"),
            "session_id": row.get("sessionId"), "type": row.get("type"),
            "is_sidechain": row.get("isSidechain"),
        }, ensure_ascii=True, sort_keys=True),
    }
