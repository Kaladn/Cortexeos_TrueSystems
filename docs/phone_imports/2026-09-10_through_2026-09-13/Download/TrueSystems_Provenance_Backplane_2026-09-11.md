# TrueSystems Provenance Backplane and Deterministic Context Recovery
**Date:** 2026-09-11  
**Status:** Design specification / pre-implementation  
**Scope:** Codebase graph provenance, compaction survival, selective context rehydration, architecture archaeology  
**Integrates:** AWRAG address-first dereference model, code graph, chat history, documents, tests, artifacts

---

## 1. Executive Summary

A code graph without provenance can preserve structure while losing intent.

It may remember:

```text
SecureCore --AUTHORIZES--> OperatorControl --SELECTS--> BoundedTool
```

but after a long execution run and context compaction it may no longer remember:

- why `AUTHORIZES` exists;
- why `SELECTS` means what it means;
- who accepted the boundary;
- which earlier design was rejected;
- which correction changed the interpretation;
- which tests currently justify the relationship;
- whether the relationship has since been superseded.

TrueSystems should therefore treat the codebase graph as an **index of claims and relationships**, not as a replacement for source evidence.

The architecture is:

```text
SOURCE STORE
chat / docs / code / tests / artifacts
        │
        ▼
PROVENANCE INDEX
stable addresses + hashes + role metadata
        │
        ▼
RELATIONSHIP GRAPH
nodes + first-class relationship records
        │
        ▼
CONTEXT RECOVERY RECORDS
recovery capsule + source refs + justification state
        │
        ▼
COMPACTION / CHECKPOINT
keep structure and addresses, drop bulky context
        │
        ▼
SELECTIVE REHYDRATION
dereference only what is needed
```

The governing idea is simple:

> **The graph carries the address. The source carries the cargo.**

Compaction should therefore stop being a destructive summary event and become a **pointer-preserving state checkpoint**.

---

## 2. Core Architectural Separation

The system must keep four things distinct:

```text
Evidence
    raw chat, code, docs, tests, artifacts

Provenance
    stable coordinates pointing to evidence

Relationships
    structural and intentional claims derived from evidence

Recovery
    bounded reconstruction of needed context from those coordinates
```

The graph is not evidence.

The capsule is not authority.

The provenance pointer is not the source.

The raw source remains the authority that can be opened and inspected.

---

## 3. Why Relationships Must Be First-Class Records

A relationship must not be only a lightweight edge property.

It needs its own identity and lifecycle because the relationship itself can acquire:

- design decisions;
- corrections;
- contradictions;
- test evidence;
- authority;
- supersessions;
- deprecation;
- recovery history.

Example:

```text
SecureCore
    -- CONTROLS -->
OperatorExecution
```

should be represented as a relationship record:

```yaml
Relationship:
  id: REL_004817
  from: securecore.authorization
  to: operator.execution
  type: CONTROLS

  status: ACTIVE
  authority: OWNER_ACCEPTED

  capsule:
    summary: "SecureCore selects abilities; operator models do not own execution authority."
    source_count: 5
    superseded_by: null

  provenance_refs:
    - REF_CHAT_0184
    - REF_CHAT_0221
    - REF_CODE_0042
    - REF_DOC_0017
    - REF_TEST_0031

  evidence_bundle_id: EB_004817
  recovery_priority: HIGH
```

This gives the edge an auditable identity independent of how the graph engine stores edges internally.

---

## 4. Frozen Laws

These are the architectural invariants to preserve unless explicitly superseded.

### 4.1 Address, not cargo

The graph stores compact source addresses, not copied chat transcripts, code bodies, or documents.

### 4.2 Raw source remains authority

A graph edge, capsule, extraction, or summary cannot outrank the original source that can be dereferenced.

### 4.3 Relationship is first-class

Every important graph relationship has a stable relationship ID and lifecycle.

### 4.4 Provenance belongs on edges as well as nodes

