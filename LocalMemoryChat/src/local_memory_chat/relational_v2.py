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
CREATE TABLE IF NOT EXISTS occurrence_positions(
 occurrence_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, block_id TEXT NOT NULL,
 sentence_id TEXT NOT NULL, sentence_ordinal INTEGER NOT NULL,
 block_ordinal INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS occurrence_positions_block ON occurrence_positions(block_id, block_ordinal);
CREATE INDEX IF NOT EXISTS occurrence_positions_sentence ON occurrence_positions(sentence_id, sentence_ordinal);
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
CREATE TRIGGER IF NOT EXISTS immutable_occurrence_position_insert
BEFORE INSERT ON occurrence_positions WHEN EXISTS(
 SELECT 1 FROM sources WHERE source_id=NEW.source_id AND status='historical_immutable')
BEGIN SELECT RAISE(ABORT, 'historical occurrence position is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_occurrence_position_update
BEFORE UPDATE ON occurrence_positions WHEN EXISTS(
 SELECT 1 FROM sources WHERE source_id=OLD.source_id AND status='historical_immutable')
BEGIN SELECT RAISE(ABORT, 'historical occurrence position is immutable'); END;
CREATE TRIGGER IF NOT EXISTS immutable_occurrence_position_delete
BEFORE DELETE ON occurrence_positions WHEN EXISTS(
 SELECT 1 FROM sources WHERE source_id=OLD.source_id AND status='historical_immutable')
BEGIN SELECT RAISE(ABORT, 'historical occurrence position is immutable'); END;
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


def _anchors(text: str) -> list[tuple[str, int, int]]:
    return [
        (match.group(0), match.start(), match.end())
        for match in WORD_RE.finditer(text)
        if match.group(0).strip()
    ]


def init_v2(runtime_root: str | Path) -> Path:
    root = Path(runtime_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(root / "relational_v2.sqlite3") as db:
        db.executescript(SCHEMA)
    return root


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
                for kind in ("conversation", "turn", "message", "message_variant", "block", "sentence", "tool_call", "tool_result")
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
                    block_byte_start = len(item.text[:start].encode("utf-8"))
                    stored.append({
                        "object_id": block_id, "source_id": source_id, "parent_id": object_id,
                        "object_type": "block", "ordinal": paragraph_ordinal,
                        "role": item.role, "speaker": item.role, "timestamp": item.timestamp,
                        "line_start": 0, "line_end": 0, "char_start": start,
                        "char_end": end, "byte_start": block_byte_start,
                        "byte_end": block_byte_start + len(paragraph.encode("utf-8")),
                        "exact_text_hash": _sha(paragraph), "text": paragraph,
                        "metadata_json": json.dumps({"paragraph_ordinal": paragraph_ordinal, "native_message_id": item.native_id}, sort_keys=True),
                    })
                    block_word_ordinal = 0
                    for sentence_ordinal, (sentence_start, sentence_end, sentence) in enumerate(_sentences(paragraph)):
                        sentence_id = f"NATSENT2-{_sha(f'{block_id}|{sentence_ordinal}|{_sha(sentence)}')[:20]}"
                        stored.append({
                            "object_id": sentence_id, "source_id": source_id, "parent_id": block_id,
                            "object_type": "sentence", "ordinal": sentence_ordinal,
                            "role": item.role, "speaker": item.role, "timestamp": item.timestamp,
                            "line_start": 0, "line_end": 0,
                            "char_start": sentence_start, "char_end": sentence_end,
                            "byte_start": block_byte_start + len(paragraph[:sentence_start].encode("utf-8")),
                            "byte_end": block_byte_start + len(paragraph[:sentence_end].encode("utf-8")),
                            "exact_text_hash": _sha(sentence), "text": sentence,
                            "metadata_json": json.dumps({
                                "sentence_ordinal": sentence_ordinal,
                                "block_word_ordinal_start": block_word_ordinal,
                                "native_message_id": item.native_id,
                            }, sort_keys=True),
                        })
                        block_word_ordinal += len(_anchors(sentence))

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
            if obj["object_type"] == "sentence":
                _index_sentence(db, source_id, obj)

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


def _sentences(text: str) -> Iterable[tuple[int, int, str]]:
    start = 0
    for boundary in re.finditer(r"[.!?]+(?=\s|$)", text):
        end = boundary.end()
        if text[start:end].strip():
            yield start, end, text[start:end]
        start = end
        while start < len(text) and text[start].isspace():
            start += 1
    if start < len(text) and text[start:].strip():
        yield start, len(text), text[start:]


def _index_sentence(db: sqlite3.Connection, source_id: str, obj: dict[str, Any]) -> None:
    metadata = json.loads(obj["metadata_json"])
    block_id = str(obj["parent_id"])
    block_start = int(metadata["block_word_ordinal_start"])
    for sentence_ordinal, (surface, start, end) in enumerate(_anchors(obj["text"])):
        # Chat lexicon values are exact observed surfaces. No normalization or hash symbolization.
        db.execute("INSERT OR IGNORE INTO anchors(surface,kind,symbol) VALUES(?,?,?)", (surface, "word_surface", surface))
        anchor_id = db.execute("SELECT anchor_id FROM anchors WHERE surface=?", (surface,)).fetchone()[0]
        occurrence_id = "OCC2-" + _sha(f"{obj['object_id']}|{sentence_ordinal}|{surface}")[:20]
        db.execute(
            "INSERT INTO occurrences VALUES(?,?,?,?,?,?,?,?)",
            (occurrence_id, obj["object_id"], anchor_id, sentence_ordinal, start, end,
             obj["byte_start"] + len(obj["text"][:start].encode("utf-8")),
             obj["byte_start"] + len(obj["text"][:end].encode("utf-8"))),
        )
        db.execute(
            "INSERT INTO occurrence_positions VALUES(?,?,?,?,?,?)",
            (occurrence_id, source_id, block_id, obj["object_id"], sentence_ordinal, block_start + sentence_ordinal),
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
        "sentence_count": int(counts.get("sentence", 0)),
        "durable_relation_count": 0,
        "tool_call_count": int(counts.get("tool_call", 0)),
        "tool_result_count": int(counts.get("tool_result", 0)),
        "artifact_count": len(adapted.artifacts),
        "status": "historical_immutable",
        "duplicate_logical_source": duplicate,
        "runtime_db": str(root / "relational_v2.sqlite3"),
    }


def project_relationships(
    center_surface: str,
    *,
    runtime_root: str | Path,
    scope_ids: Iterable[str],
    offsets: Iterable[int] | None = None,
    top_k: int | None = None,
    include_positional_mass: bool = False,
) -> dict[str, Any]:
    """Project an ephemeral directed relationship field from exact sentence occurrences."""
    root = init_v2(runtime_root)
    db_path = root / "relational_v2.sqlite3"
    scope = list(dict.fromkeys(str(value) for value in scope_ids))
    if not scope:
        raise ValueError("at least one block or sentence scope ID is required")
    lanes = list(dict.fromkeys(int(value) for value in (offsets or (-6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6))))
    if not lanes or any(value == 0 for value in lanes):
        raise ValueError("relationship offsets must be non-zero")
    database_hash_before = _sha(db_path.read_bytes())
    uri = f"file:{db_path}?mode=ro"
    with sqlite3.connect(uri, uri=True) as db:
        db.row_factory = sqlite3.Row
        sentence_ids: list[str] = []
        for object_id in scope:
            row = db.execute("SELECT object_type FROM objects WHERE object_id=?", (object_id,)).fetchone()
            if row is None:
                raise ValueError(f"scope object not found: {object_id}")
            if row["object_type"] == "sentence":
                sentence_ids.append(object_id)
            elif row["object_type"] == "block":
                sentence_ids.extend(value[0] for value in db.execute(
                    "SELECT object_id FROM objects WHERE parent_id=? AND object_type='sentence' ORDER BY ordinal,object_id",
                    (object_id,),
                ))
            else:
                raise ValueError(f"scope object must be block or sentence: {object_id}")
        sentence_ids = list(dict.fromkeys(sentence_ids))
        if not sentence_ids:
            raise ValueError("scope contains no admitted sentences")
        fields: dict[str, dict[str, Any]] = {}
        observations = 0
        source_ids: set[str] = set()
        for sentence_id in sentence_ids:
            sentence = db.execute("SELECT source_id,parent_id FROM objects WHERE object_id=?", (sentence_id,)).fetchone()
            source_ids.add(str(sentence["source_id"]))
            rows = db.execute(
                "SELECT o.occurrence_id,o.ordinal,a.surface,p.block_id,p.block_ordinal "
                "FROM occurrences o JOIN anchors a ON a.anchor_id=o.anchor_id "
                "JOIN occurrence_positions p ON p.occurrence_id=o.occurrence_id "
                "WHERE o.object_id=? ORDER BY o.ordinal",
                (sentence_id,),
            ).fetchall()
            for center_index, center in enumerate(rows):
                if center["surface"] != center_surface:
                    continue
                for distance in lanes:
                    neighbor_index = center_index + distance
                    if neighbor_index < 0 or neighbor_index >= len(rows):
                        continue
                    neighbor = rows[neighbor_index]
                    field = fields.setdefault(str(neighbor["surface"]), {
                        "surface": str(neighbor["surface"]), "lane_counts": {},
                        "total": 0, "positional_mass": 0, "supporting_observations": [],
                    })
                    lane = str(distance)
                    field["lane_counts"][lane] = int(field["lane_counts"].get(lane, 0)) + 1
                    field["total"] += 1
                    if abs(distance) <= 6:
                        field["positional_mass"] += 7 - abs(distance)
                    field["supporting_observations"].append({
                        "sentence_id": sentence_id, "block_id": str(center["block_id"]),
                        "center_occurrence_id": str(center["occurrence_id"]),
                        "neighbor_occurrence_id": str(neighbor["occurrence_id"]),
                        "signed_offset": distance,
                    })
                    observations += 1
        candidates = sorted(fields.values(), key=lambda item: (-int(item["total"]), str(item["surface"])))
        if not include_positional_mass:
            for item in candidates:
                item.pop("positional_mass", None)
        sources = [dict(row) for row in db.execute(
            f"SELECT source_id,source_path,source_hash,status FROM sources WHERE source_id IN ({','.join('?' for _ in source_ids)}) ORDER BY source_id",
            sorted(source_ids),
        )] if source_ids else []
    database_hash_after = _sha(db_path.read_bytes())
    if database_hash_before != database_hash_after:
        raise RuntimeError("relationship projection mutated the flat memory database")
    projection = {
        "schema": "local_memory_relationship_projection@1",
        "center_surface": center_surface,
        "scope_ids": scope,
        "sentence_ids": sentence_ids,
        "offsets": lanes,
        "complete_candidate_count": len(candidates),
        "observation_count": observations,
        "candidates": candidates,
        "display_top_k": candidates[:max(0, int(top_k))] if top_k is not None else candidates,
        "sources": sources,
        "database_hash": database_hash_before,
        "durable_graph_rows_written": 0,
    }
    projection_id = "PROJ2-" + _sha(json.dumps(projection, ensure_ascii=True, sort_keys=True))[:20]
    receipt = {
        "schema": "local_memory_relationship_projection_receipt@1",
        "projection_id": projection_id,
        "created_at": _now(),
        "projection": projection,
    }
    receipt_root = root / "projection_receipts"
    receipt_root.mkdir(parents=True, exist_ok=True)
    receipt_path = receipt_root / f"{projection_id}.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"projection": projection, "receipt_path": str(receipt_path)}

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
        for row in db.execute("SELECT * FROM objects WHERE object_type='sentence' ORDER BY source_id, parent_id, ordinal"):
            surfaces = [value for value, _, _ in _anchors(row["text"])]
            direct = sorted(set(query) & set(surfaces))
            if not direct:
                continue
            placeholders = ",".join("?" for _ in direct)
            counts = db.execute(
                f"SELECT COUNT(*) FROM occurrences o JOIN anchors a ON a.anchor_id=o.anchor_id WHERE o.object_id=? AND a.surface IN ({placeholders})",
                [row["object_id"], *direct],
            ).fetchone()[0]
            relation_support = 0
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
                    "reason": "direct exact-surface occurrence in an admitted sentence",
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
