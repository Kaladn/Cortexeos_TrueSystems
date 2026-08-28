# SecureCore TrueVision And AnchorWorks Package Completion Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish TrueVision SC Edition as an ops-safe logger lane and make SecureCore a callable support package for AnchorWorks.

**Architecture:** TrueVision is one sensor lane, not a brain. SecureCore loggers emit sensor events, Forge orders them, fusion compresses temporal state into binary blocks, retention turns clean time into receipts and suspicious time into cases, and AnchorWorks calls SecureCore through a narrow package API.

**Tech Stack:** Python package interfaces, Forge binary writer/reader, SecureCore sensor contracts, binary temporal fusion blocks, rolling retention, Central Writer report contracts, no UI work.

---

## Hard Laws

```text
AnchorWorks is the face.
SecureCore is the toolbox/logger/policy/agent backend.

Loggers witness.
Forge orders.
Fusion compresses.
Retention receipts clean time.
Anomalies become cases.
Agents interpret later.
Policy gates action.
Central Writer speaks.
```

```text
No raw frames by default.
No raw audio by default.
No detector authority.
No YOLO runtime.
No recognition authority.
No prompt-only agents.
No hidden mutation lanes.
No UI until backend package behavior is locked.
```

---

## Current Status

### Done Or Mostly Done

```text
Forge binary record substrate exists.
Sensor event base contract exists.
Process diff reader exists.
Network diff reader exists.
Windows Event Log collector exists.
Source registry exists.
SensorForgeSink exists.
Temporal fusion binary contract exists in securecore/sensors/fusion.py.
Fusion binary store exists in securecore/sensors/fusion_store.py.
Logging smoke creates Forge records and binary fusion blocks.
Rolling retention exists in securecore/retention/rolling.py.
TrueVision SC draft exists under securecore/truevision/.
POL draft exists under securecore/truevision/pol.py.
Tests currently pass at 196 OK after fusion/retention work.
```

### Needs Completion

```text
TrueVision real ops command.
TrueVision runtime config.
TrueVision participation in smoke path.
All-logger fusion proof including vision and HID/POL.
Retention proof with vision clean/anomaly windows.
SecureCore callable package API for AnchorWorks.
Central Writer facts-only reports for package calls.
Policy gate boundary for action requests.
AW adapter/client contract.
Packaging/import stability.
End-to-end no-agent ops test.
```

---

## File Ownership Map

### TrueVision Ops Lane

```text
securecore/truevision/contracts.py
  Owns compact TrueVision state-change payload validation.

securecore/truevision/live_capture.py
  Owns frame/state sampling and aspect-preserving grid hashing.

securecore/truevision/forge_adapter.py
  Converts TrueVision state records into SecureCore sensor events.

securecore/truevision/workers.py
  Owns explicit capture/classify/write step calls only.

securecore/truevision/pol.py
  Owns proof-of-life metadata sampling. Must remain content-free.

securecore/sensors/source_registry.py
  Declares TrueVision source mode and destination.
```

### Fusion And Retention

```text
securecore/sensors/fusion.py
  Canonical binary temporal fusion block contract.

securecore/sensors/fusion_store.py
  Binary append/read/verify store for fusion blocks.

securecore/sensors/smoke.py
  One-shot ops proof for loggers, Forge, fusion, and reports.

securecore/retention/rolling.py
  Rolling receipt/delete/preserve manager.
```

### AnchorWorks Package Boundary

```text
securecore/package_api/
  New package boundary for AW calls.

securecore/package_api/contracts.py
  Request/response dataclasses and validation.

securecore/package_api/service.py
  Callable service functions for AW.

securecore/package_api/reports.py
  Facts-only report shaping for Central Writer.

securecore/package_api/policy.py
  Package-level policy checks before any action request.

tests/package_api/
  Package boundary tests.
```

---

## Phase 1: TrueVision Ops Lock

Purpose: make TrueVision a boring logger lane.

- [ ] Add `securecore/truevision/config.py`.

Required contract:

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class TrueVisionRuntimeConfig:
    enabled: bool = False
    source_id: str = "gpu.pre_render"
    session_id: str = "securecore-local"
    grid_size: int = 32
    sample_interval_ms: int = 1000
    max_payload_bytes: int = 4096
    allow_camera: bool = False
    allow_raw_frames: bool = False
```

Tests:

```text
tests/truevision/test_config.py
- default config disabled
- raw frames false
- camera false
- payload limit enforced
```

Acceptance:

```text
TrueVision cannot run live unless enabled.
TrueVision cannot store raw frames.
TrueVision cannot enable camera by accident.
```

- [ ] Add `securecore/truevision/ops.py`.

Required function:

```python
def run_truevision_ops_once(*, forge_root, host_id, config, capture_backend) -> dict:
    ...
