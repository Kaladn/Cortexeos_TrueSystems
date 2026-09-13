# TrueSystems — Cubic Cluster / Relationship Pressure Investigation
**Date:** 2026-09-10  
**Status:** Investigation record + runnable prototype  
**Dataset used:** Starlink telemetry (`starlink.csv`)  
**Parent observed:** `utwente`  
**Records:** 325,554

## 1. Why this document exists

This captures the full design progression from the chat session so the work is not lost or flattened into a later summary. The purpose was to recover the useful algorithmic ideas from the early Cascade/Cortex work, test them on Starlink telemetry, and translate them into a data-agnostic TrueSystems substrate.

The old fixed `6-1-6` language is **not a law**. It is a simple linear probe. The deeper target is a relationship representation that can grow into cubic/hypercubic clusters while preserving exact source identity, counts, co-occurrence, position, barriers, ancestry, and children.

## 2. Recovered algorithmic lineage

The useful old shape was:

```text
ordered data
-> focus / anchor
-> bounded local neighborhood
-> count co-occurrence
-> preserve relative position
-> apply positional pressure
-> move focus
-> repeat
```

The later recursive cascade also contained a useful structural instinct: recurse around an anchor. Its hardcoded left/anchor/right string geometry and domain-specific genomic semantics are not retained as governing law.

## 3. Correction: 6-1-6 is a probe, not architecture

A one-dimensional ordered sequence can be probed as:

```text
-6 -5 -4 -3 -2 -1 | CENTER | +1 +2 +3 +4 +5 +6
```

The current prototype uses the historical positional pressure profile:

```text
distance 1 -> 1.000000
distance 2 -> 0.833333
distance 3 -> 0.666667
distance 4 -> 0.500000
distance 5 -> 0.333333
distance 6 -> 0.166667
```

This pressure expresses **position in the local linear probe**. It does not express truth probability.

## 4. Cubic translation

For three admitted dimensions, the anchor is represented by a 3D cubic neighborhood with six faces:

```text
time-       time+
azimuth-    azimuth+
elevation-  elevation+
```

A 3D cube has six 2D faces. A 4D hypercube has eight 3D cubic cells. In general, a D-dimensional hypercube has `2D` bounding facets of dimension `D-1`.

Higher-dimensional promotion **contains** lower-dimensional structure rather than deleting it.

## 5. Parent / child identity

Records are not anonymous samples.

```text
PARENT
  -> owns child observations
       -> exact source ordinal
       -> original source row
       -> timestamp
       -> raw field values
       -> derived relationship measurements
```

For this Starlink dataset:

```text
parent_id = utwente
child_count = 325,554
```

The parent surface is a compact summary. Children remain available underneath as proof.

## 6. Repeated coordinates are occupancy, not fake neighbors

Repeated azimuth/elevation values are valid repeated observations, not duplicate records.

Verified source facts:

- distinct azimuth values: **5,317**
- maximum recurrence of one azimuth value: **520**
- distinct elevation values: **11,747**
- maximum recurrence of one elevation value: **133**
- distinct `(azimuth,elevation)` coordinate pairs: **313,413**
- coordinate pairs revisited at least once: **11,559**
- extra observations on already-occupied coordinate pairs: **12,141**
- maximum recurrence of one coordinate pair: **11**

Therefore:

```text
same coordinate
-> occupancy cluster
-> occurrence count
-> source positions[]
-> co-occurring measured states[]
```

Repeated observations must not be arbitrarily chained as `+/-` spatial neighbors.

## 7. Natural barriers

Numeric adjacency is not enough to prove neighborhood. Empty regions, large time gaps, and topology can create barriers.

Starlink median temporal sampling gap is approximately **30.000 seconds**.

Largest observed time gaps include:

```text
3,094,305.142 seconds
590,518.664 seconds
6,583.356 seconds
423.975 seconds
283.298 seconds
```

Azimuth is circular. `+180°` and `-180°` are neighboring directions in angular topology, not opposite ends of a linear field.

