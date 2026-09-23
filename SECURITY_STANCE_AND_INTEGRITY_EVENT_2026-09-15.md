# TrueSystems security stance and integrity-boundary report

**Date:** 2026-09-15 (America/New_York)  
**Repository:** `/home/lamercey/TrueSystems-Alignment`  
**Branch:** `alignment/truecore-boundary`  
**HEAD:** `35073c5850e6954e4a15cbc2e089a6ed30294980`  
**Inspection mode:** read-only source, history, and external acceptance-receipt review

## Executive result

The current stance is **strong at integrity and execution admission, incomplete
at runtime reachability and actor attribution, and not a production security
certification**.

The working safety property is:

```text
host-admitted setup
  -> exact resource identity
  -> expected SHA-256
  -> manifest/entrypoint/source validation
  -> bounded worker execution
```

If the setup, source, executable, map manifest, or approved plan changes after
admission, the operation is refused before the worker is run. Authorization does
not override a stale or mismatched integrity binding.

The repository-integrity response is:

```text
trusted snapshot
  -> verify manifest, blobs, bytes, modes, additions, removals
  -> pinpoint differences
  -> SAFE_MODE_REQUIRED
  -> quarantine observed suspect copies
  -> reconstruct a read-only safe tree from trusted blobs
  -> never overwrite suspect source
```

This protected the system from running a tampered setup in the tested scenarios.
It does **not** prove who changed a real production file. Actor identity remains
unresolved unless a separate operating-system audit event is captured and bound
to the incident.

## What was actually demonstrated

### Controlled changed-file fixture

The external integrity test creates a temporary fixture repository and changes
one glyph in `engine.py`, from `owner = 'Alice'` to `owner = 'Alicf'`. The trusted
snapshot then reports `SAFE_MODE_REQUIRED`, one changed logical path, UTF-8
line/column coordinates, baseline glyph `e`, observed glyph `f`, and
`UNRESOLVED_NO_OS_AUDIT_WITNESS` for the actor.

The suspect source remains unchanged in quarantine. The trusted safe tree contains
the original `Alice` file and is read-only.

Source: [test_repository_integrity_snapshot.py](/home/lamercey/Documents/User%20System%20Test/repositories/TrueSystems-Alignment/tests/test_repository_integrity_snapshot.py:47)

This is an isolated acceptance fixture, not proof that a real production file
was changed by an attacker or by Codex.

### Tampered setup rejected before execution

The worker-bridge acceptance test replaces the host-bound map manifest hash with
an incorrect value. Constructing `OperatorBoundary` fails with
`STALE_OR_CHANGED_RESOURCE` before any worker invocation.

Source: [test_registered_worker_bridge.py](/home/lamercey/Documents/User%20System%20Test/repositories/TrueSystems-Alignment/tests/test_registered_worker_bridge.py:143)

The same boundary rejects model-supplied paths, commands, modules, ungranted
workers, unknown resources, and arguments outside the registered schema.

This is the direct safety mechanism: the caller may be authorized to request a
worker, but the requested resource no longer matches the host-admitted bytes, so
execution never begins.

## Integrity controls in force

### Repository snapshot custody

`TrueMachine/src/truemachine/repository_integrity.py` creates content-addressed
snapshots of a clean Git repository and explicitly selected external views. Each
entry records a logical path, source class, byte size, SHA-256, file mode, and
repository commit. Trusted blobs are stored under their digest names.

Symlinks, dirty repositories, invalid external views, invalid snapshot names,
blob collisions, and copy-hash mismatches are rejected.

Source: [repository_integrity.py](/home/lamercey/TrueSystems-Alignment/TrueMachine/src/truemachine/repository_integrity.py:43)

### Verification and safe mode

Verification checks the manifest digest, snapshot identity, every trusted blob,
live source paths, additions, missing files, content changes, and mode changes.
Text changes are pinpointed by line/column; binary changes use byte coordinates.

On mismatch the result is `SAFE_MODE_REQUIRED`; the verifier does not restore or
overwrite live source automatically.

Source: [repository_integrity.py](/home/lamercey/TrueSystems-Alignment/TrueMachine/src/truemachine/repository_integrity.py:167)

The incident builder copies modified or added observed files to quarantine and
reconstructs the trusted safe tree from snapshot blobs with write permission
removed. It records `suspect_source_overwritten: false`.

Source: [repository_integrity.py](/home/lamercey/TrueSystems-Alignment/TrueMachine/src/truemachine/repository_integrity.py:326)

### Host-bound integrity worker

The read-only `integrity.verify` worker cannot choose an arbitrary snapshot. The
host binds the resource kind, canonical path, allowed worker, entry/file/total
byte budgets, timeout, and manifest SHA-256.

The bridge rejects changed manifest or inode/device identity, symlinks, missing
resources, wrong workers, and ungranted workers before invocation.

Sources:

- [machine_navigation_bridge.py](/home/lamercey/TrueSystems-Alignment/TrueCore/truecore/machine_navigation_bridge.py:130)
- [machine_navigation_bridge.py](/home/lamercey/TrueSystems-Alignment/TrueCore/truecore/machine_navigation_bridge.py:149)
- [machine_navigation_bridge.py](/home/lamercey/TrueSystems-Alignment/TrueCore/truecore/machine_navigation_bridge.py:179)

### Agent and plan binding

Live-agent manifests require an exact entrypoint hash, runtime language, read and
write declarations, approval requirements, result schema, risk tier, and test
command. Read-only agents cannot declare writes.

