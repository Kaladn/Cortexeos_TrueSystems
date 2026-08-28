"""Fusion verification sentinel."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from securecore.sentinels.contracts import build_sentinel_result
from securecore.sensors.fusion_store import FusionBlockStore


def run(input_payload: dict[str, Any]) -> dict[str, Any]:
    fusion_root = Path(input_payload["fusion_root"])
    verify = FusionBlockStore(fusion_root).verify()
    if verify.get("intact"):
        return build_sentinel_result(
            sentinel_id="fusion_verify_sentinel",
            status="ok",
            facts=["fusion verify intact"],
            evidence_refs=[f"fusion://{fusion_root}"],
        )
    return build_sentinel_result(
        sentinel_id="fusion_verify_sentinel",
        status="alert",
        warnings=[f"fusion verify failed: {verify.get('error', 'unknown')}"],
        evidence_refs=[f"fusion://{fusion_root}"],
    )