Nodes answer what exists.  
Edges answer how things interact.  
Edge provenance answers why the interaction exists.

### 4.5 Structural mutation and provenance mutation are one transaction

A code or graph change is incomplete until its provenance mutation is committed.

```text
code/graph mutation
      ↓
relationship mutation
      ↓
provenance mutation
      ↓
commit accepted
```

A crash must not leave a new structural fact without an intentional-history trail.

### 4.6 Compaction preserves recovery ability

Compaction may discard bulky source text from working context, but must preserve enough structure to recover it deterministically.

### 4.7 Supersession is preserved, not erased

Old decisions remain historically addressable even when they are no longer current.

### 4.8 Recovery is bounded and honest

If required provenance cannot be recovered within the allowed walk, return:

```text
INSUFFICIENT_PROVENANCE
```

Do not reconstruct missing rationale from model guesswork.

### 4.9 Lost provenance is explicit

If an edge survives while its source trail cannot, mark:

```text
PROVENANCE_LOST
```

Such an edge cannot silently behave as fully justified authority.

### 4.10 Bidirectional indexing is mandatory

The system supports:

```text
GRAPH -> SOURCE
```

and:

```text
SOURCE -> GRAPH
```

### 4.11 Capsules are recovery hints, not truth

A recovery capsule is a compact checkpoint. It helps decide whether deeper dereference is needed, but never replaces its sources.

### 4.12 Relationship strength is not truth probability

Do not introduce a generic `confidence = 0.92` field that pretends to represent truth.

Where automation requires uncertainty metadata, use narrowly scoped fields such as:

```text
extraction_confidence
role_classification_confidence
ref_alignment_confidence
```

These describe the extractor, not the truth of the relationship.

---

## 5. Source Reference Model

All source references should share a common envelope:

```yaml
SourceRef:
  ref_id: REF_...
  type: CHAT | CODE | DOCUMENT | TEST | ARTIFACT

  source_identity: ...
  content_hash: ...
  role: ...

  created_at: ...
  indexed_at: ...

  access_policy: ...
  ref_state: VALID | STALE | BROKEN | PROVENANCE_LOST
```

Type-specific fields extend the envelope.

---

## 6. ChatRef

Chat references need enough information for precise local dereference.

```yaml
ChatRef:
  ref_id: REF_CHAT_0184

  conversation_id: CHAT_2026_09_08
  message_id: MSG_0184
  timestamp: 2026-09-08T...
  title: SecureCore operator controls

  exact_start: ...
  exact_end: ...

  content_hash: ...

  parent_message_id: ...
  previous_message_id: ...
  next_message_id: ...

  relationship_role: DESIGN_DECISION

  extraction_confidence: ...
  access_policy: ...
```

The chat role is critical because not all historical text has equal meaning.

---

## 7. Relationship Role Taxonomy

Initial role vocabulary:

| Role | Recovery meaning |
|---|---|
| `LAW` | Governing constraint; must not be silently violated. |
| `DESIGN_DECISION` | Accepted architectural choice and rationale. |
| `IMPLEMENTATION` | Discussion directly tied to implementation behavior. |
| `CORRECTION` | Explains why an earlier interpretation or approach was wrong. |
| `REJECTION` | Records an intentionally abandoned path. |
| `SUPERSESSION` | Replaces a prior decision or relationship. |
| `TEST_RESULT` | Empirical evidence about behavior. |
| `EXPLORATION` | Non-authoritative thinking; lowest default recovery priority. |

Additional role tags may be introduced, but role meaning must stay explicit.

A single source span may support more than one relationship, but its role is evaluated per relationship.

---

## 8. Stable Code References

Raw line numbers are convenient but not stable enough for long-lived provenance.

A code reference should prefer:

```text
repository identity
commit / tree identity
file identity
symbol identity
AST identity or structural signature
local structural hash
line range as convenience
```

Example:

