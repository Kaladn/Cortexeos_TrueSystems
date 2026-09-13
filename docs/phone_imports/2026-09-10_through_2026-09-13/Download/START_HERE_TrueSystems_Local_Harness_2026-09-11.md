# START HERE — TrueSystems Local Harness Bootstrap
**Date:** 2026-09-11  
**Execution model:** Local Qwen 3.x (or equivalent local coding model)  
**Purpose:** Manual document-first execution when Codex is unavailable

---

## 0. Operator Contract

You are operating inside a live TrueSystems repository.

Do not assume the repository matches the design documents.

Do not rewrite working systems because a design document sounds newer.

Do not silently rename existing architecture.

Do not invent missing implementation.

Treat the repository as current implementation truth.

Treat the attached design documents as governing architectural intent only where they do not conflict with explicit accepted repository state.

If implementation and design conflict, report the conflict before changing anything.

---

## 1. Canonical Documents in This Packet

Read these completely before modifying code:

1. `TrueSystems_Provenance_Backplane_2026-09-11.md`
2. `provenance_backplane_schema_sketch_2026-09-11.json`
3. `TrueSystems_Cubic_Cluster_Investigation_2026-09-10.md`
4. `starlink_cubic_probe_2026-09-10.py`
5. `starlink_run_summary_2026-09-10.json`

The provenance-backplane document governs context recovery and code-relationship provenance.

The cubic-cluster document governs the experimental relationship substrate.

Do not collapse the two systems into one abstraction merely because they both use graphs.

---

## 2. Frozen Laws

### Provenance / recovery

- The graph carries addresses, not cargo.
- Raw source remains authority.
- Important relationships are first-class records.
- Provenance belongs on edges as well as nodes.
- Structural mutation and provenance mutation are one accepted transaction.
- Compaction must preserve recovery ability.
- Corrections and supersessions are preserved.
- Recovery is bounded and must return `INSUFFICIENT_PROVENANCE` when evidence cannot be recovered.
- Lost provenance is explicit: `PROVENANCE_LOST`.
- Bidirectional indexing is required:
  - GRAPH -> SOURCE
  - SOURCE -> GRAPH
- Recovery capsules are hints/checkpoints, not evidence.
- Relationship strength is not truth probability.

### Relationship / cubic investigation

- `6-1-6` is a linear probe, not a universal architecture.
- Frequency measures commonality, not significance.
- Frequency classifies role.
- Common values remain context/background.
- Less-common values may probe structure.
- Rare values still require relational and positional support.
- Co-occurrence establishes relational support.
- Position establishes direction / pressure.
- Repeated coordinates are occupancy, not fake neighbors.
- Parent summarizes; children prove.
- Barriers can exist on one relationship channel while another channel remains connected.
- Topology must be preserved (for example, azimuth is circular).
- Cubic/hypercubic promotion contains lower-dimensional relationships rather than erasing them.
- Commonality at one level may trigger descent into children: data-driven resolution selection.

Do not convert any of these into generic probability/confidence scoring.

---

## 3. First Job: Repository Introspection Only

### START 0

Inspect the repository completely enough to answer:

- What currently exists?
- What actually runs end-to-end?
- What code graph / dependency graph facilities already exist?
- What history/chat/provenance facilities already exist?
- What storage layer exists?
- What compaction/checkpoint machinery exists?
- What source identities already exist for code, chat, docs, tests, and artifacts?
- What parts of the attached designs already exist under different names?
- What tests protect current behavior?
- What current architectural authority boundaries exist?

### Do not edit code during START 0.

Create:

`docs/worklogs/local-harness-introspection-2026-09-11.md`

The report must classify each relevant capability as:

- `IMPLEMENTED`
- `PARTIAL`
- `NOT_IMPLEMENTED`
- `CONFLICTS_WITH_CURRENT_DESIGN`
- `UNKNOWN`

### STOP 0

Stop after writing the introspection report.

Do not continue into implementation until the operator reviews the report.

---

## 4. Second Job: Minimal Provenance Backplane Plan

Only after operator approval of STOP 0.

### START 1

Design the smallest implementation that fits the live repository.

Minimum logical objects:

```text
Relationship
ContextRecoveryRecord
RecoveryCapsule
SourceRef
ChatRef
CodeRef
DocRef
TestRef
ArtifactRef
EvidenceBundle
DecisionLineage
```

Do not force all of these into separate classes/tables if existing repository structure already provides a cleaner representation.

Required indexes:

