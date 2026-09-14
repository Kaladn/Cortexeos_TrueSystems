"""Session lifecycle tests for the retained evidence-session boundary."""

from __future__ import annotations

import json
from pathlib import Path

from wolf_engine.evidence.session_manager import EvidenceSessionManager


class TestSessionManager:
    def test_start_creates_directory_and_manifest(self, tmp_path):
        manager = EvidenceSessionManager(str(tmp_path), node_id="node_1")
        info = manager.start("test_session")
        assert info.session_id
        assert info.node_id == "node_1"
        manifest = Path(info.session_dir) / "manifest.json"
        assert manifest.exists()
        assert json.loads(manifest.read_text(encoding="utf-8"))["label"] == "test_session"

    def test_stop_updates_manifest(self, tmp_path):
        manager = EvidenceSessionManager(str(tmp_path))
        manager.start("s1")
        info = manager.stop()
        assert info is not None
        assert info.end_time is not None
        manifest = json.loads(Path(info.session_dir, "manifest.json").read_text(encoding="utf-8"))
        assert manifest["end_time"] is not None

    def test_double_start_finalizes_first(self, tmp_path):
        manager = EvidenceSessionManager(str(tmp_path))
        first = manager.start("first")
        second = manager.start("second")
        assert first.session_id != second.session_id
        manifest = json.loads(Path(first.session_dir, "manifest.json").read_text(encoding="utf-8"))
        assert manifest["end_time"] is not None

    def test_list_sessions(self, tmp_path):
        manager = EvidenceSessionManager(str(tmp_path))
        manager.start("a")
        manager.stop()
        manager.start("b")
        manager.stop()
        assert len(manager.list_sessions()) == 2