```yaml
CodeRef:
  ref_id: REF_CODE_0042

  repository: TrueSystems
  commit: abc123...
  file: securecore/auth.py

  symbol: SecureCore.authorize_operation
  symbol_signature: "authorize_operation(request, actor, contract)"
  ast_fingerprint: ...
  local_structural_hash: ...

  lines_at_capture: 142-217
  content_hash: ...

  relationship_role: IMPLEMENTATION
```

If lines move but the symbol survives, the provenance pointer can be re-anchored.

If the symbol changes materially, the reference can become:

```text
STALE
```

until validated.

---

## 9. Document, Test, and Artifact References

### 9.1 DocRef

```yaml
DocRef:
  document_id: ...
  section_id: ...
  heading_path: [...]
  exact_span: ...
  content_hash: ...
  role: LAW | DESIGN_DECISION | CORRECTION | ...
```

### 9.2 TestRef

```yaml
TestRef:
  repository: ...
  file: ...
  test_id: ...
  commit: ...
  outcome_at_capture: PASS | FAIL
  output_hash: ...
  role: TEST_RESULT
```

### 9.3 ArtifactRef

Used for generated reports, benchmark packets, images, data outputs, or other non-code evidence.

---

## 10. Context Recovery Record

The `ContextRecoveryRecord` is the relationship-facing recovery object.

```yaml
ContextRecoveryRecord:
  relationship_id: REL_004817

  graph_from: securecore.authorization
  graph_to: operator.execution
  relation_type: CONTROLS

  status: ACTIVE
  authority: OWNER_ACCEPTED

  capsule:
    summary: "SecureCore selects abilities; operator models do not own execution authority."
    critical_constraints:
      - "Operator cannot acquire execution authority by inference."
    source_counts:
      chat: 3
      code: 2
      document: 1
      test: 4
    superseded_by: null

  provenance_refs:
    - REF_CHAT_0184
    - REF_CHAT_0221
    - REF_CODE_0042
    - REF_DOC_0017
    - REF_TEST_0031

  evidence_bundle_id: EB_004817

  recovery_priority: HIGH
  last_validated: ...
```

---

## 11. EvidenceBundle / Justification State

A relationship should preserve disagreement rather than collapsing it.

```yaml
EvidenceBundle:
  id: EB_004817
  relationship_id: REL_004817

  supporting_refs:
    - REF_CHAT_0184
    - REF_DOC_0017
    - REF_CODE_0042
    - REF_TEST_0031

  contradicting_refs:
    - REF_CHAT_0221

  correction_refs:
    - REF_CHAT_0245

  supersession_refs: []

  resolution:
    state: RESOLVED
    current_relationship: REL_004817
    resolution_ref: REF_CHAT_0245

  validation:
    method: OWNER_ACCEPTED_PLUS_TEST
    last_validated: ...
```

This is not a confidence score.

It is a structured record of:

- what supports the relationship;
- what contradicts it;
- what corrected it;
- what superseded it;
- how the current state was resolved.

Suggested relationship lifecycle states:

```text
ACTIVE
DISPUTED
SUPERSEDED
DEPRECATED
PROVENANCE_LOST
```

The graph can therefore preserve disagreement without losing the current surviving interpretation.

---

## 12. Decision Lineage

Design history should remain explicit:

```text
Decision
    ↓
Correction
    ↓
Correction
    ↓
Supersession
```

Example:

```text
D1
"Operator owns execution authority."

D2 CORRECTION
"Execution authority belongs to SecureCore."

D3 SUPERSESSION
"SecureCore delegates bounded execution through ExecutionContract."
```

Recovery should resolve toward the current surviving relationship while retaining the old decisions for archaeology.

Old does not mean deleted.

Historical does not mean current.

---

## 13. Recovery Capsule

The capsule is deliberately tiny.

Example:

```yaml
capsule:
  relationship_id: REL_004817
  summary: "SecureCore owns authority; execution occurs only through bounded contracts."
  authority: OWNER_ACCEPTED
  status: ACTIVE

  source_count: 8
  important_roles:
    - LAW
    - DESIGN_DECISION
    - CORRECTION
    - TEST_RESULT

  superseded_by: null
  recovery_priority: HIGH
```

