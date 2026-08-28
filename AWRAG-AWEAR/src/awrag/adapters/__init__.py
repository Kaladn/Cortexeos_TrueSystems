from __future__ import annotations

from pathlib import Path
from typing import Any

from ..engine.base import utc_now, with_protected_notice, write_json


def detect_source_adapter(source_dir: str | Path) -> str | None:
    Path(source_dir).expanduser().resolve()
    return None


def prepare_source_with_adapter_if_present(source_dir: str | Path, out_dir: str | Path) -> dict[str, Any]:
    source = Path(source_dir).expanduser().resolve()
    out = Path(out_dir).expanduser().resolve()
    adapter = detect_source_adapter(source)

    out.mkdir(parents=True, exist_ok=True)
    manifest = with_protected_notice({
        "schema": "awrag_adapter_selection@1",
        "created_at": utc_now(),
        "adapter_used": False,
        "adapter_name": None,
        "source_dir": str(source),
        "out_dir": str(out),
        "ingest_source_dir": str(source),
        "clean_questions_path": None,
        "raw_source_copied_into_dataset": False,
        "ingest_contract": "No adapter matched. Run normal generic intake against ingest_source_dir.",
    })
    selection_path = out / "ADAPTER_SELECTION_MANIFEST.json"
    write_json(selection_path, manifest)
    manifest["selection_manifest_path"] = str(selection_path)
    return manifest


__all__ = [
    "detect_source_adapter",
    "prepare_source_with_adapter_if_present",
]
