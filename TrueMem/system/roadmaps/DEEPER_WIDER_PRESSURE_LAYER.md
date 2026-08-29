# Deeper/Wider Pressure Layer

Status: parked roadmap doctrine; not default query behavior.

This lane describes off-path pressure inspection over already written retrieval
packets. It does not decide evidence admission inside `truemem query` or
`truemem batch`.

```text
retrieval packet
-> candidate anchor split
-> rejection audit
-> Deeper/Wider off-path inspection
-> diagnostic pressure status
-> separate receipt
```

It is not answer generation.

It is not domain-specific reasoning.

It is an evidence-field pressure layer.

## Purpose

Retrieval can reject a useful evidence-bearing passage when the passage does
not repeat scenario words from the question. Deeper/Wider is the parked
off-path inspection doctrine for those candidates.

```text
reject_confirmed
```

becomes:

```text
candidate_needs_pressure
candidate_context_gap
candidate_core_supported_story_missing
```

The compact rule:

```text
If TrueMem found it strongly,
but rejected it mostly for story-wrapper absence,
do not throw it away.
Pressure it.
```

## Diagnostic Shape

The v0 pressure packet should contain:

```text
question
question_anchor_split
  scenario_terms
  evidence_bearing_terms
  ambiguity_terms

candidate
  citation
  coordinates
  native_rank_key
  matched_terms
  missing_terms
  matched_evidence_terms
  missing_evidence_terms
  matched_scenario_terms
  missing_scenario_terms

candidate_status_before_pressure
  retained
  rejected
  reject_reason

pressure_trigger
  strong_evidence_anchor_match
  scenario_gap_only
  coordinate_supported
  native_rank_strong
  ambiguity_present

deeper_inspection
  same_source_window
  previous_block
  current_block
  next_block
  local_support_delta
  local_contradiction_delta

wider_inspection
  retained_candidate_comparison
  rejected_candidate_comparison
  topk_neighbor_field
  related_coordinate_field
  contradiction_field
  completion_field

retrieval_pressure_marker
  ordinary_qualified
  pressure_inspection_needed
  confirm_reject

off_path_pressure_observation
  keep_as_partial_support
  keep_as_context_gap
  contradiction_seen
  require_more_evidence

support_status
  partially_supported
  unresolved
  unsupported

receipts
  no_rank_mutation
  no_answer_generation
  no_raw_doc_guessing
  no_dataset_state_mutation
  citations_used
  coordinates_used
```

## Q1 Pressure Example

Question:

```text
Bob and Ted are close friends. Ted is on trial for drug offences,
and Bob has been selected as a juror in Ted's case. Is the judge
required to excuse Bob from serving on the jury?
```

Found candidate:

```text
1.2-c2-s2
```

Matched anchors:

```text
excuse
juror
jury
offence
serving
trial
```

Missing scenario/story anchors:

```text
bob
ted
friend
close
selected
drug
```

Correct pressure result:

```text
candidate_needs_pressure
```

The missing story wrapper does not prove the candidate useless. It proves the
candidate needs local and field pressure before any off-path support judgment.

## Deeper v0

For each packet candidate that triggers pressure:

```text
read same-source previous block
read same-source current block
read same-source next block
record whether local context completes, contradicts, or leaves unresolved
```

Deeper v0 must use existing citations and coordinates. It must not read raw
external source paths, mutate dataset state, or run intake.

## Wider v0

For each packet candidate that remains unresolved after Deeper:

```text
compare retained candidates
compare rejected candidates
compare related topK candidates
record completion and contradiction fields
```

Wider v0 must stay inside the retrieved/query packet and already indexed
dataset coordinates.

## Relationship To Speech

Speech is downstream of retrieval packets. Deeper/Wider does not change
retrieval admission. If off-path thinking produces a separate diagnostic
receipt, speech may render that receipt only as a separate artifact.

## Non-Goals

```text
no legal-only rules
no benchmark-specific answer-key use
no LLM reasoning authority
no replacement of ranking
no silent promotion
no retrieval admission changes
no natural-language answer generation
```

## Success Condition

A successful v0 run proves:

```text
the source query packet was not mutated
dataset state was not mutated
ranking was not changed
candidate anchor splits were recorded
rejected-but-found candidates were inspected off-path
diagnostic observations cite coordinates
retrieval packet and dataset state were not changed
```
