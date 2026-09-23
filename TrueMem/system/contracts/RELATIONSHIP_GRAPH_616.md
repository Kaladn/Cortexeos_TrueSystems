# Deterministic 6-1-6 relationship graph

Relationship authority is the admitted dataset anchor stream. For every anchor
occurrence, TrueMem records twelve independent signed lanes: `-6..-1` and
`+1..+6`. Rebuilding the same dataset from the same admitted stream produces the
same relationship counts.

For every ordered anchor pair and signed lane, the graph exposes these values
without collapsing them:

- exact signed count;
- lane-conditional probability;
- dataset background probability;
- directional lift and natural-log lift;
- natural-log support confidence.

The complete signed lane vector is retained for every centered observation.
There is no standing center-neighbor total, pair total, distance distribution,
or all-lane ranking scalar. Any comparison must retain the twelve signed
positions as a vector and preserve the center that produced them.

Multi-hop paths retain the ordered signed lane profiles and separate
bottleneck/geometric-mean measurements for lane-local conditional strength and
lift. Path selection is deterministic and lexicographic over preserved lane
vectors. No weighted scalar, pair aggregate, or guessed coefficient combines
the context cloud.

Every prediction candidate exposes this vector:

`Local, Back, Cloud, Forward, Support, Lift, SignedLanes`

The current anchor supplies at most six observed `+1` candidates. Backside
support checks the candidate against the actual expected signed lane for each of
the six resolved anchors. Cloud support retains query-to-candidate trails.
Forward support temporarily centers the candidate and exposes its next six
choices. Bounded branches retain reproducible warnings and pruning receipts for
tiny support, reverse-dominant contradiction, cloud divergence, future support
collapse, and evidence dead ends.

Reasoning terminates only through evidence convergence. Surviving paths return
the original strings plus source, block, sentence, line, and citation
coordinates. Dataset-native symbols do not cross the model handoff as meaning.
