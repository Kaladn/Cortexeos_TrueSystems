# SecureCore Promise Ledger

This file tracks promises that are incomplete, half-built, or deliberately parked.
It is the repo-side burn-down list. A promise is not done until code, tests, and a receipt exist.

## Current Truth Document

The current runtime/status authority is:

```text
docs/security/SECURECORE_OPERATIONAL_TRUTH_LOCK.md
```

Older TODOs and phase plans remain useful design history, but their status lines may be stale. When they conflict with tested code or the operational truth lock, use the operational truth lock.

## Rules

```text
No fake completion.
No silent scope expansion.
No media generation inside SecureCore until reopened by Lee.
Text facts reports are allowed.
Central Writer speaks.
Policy Gate approves action.
AI models interpret; they do not execute, approve, or own truth.
Model assistance is OpenAI API session only.
Models read shaped data only when explicitly routed.
Models do not mutate SecureCore.
```

## Completed In This Pass

- Former embedded model runtime files were removed.
- Local-model selection is no longer a SecureCore runtime lane.
- Active SecureCore roadmap now keeps broad generation/artifact work parked.

## Active Incomplete Promises

### 1. Text Facts Report Output

Status: runtime output path complete; integration callers still need to use it.

Done:
- Central Reader bundle contract.
- Central Writer request contract.
- Model writer report request contract.
- Facts report contract.
- Writer receipt contract.
- Writer rejection contract.
- Concrete output folders: `reports/` and `receipts/`.
- `CentralWriter` runtime validates requests, writes facts reports, and returns receipts.
- Invalid requests produce no report file.
- Tests cover agent requests, model requests, rejection contract, and invalid request behavior.

Still needed:
- Wire selected callers, such as email sentinel and incident summaries, through `CentralWriter`.
- Add app/CLI route only after backend caller integration is stable.

Done criteria:
- A model or agent can request a facts-only text report, Central Writer validates it, writes it, and returns a receipt.

### 2. Forge Binary Cutover

Status: binary foundation and sharded Forge V2 foundation work; global cutover not done.

Done:
- Binary record codec.
- Forge writer.
- Forge reader.
- WAL recovery.
- Rebuildable index.
- Pulse writer.
- Optional substrate dual-write.
- Sensor Forge sink.
- Sharded Forge writer/reader beside the existing Forge path.
- Binary shard index rebuild and tail behavior.

Still needed:
- Decide cutover policy.
- Prove load/stress behavior.
- Decide retention/shard shape.
- Decide whether JSONL remains primary or Forge becomes primary.

Done criteria:
- One truth path is declared and verified under load.

### 3. Always-On Logging

Status: one-shot readers and broad Windows Event Log registry coverage exist; service loop incomplete.

Done:
- Process snapshot/diff.
- Network snapshot/diff.
- Bounded Windows Event Log reader.
- Source registry.
- Cursor store.
- Sensor event contract.
- One-shot smoke test.
- Open-window snapshot/diff.
- Registry entries for Application, System, Security, Defender, PowerShell, WMI, Task Scheduler, BITS, Terminal Services, User Profile Service, Code Integrity, AppLocker, Firewall, DNS Client, and Network Profile.
- Collector helper for all enabled eventlog sources.

Still needed:
- Always-on low-cost reader loop.
- Throttle/cooldown/budget rules.
- Retention policy.
- Wake-up thresholds.
- Backlog/causal chain replay command.

Done criteria:
- SecureCore can run low-level observation continuously without high-cost agents or uncontrolled log growth.

### 3A. Internal Self Logger

Status: receipt builder exists; live scheduler/integration incomplete.

Done:
- Independent `securecore/internal_watch` package exists.
- Self-audit receipt contract exists.
- System trust receipt contract exists.
- Green/yellow/red trust posture output exists.
- Human-verification metadata is carried as evidence, not final decision authority.
- Machine-growth notes are carried as lessons, not fact authority.
- Receipts are explicitly outside the normal logging lane.
- Validation rejects mutation authority, policy approval authority, recovery action, suppression authority, and normal-log-lane pollution.
- Trust posture is limited to Forge, fusion, retention, policy, runner, queues, mutation, and watchers.
- Unbounded diary-style targets are rejected.

Still needed:
- Decide default receipt location outside volatile operational logs.
- Wire a low-frequency explicit self-check command.
- Add checks for Forge health, fusion health, policy receipts, runner status, and unexpected mutation drift.
- Decide what AW may request from SC self-audit status.

Done criteria:
- SecureCore can produce independent self-audit receipts about itself without mutating runtime or approving action.

### 3B. Performance Logger

Status: receipt builder exists; live instrumentation incomplete.

Done:
- Independent `securecore/performance` package exists.
- Performance receipt contract exists.
- Cost posture fields exist for duration, CPU, memory, disk, Forge latency, fusion build time, queue wait, model latency, GPU/VRAM, energy estimate, throughput, and errors.
- Bottleneck hint exists.
- Validation rejects truth authority, behavior-change authority, and policy approval authority.

Still needed:
- Add explicit instrumentation wrappers for selected workers/tools.
- Add psutil-backed optional sampler.
- Add GPU/VRAM probe adapters where available.
- Add comparison reports for before/after algorithm changes.

Done criteria:
- SecureCore can prove whether worker, tool, model, or algorithm changes improved cost without letting the performance logger decide truth or mutate behavior.

### 3C. Sentinel Agents

Status: first observer-only sentinels exist; broader automation and runner integration incomplete.

Done:
- Sentinel manifest/result contract exists.
- Sentinels reject mutation authority, policy approval authority, temporal write authority, and direct user alert authority.
- `forge_verify_sentinel` exists.
- `fusion_verify_sentinel` exists.
- `system_trust_sentinel` exists.
- Sentinel results can request backend engines without authorizing engine writes.

