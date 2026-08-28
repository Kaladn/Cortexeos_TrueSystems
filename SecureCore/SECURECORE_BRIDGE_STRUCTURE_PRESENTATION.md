# SecureCore Bridge Structure

## Purpose

This document defines the SecureCore bridge philosophy and module shape for generation, implementation planning, and code review.

The goal is not one giant orchestrator.
The goal is many small, restartable, typed bridges that move shaped data between system lanes without owning truth, policy, memory, or runtime authority.

## Core Law

```text
Truth lives in durable stores.
Policy lives in policy contracts.
Authority lives with the user.
Bridges only move shaped data.
```

## Anti-Goal

Do not build a god bridge.

Forbidden:

```text
one bridge that knows every subsystem
one bridge that owns all queues
one bridge that blocks unrelated operations
one bridge that becomes memory
one bridge that becomes policy
one bridge that becomes truth
one bridge that requires full system restart
one bridge that silently retries forever
one bridge that hides failures
```

## Operating Target

```text
near-zero downtime while host is awake
small bridge failure should not stop unrelated systems
bridge state must be rebuildable from durable records
each bridge can restart independently
each bridge has bounded input and bounded output
```

## Bridge Definition

A bridge is a narrow process/module that converts one approved input shape into one approved output shape.

It must answer:

```text
what input shape do I accept?
what output shape do I emit?
what source owns truth?
what cursor or sequence do I use?
what happens if I crash?
what proof/receipt do I leave?
what am I forbidden to do?
```

## Universal Bridge Contract

Every bridge should have this conceptual contract:

```json
{
  "bridge_id": "string",
  "schema_version": 1,
  "input_kind": "string",
  "output_kind": "string",
  "source_ref": "string",
  "cursor": {},
  "sequence": 0,
  "idempotency_key": "string",
  "started_at_utc": "canonical UTC timestamp",
  "completed_at_utc": "canonical UTC timestamp",
  "status": "accepted|written|skipped|rejected|failed",
  "output_refs": [],
  "receipt_ref": "string",
  "error": ""
}
```

## Universal Bridge Laws

```text
1. Bridge input must be validated before work.
2. Bridge output must be validated before write.
3. Bridge failure must be visible.
4. Bridge retry must be bounded.
5. Bridge output must be idempotent when possible.
6. Bridge state must be reconstructable from cursor/sequence/receipts.
7. Bridge cannot approve action.
8. Bridge cannot mutate source truth.
9. Bridge cannot emit user-facing claims except through Central Writer.
10. Bridge cannot call high-risk adapters without Policy Gate proof.
```

## Durable Recovery Model

If a bridge dies:

```text
source truth remains
Forge/binary records remain
cursor remains
receipts remain
bridge restarts
bridge reads last cursor/sequence
bridge skips already-written idempotency keys
bridge continues
```

No bridge should be the only place where an important fact exists.

## Bridge Families

### 1. Reader Bridges

Purpose:

```text
read from one approved source
emit shaped facts
never write reports
never approve action
```

Examples:

```text
ForgeReaderBridge
EventLogReaderBridge
EmailHeaderReaderBridge
ChatMemoryReaderBridge
IncidentWindowReaderBridge
```

Input:

```text
source config
cursor
read request
```

Output:

```text
central_reader_bundle
```

Failure behavior:

```text
do not block writer
do not block sensors
return failed receipt/status
resume from cursor
```

### 2. Writer Bridges

Purpose:

```text
turn valid facts-only requests into operator-facing text reports
write receipt
never gather evidence
never approve action
```

Examples:

```text
CentralFactsWriterBridge
OperatorReportWriterBridge
```

Input:

```text
central_writer_request
central_model_writer_report_request
```

Output:

```text
securecore_facts_report
central_writer_receipt
central_writer_rejection
```

Failure behavior:

```text
invalid request creates no report
rejection can be written
receipt proves output or rejection
```

### 3. Sensor Bridges

Purpose:

```text
convert sensor observations into validated sensor events
```

Examples:

```text
ProcessDiffBridge
NetworkDiffBridge
WindowsEventLogBridge
TrueVisionStateBridge
AudioSoundstageBridge
HIDActivityBridge
```

Input:

```text
raw observation or metadata snapshot
previous snapshot/cursor
```

Output:

```text
sensor_event
```

Failure behavior:

```text
skip bad event
record failure status
do not kill other sensors
```

### 4. Sensor-To-Forge Bridges

Purpose:

```text
write validated sensor events into Forge/binary stores
```

Examples:

```text
SensorForgeSink
```

Input:

```text
validated sensor_event[]
destination
```

Output:

```text
Forge records
Forge verify status
```

Failure behavior:

```text
WAL recovery
index rebuild
source cursor remains
replay possible
```

### 5. Policy Adapter Bridges

Purpose:

```text
execute one adapter action only after Policy Gate approval
```

Examples:

