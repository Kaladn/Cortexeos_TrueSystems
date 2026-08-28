from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from core.lakespeak.schemas import AnchorRecord, ChunkAnchors, ChunkRef, ChunkRelations, RelationEdge
from core.structural_memory import ledger


def _configure_paths(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(ledger, "ANCHOR_OBSERVATIONS_DIR", tmp_path / "anchor_observations")
    monkeypatch.setattr(ledger, "RELATION_OBSERVATIONS_DIR", tmp_path / "relation_observations")
    monkeypatch.setattr(ledger, "STRUCTURAL_LIFECYCLE_DIR", tmp_path / "lifecycle")
    monkeypatch.setattr(ledger, "STRUCTURAL_VIEWS_DB_PATH", tmp_path / "views" / "structural_memory.sqlite3")


def test_record_map_snapshot_appends_and_materializes(tmp_path, monkeypatch):
    _configure_paths(tmp_path, monkeypatch)

    result = ledger.record_map_snapshot(
        corpus_id="chats",
        map_id="map_123",
        cite_id="cite_123",
        canonical="2026-03-15:DOC:chat_2026-03-15.jsonl",
        filename="chat_2026-03-15.jsonl",
        anchors={
            "forest": {
                "symbol": "TREE",
                "lexicon_payload": {"hex": "HX001", "symbol": "TREE"},
                "lexicon_word": "forest",
                "frequency": 12,
                "before": {
                    "1": [{"token": "ancient", "count": 2, "in_lexicon": True, "symbol": "OLD"}],
                },
                "after": {
                    "2": [{"token": "grows", "count": 3, "in_lexicon": False, "symbol": None}],
                },
            }
        },
        observed_at_utc="2026-03-15T10:00:00+00:00",
    )

    assert result == {"anchor_events": 1, "relation_events": 2}

    anchor_lines = (tmp_path / "anchor_observations" / "2026-03-15.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(anchor_lines) == 1
    anchor_record = json.loads(anchor_lines[0])
    assert anchor_record["anchor_token"] == "forest"
    assert anchor_record["anchor_count"] == 5
    assert anchor_record["window_count"] == 2

    with sqlite3.connect(tmp_path / "views" / "structural_memory.sqlite3") as conn:
        anchor_total = conn.execute(
            "SELECT anchor_count_total, window_count_total FROM anchor_totals WHERE corpus_id = ? AND anchor_token = ?",
            ("chats", "forest"),
        ).fetchone()
        assert anchor_total == (5, 2)
        lifecycle = conn.execute(
            "SELECT state FROM lifecycle_entities WHERE entity_kind = ? AND entity_id = ?",
            ("map", "map_123"),
        ).fetchone()
        assert lifecycle == ("created",)


def test_record_lakespeak_ingest_appends_and_rebuilds(tmp_path, monkeypatch):
    _configure_paths(tmp_path, monkeypatch)

    chunk = ChunkRef(
        chunk_id="ch_1",
        receipt_id="rcpt_1",
        corpus_id="chats",
        ordinal=0,
        source_hash="sha256:abc",
        source_path="D:/CLEARBOX/data/chats/2026-03-15.jsonl",
        span_start=0,
        span_end=32,
        text_hash="sha256:def",
        token_count=4,
        text="forest grows in silence",
    )
    chunk_anchors = ChunkAnchors(
        chunk_id="ch_1",
        receipt_id="rcpt_1",
        corpus_id="chats",
        anchor_count=1,
        anchors=[
            AnchorRecord(
                token="forest",
                hex_addr="HX001",
                symbol="TREE",
                position=0,
                frequency=9,
            )
        ],
        anchor_counts={"forest": 2},
        window_counts={"forest": 1},
        created_at_utc="2026-03-15T11:00:00+00:00",
    )
    chunk_relations = ChunkRelations(
        chunk_id="ch_1",
        receipt_id="rcpt_1",
        corpus_id="chats",
        relation_count=1,
        relations=[
            RelationEdge(
                source_token="forest",
                target_token="grows",
                distance=1,
                direction="after",
                co_occurrence_count=2,
                source_hex="HX001",
                target_hex="HX002",
            )
        ],
        created_at_utc="2026-03-15T11:00:00+00:00",
    )

    result = ledger.record_lakespeak_ingest(
        receipt_id="rcpt_1",
        corpus_id="chats",
        chunks=[chunk],
        all_anchors=[chunk_anchors],
        all_relations=[chunk_relations],
        source_path="D:/CLEARBOX/data/chats/2026-03-15.jsonl",
        lake_path="D:/CLEARBOX/data/indexes/lakespeak/chunks/chats/rcpt_1",
        observed_at_utc="2026-03-15T11:00:00+00:00",
    )

    assert result == {"anchor_events": 1, "relation_events": 1}

    ledger.rebuild_views()

    with sqlite3.connect(tmp_path / "views" / "structural_memory.sqlite3") as conn:
        anchor_total = conn.execute(
            "SELECT support_count, anchor_count_total, window_count_total FROM anchor_totals WHERE corpus_id = ? AND anchor_token = ?",
            ("chats", "forest"),
        ).fetchone()
        assert anchor_total == (1, 2, 1)
        relation_total = conn.execute(
            """
            SELECT support_count, co_occurrence_total
            FROM relation_totals
            WHERE corpus_id = ? AND source_token = ? AND target_token = ? AND distance = ? AND direction = ?
            """,
            ("chats", "forest", "grows", 1, "after"),
        ).fetchone()
        assert relation_total == (1, 2)
