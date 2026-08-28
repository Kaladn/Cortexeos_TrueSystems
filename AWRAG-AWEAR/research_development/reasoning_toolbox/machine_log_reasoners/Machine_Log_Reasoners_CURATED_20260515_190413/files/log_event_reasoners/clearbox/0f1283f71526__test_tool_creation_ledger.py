from __future__ import annotations

import json

from core.tool_creation import ledger


def test_tool_creation_ledger_writes_factory_tool_and_test_records(tmp_path, monkeypatch) -> None:
    tool_root = tmp_path / "data" / "tool creation"
    monkeypatch.setattr(ledger, "TOOL_CREATION_LEDGER_DIR", tool_root / "ledger")
    monkeypatch.setattr(ledger, "TOOL_CREATION_SESSIONS_DIR", tool_root / "sessions")
    monkeypatch.setattr(ledger, "TOOL_CREATION_TOOLS_DIR", tool_root / "tools")
    monkeypatch.setattr(ledger, "TOOL_CREATION_TESTS_DIR", tool_root / "tests")

    factory_event = ledger.record_factory_turn(
        session_id="tool_factory",
        side_chat_id="side_20260315_160000_deadbeef",
        provider="ollama",
        model="qwen2.5:7b-instruct",
        user_message="Build me a safe csv tool.",
        response_text="Draft ready.",
    )
    tool_event = ledger.record_tool_definition_event(
        action="saved",
        tool_name="csv_helper",
        tool_data={"name": "csv_helper", "safety": "read"},
    )
    test_event = ledger.record_tool_test_run(
        tool_name="csv_helper",
        arguments={"path": "sample.csv"},
        result="ok",
    )

    assert factory_event["event_type"] == "factory_turn"
    assert tool_event["event_type"] == "tool_definition"
    assert test_event["event_type"] == "tool_test"

    ledger_files = list((tool_root / "ledger").glob("*.jsonl"))
    assert len(ledger_files) == 1
    ledger_records = [
        json.loads(line)
        for line in ledger_files[0].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [record["event_type"] for record in ledger_records] == [
        "factory_turn",
        "tool_definition",
        "tool_test",
    ]

    session_files = list((tool_root / "sessions").glob("*.jsonl"))
    assert len(session_files) == 1
    assert "side_20260315_160000_deadbeef" in session_files[0].stem

    tool_snapshots = list((tool_root / "tools" / "csv_helper").glob("*.json"))
    assert len(tool_snapshots) == 1
    snapshot = json.loads(tool_snapshots[0].read_text(encoding="utf-8"))
    assert snapshot["action"] == "saved"
    assert snapshot["tool_name"] == "csv_helper"

    test_files = list((tool_root / "tests").glob("*.jsonl"))
    assert len(test_files) == 1
    test_records = [
        json.loads(line)
        for line in test_files[0].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert test_records[0]["tool_name"] == "csv_helper"
