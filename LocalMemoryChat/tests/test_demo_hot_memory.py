from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from local_memory_chat.memory import (
    add_file,
    ask,
    attach_source,
    build_sqlite_support,
    import_demo,
    index_source,
    init_runtime,
    inspect_binary,
    list_sources,
)


def test_import_demo_builds_hot_counts_and_address_index(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"

    result = import_demo(ROOT / "data" / "demo" / "synthetic_chat.jsonl", runtime_root=runtime, memory_profile_id="demo")

    profile = runtime / "profiles" / "demo"
    assert result["source_count"] == 6
    assert (profile / "sources" / "source_manifest.jsonl").exists()
    assert (profile / "hot" / "hot_counts.json").exists()
    assert (profile / "hot" / "hot_address_index.jsonl").exists()
    hot_counts = json.loads((profile / "hot" / "hot_counts.json").read_text(encoding="utf-8"))
    assert hot_counts["anchors"]["memory"] >= 1
    assert hot_counts["cohabitation"]


def test_ask_searches_hot_memory_and_writes_packet_and_receipt(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    import_demo(ROOT / "data" / "demo" / "synthetic_chat.jsonl", runtime_root=runtime, memory_profile_id="demo")

    result = ask("what did we decide about local render providers?", runtime_root=runtime, memory_profile_id="demo")

    packet = result["packet"]
    assert packet["search_policy"]["hot_searched"] is True
    assert packet["search_policy"]["cold_searched"] is False
    assert packet["evidence_items"]
    assert packet["evidence_items"][0]["citation"].startswith("MEMCIT-")
    assert "renderer" in packet["evidence_items"][0]["snippet"] or "memory" in packet["evidence_items"][0]["snippet"]
    assert Path(result["packet_path"]).exists()
    assert Path(result["receipt"]["receipt_path"]).exists()


def test_init_runtime_creates_ignored_runtime_shape(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"

    result = init_runtime(runtime, memory_profile_id="demo")

    assert result["memory_profile_id"] == "demo"
    assert (runtime / "profiles" / "demo" / "sources").exists()
    assert (runtime / "profiles" / "demo" / "hot").exists()
    assert (runtime / "profiles" / "demo" / "packets").exists()
    assert (runtime / "profiles" / "demo" / "receipts").exists()


def test_add_file_is_searchable_immediately_with_line_citation(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    note = tmp_path / "note.md"
    note.write_text(
        "# Render Providers\n"
        "Local render providers are deferred until memory packets are stable.\n"
        "The model is voice, not authority.\n",
        encoding="utf-8",
    )

    receipt = add_file(note, runtime_root=runtime, memory_profile_id="demo", source_label="render-note", chunk_lines=2)
    result = ask("what did we decide about render providers?", runtime_root=runtime, memory_profile_id="demo")

    assert receipt["source_hash_unchanged"] is True
    assert result["packet"]["evidence_items"]
    top = result["packet"]["evidence_items"][0]
    assert top["source_type"] == "file"
    assert top["source_label"] == "render-note"
    assert top["citation"].startswith("MEMCIT-")
    assert top["address"]["line_start"] == 1
    assert "render providers" in top["snippet"].casefold()


def test_attach_source_writes_runtime_only_manifest(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    note = tmp_path / "private.md"
    note.write_text("Private project memory says packet first, renderer second.", encoding="utf-8")

    receipt = attach_source(note, source_type="file", label="private-note", runtime_root=runtime, memory_profile_id="demo")
    sources = list_sources(runtime, memory_profile_id="demo")

    assert receipt["source_type"] == "file"
    assert receipt["private_data_exported"] is False
    assert sources["source_count"] == 1
    assert sources["sources"][0]["source_id"] == receipt["source_id"]
    assert sources["sources"][0]["path"] == str(note.resolve())


def test_index_source_file_creates_hot_memory_and_preserves_source_hash(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    note = tmp_path / "private.md"
    note.write_text("Private file memory says cross-source citations need address records.", encoding="utf-8")
    attach = attach_source(note, source_type="file", label="private-note", runtime_root=runtime, memory_profile_id="demo")

    receipt = index_source(attach["source_id"], runtime_root=runtime, memory_profile_id="demo", hot=True)
    result = ask("what needs address records?", runtime_root=runtime, memory_profile_id="demo")

    assert receipt["status"] == "indexed_hot"
    assert receipt["source_hash_unchanged"] is True
    assert result["packet"]["evidence_items"]
    assert result["packet"]["evidence_items"][0]["citation"].startswith("MEMCIT-")
    assert "address records" in result["packet"]["evidence_items"][0]["snippet"].casefold()


def test_list_sources_reports_index_receipt_status(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    note = tmp_path / "private.md"
    note.write_text("Private file memory says source status should follow receipts.", encoding="utf-8")
    attach = attach_source(note, source_type="file", label="private-note", runtime_root=runtime, memory_profile_id="demo")

    index_source(attach["source_id"], runtime_root=runtime, memory_profile_id="demo", hot=True)
    sources = list_sources(runtime, memory_profile_id="demo")

    row = sources["sources"][0]
    assert row["source_id"] == attach["source_id"]
    assert row["indexed"] is True
    assert row["latest_index_status"] == "indexed_hot"
    assert row["latest_index_receipt"]


def test_index_source_file_root_indexes_text_files_only(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    root = tmp_path / "root"
    root.mkdir()
    (root / "one.md").write_text("Alpha memory packet citations live here.", encoding="utf-8")
    (root / "two.txt").write_text("Beta address records prove source locations.", encoding="utf-8")
    (root / "image.bin").write_bytes(b"\x00\x01binary")
    attach = attach_source(root, source_type="file-root", label="private-root", runtime_root=runtime, memory_profile_id="demo")

    receipt = index_source(attach["source_id"], runtime_root=runtime, memory_profile_id="demo", hot=True)
    result = ask("where do address records prove source locations?", runtime_root=runtime, memory_profile_id="demo")

    assert receipt["file_count"] == 2
    assert receipt["source_hash_unchanged"] is True
    assert result["packet"]["evidence_items"][0]["source_type"] == "file"
    assert "source locations" in result["packet"]["evidence_items"][0]["snippet"].casefold()


def test_chat_binary_attach_is_not_decoded_in_v0(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    binary = tmp_path / "chat.awbin"
    binary.write_bytes(b"fake-binary-chat")
    attach = attach_source(binary, source_type="chat-binary", label="chat-bin", runtime_root=runtime, memory_profile_id="demo")

    receipt = index_source(attach["source_id"], runtime_root=runtime, memory_profile_id="demo", hot=True)

    assert attach["status"] == "attached_not_decoded"
    assert receipt["indexed"] is False
    assert receipt["status"] == "attached_not_decoded"
    assert receipt["source_hash_unchanged"] is True


def test_inspect_binary_reports_header_without_decoding(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    binary = tmp_path / "chat.awbin"
    binary.write_bytes(b"GGUF\x03\x00\x00\x00" + b"\x00" * 128)
    attach = attach_source(binary, source_type="chat-binary", label="chat-bin", runtime_root=runtime, memory_profile_id="demo")

    receipt = inspect_binary(attach["source_id"], runtime_root=runtime, memory_profile_id="demo", sample_bytes=8)

    assert receipt["possible_format"] == "gguf"
    assert receipt["decode_status"] == "not_decoded"
    assert receipt["no_mutation"] is True
    assert receipt["source_hash_unchanged"] is True
    assert receipt["first_bytes_hex"].startswith("47 47 55 46")
    assert receipt["record_count_if_detectable"] is None
    assert Path(receipt["receipt_path"]).exists()


def test_inspect_binary_rejects_non_binary_sources(tmp_path: Path) -> None:
    runtime = tmp_path / "runtime"
    note = tmp_path / "private.md"
    note.write_text("Private project memory says packet first.", encoding="utf-8")
    attach = attach_source(note, source_type="file", label="private-note", runtime_root=runtime, memory_profile_id="demo")

    try:
        inspect_binary(attach["source_id"], runtime_root=runtime, memory_profile_id="demo")
    except ValueError as exc:
        assert "chat-binary" in str(exc)
    else:
        raise AssertionError("inspect_binary should reject non-chat-binary sources")


def test_sqlite_support_builds_binary_and_row_index(tmp_path: Path) -> None:
    import sqlite3

    runtime = tmp_path / "runtime"
    db = tmp_path / "chat.sqlite"
    con = sqlite3.connect(db)
    con.execute("create table messages(role text, body text)")
    con.execute("insert into messages(role, body) values (?, ?)", ("user", "hello memory"))
    con.execute("insert into messages(role, body) values (?, ?)", ("assistant", "packet first"))
    con.commit()
    con.close()
    attach = attach_source(db, source_type="chat-binary", label="chat-db", runtime_root=runtime, memory_profile_id="demo")

    receipt = build_sqlite_support(attach["source_id"], runtime_root=runtime, memory_profile_id="demo")
    sources = list_sources(runtime, memory_profile_id="demo")

    assert receipt["row_count"] == 2
    assert receipt["table_count"] == 1
    assert receipt["source_hash_unchanged"] is True
    assert Path(receipt["binary_path"]).exists()
    assert Path(receipt["index_path"]).exists()
    index_lines = Path(receipt["index_path"]).read_text(encoding="utf-8").splitlines()
    assert len(index_lines) == 2
    assert "SQLCIT-" in index_lines[0]
    assert sources["sources"][0]["sqlite_support_built"] is True


def test_sqlite_support_can_record_live_source_hash_mismatch(tmp_path: Path) -> None:
    import sqlite3

    runtime = tmp_path / "runtime"
    db = tmp_path / "chat.sqlite"
    con = sqlite3.connect(db)
    con.execute("create table messages(body text)")
    con.execute("insert into messages(body) values (?)", ("before",))
    con.commit()
    con.close()
    attach = attach_source(db, source_type="chat-binary", label="chat-db", runtime_root=runtime, memory_profile_id="demo")
    con = sqlite3.connect(db)
    con.execute("insert into messages(body) values (?)", ("after",))
    con.commit()
    con.close()

    receipt = build_sqlite_support(
        attach["source_id"],
        runtime_root=runtime,
        memory_profile_id="demo",
        allow_live_source=True,
    )

    assert receipt["attached_hash_matches_before"] is False
    assert receipt["live_source_allowed"] is True
    assert receipt["row_count"] == 2
