from __future__ import annotations

import bridges.tool_defs as tool_defs


def test_parse_tool_call_close_only_drift() -> None:
    text = 'portun {"name": "get_system_metrics", "arguments": {}} </tool_call>'
    calls = tool_defs.parse_tool_calls(text)
    assert calls == [{"name": "get_system_metrics", "arguments": {}}]


def test_parse_tool_call_close_tag_scan_salvage() -> None:
    text = 'noise before {"name":"get_system_metrics","arguments":{"x":1}} </tool_call> trailing'
    calls = tool_defs.parse_tool_calls(text)
    assert calls == [{"name": "get_system_metrics", "arguments": {"x": 1}}]


def test_strip_tool_calls_removes_close_only_drift() -> None:
    text = 'portun {"name": "get_system_metrics", "arguments": {}} </tool_call>\nDone.'
    cleaned = tool_defs.strip_tool_calls(text)
    assert "get_system_metrics" not in cleaned
    assert "tool_call" not in cleaned
    assert "Done." in cleaned


def test_parse_and_strip_close_only_drift_with_newlines() -> None:
    text = 'portun\n{"name": "get_system_metrics", "arguments": {}}\n</tool_call>'
    calls = tool_defs.parse_tool_calls(text)
    assert calls == [{"name": "get_system_metrics", "arguments": {}}]
    cleaned = tool_defs.strip_tool_calls(text)
    assert cleaned == ""
