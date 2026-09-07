# System-wide 6-1-6 context clouds and scoring preparation

Every admitted anchor occurrence is the center of one context cloud. Its cloud
contains the available anchors at exact signed offsets `-6..-1,+1..+6` inside
the same admitted block or explicitly bounded sequence. Block, line,
conversation, file, dataset, or modality boundaries are never crossed merely
to fill missing lanes.

The cloud is an occurrence-local measurement. Neighboring anchors prove
observed adjacency, not semantic relation, causality, equivalence, intent, or
correctness. Equal anchor strings in different occurrences do not merge their
source identities.

## Unchanged authority

- Complete anchors remain admitted, including glue and punctuation.
- All twelve signed lanes remain separate.
- Raw occurrence and relationship counts remain authoritative.
- Source coordinates and citations remain attached.
- A weighted view never mutates counts or replaces lexicographic relationship
  measurements.

## Weight preparation

The first experimental lane view preserves these components:

- declared positive and negative edge counts;
- declared positive and negative center counts;
- beta-smoothed outcome support;
- the center anchor's outcome baseline;
- outcome contrast;
- signed-distance proximity `(7 - abs(offset)) / 6`;
- existing anchor-direction weight (`content=1`, `relation=0.5`, `object=0.65`,
  `glue=0`, `boundary=0`); and
- sample confidence `1 - exp(-edge_observations / 8)`.

The diagnostic cloud weight is their disclosed product:

```text
anchor_direction_weight
* distance_proximity
* sample_confidence
* (edge_outcome_support - center_outcome_support)
```

Negative weight means association away from the declared positive outcome. A
zero glue or boundary weight does not delete that anchor or lane; it prevents
that center from independently steering the scored direction.

## Correctness boundary

Every scoring call requires a label contract naming the outcome, positive and
negative labels, and their authority. Parser acceptance, receipt verification,
human grading, benchmark labels, and test execution are different outcomes and
must never be mixed under one unnamed score.

The general result is an outcome-support association. It may populate
`bounded_correctness_score` only when the label contract explicitly grants
correctness authority for that bounded question. Even then, the score means
correct under that named test/label contract—not generally correct, safe, or
useful.

Weights are fit from training partitions only. Validation and test labels stay
sealed until evaluation. Dataset-specific adapters may rename the outcome but
must call the system-wide TrueMem formula and retain every component.