```text
relationship_id -> refs
source_ref -> relationship_ids
conversation_id + message_id -> relationship_ids
code_symbol_id -> relationship_ids
decision_id -> relationship_ids
test_id -> relationship_ids
```

Required relationship lifecycle:

```text
ACTIVE
DISPUTED
SUPERSEDED
DEPRECATED
PROVENANCE_LOST
```

Required recovery outcomes:

```text
RECOVERED
CAPSULE_SUFFICIENT
INSUFFICIENT_PROVENANCE
PROVENANCE_LOST
ACCESS_DENIED
STALE_REFERENCE
```

Create a design report only.

### STOP 1

Do not implement until reviewed.

---

## 5. Third Job: Provenance MVP

Only after approval.

### START 2

Implement the smallest vertical slice:

1. Reify one important relationship as a stable record.
2. Attach one stable code source ref.
3. Attach one chat/doc source ref if available.
4. Create a recovery capsule.
5. Implement `rehydrate(relationship_id, need)`.
6. Dereference exact source + local context.
7. Return citations/coordinates.
8. Return `INSUFFICIENT_PROVENANCE` rather than guessing.
9. Add one SOURCE -> GRAPH reverse lookup.
10. Add tests.

For code refs, prefer:

```text
repository identity
commit/tree identity
file identity
symbol identity
AST or structural fingerprint
local content hash
line range only as convenience
```

### STOP 2

Write test results and exact changed files.

---

## 6. Fourth Job: Compaction Survival

### START 3

Add durable serialization of:

- relationship IDs
- graph endpoints and type
- lifecycle state
- authority state
- recovery capsule
- source pointers
- source hashes
- correction/supersession lineage
- EvidenceBundle
- bidirectional indexes

The survival store must exist outside the model's active context.

After a simulated compaction:

1. reload only the lightweight checkpoint;
2. touch a protected relationship;
3. trigger deterministic rehydration;
4. recover original rationale/source;
5. prove the rejected/superseded version is not restored as current.

### STOP 3

Provide replay evidence.

---

## 7. Fifth Job: Transactional Provenance

### START 4

For protected relationships:

```text
BEGIN MUTATION

code/graph mutation
relationship mutation
provenance mutation
EvidenceBundle mutation
index mutation
integrity validation
commit

END MUTATION
```

If provenance persistence fails, the protected structural mutation must not silently become accepted state.

Test crash/failure boundaries.

### STOP 4

Report pass/fail.

---

## 8. Cubic / Relationship Substrate Work

Do not begin this merely because the packet contains the experiment.

First identify whether the live repository has an appropriate relationship-analysis surface.

When authorized, use the Starlink prototype as an empirical reference only.

Do not freeze its provisional frequency estimator.

Frozen rule:

> Each parent establishes its own frequency structure; commonality classification is parent-local and distribution-derived.

The current mean-occupancy estimator is an experiment.

The system should preserve:

```text
parent identity
child source identity
raw counts
co-occurrence counts
signed source position
positional pressure
topology
barriers
occupancy
independent relationship channels
```

No single scalar may replace these measurements.

---

## 9. Context Discipline

The local model must not rely on its own conversational memory as project authority.

When a relationship is important:

1. inspect the recovery capsule;
2. dereference its source if needed;
3. read exact local evidence;
4. follow correction/supersession links;
5. act on the surviving interpretation.

When uncertain, recover evidence.

When evidence is missing, say so.

Do not improvise project history.

---

## 10. Drift Guard

Classify incoming operator instructions against current frozen state:

```text
CONSISTENT
CLARIFICATION_ONLY
DEFERRED_IDEA
SCOPE_EXPANSION
METHOD_CONFLICT
AUTHORITY_CONFLICT
EXPERIMENT_INVALIDATION_RISK
EXPLICIT_SUPERSESSION_REQUIRED
```

Exploratory language is not authorization to mutate architecture.

Corrections do not silently erase history.

Supersessions must be explicit.

---

## 11. Worklog / Checkpoint Rules

For every stage:

- write a concise worklog;
- record exact files touched;
- record tests executed;
- record failures;
- record unresolved questions;
- record any conflict with frozen laws;
- stop at the requested STOP marker.

Do not consume a giant prompt and then reconstruct history from memory.

Use the worklog as accumulated execution state.

---

## 12. Completion Standard

A stage is complete only when:

- implementation matches the approved stage;
- tests pass or failures are explicitly reported;
- provenance for protected structural changes exists;
- worklog is current;
- repository state is resumable;
- no unapproved architectural expansion occurred.

The objective is not maximum code output.

The objective is deterministic, auditable continuity.