Still needed:
- Add manifest files for each sentinel when runner wiring is ready.
- Add `performance_profile_sentinel`.
- Add `eventlog_sweep_sentinel`.
- Add `retention_status_sentinel`.
- Add `email_sentinel_poll_sentinel`.
- Add `aw_route_tap_reader_sentinel`.
- Wire sentinel calls through the approved runner path.
- Add solo/dual/multi-chain orchestration contracts after sentinel basics are stable.
- Add two-way agent communication contracts only after chain receipts are stable.

Done criteria:
- SecureCore can run safe coded sentinels as solo, paired, or chained observers without giving agents temporal write authority or action authority.

### 3D. Agent Handoff Comms

Status: contract exists; runner integration and orchestration incomplete.

Done:
- `AgentHandoffPacket` contract exists.
- `AgentHandoffReply` contract exists.
- Handoff packets reject open conversation mode.
- Handoff packets and replies reject temporal write authority, mutation authority, policy approval authority, and direct user alert authority.
- Replies must match the packet's `allowed_reply_kind` when validating against a packet.

Still needed:
- Runner integration for one approved handoff path.
- Chain receipt format for solo, dual, and multi-chain work.
- Handoff inbox/outbox storage policy.
- Timeout behavior and stale handoff cleanup.
- Two-way exchange policy after single handoff receipts are stable.

Done criteria:
- Agents can exchange typed handoff packets and replies through the approved runner path without open-ended conversations or hidden authority.

### 4. Temporal Causality

Status: checker exists, broader causal intake incomplete.

Done:
- Temporal causality log checker.
- Timestamp validation.
- Sequence/cursor/hash checks.
- Breach/error lead-up support for event logs.

Still needed:
- Causal intake command.
- Backlog reader for selected event families.
- Temporal promotion rules.
- Integration with wake-up cascade.

Done criteria:
- Given a suspicious event, SecureCore can reconstruct a bounded lead-up trail with proof.

### 5. Multi-Language Agent Runner

Status: manifest validation exists, runner adapters incomplete.

Done:
- Live-agent manifest contract.
- Prompt-only production agents rejected.
- Allowed runtime languages declared.
- Recovered security agents staged.

Still needed:
- Rust runner adapter.
- C++ runner adapter.
- Python runner adapter.
- PowerShell runner adapter.
- Structured input/output envelope.
- Timeout and dry-run enforcement.

Done criteria:
- SecureCore can call approved agents in supported languages without granting default authority.

### 6. Policy Gate And Adapter Handoff

Status: contracts exist, execution handoff incomplete.

Done:
- Policy decision contracts.
- Approval requires user identity and phrase.
- AI-only approval rejected.

Still needed:
- Adapter handoff receipt.
- Expiry/revocation tests.
- Firewall/action adapter flow under strict approval.

Done criteria:
- No mutation-capable adapter can run without a proved human approval chain.

### 7. Tool/Agent Factory

Status: selection spine exists, build factory incomplete.

Done:
- Capability registry.
- Chain recipe contract.
- Situational picker.
- Negative tests for blocked actions, missing dependencies, unknown capabilities, and approval requirements.

Still needed:
- Agent build request contract.
- Sandbox test contract.
- Activation contract.
- Central Writer report step for tool creation.

Done criteria:
- SecureCore can propose, validate, test, and stage a tool/agent without direct execution or hidden authority.

### 8. TrueVision And Audio State Logging

Status: TrueVision SC visual metadata lane exists; audio lane remains planned.

Done:
- Source registry contains disabled/placeholder media lanes.
- Sensor contract supports `vision`.
- Tests prove camera/microphone default disabled.
- TrueVision SC Edition compact state-change contract.
- Aspect-preserving grid hash/diff path.
- Explicit ops-once path.
- Forge adapter and worker set.
- Proof-of-Life metadata worker.
- Glyph metadata extender with no text/fact authority.

Still needed:
- Audio soundstage state-change contract.
- Synthetic test windows.
- Forge write tests.
- Wake-up request tests.

Done criteria:
- SecureCore logs compact media state changes as metadata, not raw capture, and wakes higher agents only through policy-bound pathways.

### 9. Email Sentinel

Status: mini-backend exists, Central Writer integration incomplete.

Done:
- Header-only bridge/service/sandbox.
- Routes and tests.
- No body/download/HTML/attachment by default.

Still needed:
- Real configured mailbox bridge.
- Device pool notification adapter.
- Central Writer report integration.
- Retention rules for normal headers.

Done criteria:
- Important security/banking alert patterns can become governed user notifications without downloading full mail.

### 10. Cognitive Identity

Status: HID substrate exists, cognitive identity incomplete.

Done:
- HID substrate tests.
- Synthetic activity record support.
- Attestation shape.

Still needed:
- Real hardware reader integration.
- Identity log separate from normal purge.
- Pattern baseline period.
- User-present signal for security decisions.

Done criteria:
- SecureCore can say whether an action likely came from the user, with bounded confidence and no AI-only final decision.

### 11. UI

Status: last by rule.

Done:
- Frontdoor exists.
- UI maps started.

Still needed:
- Do not build broadly until backend promises above are stable.
- Every surface gets a card map before assembly.
- No fake controls.

Done criteria:
- UI shows only runtime-supported controls and truthful status.

## Parked Promises

### Media Generation / Synthetic Artifact Generation

Status: parked.

Reason:
- The security core must work before generated media or broad artifact tooling enters the repo.

Allowed now:
- Text facts reports only.

Not allowed now:
- Image generation.
- Video generation.
- Synthetic evidence.
- Media artifact generation engine.
- Generated media release workflow.

Reopen condition:
- User explicitly reopens it after logging, policy, Central Writer, and agent runner are stable.
