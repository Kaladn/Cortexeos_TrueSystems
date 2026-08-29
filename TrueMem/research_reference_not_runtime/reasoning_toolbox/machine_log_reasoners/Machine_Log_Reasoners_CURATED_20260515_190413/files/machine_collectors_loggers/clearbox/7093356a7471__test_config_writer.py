from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from bridges.state import BridgeState


def _write_base_config(tmp_path: Path) -> Path:
    lexicon_root = tmp_path / "Lexical Data" / "Canonical"
    reports_root = tmp_path / "reports"
    lexicon_root.mkdir(parents=True, exist_ok=True)
    reports_root.mkdir(parents=True, exist_ok=True)

    config = {
        "lexicon_root": str(lexicon_root),
        "reports_root": str(reports_root),
        "gpu": "auto",
        "min_len": 5,
        "topK": 10,
        "window": 6,
        "routing": {"dev_mode": False},
        "network": {"require_auth": True},
        "clearbox_node": {"require_hello": True},
        "server": {"host": "127.0.0.1", "port": 5050},
    }
    config_path = tmp_path / "clearbox.config.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config_path


def test_write_config_concurrent_updates_are_atomic(tmp_path: Path) -> None:
    config_path = _write_base_config(tmp_path)
    async def _run() -> None:
        state = BridgeState(config_path)
        async def update_one() -> None:
            await state.write_config(
                {
                    "routing": {"dev_mode": True},
                    "log_level": "debug",
                }
            )

        async def update_two() -> None:
            await state.write_config(
                {
                    "network": {"require_auth": False},
                    "clearbox_node": {"require_hello": False},
                }
            )

        try:
            await asyncio.gather(update_one(), update_two())

            loaded = json.loads(config_path.read_text(encoding="utf-8"))
            assert loaded["routing"]["dev_mode"] is True
            assert loaded["network"]["require_auth"] is False
            assert loaded["clearbox_node"]["require_hello"] is False
            assert loaded["log_level"] == "debug"
        finally:
            await state.close()

    asyncio.run(_run())