A barrier can exist on one channel while a relationship survives on another. Spatial separation, temporal adjacency, shared parent identity, recurrence, and state co-occurrence are independent relationship channels.

## 8. Frozen frequency law

> **Frequency classifies role, not importance.**

Frequency measures **commonality**.

It does not compete with co-occurrence or positional pressure.

```text
frequency     -> eligibility / background role
co-occurrence -> relational support
position      -> signed pressure / direction
cube faces    -> multi-axis structure
parent        -> summary
children      -> proof
```

### Common values

Common values are not deleted and are not weakened into fake low-confidence values.

Their job changes:

```text
common at this parent/level
-> retain as context/background
-> do not let it dominate discovery-center selection
-> descend into children when more resolution is required
```

### Less-common values

Less-common values may probe structure.

### Rare values

Rarity is not importance. Rare values must still earn structural relevance through repeatable co-occurrence and positional support.

## 9. Provisional commonality estimator

The session tested a first implementation:

```text
mean occupancy = number of observations / number of unique values

value occupancy > mean occupancy
-> common/background center
```

**This formula is NOT frozen.**

The frozen law is that **each parent establishes its own frequency structure and commonality classification is distribution-derived**.

Candidate future estimators include:

- natural gaps in the frequency distribution
- quantile break
- multimodal partition
- entropy-derived partition
- other empirically testable parent-local methods

## 10. Verified Starlink commonality result

Using the provisional mean-occupancy estimator:

| Field | Unique | Eligible discovery children | Eligible % |
|---|---:|---:|---:|
| state | 5 | 42 | 0.013% |
| uplink | 16,734 | 42,918 | 13.183% |
| downlink | 28,796 | 41,163 | 12.644% |
| pop_ping_latency | 4,925 | 25,463 | 7.821% |
| ping_drop | 10,145 | 38,651 | 11.872% |
| mean_ping_latency | 124,426 | 99,127 | 30.449% |
| ping_stdvar | 220,664 | 156,538 | 48.084% |
| fraction_obstructed | 2,410 | 32,677 | 10.037% |
| obstruction_duration | 31 | 14,756 | 4.533% |
| obstruction_interval | 6 | 14,756 | 4.533% |
| direction_azimuth | 5,317 | 41,979 | 12.895% |
| direction_elevation | 11,747 | 53,170 | 16.332% |

The `state` field is the clearest example:

```text
CONNECTED    325,512
NO_PINGS     25
SEARCHING    10
NO_DOWNLINK  5
OBSTRUCTED   2
```

`CONNECTED` becomes background for discovery at this parent/level. It remains available as context around uncommon states.

## 11. Child significance

A child signifies an **occurrence witness**.

It is not itself a category, confidence, or summary.

A child owns:

```text
ChildWitness
    parent_id
    source_ordinal
    source_row
    timestamp
    raw_values

    per-channel:
        commonality_role
        cooccurrence_counts[-6..-1,+1..+6]
        positional_pressure[-6..-1,+1..+6]

    cubic_surface:
        time-
        time+
        azimuth-
        azimuth+
        elevation-
        elevation+
```

## 12. Co-occurrence law

Co-occurrence supplies relational support.

For each eligible center value and each signed linear offset, count the exact observed neighbor value:

```text
count(center_value, neighbor_value, signed_offset)
```

Then apply the positional pressure for that offset:

```text
relationship_pressure =
    observed_cooccurrence_count
    × positional_pressure
```

The count is empirical. The positional multiplier only preserves the local positional pressure requested by the linear probe.

Do not reinterpret the resulting number as truth probability.

## 13. Signed position

The sign must be retained.

```text
-3 != +3
```

Magnitude can order traversal candidates; sign identifies direction.

The original source ordinal remains separately preserved so a derived pressure can never replace the actual source position.

## 14. Cubic face projection

The prototype projects relationship pressure into independent facets:

