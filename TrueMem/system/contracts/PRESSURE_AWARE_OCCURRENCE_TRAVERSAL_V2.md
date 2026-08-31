# Pressure-Aware Occurrence Traversal v2

## Boundary

This layer gathers, discerns, compiles, and hands off evidence. It does not
form textual answers, execute operations, change ranking, create authority, or
use a model. TrueVision remains the structural-compilation authority. TrueMem
operates only over verified admitted records.

## Exact pressure points

A pressure point is an exact evidence obligation. Every obligation names one
or more verified question ruling structures and exactly one evidence form:

- `EXACT_STRUCTURE`: one of the declared admitted structure forms must occur;
- `EXACT_RELATION_FIELD`: every declared complete anchor must occur inside one
  exact relation-phrase occurrence; its subject, relation, and object
  occurrences become the evidence;
- `EXACT_CONTEXT_ANCHORS`: every declared complete anchor must occur inside the
  current bounded parent cloud; and
- `EXACT_PARENT_TRANSITION`: an exact mention structure must cross through an
  admitted binding to a parent with an exact native identity structure.

Generic structure-kind presence cannot satisfy a pressure point. Every ruling
structure must be present in the temporary question overlay and the admitted
dataset. Every evidence structure or anchor must already exist in the admitted
dataset lexicon.

Every pressure point also declares exact `transition_context_anchor_keys`.
Those anchors must occur in the mention occurrence's native signed 6-1-6
posting cloud before that binding may widen to another parent. A pressure point
without proved local transition context grants no cross-parent transition.

## Branch state

Each branch retains:

```text
branch ID and predecessor branch ID
current parent object
incoming binding
parent history
satisfied pressure mask
ruling-group-seen mask
exact pressure evidence
exact transition evidence
```

Parent history is branch-local. Independent branches cannot terminate or erase
one another.

## Traversal semantics

1. Inspect all exact structural occurrences, complete native anchor postings,
   and relations in the current bounded parent cloud.
2. Update ruling and pressure masks from exact evidence.
3. Complete branches whose entire pressure burden is satisfied.
4. Only incomplete branches may inspect admitted reference bindings.
5. Every verified binding creates one continuation candidate.
6. Every candidate of an ambiguous binding creates a separate explicit branch.
7. A parent already present in that branch's history is not re-entered.
8. Preserve all independently qualifying paths until workspace compilation.
9. After every active branch at a depth has completed local inspection, the
   first depth containing one or more fully resolved proof paths closes the
   evidence workspace. All complete paths at that depth are preserved; no
   unresolved branch may widen after the exact burden has been met.

Local cloud inspection always precedes cross-parent widening.

## Fixed point

A complete round terminates globally as `NO_NEW_VERIFIED_STATE` when it creates
no new verified parent transition and resolves no new pressure point. Other
terminal states are:

```text
ALL_PRESSURE_POINTS_RESOLVED
NO_ADMITTED_START_EVIDENCE
NO_VALID_FRONTIER
TRAVERSAL_BUDGET_EXHAUSTED
STALE_PROVENANCE
```

## Device and storage

The B70 hot path uses compressed sparse row adjacency for:

```text
parent -> child occurrences
parent -> relation edges
occurrence -> child anchor symbols
mention occurrence -> candidate parent bindings
parent -> native identity occurrences
structure form -> exact occurrences
block -> exact native anchor postings
```

CSR range expansion, pressure masks, cycle filtering, binding expansion, and
frontier construction execute on XPU. CPU work is bounded to verified artifact
loading, branch identity bookkeeping, and receipt serialization. No ranking or
relationship computation falls back to CPU.

Physical CSR optimization may not alter the logical occurrence graph or its
traversal semantics.

## Evidence workspace

The handoff workspace contains every independently qualifying branch, its exact
pressure evidence, exact context-cloud records that resolved obligations, the
signed 6-1-6 posting records that qualified each transition, exact mention and
binding records that produced parent transitions, citations, termination
status, and device receipt.

The workspace explicitly records:

```text
textual_answer_formed = false
handoff_only = true
model_used = false
training_performed = false
ranking_modified = false
source_authority_modified = false
operator_capability_created = false
```
