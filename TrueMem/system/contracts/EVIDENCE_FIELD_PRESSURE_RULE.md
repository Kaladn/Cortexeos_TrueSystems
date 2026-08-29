# Evidence Field Pressure Rule

Status: system law.

This rule governs diagnostic evidence pressure after retrieval and before any
off-path thinking, speech rendering, or operator-facing summary.

TrueMem retrieval does not perform pressure promotion. It may mark pressure
diagnostics such as `candidate_needs_pressure`, `scenario_gap`,
`coverage_miss`, `bridge_required`, and `pressure_inspection_needed`. Any
bridge walk, pressure promotion, legal synthesis, or benchmark validation
belongs off-path.

## Court Law

```text
Scenario anchors decorate the retrieval field.
Evidence-bearing anchors carry the proof burden.
```

Operator form:

```text
Scenario anchors direct the search.
Evidence-bearing anchors satisfy the burden of proof.
```

Missing scenario terms do not automatically defeat a candidate that carries
real evidence-bearing support.

Short form:

```text
missing scenario terms != failed evidence
missing scenario terms = proof pressure trigger
```

## Anchor Classes

A question can contain different kinds of anchors.

Scenario or context anchors:

```text
names
examples
setup words
local story details
illustrative facts
```

Evidence-bearing anchors:

```text
subject
relation
value
frame
condition
exception
authority-bearing term
answer-bearing term
```

Ambiguity anchors:

```text
terms that may be scenario or evidence-bearing until local context is checked
```

The packet must preserve the split instead of flattening all anchors into one
undifferentiated required-term list.

## Rejected-But-Found Rule

If TrueMem found a candidate strongly, but qualification rejected it mostly because
scenario or story-wrapper anchors were absent, the candidate must not disappear
into a final unsupported conclusion without pressure review.

The correct middle state is:

```text
candidate_needs_pressure
```

not:

```text
final_no_support
```

A rejected candidate deserves Deeper/Wider pressure when:

```text
it has strong evidence-bearing anchor matches
it has real citation and coordinate support
it failed mostly because scenario/example terms were missing
its native rank key says TrueMem found something strong
```

## Deeper

Deeper is local proof pressure.

```text
Stay near the found passage.
Inspect the local neighborhood.
Use the same citation/source/coordinate area.
Check previous/current/next blocks.
Ask whether this local field supports, completes, or contradicts the candidate.
```

Deeper does not run new intake, mutate ranking, call a model, or generate an
answer. It records pressure evidence.

## Wider

Wider is surrounding-field pressure.

```text
Look across the evidence field.
Compare retained candidates.
Compare rejected candidates.
Compare topK and related coordinate fields.
Ask whether another cited field completes, contradicts, or clarifies the candidate.
```

Wider does not turn surrounding context into speech unless that context adds
cited support.

## Pressure Decisions

An off-path pressure review may decide:

```text
keep_as_partial_support
keep_as_context_gap
confirm_reject
require_more_evidence
```

TrueMem retrieval itself may only mark:

```text
ordinary_qualified
pressure_inspection_needed
confirm_reject
```

Support status after pressure may be:

```text
supported
partially_supported
unresolved
unsupported
```

## Forbidden

```text
no answer generation
no benchmark answer-key leakage
no raw document guessing
no LLM authority
no changing retrieval/ranking
no mutation of dataset state
no speech from wider context unless it adds cited support
```

## Required Receipts

Any implementation of this rule must produce receipts showing:

```text
no_rank_mutation
no_answer_generation
no_raw_doc_guessing
no_dataset_state_mutation
citations_used
coordinates_used
pressure_decision
support_status
```

## Why This Law Exists

The old failure mode is:

```text
question mentions scenario anchors
candidate lacks scenario anchors
candidate is rejected
packet says no support
```

The correct evidence-field behavior is:

```text
question mentions scenario anchors
candidate covers evidence-bearing anchors
candidate lacks scenario anchors
candidate receives a pressure-inspection marker
off-path thinking records whether cited pressure supports, partially supports, or defeats it
```

The evidence packet speaks first. Speech only expresses admitted evidence.
Thinking consumes packets off-path.

## Pressure Probe Sidecar

Pressure probes are bounded second-layer questions generated from admitted cited
evidence packets. The preferred system name for each generated question is:

```text
pressure hypothesis
```

Each pressure hypothesis asks:

```text
If this admitted evidence is true, what else should also be true in the dataset?
```

They ask whether the existing evidence field can:

```text
back up admitted evidence anchors
bridge missing evidence-bearing terms
test scenario-wrapper gaps
clarify same-citation/local-neighborhood support
surface conditions, exceptions, limits, or contradictions
```

They are not answers. They are not ranking changes. They are not a model call.

Sidecar law:

```text
evidence packet -> pressure probe questions -> optional normal TrueMem query/batch
```

The sidecar must record:

```text
no retrieval
no topK
no intake
no rank mutation
no speech generation
no answer generation
no answer-key leakage
no raw document guessing
```