The capsule exists to answer:

> Do I already know enough to proceed safely?

If yes, the system can continue.

If no, it dereferences.

---

## 14. Deterministic Rehydration Triggers

Recovery must not depend solely on the model noticing that it is uncertain.

Recommended triggers include:

1. A relationship is touched for the first time after compaction.
2. The relationship carries `CORRECTION`.
3. The relationship carries `SUPERSESSION`.
4. The relationship is an authority or security boundary.
5. A proposed mutation conflicts with the capsule.
6. A relevant test fails.
7. A relationship is `DISPUTED`.
8. A relationship is `STALE`.
9. A source hash no longer matches.
10. A requested change crosses a protected graph boundary.
11. The model explicitly requests deeper rationale.
12. The current task requires a role not represented in the active capsule.

Model uncertainty may trigger recovery too, but it is not the only trigger.

---

## 15. Rehydration Algorithm

```python
def rehydrate(rel_id, need, budget):
    rel = load_relationship(rel_id)
    crr = load_context_recovery_record(rel_id)

    if crr.status == "PROVENANCE_LOST":
        return INSUFFICIENT_PROVENANCE

    if capsule_satisfies(crr.capsule, need):
        return capsule_answer(crr.capsule)

    refs = rank_refs(
        crr.provenance_refs,
        need=need,
        preferred_roles=required_roles(need),
        relationship_status=crr.status,
        recovery_priority=crr.recovery_priority,
    )

    context_pack = []

    for ref in refs:
        material = dereference(ref)

        if ref.type == "CHAT":
            material = exact_span_plus_local_context(
                ref,
                previous=True,
                following=True,
            )

        context_pack.append(material)

        if requirement_satisfied(context_pack, need):
            return cited_context_pack(context_pack)

        if budget_exhausted(context_pack, budget):
            break

    # bounded expansion
    for anchor in related_recovery_anchors(refs):
        material = bounded_walk(anchor, need, budget)
        context_pack.extend(material)

        if requirement_satisfied(context_pack, need):
            return cited_context_pack(context_pack)

        if budget_exhausted(context_pack, budget):
            break

    return INSUFFICIENT_PROVENANCE
```

### Recovery stop conditions

Recovery must stop when one of these occurs:

- the requirement is satisfied;
- required role evidence has been found;
- the configured token/byte budget is reached;
- maximum traversal depth is reached;
- no qualifying evidence remains;
- access policy blocks further dereference.

The correct failure output is insufficiency, not hallucinated reconstruction.

---

## 16. AWRAG Dereference Rule

For chat and prose sources, use the same local evidence navigation rule already established for AWRAG:

```text
previous block/message
target span
next block/message
```

If the requirement is still unsatisfied:

```text
walk backward
walk forward
follow related provenance anchors
```

Only continue while the evidence requirement remains unsatisfied and the recovery budget allows it.

The system should return exact source coordinates with the recovered material.

---

## 17. Bidirectional Indexes

Minimum indexes:

```text
relationship_id
    -> provenance refs

(node_id, relationship_type)
    -> relationship IDs

conversation_id + message_id
    -> relationship IDs

decision_id
    -> relationship IDs

code symbol identity
    -> relationship IDs

test_id
    -> relationship IDs

source ref
    -> relationships using that source
```

These indexes support two equally important directions.

### 17.1 GRAPH -> SOURCE

Question:

> Why is this edge here?

Result:

```text
REL_004817
  -> decision chat
  -> correction chat
  -> design doc
  -> implementation symbol
  -> test
```

### 17.2 SOURCE -> GRAPH

Question:

> What parts of the current system came out of this conversation?

Result:

```text
Conversation CHAT_2026_09_08

Currently supports:
  SecureCore.authorize()
  OperatorCatalog
  HumanPresenceGate
  ExecutionContract

Superseded:
  OldAutoController

Disputed:
  REL_004817
```

