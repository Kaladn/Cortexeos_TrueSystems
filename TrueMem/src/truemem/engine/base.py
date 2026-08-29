from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

COPYRIGHT = "Copyright (c) 2026 Lee Mercey. Owner: Cortex Evolved Systems. All rights reserved."
WATERMARK = "TrueMem public-review facsimile output; not source evidence. Verify against cited source coordinates."
LICENSE_REF = "TrueMem Public Review License"
FACSIMILE_WARNING = "This output is a local processing facsimile, not source evidence or professional advice."
MAX_BLOCK_LINES = 40
SYMBOL_SYSTEM = "truemem_dataset_6b@1"
SYMBOL_BYTES = 6
SYMBOL_HEX_CHARS = SYMBOL_BYTES * 2
COUNT_BACKEND = "truemem_native_binary_counts@1"


@dataclass(frozen=True)
class DatasetPaths:
    root: Path
    incoming: Path
    state: Path
    counts: Path
    coordinates: Path
    citations: Path
    outputs: Path
    receipts: Path
    qa: Path
    qa_ledger_path: Path
    anchor_counts_path: Path
    relation_counts_path: Path
    block_anchor_path: Path
    blocks_path: Path
    lexicon_path: Path
    chat_metadata_path: Path
    manifest_path: Path


def safe_id(value: str) -> str:
    out = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or "").strip()).strip("._")
    if not out:
        raise ValueError("dataset id is required")
    return out

def dataset_paths(runtime_root: str | Path, dataset_id: str) -> DatasetPaths:
    root = Path(runtime_root).expanduser().resolve() / "datasets" / safe_id(dataset_id)
    return DatasetPaths(
        root=root,
        incoming=root / "incoming",
        state=root / "state",
        counts=root / "counts",
        coordinates=root / "coordinates",
        citations=root / "citations",
        outputs=root / "outputs",
        receipts=root / "receipts",
        qa=root / "qa",
        qa_ledger_path=root / "qa" / "questions_answers.jsonl",
        anchor_counts_path=root / "counts" / "anchor_counts.awbin",
        relation_counts_path=root / "counts" / "relation_counts.awbin",
        block_anchor_path=root / "counts" / "block_anchor_postings.awbin",
        blocks_path=root / "state" / "blocks.jsonl",
        lexicon_path=root / "state" / "dataset_lexicon.json",
        chat_metadata_path=root / "state" / "chat_metadata_index.jsonl",
        manifest_path=root / "dataset_manifest.json",
    )

def public_paths(paths: DatasetPaths) -> dict[str, str]:
    return {
        "dataset_root": str(paths.root),
        "anchor_counts": str(paths.anchor_counts_path),
        "relation_counts": str(paths.relation_counts_path),
        "block_anchor_postings": str(paths.block_anchor_path),
        "lexicon": str(paths.lexicon_path),
        "coordinates": str(paths.coordinates),
        "citations": str(paths.citations),
        "outputs": str(paths.outputs),
        "receipts": str(paths.receipts),
        "qa": str(paths.qa),
        "qa_ledger": str(paths.qa_ledger_path),
    }

def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(with_protected_notice(payload), ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

def protected_notice() -> dict[str, Any]:
    return {
        "copyright": COPYRIGHT,
        "owner": "Cortex Evolved Systems",
        "license": LICENSE_REF,
        "watermark": WATERMARK,
        "facsimile_warning": FACSIMILE_WARNING,
        "watermark_locked": True,
        "removal_prohibited": True,
    }

def with_protected_notice(payload: dict[str, Any]) -> dict[str, Any]:
    protected = protected_notice()
    protected.update(payload)
    for key, value in protected_notice().items():
        protected[key] = value
    return protected

def sha1_text(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", errors="replace")).hexdigest()

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def unique_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
