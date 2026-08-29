"""Suspicious activity bridge: causality before containment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from truecore.incidents.causality import build_causality_chain
from truecore.network.sandbox_containment import execute_sandboxed_containment


def handle_suspicious_activity(
    *,
    output_root: str | Path,
    chain_id: str,
    trigger_event_id: str,
    fusion_block_id: str,
    events: list[dict[str, Any]],
    remote_ip: str,
    actor_process: str,
    process_hash: str,
    remote_endpoint: str,
    reason_code: str,
    firewall_adapter: Any | None,
    ttl_seconds: int = 300,
) -> dict[str, Any]:
    """Build causality, then run sandboxed trap/block/release receipts."""

    root = Path(output_root)
    root.mkdir(parents=True, exist_ok=True)
    chain = build_causality_chain(
        chain_id=chain_id,
        trigger_event_id=trigger_event_id,
        fusion_block_id=fusion_block_id,
        events=events,
    )
    chain_path = root / "causality_chain.json"
    chain_path.write_text(json.dumps(chain, indent=2, sort_keys=True), encoding="utf-8")
    return execute_sandboxed_containment(
        output_root=root,
        remote_ip=remote_ip,
        observed_event_refs=[f"event:{event_id}" for event_id in chain["event_refs"]],
        actor_process=actor_process,
        process_hash=process_hash,
        remote_endpoint=remote_endpoint,
        fusion_block_ref=f"fusion:block:{fusion_block_id}",
        causality_chain_ref=f"causality:chain:{chain_id}",
        reason_code=reason_code,
        firewall_adapter=firewall_adapter,
        ttl_seconds=ttl_seconds,
    )
