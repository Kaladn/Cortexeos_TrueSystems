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

Across all twelve lanes for a pair, it also exposes the signed-distance
distribution, squared-probability concentration, positive and negative support,
and direction consistency.

Multi-hop paths retain separate bottleneck and geometric-mean measurements for
conditional strength, lift, and positional stability, plus total log support.
Path selection is deterministic and lexicographic. No weighted scalar or guessed
coefficient combines these fields.

Every prediction candidate exposes this vector:

`Local, Back, Cloud, Forward, Support, Lift, DistanceStability, Direction`

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
