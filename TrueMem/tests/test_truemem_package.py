from __future__ import annotations

import subprocess
import sys


def test_truemem_module_cli_exposes_current_cli_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "truemem.cli", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "TrueMem dataset-local evidence engine CLI" in result.stdout
    assert "pressure-coordination-audit" in result.stdout


def test_truemem_package_is_the_direct_implementation() -> None:
    import truemem

    assert truemem.__version__ == "0.05"
    assert not hasattr(truemem, "__compatibility_package__")
