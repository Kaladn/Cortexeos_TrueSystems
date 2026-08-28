"""Forge verification sentinel."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from securecore.forge.sharded import ShardedForgeReader
from securecore.sentinels.contracts import build_sentinel_result


def run(input_payload: dict[str, Any]) -> dict[str, Any]:
    forge_root = Path(input_payload["forge_root"])
    streams = [str(item) for item in input_payload.get("streams", [])]
    facts: list[str] = []
    warnings: list[str] = []
    evidence_refs: list[str] = []
    status = "ok"
    for stream in streams:
        reader = ShardedForgeReader(forge_root / stream)
        verify = reader.verify()
        evidence_refs.append(f"forge://{stream}")
        if verify.get("intact"):
            facts.append(f"{stream} intact")
        else:
            status = "alert"
            warnings.append(f"{stream} verify failed: {verify.get('error', 'unknown')}")
    return build_sentinel_result(
        sentinel_id="forge_verify_sentinel",
        status=status,
        facts=facts,
        evidence_refs=evidence_refs,
        warnings=warnings,
    )
