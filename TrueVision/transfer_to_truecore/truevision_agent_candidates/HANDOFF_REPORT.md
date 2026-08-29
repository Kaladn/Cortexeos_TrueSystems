# TrueVision Agent Candidate Handoff

## Purpose

Stage TrueCore-formatted agent candidates that reason over TrueVision worker
outputs without moving TrueVision workers into TrueCore.

## Agents

```text
truevision_worker_receipt_router
truevision_consensus_reasoning_agent
truevision_zero_tolerance_gate_agent
```

## TrueCore Format

Agent manifests match the live-agent contract used by:

```text
D:\TrueCore_Workspace\TrueCore\truecore\live_agents\manifest.py
```

Catalog files match the existing TrueCore live-agent CSV header:

```text
operator_id,name,category,agent_tier,definition,input_shape,output_shape,assumptions_in,assumptions_out,side_effects,dependencies,statefulness,sync_mode,destruction_score,risk_type,risk_reason,requires_confirmation,sandbox_required,promotion_ready,contract_status,category_confidence,source_file
```

## Validation

Current package validation:

```text
TrueCore manifest validator: pass
zero-tolerance gate agent: pass
catalog rows: 3
agent manifests: 3
prompt-only agents: 0
fake hashes: 0
worker migration into TrueCore: 0
```

## What Stays In TrueVision

```text
capture workers
meter workers
glyph workers
geometry workers
geography/context workers
render/proof workers
cleanup workers for TrueVision temp areas
```

## What Moves To TrueCore Later

Only coordinating/reasoning/gating agents may be copied into TrueCore:

```text
truecore/live_agents/AGENTS/agents/*.agent.json
truecore/live_agents/AGENTS/truevision-agents/*.py
truecore/live_agents/AGENTS/catalog/*.csv
truecore/live_agents/AGENTS/catalog/truecore_export.json
```

## Activation Boundary

This package is not active by directory presence. TrueCore must validate,
test, review, and register agents before live use.

All three candidates are marked:

```text
promotion_ready: REVIEW
contract_status: CANDIDATE
```

They are not claimed production-ready.

## Package Law

```text
Workers gather.
Agents reason.
TrueCore gates.
Operators approve.
Receipts prove.
```