Source: [manifest.py](/home/lamercey/TrueSystems-Alignment/TrueCore/truecore/live_agents/manifest.py:19)

Bounded jobs additionally bind implementation source hashes and an approved plan
hash. A changed implementation returns `WORKER_IMPLEMENTATION_CHANGED` before
the worker process starts.

Source: [bounded_jobs.py](/home/lamercey/TrueSystems-Alignment/TrueCore/truecore/bounded_jobs.py:83)

Registered repository workers hash the manifest before and after execution and
reject changed manifests or result-binding mismatches.

Source: [registered_worker_bridge.py](/home/lamercey/TrueSystems-Alignment/TrueCore/truecore/registered_worker_bridge.py:167)

### Bounded process controls

The bounded-job path enforces exact plan and implementation hashes, approval
identity, step/dependency limits, output-root identity, timeout and output-byte
budgets, process-group termination on overflow, incident output on failure, and
terminal receipt inspection before replay.

Source: [bounded_jobs.py](/home/lamercey/TrueSystems-Alignment/TrueCore/truecore/bounded_jobs.py:91)

## Acceptance evidence

The final integrity acceptance log records four passing tests: missing/added/
external-view changes are distinct; manifest tampering fails closed; mode and
budgets are enforced; and one-glyph changes are pinpointed while the safe tree
preserves the baseline.

The final boundary regression also records passing checks for changed executable
hashes, changed map manifests, model path/command/module rejection, symlink and
path-traversal rejection, common worker-result validation, preserved
`NOT_IMPLEMENTED` authority gaps, no model-weight loading, and no capture/action.

Artifacts:

- [Integrity acceptance](/home/lamercey/Documents/User%20System%20Test/repositories/TrueSystems-Alignment/output/repository-integrity-acceptance-20260914T103026Z.log)
- [Full boundary regression](/home/lamercey/Documents/User%20System%20Test/repositories/TrueSystems-Alignment/output/full-integrity-and-boundary-regression-20260914T103616Z.log)
- [Security investigation](/home/lamercey/Documents/User%20System%20Test/repositories/TrueSystems-Alignment/output/repository-security-investigation-release-20260914T110000Z/REPORT.md)

Two earlier failures remain preserved in the external history: a missing-file
fixture initially raised `FileNotFoundError`, and an intermediate source
extraction made an agent usage hash stale. The corrected final regression passed.
Neither failure was hidden or converted into a false success.

## Security stance

Verified strengths:

- exact-byte, manifest, blob, and file-mode integrity checks;
- deterministic source-difference pinpointing;
- quarantine without suspect-source overwrite;
- trusted read-only safe-tree reconstruction;
- host-bound read-only integrity verification;
- manifest and entrypoint hash binding;
- refusal before execution when setup identity changes;
- model cannot supply paths, commands, modules, roots, grants, or budgets;
- bounded process time and output;
- common worker-result validation and receipts;
- explicit preservation of `NOT_IMPLEMENTED` graph authority.

Not yet proven or not safe to promote:

- which process/person caused a real file change;
- full OS-audit actor attribution;
- full control-flow/data-flow reachability;
- permission dominance over every privileged sink;
- Rust/native TrueComputer, TrueCore frontdoor, and TrueVision paths;
- production sandboxing of arbitrary agent processes;
- production safety of the legacy control API;
- obsolete question-shaped TrueMem compatibility surfaces;
- cryptographic authenticity against an attacker who can rewrite both a vault
  and its independently stored hash;
- automatic restoration of live source.

## What “full auth” means

Full user or Codex authorization is not an integrity bypass. The effective gate
is conjunctive:

```text
authorization
AND host-bound resource identity
AND expected content hash
AND valid manifest/plan
AND valid operation parameters
AND bounded execution contract
```

If one term fails, execution stops. This is why legitimate authority cannot
accidentally run a modified setup merely because it still has permission to run
the operation.

## Attribution boundary

Hash comparison proves which bytes or modes changed. It does not prove which
process wrote them. File owner and modification time are observations, not
offender proof. The correct status remains
`UNRESOLVED_NO_OS_AUDIT_WITNESS` until a separate OS audit event is captured and
bound to the integrity incident.

## Current risk posture and next work

There is no evidence from this inspection of an active exposed service or a
successful execution of a tampered setup. The larger remaining risk is that an
operator could ignore `NOT_IMPLEMENTED` graph authority, dormant direct routes,
or unqualified native surfaces and mistake static evidence for a clean bill of
health.

Next security work:

1. Preserve final snapshots and receipts.
2. Add OS-audit capture for actor attribution.
3. Keep the legacy control API disabled until it routes through TrueCore.
4. Keep question-shaped TrueMem surfaces out of the authoritative interface.
5. Add Rust/native structural mapping.
6. Add witnessed control/data-flow and permission-dominance relationships.
7. Qualify a real sandbox before accepting arbitrary agent code.

## Bottom line

The demonstrated safety sequence is:

```text
setup changed
  -> hash or manifest mismatch
  -> reject before worker execution
  -> preserve evidence of the suspect state
  -> enter safe mode when a trusted snapshot differs
  -> continue only from a verified safe tree or reviewed state
```

The defensible claim is narrow and strong: **a changed, unadmitted setup was not
allowed to run through the tested TrueCore/TrueMachine boundary.** The repository
does not yet support the broader claim that every runtime path is secure or that
the actor behind a real file change is automatically identified.
