# TrueSystems standing checkpoint — 2026-08-31

Status: known-good architectural checkpoint before the disconnected native-model experiment.

## Runtime role boundary

The controlling interaction law is:

```text
human or questionnaire
→ operator LLM constructs a bounded work order
→ TrueSystems returns deterministic evidence, coordinates, operations, and receipts
→ operator LLM reasons and communicates from the handoff
→ human
```

TrueSystems does not compose the final textual answer. The operator LLM does
not become evidence, symbol, relationship, dataset, operation, or receipt
authority.

The detailed contract is
`docs/CODEX_TRUESYSTEMS_OPERATOR_HANDOFF_CONTRACT.md`.

## Current repository boundary

- AWRAG is retired as a production/runtime concept. It remains historical
  prototype evidence only.
- TrueVision/DocuFilm remains the sole intake authority.
- TrueMem retains deterministic dataset-local lexicons, symbols, occurrences,
  signed 6-1-6 relationships, structures, binaries, source coordinates,
  citations, traversal, and evidence packets.
- Dataset symbols remain local. A combined dataset must be re-admitted and
  resymbolized from its approved sources; existing symbolic namespaces are not
  merged.
- Exact source text is admitted with zero normalization.
- The protected lexicon is the reversible external key. Native model inputs
  must not receive lexical strings.

## SciFact standing

SciFact is admitted as its own self-contained dataset volume under the external
User System Test library. Its publication manifest identity is:

```text
541266327de5248955c0fef365232569557e087ea37539301591af4c4059d26b
```

The resident B70 evidence-ranking path passed CPU-reference equivalence checks
and explicit zero/one-candidate terminal checks without silent CPU fallback.

The 300-claim direct-query run is classified only as:

```text
DIRECT_QUERY_BASELINE_NOT_OPERATOR_LOOP
```

Its hit-at-10 result was 193/300 (64.3333%). It is not a grade for the complete
Codex→TrueSystems→Codex architecture.

The first 20-claim operator fixture tested direct word rearrangement only:

```text
direct-query baseline hits: 16/20
direct-rearrangement operator hits: 15/20
net change: -1
supported from returned evidence: 7
refuted from returned evidence: 2
insufficient evidence: 11
unsupported facts introduced: 0
```

The valid finding is that the work-order and evidence-handoff boundary works.
The invalid inference would be that word removal/reordering constitutes the
complete operator method. It does not. The correct operator must identify
ruling identities, relations, outcomes, values, comparisons, quantities,
polarity, and independent evidence obligations; gather exact occurrence fields;
inspect their signed context; and continue until the evidence burden resolves
or reaches a fixed point.

## Performance standing

After the SciFact dataset is resident on the Intel Arc Pro B70, exact posting
lookup is effectively immediate. Measured examples were approximately 47–58
microseconds for the XPU posting slice. The performance problem was not exact
anchor lookup; it was applying generic ranked-document behavior where the
operator should have constructed explicit occurrence and evidence obligations.

## Native-model experiment boundary

The next native-model experiment is intentionally disconnected from this
repository. This repository remains the frozen implementation/source authority
and must not accumulate experimental training code, generated combined-world
data, model checkpoints, optimizer logs, or benchmark outputs.

The experiment direction is frozen as:

```text
approved exact sources
→ one new combined dataset identity
→ one new exact lexicon and symbolic namespace
→ one recalculated occurrence stream and signed 6-1-6 map
→ protected external lexicon
→ pure-symbol model input
```

Questions, answers, qrels, expected documents, expected paths, benchmark labels,
and reserved tests must be held outside training before corpus construction.

The controlled neural comparison is:

```text
Control A: pure symbolic sequence
Treatment B: same sequence + native 240-wide location state
```

The 240-wide state is exactly twelve signed lanes times twenty deterministic
fields. The current anchor has its own embedding and is not a thirteenth lane.
The exact twenty fields remain deliberately unspecified and must be frozen in a
separate design gate before combined-world construction or optimizer execution.

## Stop boundary

No native-model training is authorized by this checkpoint. Before optimizer
update 1, the disconnected experiment must produce the complete source estate,
reservations, duplicate accounting, combined lexicon uniqueness proof,
relationship artifacts, exact twenty-field lane contract, pure-symbol leakage
audit, splits, model identity, parameter count, hardware estimate, and training
configuration for explicit review.