This is architecture archaeology: effectively **idea-level blame/history** rather than code-line blame.

---

## 18. Impact Archaeology

Before changing an important relationship, the system can ask:

```text
What currently depends on this decision?
```

Example:

```text
Proposed change:
"Allow operator to execute directly."

Affected relationship:
SecureCore --SELECTS--> Operator

Authority:
OWNER_ACCEPTED

Supporting decisions:
3

Corrections:
1

Dependent symbols:
4

Dependent tests:
7

Dependent relationships:
5

Result:
EXPLICIT_SUPERSESSION_REQUIRED
```

This prevents refactors from accidentally resurrecting rejected designs.

---

## 19. Compaction Contract

### 19.1 Compaction may drop from active model context

- raw chat bodies;
- large source excerpts;
- duplicated explanatory prose;
- low-priority exploratory context;
- already-resolved temporary discussion;
- source material that can be deterministically dereferenced later.

### 19.2 Compaction must preserve outside model context

- relationship IDs;
- `from / to / type`;
- lifecycle status;
- authority state;
- recovery capsules;
- source pointers;
- source hashes/fingerprints;
- correction and supersession chains;
- EvidenceBundle state;
- bidirectional indexes;
- enough graph identity to resume traversal;
- ref validity/staleness state.

The survival store should live outside the model context in durable local storage.

Upon resume, only a lightweight checkpoint is reintroduced to working context.

---

## 20. Transactional Provenance

Automatic provenance capture is useful, but asynchronous "we will index it later" is not sufficient for protected relationships.

For critical mutations:

```text
BEGIN MUTATION

1. mutate code / graph
2. create or update relationship record
3. attach source refs
4. update evidence bundle
5. update indexes
6. validate hashes / identities
7. commit mutation

END MUTATION
```

If provenance writing fails, the structural mutation should not be treated as fully accepted.

For lower-value ephemeral edges, the system may use relaxed capture rules, but tiering must be explicit.

---

## 21. Provenance Tiers

Not every graph edge needs the same burden.

Suggested tiers:

### Critical

Authority, security, safety, ownership, execution boundaries, irreversible architecture laws.

Requires:

- stable refs;
- capsule;
- justification state;
- durable transaction;
- explicit supersession chain.

### Normal

Important implementation/design relationships.

Requires:

- at least one valid source ref;
- compact capsule when likely to survive compaction;
- ref integrity checks.

### Ephemeral

Short-lived exploratory relationships.

May be dropped or summarized if they have not become part of accepted architecture.

Promotion from ephemeral to normal/critical occurs when the relationship becomes relied upon.

---

## 22. Ref Integrity and Drift

### Chat

If chat logs are immutable, message IDs and hashes should remain stable.

If imported/exported formats change, use content hash plus local neighbor identities for re-anchoring.

### Code

Line numbers drift.

Re-anchor using:

- repository / commit;
- file identity;
- symbol signature;
- AST/structural identity;
- local hash;
- surrounding symbol relationships.

### Documents

Prefer stable section IDs / heading ancestry / content fingerprints over page numbers alone.

### Broken refs

A reference can move through:

```text
VALID
STALE
BROKEN
PROVENANCE_LOST
```

A stale ref should be repaired before a critical relationship is relied upon.

---

## 23. Access Control and Privacy

Provenance stores addresses to potentially sensitive sources.

The graph should not imply that every consumer may dereference every address.

Access is checked at dereference time.

A relationship may be visible while one or more supporting sources remain unavailable to the current actor.

Recovery output must preserve that distinction rather than leaking protected source data into graph metadata.

---

## 24. Preventing Hallucinated Provenance

Automatically extracted refs should be distinguishable from accepted provenance.

Example:

```text
ref_origin:
    HUMAN_DECLARED
    CODE_DERIVED
    MODEL_EXTRACTED
    TEST_DERIVED
```

For critical relationships, model-extracted provenance should require validation or acceptance before becoming authoritative.

