# TrueMem Three-Lane Law

TrueMem is the evidence machine, not the thinker.

```text
Intake builds the field.
Retrieval pulls cited evidence packets.
Speech renders packets.
Thinking consumes packets off-path.
```

## Intake

Intake owns:

```text
source files
blocks
citations
coordinates
dataset lexicon
symbols
anchor counts
six-window relation counts
readiness/status
```

Intake does not reason, decide, score benchmark truth, render speech, or carry
expected answer metadata into the evidence field.

## Retrieval

Retrieval owns:

```text
question anchors
dataset cloud fit
TopK evidence retrieval
candidate scoring
mechanical qualification/filtering
locations
rejected_locations
evidence packet receipts
```

Retrieval may mark diagnostics:

```text
candidate_needs_pressure
scenario_gap
coverage_miss
bridge_required
pressure_inspection_needed
```

Retrieval does not perform bridge reasoning, pressure promotion, answer
synthesis, legal validation, benchmark validation, or deeper meaning decisions.

## Speech

Speech owns:

```text
packet-to-readable output
evidence trace
count-walk speech attempts
markdown/json rendering
```

Speech does not decide truth. It expresses admitted packet evidence and records
when evidence or local count-walk support is missing.

## Thinking

Thinking owns off-path work over already written packets:

```text
reverse-walk
pressure coordination
REAPER-style checks
formula experiments
benchmark Q/A validation
```

Thinking consumes TrueMem packets. It does not mutate intake, retrieval, speech,
native counts, ranking, citations, coordinates, or source datasets.

## Boundary Test

If a behavior changes which evidence is admitted during `truemem query` or
`truemem batch`, it belongs to retrieval only if it is mechanical filtering. If it
requires a bridge, pressure walk, formula judgment, legal synthesis, or claim
validation, it belongs off-path in thinking.
