# TrueMem relationship training shape

This document records the implemented shape as of 2026-08-29. It is an
implementation map, not authority to redesign intake or introduce a model.

## What is trained

TrueMem does not train on prose, symbols as meaning, or model-generated labels.
Its trained object is the deterministic map derived from the admitted anchor
stream. DocuFilm remains the only public intake authority.

For each paragraph block, the active intake:

1. preserves the original block text and source coordinates;
2. produces complete-word, boundary, and object anchors with `anchorize`;
3. assigns each anchor occurrence an exact zero-based position in that block;
4. counts each anchor occurrence;
5. counts every ordered neighbor at signed offsets `-6..-1,+1..+6` when the
   intake window is six;
6. writes anchors, signed relationships, and block positions to native binary
   artifacts; and
7. preserves block and numbered-sentence text for evidence convergence.

Relationships are therefore derived observations, never invented edges. The
same admitted anchor stream, window, and symbol assignment state reproduce the
same anchor and relationship counts.

## Active artifacts and record shapes

The live `docufilm-intake` path uses the constants and writers in
`TrueMem/src/truemem/engine/base.py`, `storage.py`, and `symbolizer.py`.

| Artifact | Active record | Purpose |
| --- | --- | --- |
| `anchor_counts.awbin` | `>6sQ` | six-byte symbol and occurrence count |
| `relation_counts.awbin` | `>6s6shI` | center symbol, neighbor symbol, signed offset, count |
| `block_anchor_postings.awbin` | `>6sIH` | symbol, block ordinal, position |
| `state/dataset_lexicon.json` | JSON | exact anchor string to active symbol resolution |
| `state/blocks.jsonl` | JSONL | original text, source lines, numbered sentences, anchors |
| `coordinates/coordinate_index.jsonl` | JSONL | source location resolution |
| `citations/citations.jsonl` | JSONL | citation markers and source coordinates |

The active symbol allocator is `workspace_monotonic_integer_6b`. It allocates a
non-overlapping range to each dataset within one runtime root. Symbols remain
opaque: callers exchange original strings and source coordinates, not symbol
values as meaning.

`TrueMem/src/truemem/engine/dataset_local_v2.py` contains a separate four-byte,
sorted-frozen, dataset-local format. It is tested as a standalone format but is
not called by `docufilm-intake`, query, or deeper/wider. It must not be described
as the active storage path or mixed with active six-byte artifacts.

## Current answer relationship path

The first answer path is implemented as follows:

```text
question strings
  -> exact query anchors
  -> dataset cloud gate and qualified source blocks
  -> resolved history ending at the current anchor
  -> at most six observed +1 candidates
  -> eight-field relationship vector for each candidate
  -> deterministic lexicographic branch ordering
  -> bounded branch retention/backtracking
  -> original-string answer path
  -> block and numbered-sentence source convergence
```

Each candidate retains these fields independently:

`Local, Back, Cloud, Forward, Support, Lift, DistanceStability, Direction`

No weighted scalar combines them. Candidate rank one is not forced. Choosing a
candidate moves the center and recalculates the next field. The optional
deeper/wider operation accepts the already-returned first prediction and walks
the same native relationship authority without mutating that answer.

## Existing measurements

The relationship graph currently exposes, per signed lane:

- exact count;
- lane-conditional probability;
- dataset background probability;
- lift and natural-log lift; and
- natural-log support confidence.

Across the twelve lanes it exposes distance distribution and concentration,
positive and negative support, and direction consistency. Multi-hop paths keep
conditional, lift, stability, and support measurements separate.

## Safe extension boundary

New relationship measurements may be added only as derived, versioned views of
the admitted counts and coordinates. An extension must:

- leave DocuFilm intake authority and the admitted anchor stream unchanged;
- leave original text and citation coordinates authoritative;
- preserve all twelve signed lanes independently;
- retain existing measurements instead of collapsing them into a magic score;
- identify the exact binary/schema version it reads;
- return original strings across dataset or model boundaries;
- remain deterministic for identical admitted data and configuration; and
- prove first-answer behavior separately from optional deeper/wider behavior.

Changing anchor identity, symbol allocation, record width, relation-window
semantics, or evidence convergence is a storage migration, not a relationship
feature. It requires an explicit migration decision and compatibility tests.

## Proven and not yet proven

Implemented in code:

- signed neighborhood counts during intake;
- native relationship binary storage and lexicon resolution;
- lane, edge, and multi-hop measurements;
- moving six-choice prediction with bounded branch retention;
- optional deeper/wider traversal after the first answer; and
- block/sentence citation convergence.

Not established merely by code presence:

- that the current lexicographic field order produces the best answer for a
  large real document;
- that every branch-warning label causes pruning (warnings are currently
  recorded while beam width performs the actual bounded pruning);
- that the dormant four-byte format should replace the active six-byte format;
  or
- that a successful unit test validates answer quality.

Those are experiment or migration questions and must remain visible rather than
being converted into documentation claims.