Do not invent a missing source because the relationship "obviously" seems correct.

---

## 25. Conflict Resolution

The architecture requires an explicit authority policy but should not silently freeze a universal precedence ordering before implementation testing.

A candidate policy may distinguish:

```text
OWNER_ACCEPTED
LAW
TEST_VERIFIED
CODE_DERIVED
CHAT_DESIGN
EXPLORATION
```

Corrections and supersessions must be able to invalidate earlier states.

The final precedence rules should be explicit, testable, and stored as policy rather than inferred ad hoc by the model.

---

## 26. Current Relationship Query

The system should be able to answer:

```text
relationship_current_state(REL_004817)
```

with:

```text
status: ACTIVE
authority: OWNER_ACCEPTED

current_interpretation:
"SecureCore delegates bounded execution through ExecutionContract."

supporting_refs:
...

contradicting_refs:
...

superseded_relationships:
...

last_validated:
...
```

This separates "all historical discussion" from "the currently surviving interpretation."

---

## 27. Recovery Query Examples

### Why does this edge exist?

```text
rehydrate(
    REL_004817,
    need="Why does SecureCore control operator execution?"
)
```

### What corrected the old design?

```text
rehydrate(
    REL_004817,
    need="Find the correction and supersession chain."
)
```

### Which code depends on this conversation?

```text
source_impact(
    conversation_id=CHAT_2026_09_08,
    message_id=MSG_0184
)
```

### Is this proposed edit invalidating owner-accepted architecture?

```text
impact_check(
    proposed_mutation,
    authority_minimum=OWNER_ACCEPTED
)
```

---

## 28. Minimal Storage Model

An MVP can use a local relational or document database without requiring a specialized graph database.

Core collections/tables:

```text
nodes
relationships
source_refs
relationship_refs
evidence_bundles
decision_lineage
recovery_capsules
ref_integrity
source_to_relationship_index
relationship_to_source_index
```

The graph view can be materialized from those records.

This keeps the logical model independent of any particular graph database.

---

## 29. MVP Implementation Path

### Phase 1 - Relationship identity

1. Reify important edges as relationship records.
2. Add stable relationship IDs.
3. Attach basic node/edge source refs.

### Phase 2 - Chat provenance

4. Build ChatRef ingestion.
5. Add relationship-role tagging.
6. Add source hashes.
7. Add GRAPH -> CHAT dereference.

### Phase 3 - Recovery

8. Add recovery capsules.
9. Implement `rehydrate(rel_id, need)`.
10. Use exact span +/- local context.
11. Add bounded backward/forward traversal.
12. Return `INSUFFICIENT_PROVENANCE` when unsatisfied.

### Phase 4 - Justification state

13. Add EvidenceBundle.
14. Preserve supporting/contradicting/correction/supersession refs.
15. Add relationship lifecycle states.

### Phase 5 - Bidirectional archaeology

16. Build CHAT -> GRAPH index.
17. Build code-symbol -> relationship index.
18. Add impact queries.

### Phase 6 - Compaction survival

19. Serialize graph checkpoint + capsules + indexes outside model context.
20. Restore lightweight checkpoint after compaction.
21. Add deterministic rehydration triggers.

### Phase 7 - Transactional mutation

22. Couple protected code/graph mutations to provenance writes.
23. Add mutation rollback/failure handling.
24. Add provenance tiers.

---

## 30. Acceptance Tests

### Provenance recovery

Given a relationship with a design decision and later correction:

- compaction occurs;
- raw discussion is absent from working context;
- `rehydrate()` must recover the accepted correction;
- it must not present the rejected earlier design as current.

### Supersession

Given:

```text
REL_A -> superseded by REL_B
```

a current-state query must return `REL_B` while preserving `REL_A` for history.

### Broken source

If a critical CodeRef cannot be re-anchored:

```text
status = STALE or PROVENANCE_LOST
```

The system must not silently accept it as fresh evidence.

### Bidirectional index

