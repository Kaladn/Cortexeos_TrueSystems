# Bounded Operation Requirements and Protection Plan

Status: required next implementation contract; placeholders only

## Purpose

Every callable TrueSystems operation must teach an authorized caller exactly
which caller-owned values it accepts. A model, human interface, or future agent
must not be expected to remember hidden call syntax, and the system must not
guess missing values or disclose host-owned authority controls.

This document does not claim that the correction packet or final protective
service is implemented. The current boundary commonly returns generic rejection
codes such as `INVALID_ARGUMENTS`; those are insufficient for this contract.

## Proposed deterministic response

The planned response schema is `truecore.operation_requirements@1`. A valid
operation with an incomplete or invalid caller contract returns one of:

```text
REQUIREMENTS_MISSING
INVALID_ARGUMENTS
UNKNOWN_ARGUMENTS
FORBIDDEN_ARGUMENTS
UNAUTHORIZED_OPERATION
UNKNOWN_OPERATION
```

Only the first four are correction packets for a known operation. Authorization
failure must not be disguised as missing input, and an unknown operation must
not expose a neighboring operation's schema.

Each eligible correction packet contains:

```yaml
schema: truecore.operation_requirements@1
status: REQUIREMENTS_MISSING
operation: process.inspect
required:
  pid:
    supplied_state: MISSING
    type: integer
    minimum: 1
optional:
  include_children:
    type: boolean
    deterministic_default: false
invalid: {}
unknown: []
forbidden: []
retryable: true
```

For every field the response may state its type, bounds, enum, format,
cross-field constraints, and a deterministic default declared by code. It must
not supply an inferred value.

## Host-owned fields never become caller inputs

The correction packet must not advertise, request, or accept host-owned values,
including:

- filesystem or dataset roots;
- credentials, secrets, and authority state;
- grants, approval objects, and executable bindings;
- budgets, resource assignments, and protected target resolution;
- canonical manifest identities selected by policy;
- internal routing or implementation module names.

The host may bind those values internally. Their absence is a host prerequisite
or authorization failure, not a prompt asking the model to invent them.

## Read-only out-of-bounds law

An operation is in bounds only when its registered operation identity, caller
schema, host binding, authority grant, resolved target, budgets, and—where
required—single-use approval all match.

Anything outside that complete boundary is read-only at most. If no qualified
read operation exists, it is refused. The system must not convert an incomplete
mutation request into a broad inspection or a nearby mutation.

Protected classes include:

- source repositories and the full runtime/supporting code set;
- admitted, canonical, frozen, or evaluation datasets;
- manifests, immutable receipts, policy, grants, approvals, and authority
  configuration;
- qualified external graph views and recovery snapshots once admitted into the
  governing state.

Generic agents and graph tools may locate, hash, compare, and report these
objects through qualified read-only operations. They may not modify them.

## Future secured mutation routing placeholder

Before the final seal, every authorized update to protected code or data must be
routed through one qualified protective service owned and admitted by TrueCore.
The service does not yet exist. Its required contract is:

```text
registered mutation intent
-> resolve exact protected target
-> verify current qualified identity
-> bind single-use authority and approval
-> preserve pre-state and suspect bytes
-> perform the smallest authorized change
-> localize and verify the post-state
-> issue one bounded-run receipt
-> requalify affected paths
```

Unmatched drift must fail closed into safe/secure mode. Quarantine is a
non-destructive preserved copy, not silent deletion or overwrite. Offender
identity may be reported only from witnessed audit/runtime lineage; otherwise
the result must state the furthest provable causal boundary.

These are placeholders for later code, schemas, workers, and tests. Future work
must route to them once qualified; documentation alone must never simulate the
service.

## Receipt policy

- Ephemeral debug telemetry may be discarded after a bounded run is resolved.
- One durable bounded-run receipt summarizes requested operation, bindings,
  result, verification, and recovery state.
- A separate incident receipt is retained only for a meaningful denial,
  corruption, drift, partial failure, security event, or recovery.
- Event spam and repeated equivalent receipts must not become architectural
  authority.

## Required external acceptance

The implementation is incomplete until external tests prove:

1. missing required argument;
2. misnamed and unknown arguments;
3. invalid type, format, enum, and range;
4. forbidden caller variable;
5. deterministic default declared by code;
6. unauthorized versus unknown operation;
7. retry after corrected caller arguments;
8. host-owned fields never appear as caller-suppliable inputs;
9. out-of-bounds mutation cannot alter protected code or datasets;
10. changed protected identity invalidates the request before mutation;
11. partial failure preserves pre-state and issues an incident receipt;
12. correction packets and help are generated from the same callable schema.

## Naming gate

The final name of the temporal/sensory/security observation role must be settled
before schemas, worker identities, safe-mode events, manifests, and the final
seal are frozen. Current `TrueCog` and `CompuCog` wording is provisional lineage
and owner-facing terminology. Rename only after a complete witnessed impact map
and explicit owner approval.

