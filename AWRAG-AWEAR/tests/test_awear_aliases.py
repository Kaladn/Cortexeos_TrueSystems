from __future__ import annotations

import subprocess
import sys


def test_awear_module_cli_alias_exposes_current_cli_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "awear.cli", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "AWEAR dataset-local evidence engine CLI" in result.stdout
    assert "pressure-coordination-audit" in result.stdout


def test_awear_package_reexports_existing_awrag_engine() -> None:
    import awear
    import awrag

    assert awear.__compatibility_package__ is awrag
