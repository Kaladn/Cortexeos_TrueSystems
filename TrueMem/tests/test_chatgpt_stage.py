from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from truemem.engine import stage_chatgpt_export


def test_stage_chatgpt_export_writes_chat_turn_markdown(tmp_path: Path) -> None:
    export = tmp_path / "export"
    export.mkdir()
    (export / "conversations-000.json").write_text(
        json.dumps(
            [
                {
                    "id": "conv-1",
                    "title": "TrueMem Plan",
                    "default_model_slug": "gpt-test",
                    "mapping": {
                        "n1": {
                            "id": "n1",
                            "message": {
                                "id": "m1",
                                "author": {"role": "user"},
                                "create_time": 1710000000.0,
                                "content": {"content_type": "text", "parts": ["Build the evidence field."]},
                                "metadata": {},
                            },
                        },
                        "n2": {
                            "id": "n2",
                            "message": {
                                "id": "m2",
                                "author": {"role": "assistant"},
                                "create_time": 1710000001.0,
                                "content": {"content_type": "text", "parts": ["Intake builds counts."]},
                                "metadata": {"model_slug": "gpt-test"},
                            },
                        },
                        "n3": {
                            "id": "n3",
                            "message": {
                                "id": "m3",
                                "author": {"role": "assistant"},
                                "create_time": 1710000002.0,
                                "content": {"content_type": "thoughts", "parts": ["skip me"]},
                                "metadata": {"model_slug": "gpt-test"},
                            },
                        },
                    },
                }
            ]
        ),
        encoding="utf-8",
    )

    result = stage_chatgpt_export(export, tmp_path / "staged" / "chat.md")

    staged = Path(result["output_path"]).read_text(encoding="utf-8")
    assert result["conversation_count"] == 1
    assert result["turn_count"] == 2
    assert result["speaker_counts"] == {"assistant": 1, "user": 1}
    assert "CHAT_SOURCE_EXPORT: chatgpt_data_export" in staged
    assert "CHAT_CONVERSATION_ID: conv-1" in staged
    assert "CHAT_SPEAKER: user" in staged
    assert "Build the evidence field." in staged
    assert "Intake builds counts." in staged
    assert "skip me" not in staged


def test_stage_chatgpt_cli_help_exists() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "truemem.cli", "stage-chatgpt", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "--export-root" in result.stdout
    assert "--max-conversations" in result.stdout