```text
FirewallAdapterBridge
NotificationAdapterBridge
DevicePoolAdapterBridge
RemoteControlAdapterBridge
```

Input:

```text
action_request
policy_decision
approval proof
dry_run flag
```

Output:

```text
adapter_result
adapter_receipt
```

Failure behavior:

```text
fail closed
dry-run required for high-risk actions
no approval means no execution
```

### 6. Model Bridges

Purpose:

```text
connect approved OpenAI API sessions to read-only context and structured advisory output
```

Examples:

```text
OpenAIAdvisoryBridge
ModelSessionBridge
NoModelModeBridge
```

Input:

```text
reader bundle
model session status
approved prompt/context packet
```

Output:

```text
advisory interpretation
facts-only report request
```

Forbidden:

```text
tool calls
policy approval
runner execution
fact authority
direct writer mutation
```

Failure behavior:

```text
slow model rejected
fallback to no_model_mode
```

### 7. Agent Runner Bridges

Purpose:

```text
call approved executable agents with structured input/output
```

Examples:

```text
RustAgentRunnerBridge
CppAgentRunnerBridge
PythonAgentRunnerBridge
PowerShellAgentRunnerBridge
```

Input:

```text
validated agent manifest
structured request
timeout
dry_run flag
```

Output:

```text
agent_result
agent_log_ref
agent_receipt
```

Forbidden:

```text
prompt-only production agents
unbounded runtime
self-granted permissions
unstructured output as authority
```

Failure behavior:

```text
kill on timeout
capture stderr/stdout hashes
return failed receipt
do not affect other agents
```

### 8. UI/API Bridges

Purpose:

```text
move operator requests from local UI/API into backend routes
```

Examples:

```text
RustFrontdoorApiProxy
```

Input:

```text
HTTP request
session/auth token
```

Output:

```text
backend response
```

Forbidden:

```text
business logic
truth storage
policy bypass
fake runtime status
```

Failure behavior:

```text
backend unavailable message
UI remains local
other backend systems continue
```

## Recommended Module Layout

```text
securecore/
  central/
    contracts.py
    reader.py
    writer.py
    report_flow.py

  sensors/
    contracts.py
    windows_readers.py
    forge_sink.py
    truevision_state.py
    audio_state.py

  policy/
    contracts.py
    adapter_handoff.py

  tools/
    capabilities.py
    picker.py
    recipes.py

  openai_session.py

  live_agents/
    manifest.py
    runner/
      rust_runner.py
      cpp_runner.py
      python_runner.py
      powershell_runner.py
```

## Central Reader/Writer Flow

Do not build one big CentralBridge.

Use a tiny flow object:

```text
read facts
validate reader bundle
build writer request
write facts report
return receipt
```

Suggested file:

```text
securecore/central/report_flow.py
```

Allowed:

```text
call CentralReader
call CentralWriter
return receipt
```

Forbidden:

```text
query every system directly
own policy
own queues
own retries across subsystems
execute adapters
call agents
```

## Example: Email Alert Report Flow

```text
EmailHeaderBridge
  -> header diff
  -> EmailSentinelService sandbox
  -> CentralReader reads matched header facts
  -> CentralWriter writes facts report
  -> Policy/Notification bridge later decides whether to text user
```

No body download.
No HTML render.
No attachment fetch.
No direct user alert from email reader.

## Example: Suspicious Process Flow

```text
ProcessDiffBridge
  -> sensor_event
  -> SensorForgeSink
  -> Forge records
  -> Wake request if anomaly threshold crossed
  -> Agent investigation
  -> CentralReader bundle
  -> CentralWriter facts report
  -> Policy Gate if action is requested
```

If ProcessDiffBridge dies, Forge and existing process snapshots remain.
Other sensors continue.

## Example: Model-Assisted Report Flow

```text
CentralReader bundle
  -> OpenAIAdvisoryBridge uses an approved API-key session or no_model_mode
  -> model produces advisory language task only
  -> CentralWriter validates facts-only report request
  -> report + receipt
```

Model does not call tools.
Model does not approve actions.
Model does not own fact authority.
Model assistance interprets shaped data, explains system state, summarizes,
drafts, and helps build inside SecureCore only through approved sessions.
It is not a security authority and it does not mutate the system.

## Bridge Health Checklist

Each bridge should expose:

```text
bridge_id
last_seen_utc
last_cursor
last_sequence
last_success_utc
last_failure_utc
failure_count
last_error
pending_count if applicable
replay_supported
```

## Test Requirements

Every bridge needs tests for:

```text
valid input accepted
invalid input rejected
output shape validated
no forbidden authority
idempotency or duplicate skip
crash/restart cursor behavior
downstream unavailable behavior
no unrelated subsystem failure
```

## Final Architecture Law

```text
Readers gather.
Sensors observe.
Forge orders.
Models interpret.
Pickers choose capabilities.
Agents investigate.
Writer reports facts.
Policy approves action.
Adapters act.

Bridges move.
Bridges do not rule.
```
