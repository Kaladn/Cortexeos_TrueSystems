# Symbol-Only Model Experiment — Flat Corpus Baseline

Status: **future experiment contract; not implemented, prepared, authorized, or trained**.

This document freezes a deliberately narrow baseline experiment. It does not
authorize corpus construction, optimizer execution, checkpoint creation,
deployment, or a subsequent 6-1-6 experiment.

## Purpose

Test whether the existing governed dataset can train the existing local model
when the entire training corpus is represented only by its existing
dataset-local symbols.

Hypothesis:

> If stable identity, occurrence, ordering, and repeated relationships carry
> the learnable information, replacing every admitted source anchor with its
> existing dataset-local symbol should still allow a model to learn useful
> corpus structure.

This is a baseline, not a redesign of TrueMem, TrueVision, traversal,
retrieval, training architecture, or the lexicon. Explicit 6-1-6 training
structure is forbidden in this experiment and remains a later comparison.

## Law 1 — Existing dataset and lexicon only

Use the existing governed dataset, existing dataset-local lexicon, and current
symbol allocation exactly as admitted.

Do not:

- create a new lexicon;
- merge or invent symbols;
- normalize source anchors differently;
- use a global vocabulary;
- use BPE or subword processing;
- derive embeddings from source text;
- translate symbols back into text for model input;
- use an LLM to classify, summarize, or rewrite the corpus.

The training representation may use the real fixed-width symbol identities or
deterministic dense IDs derived reversibly from them.

## Law 2 — Flat symbolic corpus

Produce an experimental derivative in which admitted source anchors are
replaced by their existing symbols while preserving exact occurrence order.

Model features must contain no:

- human-readable words;
- BPE pieces;
- semantic labels;
- inferred classes;
- pretrained identities.

Preserve document, block, sentence, and occurrence ordering already represented
by intake. Any boundary marker required by the retained trainer must be a
documented deterministic symbol. The authoritative dataset remains untouched.

## Law 3 — Lexicon remains outside the model

The lexicon is the reversible human/evaluation boundary:

```text
model world: symbols only

human inspection:
symbol ↔ dataset lexicon ↔ admitted source anchor
```

The lexicon may only:

- generate the derivative corpus;
- verify reversibility;
- decode input or output for inspection;
- construct evaluation reports;
- resolve generated symbols to admitted anchors.

Lexical strings must never become training features.

## Law 4 — Retain the historical training method

Use the existing runnable local symbolic-model training path as closely as
possible. Do not introduce a replacement architecture merely because the data
is now expressed as symbols.

Preserve where applicable:

- dimensions and layer count;
- attention configuration;
- causal objective;
- context length;
- optimizer and scheduler;
- training budget;
- device behavior;
- validation cadence;
- stopping and checkpoint-selection laws.

This experiment changes the data representation, not several variables at
once. Any unavoidable trainer adaptation must be the smallest deterministic
method-equivalent change and must be documented before optimizer execution.

No pretrained model. Train from scratch.

## Law 5 — Exact symbol identity

A dense training ordinal is permitted only as a perfect reversible bijection:

```text
permanent dataset-local symbol ↔ dense training ID
```

Requirements:

- no collisions;
- no collision-tolerant hashing;
- no semantic grouping;
- no approximate identity;
- no cross-symbol sharing.

Freeze and hash the exact mapping before training.

## Law 6 — Symbolic training and inference

Training and inference receive symbols only. After training:

1. supply symbolic evaluation input;
2. capture raw symbolic output first;
3. preserve unresolved, invalid, and repetitive outputs unchanged;
4. decode a separate human-readable view through the frozen lexicon.

Both raw and decoded outputs are required. Decoding is inspection, not model
input and not output repair.

## Law 7 — Prior-run control

Compare against the closest prior symbolic/whole-word model experiment using
equivalent measurements where possible:

- vocabulary size;
- parameter count;
- examples, windows, and symbol occurrences;
- optimizer updates;
- context length;
- training and validation loss curves;
- held-out cross-entropy and meaningful Top-K measurements;
- wall time;
- peak RAM and VRAM;
- GPU utilization;
- raw generated symbol sequences;
- decoded inspection sequences;
- invalid or unresolved symbols;
- repetition behavior.

Do not claim superiority from visually pleasing decoded text.

## Law 8 — Pre-training corpus verification

Before optimizer update 1, prove:

1. Every corpus item reverses to its exact admitted anchor.
2. Symbol order equals admitted occurrence order.
3. No symbol collision exists.
4. No admitted source anchor was silently dropped.
5. No human-readable lexical feature entered model input.
6. Source authority remained unchanged.
7. Two independent derivative builds are byte-identical.