```text
time- / time+
azimuth- / azimuth+
elevation- / elevation+
```

Time direction comes from signed source order.

Azimuth direction uses circular angular delta.

Elevation direction uses signed elevation delta.

The six face values form a **pressure signature**, not a truth score.

## 15. Parent surface

A parent surface summarizes measured child structure without erasing the children.

```text
ParentSurface
    parent_id
    child_count
    frequency_roles
    occupancy_counts
    cooccurrence_counts
    face_pressure_sums
    dominant_face_counts
    barriers
    recurrence
    transition observations
```

If a surface result matters, descend to the children and exact source positions that produced it.

## 16. Recursive resolution selection

The housing analogy exposed a broader rule:

```text
DWELLING
  -> detached house
  -> apartment
  -> condominium
  -> townhouse
  -> none
```

If a property is overwhelmingly common at the current parent level, it may provide little discovery information there.

Do not discard it.

Keep it as background and **descend one level**.

If a newly exposed child becomes common within that new parent, descend again.

Therefore the representation performs **data-driven resolution selection**:

> Common at this level? Keep it as context and examine its children.

This is stronger than inverse-frequency weighting.

## 17. Fluid / CFD translation

The same laws can be applied without injecting vortex labels.

Potential independent channels:

```text
x
y
z
time
u
v
w
pressure
vorticity
strain
energy
gradient terms
```

The roles remain unchanged:

```text
frequency
-> commonality / background role

co-occurrence
-> which measured states repeatedly occur together

position
-> where the relationship occurs in x/y/z/time

cubic consensus
-> emerging multi-axis structure
```

A common laminar/background state remains context.

A less-common state may probe.

A rare state is not automatically important.

Repeated co-occurrence plus positional organization must support the structure.

## 18. AWRAG relationship

This cubic substrate remains compatible with the AWRAG locator contract.

AWRAG:

```text
finds qualifying relationship locations
-> returns exact coordinates + measurements
```

Verifier:

```text
opens coordinates
-> judges support / contradiction / insufficiency
```

Speaker:

```text
explains
```

Relationship strength remains separate from truth.

Dominant relationship decay is a **handoff/crossover between competing relationship paths**, not a requirement that relationship strength reach zero.

## 19. Investigation laws frozen from this session

1. `6-1-6` is a useful linear probe, not a universal architecture.
2. Dataset dimensionality and topology must be preserved rather than flattened for convenience.
3. Repeated coordinates create occupancy/count mass; they are not fake directional neighbors.
4. Parent identity belongs to the owner/source of the records.
5. Parent surfaces summarize; children and exact source coordinates prove.
6. Frequency measures commonality, not significance.
7. Frequency classifies role rather than contributing a competing importance score.
8. Common values remain context/background.
9. Less-common values may probe structure.
10. Rare values require co-occurrence and positional support.
11. Co-occurrence establishes relational support.
12. Position establishes signed pressure/direction.
13. Positional pressure does not replace raw count or source position.
14. Relationship channels remain independent until the data justifies a higher-order structure.
15. Empty regions/gaps may form barriers.
16. Topology matters; circular variables must remain circular.
17. A barrier on one channel does not erase relationships on other channels.
18. Cubic/hypercubic promotion contains lower-dimensional relationships.
19. Commonality at one level may trigger descent into children: data-driven resolution selection.
20. Relationship strength is not truth probability.
21. The data should reveal cluster structure before labels are imposed.

## 20. Files in this package

```text
TrueSystems_Cubic_Cluster_Investigation_2026-09-10.md
starlink_cubic_probe_2026-09-10.py
starlink_run_summary_2026-09-10.json
starlink_frequency_roles_2026-09-10.csv
starlink_common_values_top100_2026-09-10.csv
README.md
```

The Python prototype is deliberately transparent. It does not train a model and does not assign semantic labels. It emits parent-local frequency roles, exact co-occurrence counts, signed positional pressure, cubic face pressure, parent summaries, and per-child source identity.
