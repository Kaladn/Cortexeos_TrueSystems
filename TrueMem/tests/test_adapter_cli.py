from __future__ import annotations

import subprocess
import sys


def test_adapter_auto_prepare_live_under_adapters_namespace() -> None:
    top = subprocess.run([sys.executable, "-m", "truemem.cli", "--help"], check=True, capture_output=True, text=True)
    adapters = subprocess.run([sys.executable, "-m", "truemem.cli", "adapters", "--help"], check=True, capture_output=True, text=True)
    prepare = subprocess.run(
        [sys.executable, "-m", "truemem.cli", "adapters", "prepare", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "adapters" in top.stdout
    assert "prepare" in adapters.stdout
    assert "--source" in prepare.stdout
    assert "--out" in prepare.stdout
