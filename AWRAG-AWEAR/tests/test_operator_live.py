from __future__ import annotations

import builtins
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


from awrag.operator_live import run_live_shell
from awrag.operator_shell import OperatorShell


def test_live_fallback_keeps_plain_shell_when_rich_missing(monkeypatch):
    shell = OperatorShell(chat_counts_enabled=False)
    called = {"plain": False}
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "rich" or name.startswith("rich."):
            raise ImportError("rich intentionally hidden for fallback test")
        return real_import(name, *args, **kwargs)

    def fake_run():
        called["plain"] = True

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.setattr(shell, "run", fake_run)

    run_live_shell(shell)

    assert called["plain"] is True


def test_operator_shell_once_menu_stays_plain_behavior():
    shell = OperatorShell(chat_counts_enabled=False)

    result = shell.handle_input("menu")

    assert result["kind"] == "menu"
    assert "AWEAR CLI Cockpit" in str(result["message"])
    assert "1. Chat mode" in str(result["message"])


def test_read_system_metrics_is_read_only_packet():
    shell = OperatorShell(chat_counts_enabled=False)

    metrics = shell.read_system_metrics()

    assert metrics["schema"] == "awrag_system_metrics@1"
    assert metrics["no_mutation"] is True
