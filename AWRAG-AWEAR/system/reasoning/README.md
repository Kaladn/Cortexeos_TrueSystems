# AWEAR Reasoning Lane

This directory is the parked home for reasoning-side notes that sit beside the evidence engine.

AWEAR core remains the dataset-local evidence machine:

```text
anchors
counts
coordinates
citations
candidate qualification
evidence packets
speech rendering
```

The reasoning lane is for bridge work that is intentionally outside native AW intake, retrieval, and speech:

```text
question
-> claim / doctrine formation
-> evidence verification target
-> cited support check
-> admitted reasoning receipt
```

## Boundary

Reasoning work must not pollute core retrieval, intake, ranking, or dataset storage.

Allowed here:

```text
claim formation notes
reasoning engine comparison
question-answer pair verification doctrine
reasoning receipts
sidecar designs
```

Not allowed here:

```text
answer-key leakage into intake
dataset-specific logic in awrag.engine
raw document mutation
retrieval/ranking mutation without explicit promotion
speech renderer removal
```

## Current Finding

AW remains the evidence machine. Thinking consumes packets off-path and must not
mutate intake, retrieval, speech, or dataset storage.

## Notes

- `PRE_REASONING_BASELINE.md`
- `ANSWER_REASONING_REVERSE_WALK.md`
- `REAPER_PRESSURE_COORDINATION_NOTES.md`
- `PRESSURE_COORDINATION_AGENT.md`
