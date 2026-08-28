# TrueVision SC Edition Agentic Ops Map

- Created: 2026-05-17
- Scope: backend only
- UI status: parked

## Core Role

TrueVision SC Edition is a small GPU-output state-change logger. It records
moment changes from full GPU pre-render output into compact metadata records.
It does not store screenshots, video, text extraction, object labels, or raw
frames.

The capture backend is an explicit install point. The current SecureCore code
expects an injected full GPU pre-render surface provider and does not import the
old gaming runtime, old detector workers, or any recognition stack.

```text
GPU output state
-> aspect-preserving grid hash
-> small state-change record
-> sensor event
-> Forge
-> low-cost anomaly signal
-> larger agents only if needed
```

## Base Workers

```text
TrueVisionSCLiveCapture
  role: capture full GPU pre-render surface through an injected backend
  writes: none
  output: truevision_sc_state_change
  install status: backend injection point only; no live desktop hook enabled yet

TrueVisionSCForgeWorker
  role: convert state-change records into sensor events and write to Forge
  writes: sensor_vision only
  output: Forge records

TrueVisionSCAnomalyWorker
  role: classify compact state-change ratios into low/medium/high visual-change pressure
  writes: none
  output: small anomaly dict

TrueVisionSCWorkerSet
  role: explicit one-step capture -> classify -> Forge write coordinator
  writes: sensor_vision only through TrueVisionSCForgeWorker
  output: event id, compact state-change metadata, compact anomaly metadata

ProofOfLifeWorker
  role: live proof-of-life logger
  writes: sensor_hid only
  output: camera-present metadata if available, otherwise local-HID recent activity
  raw content: none
```

## Current Agent Compatibility

| Agent | Status | Why | Required Change |
| --- | --- | --- | --- |
| `chain_auditor` | compatible now | audits substrate/Forge integrity and does not need visual semantics | none |
| `cognitive` | slight adapter | already reads HID and human activity; visual state changes can improve local-presence context | feed summarized TrueVision state into HID/activity-burst or a future visual context reader |
| `escalation` | compatible after derived decision | consumes `agent_decisions`, not raw visual state | add a visual anomaly decision producer later |
| `containment` | compatible after escalation | only reacts to escalation decisions | none until visual anomalies become escalation evidence |
| `watcher` | not direct | designed for ingress HTTP request patterns | leave out |
| `profiler` | not direct | attacker profile from ingress/mirror traffic | leave out unless visual state becomes a mirror/session feature |
| `decoy_orchestrator` | not direct | honeypot decoy strategy | leave out |
| `temporal_causality_log_checker` | compatible now | read-only checker for event logs and causality chains | use after Forge/sensor logs exist |
| `recovered_security_snapshot` | adjacent only | evidence snapshot script, not live vision | no direct use |
| `recovered_security_firewall_enforcer` | not direct | enforcement, approval-gated | never driven by vision alone |

## Agentic Ops Fit

```text
Always-low workers:
  TrueVisionSCLiveCapture
  TrueVisionSCAnomalyWorker
  TrueVisionSCForgeWorker
  ProofOfLifeWorker

Always-safe readers:
  temporal_causality_log_checker
  chain_auditor

Wake-on-anomaly candidates:
  cognitive
  escalation

Never direct from vision:
  containment
  firewall enforcer
  decoy orchestrator
```

## Hard Boundaries

```text
No raw media payloads.
No screenshot truth.
No text extraction.
No object recognition.
No detector stack.
No automatic enforcement.
No high-tier agent wake unless anomaly or operator request triggers it.
```

## First Live Test Contract

For the first installed run:

```text
duration: 5 minutes
surface: full GPU pre-render output
output: sensor_vision Forge records only
record type: state_change
payload class: small_metadata
expected: no raw media fields
expected: Forge verify OK
expected: summary count + max change ratio + anomaly counts
```

Do not run the 5-minute live test until the GPU pre-render backend is selected
and explicitly installed.