```

Required behavior:

```text
if disabled: return skipped report
if enabled: capture one state change
write sensor_vision through Forge
return count/summary only
```

Tests:

```text
disabled config writes nothing
enabled config writes one sensor_vision event
payload contains no frame/pixel/raw fields
Forge verifies
```

---

## Phase 2: All-Logger Fusion Proof

Purpose: prove every logger lane can participate in one binary fusion block.

- [ ] Extend `securecore/sensors/smoke.py` with optional synthetic HID and vision events.

Required options:

```python
include_hid: bool = False
include_vision: bool = False
hid_events: list[dict] | None = None
vision_events: list[dict] | None = None
```

Required behavior:

```text
process events write sensor_process
network events write sensor_network
eventlog events write sensor_eventlog
hid/POL events write sensor_hid
vision events write sensor_vision
fusion_source_counts includes every present lane
```

Tests:

```text
tests/sensors/test_smoke.py
- process/network/eventlog/HID/vision all count into fusion block
- source_counts include zeros for absent lanes
- fusion verify intact
```

Acceptance:

```text
One smoke run proves all active logger lanes can enter binary fusion.
No agents are launched.
No UI is touched.
```

---

## Phase 3: Retention With Vision

Purpose: prove TrueVision detail does not create permanent log hoarding.

- [ ] Extend `tests/retention/test_rolling_retention.py`.

Add cases:

```text
clean vision window -> health receipt + deletion receipt + detail deleted
vision anomaly flag -> forensic manifest + detail preserved
broken fusion verification -> no deletion
```

Required result:

```text
Clean visual state expires.
Suspicious visual state preserves the window.
Receipts survive deletion.
```

---

## Phase 4: SecureCore Package API For AnchorWorks

Purpose: make SecureCore callable without turning it into a UI or microservice mess.

- [ ] Create `securecore/package_api/__init__.py`.

- [ ] Create `securecore/package_api/contracts.py`.

Required objects:

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True, slots=True)
class SecureCoreRequest:
    request_id: str
    caller: str
    route: str
    purpose: str
    payload: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True, slots=True)
class SecureCoreResponse:
    request_id: str
    status: str
    facts: list[str]
    evidence_refs: list[str]
    warnings: list[str]
    action_required: bool = False
    approval_required: bool = False
```

Allowed routes first:

```text
status.summary
logs.health
fusion.latest
retention.close_window
report.text_facts
policy.check_action
```

Forbidden:

```text
direct firewall mutation
direct registry mutation
direct process kill
direct agent launch
direct model/tool execution
```

Tests:

```text
unknown route rejected
missing request_id rejected
AW caller allowed read-only routes
mutation route requires policy approval and returns approval_required
```

- [ ] Create `securecore/package_api/service.py`.

Required service:

```python
class SecureCorePackageService:
    def handle(self, request: SecureCoreRequest) -> SecureCoreResponse:
        ...
```

Initial implementation:

```text
status.summary -> return package status facts
logs.health -> return logger/fusion/retention status if roots exist
fusion.latest -> return latest fusion metadata only
report.text_facts -> shape facts-only report
unknown -> rejected
```

Tests:

```text
returns facts only
does not mutate Forge
does not launch agents
does not require UI/server
```

---

## Phase 5: Central Writer Bridge

Purpose: let AW ask SC for tight facts-only text without letting models become authority.

- [ ] Create `securecore/package_api/reports.py`.

Required function:

```python
def build_text_facts_report(*, title: str, facts: list[str], evidence_refs: list[str], warnings: list[str]) -> dict:
    ...
```

Rules:

```text
facts only
no speculation
no hidden inference
no first-person model voice
evidence refs required for non-empty facts
```

Tests:

```text
empty evidence with facts rejected
warnings allowed
report contains no action unless explicit approval route
```

---

## Phase 6: Policy Boundary

Purpose: guarantee callable package does not become a backdoor.

- [ ] Create `securecore/package_api/policy.py`.

Rules:

```text
read-only routes allowed for AW
report routes allowed for AW
action routes return approval_required
unknown caller rejected
unknown route rejected
unknown model id rejected
agent launch forbidden through package API
```

Tests:

```text
AW can ask fusion.latest
AW can ask report.text_facts
AW cannot launch agent
AW cannot mutate firewall
rogue caller rejected
```

---

## Phase 7: End-To-End Ops Proof

Purpose: one command proves SecureCore can serve AW as a backend package.

- [ ] Add `tests/package_api/test_aw_package_flow.py`.

Proof path:

```text
synthetic process/network/eventlog/HID/vision events
-> Forge writes
-> binary fusion block
-> retention close clean window
-> AW-style package request: logs.health
-> AW-style package request: report.text_facts
```

Expected:

```text
no agents launched
no UI dependency
no external network dependency
no raw content stored
facts-only response
fusion binary verifies
retention receipt exists
```

---

## Phase 8: Documentation Lock

Purpose: make future agents stop confusing AW and SC.

- [ ] Update `docs/security/SECURECORE_MASTER_TODO.md`.

Add:

```text
TrueVision ops lock status.
Fusion binary status.
Retention status.
SecureCore package API status.
AW/SC boundary law.
```

- [ ] Add `docs/security/SECURECORE_ANCHORWORKS_PACKAGE_CONTRACT.md`.

Must include:

```text
AW is the face.
SC is callable backend.
SC cannot mutate AW.
AW cannot bypass SC policy.
All SC responses are facts/warnings/evidence refs.
No UI dependency.
No prompt-agent authority.
```

---

## Final Verification

Run:

```powershell
python -m unittest tests.truevision.test_sc_edition tests.truevision.test_pol tests.sensors.test_fusion_block tests.sensors.test_smoke tests.retention.test_rolling_retention -q
python -m unittest discover -s tests -q
git status --short --branch
```

Expected:

```text
focused tests OK
full tests OK
no runtime/generated data staged
dirty tree only includes intentional code/docs/tests
```

---

## Finish Line Definition

SecureCore is a proper callable package for AnchorWorks when:

```text
TrueVision can run as a disabled-by-default logger lane.
All logger lanes can enter binary fusion.
Clean windows become tiny receipts and delete detail.
Suspicious windows preserve forensic manifests.
AW can call SC package functions without server/UI.
AW receives facts, warnings, and evidence refs only.
No SC route launches agents or mutates controls without policy approval.
All behavior is covered by tests.
```