Freeze hashes for:

- source dataset authority;
- lexicon;
- permanent-symbol/dense-ID mapping;
- symbolic corpus;
- train/validation/test reservations;
- training configuration.

## Law 9 — Flat means flat

Forbidden during this baseline:

- 6-1-6 matrices or lanes;
- context-cloud embeddings;
- structural relationship weights;
- parent/child graph features;
- traversal paths;
- pressure points;
- relation labels;
- derived fragments;
- grouped-pattern channels.

The later comparison may be:

```text
A. flat dataset-local symbolic sequence
B. explicit signed 6-1-6 symbolic structure
```

Experiment A must not contain features from B.

## Execution stages

### Stage 1 — Inspect

Locate and verify:

- governed dataset;
- authoritative lexicon and symbol allocation;
- prior runnable model/trainer implementation;
- prior configuration, checkpoint, curves, and report.

Make no changes. Record exactly what can be reused. Stop only for ambiguous,
inconsistent, stale, or missing authority.

### Stage 2 — Build derivative corpus

Construct the deterministic anchor-to-symbol stream outside source authority.
Generate and hash:

- flat symbolic corpus;
- reversible dense-ID table, if required;
- corpus manifest;
- source and derivative statistics;
- complete verification receipt.

Continue only after exact reversibility and two-build determinism pass.

### Stage 3 — End-to-end fixture

Run a small fixture through:

```text
symbolic source
→ training representation
→ retained trainer
→ fixture checkpoint
→ symbolic inference
→ separate decoded inspection
```

Prove that lexical text never enters model features. Stop and report the exact
boundary if the fixture fails.

### Stage 4 — Full bounded training

Train once from scratch on the complete flat symbolic derivative using the
retained method. Use the Intel Arc Pro B70 for model work and parallelize safe
CPU preparation while preserving operator headroom, determinism, and an
interrupt path.

Record utilization, thermals, RAM, VRAM, throughput, wall time, bottlenecks,
every optimizer update, validation event, checkpoint identity, and artifact
hash.

### Stage 5 — Symbolic inference

After checkpoint selection is frozen, evaluate with symbolic inputs only.
Measure:

- continuation behavior;
- held-out next-symbol prediction;
- occurrence-pattern learning;
- repetition;
- symbol validity;
- sequence coherence.

Capture raw output before lexicon decoding.

### Stage 6 — Comparison

Answer without retuning:

1. Did flat dataset-local symbols train successfully?
2. Did loss meaningfully decrease?
3. Did held-out prediction demonstrate learned structure?
4. Did generation produce valid dataset symbols?
5. How did behavior compare with the prior representation?
6. Is readable lexical form demonstrably necessary?
7. What does the baseline establish before explicit 6-1-6 training?

## Success boundary

The experiment succeeds as an experiment when:

- the complete derivative is deterministic and reversible;
- the mapping is an exact bijection;
- model inputs contain no source words;
- bounded training completes under the frozen method;
- inference remains symbolic;
- held-out and generation results are honestly preserved.

Good prose is not required. Falling loss alone is not sufficient evidence of
useful learned structure.

## Prohibitions

- No dataset-specific answers or expected continuations.
- No benchmark-oracle steering.
- No manually supplied target paths.
- No new semantic labels.
- No LLM corpus transformation.
- No BPE or pretrained embeddings.
- No 6-1-6 training features.
- No model redesign unless the retained trainer literally cannot accept the
  frozen symbolic vocabulary.
- No source-authority mutation.
- No hidden failed or repetitive generations.
- No success claim without held-out symbolic evaluation.
- No deployment or runtime connection.
- No automatic continuation into the structured 6-1-6 experiment.

## Required final report

Report:

- source dataset identity;
- lexicon identity and hash;
- derivative corpus path and hash;
- symbol and occurrence counts;
- dense-ID mapping, if used;
- model identity and configuration;
- parameter count;
- training configuration and split manifests;
- complete loss progression and held-out metrics;
- training time and hardware measurements;
- raw symbolic inference samples;
- separately decoded samples;
- comparison with the prior run;
- failures and anomalies;
- whether the hypothesis remains plausible.

End with exactly one of:

```text
FLAT_SYMBOL_BASELINE: PROVEN
FLAT_SYMBOL_BASELINE: PARTIAL
FLAT_SYMBOL_BASELINE: FAILED
```

Stop after reporting. Do not begin explicit 6-1-6 structured training.