Given a chat message ID, the system must return every current relationship linked to that message.

### Bounded recovery

Given a recovery requirement that cannot be satisfied within the configured budget, the result must be:

```text
INSUFFICIENT_PROVENANCE
```

not generated rationale.

### Transactionality

If a protected relationship mutation succeeds but provenance persistence fails, the mutation must fail or remain explicitly unaccepted.

### Access controls

A consumer without permission to dereference a source must not receive the protected cargo through recovery output.

---

## 31. Failure Modes to Guard Against

### Provenance explosion

Do not attach every source to every edge. Use role-aware selection and provenance tiers.

### Summary authority drift

Do not allow capsule prose to become more authoritative than the source.

### Resurrection of dead decisions

Always inspect correction/supersession state when recovering a protected relationship.

### Line-number rot

Do not rely on line number alone for code provenance.

### Infinite archaeology

Bound the recovery walk.

### Fake confidence

Do not convert provenance into unsupported truth probabilities.

### Index divergence

Bidirectional indexes must be transactionally maintained with relationship/source mutations.

### Silent provenance loss

Use explicit status such as `PROVENANCE_LOST`.

---

## 32. Design Contribution Synthesis

Several independent model reviews converged on the same architecture. The useful additions have been retained here rather than preserving model-specific wording.

### Gemini review contributions retained

- stable code pointers should use symbol/AST identity, not raw line numbers;
- compaction survival store must live outside model context;
- GRAPH -> CHAT and CHAT -> GRAPH enable impact archaeology;
- provenance capture must be integrated with execution.

### TrueSystems correction to Gemini

Automatic background capture is insufficient for protected changes.

> **A structural mutation is incomplete until its provenance mutation is committed.**

### Copilot review contributions retained

- `EvidenceBundle` / justification state;
- supporting vs contradicting evidence;
- explicit correction/supersession lineage;
- separation of memory, knowledge, evidence, and context;
- "idea-level blame" / architecture archaeology framing.

### Grok review contributions retained

- concise framing of the backplane as the missing half of AWRAG-style memory;
- code graph + provenance index + recovery capsules = selective rehydration rather than amnesia.

### DeepSeek review contributions retained

- `PROVENANCE_LOST`;
- explicit bidirectional indexes;
- bounded rehydration with `INSUFFICIENT_PROVENANCE`;
- provenance tiers to prevent graph explosion;
- stale-reference maintenance;
- access checks at dereference time;
- implementation-ready MVP sequence.

---

## 33. Short Form

```text
Do not treat the graph as memory.

Treat the graph as claims and relationships.

Give every important relationship a stable identity.

Attach exact source addresses to the relationship.

Store a tiny recovery capsule.

Preserve corrections and supersessions.

Preserve supporting and contradicting evidence separately.

Compaction may throw away cargo from active context.
It must not throw away the addresses.

When context is needed:
    dereference exact source
    load local context
    follow bounded recovery paths
    stop when the requirement is satisfied

If the source trail is insufficient:
    say INSUFFICIENT_PROVENANCE

If the trail is lost:
    say PROVENANCE_LOST

Graph -> Source recovers rationale.
Source -> Graph reveals architectural impact.

Structural mutation + provenance mutation = one accepted transaction.

The graph remembers where the important shit came from.
```

---

## 34. Architectural Bottom Line

This is not merely RAG for code.

It is a **provenance-aware relationship backplane** for long-lived AI-assisted systems.

Its job is not to force every past conversation into current context.

Its job is to preserve:

```text
what relationship exists
why it exists
what sources justify it
what contradicted it
what corrected it
what superseded it
what currently depends on it
where the exact source material lives
```

That converts context recovery from a probabilistic recollection problem into an addressable evidence-recovery problem.

The result is a codebase graph that can answer not only:

> What calls what?

but:

> Why is this relationship here, who established it, what corrected it, is it still current, what depends on it, and where is the exact source that proves it?

That is the TrueSystems Provenance Backplane.
