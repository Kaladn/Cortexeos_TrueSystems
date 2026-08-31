# Structural Binding M1 audit

Checkpoint: `ff3658a1cf550355e14c4f57a6be76ace62ae55e`

## Observed active path

```text
truemem docufilm-intake
  -> TrueMem pipeline reads UTF-8 text
  -> paragraph blocks
  -> anchorize
  -> anchor and signed relationship observations
  -> workspace_monotonic_integer_6b allocation
  -> native count/posting binaries and source indexes
```

The active six-byte artifacts are:

- `counts/anchor_counts.awbin` (`>6sQ`)
- `counts/relation_counts.awbin` (`>6s6shI`)
- `counts/block_anchor_postings.awbin` (`>6sIH`)
- `state/dataset_lexicon.json`
- `state/blocks.jsonl`
- coordinate and citation JSONL indexes

The separate four-byte dataset-local writer is dormant and is not an
integration target.

## Defect

`TrueVisionIntake/truevision_intake/docufilm_truemem.py` implements a DocuFilm
parent/contained handoff, but the active TrueMem command does not call it. The
active path therefore assigns the correct intake-authority label without an
executable TrueVision admission handoff.

## Compatible insertion

TrueVision compiles logical structures independently for each admitted block.
TrueMem aggregates their deterministic structure keys with ordinary anchors
before invoking the existing allocator. Once symbols exist, TrueVision records
are resolved into a compact structural graph artifact. Existing counts and
postings are written exactly as before.

This provides dataset-local structure symbols without a second namespace and
without inserting structural parents into the signed anchor stream.

## Measured access requirements

- exact structure lookup by dataset-local symbol;
- exact structure postings by symbol;
- parent-to-child enumeration;
- outgoing explicit-relation enumeration;
- reverse resolution to block, sentence, anchor, and byte coordinates;
- deterministic XPU projection to CSR-like arrays.

Source text is not duplicated in the structural artifact.

