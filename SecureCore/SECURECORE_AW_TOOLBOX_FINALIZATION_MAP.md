# SecureCore As AnchorWorks Toolbox Finalization Map

- Created: 2026-05-16
- Scope: backend only
- UI status: parked until backend contracts and usage proof are stable

## Core Law

```text
AnchorWorks speaks.
SecureCore guards.
Communicast carries.
The user rules.
```

SecureCore is not the face. AnchorWorks remains the user-facing conductor and
rendering surface. SecureCore is the protected toolbox behind it: logging,
policy, agent execution, OpenAI-session model assistance, temporal investigation,
and safety services.

## Authority Split

```text
AnchorWorks:
  user-facing speech
  task framing
  rendering
  deterministic language/count route work

SecureCore:
  logging
  policy gates
  agent/tool capability registry
  temporal/causality checks
  Central Writer facts-only internal reports
  OpenAI-session model assistance under identity controls

Communicast:
  shaped receipts between systems
  no mutation authority
  no user-facing authority
  no hidden bridge behavior
```

## Communicast Boundary

Communicast messages are small shaped handoffs. They must include:

```text
schema_version
kind
message_id
created_at_utc
source_system
source_component
target_system
topic
authority
payload_schema
payload
evidence_refs
trace_refs
user_facing
```

Rules:

```text
Only AnchorWorks may publish anchorworks.face.rendered.
SecureCore may send toolbox results to AnchorWorks.
SecureCore support messages are not user-facing.
Every message needs evidence refs and trace refs.
No Communicast message authorizes enforcement.
No Communicast message mutates AnchorWorks.
```

## Current Usage Shape

```text
AnchorWorks task
-> needs protected support
-> SecureCore capability/toolbox route
-> SecureCore logs/checks/policy/agent result
-> Communicast shaped result
-> AnchorWorks decides how or whether to speak
```

SecureCore can also read AnchorWorks route pressure for internal support through
the route tap, but that does not replace AnchorWorks final speech.

## Tonight Lock

```text
No UI work.
No broad runtime rewrite.
No old system resurrection.
No god bridge.
No SecureCore face.
```

Allowed tonight:

```text
backend contracts
small usage proofs
logging health checks
route tap checks
Central Writer contract checks
Communicast validation
```

## Verification

Focused proof commands:

```powershell
python -m unittest tests.communicast.test_contracts -q
python -m unittest tests.route_tap.test_anchorworks_route_tap tests.route_tap.test_anchorworks_client -q
python -m unittest tests.central.test_contracts tests.central.test_writer_runtime -q
```

Expected:

```text
Communicast accepts AW face messages.
Communicast accepts SC toolbox messages targeting AW.
Communicast rejects SC claiming AW face authority.
Route tap ignores poisoned final speech and uses structured admitted paths.
Central Writer remains facts-only.
```

Tiny law:

```text
Support may inform the face.
Support may not become the face.
```
