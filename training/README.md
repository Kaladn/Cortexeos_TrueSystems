# TrueSystems operator-training builders

This directory contains builders, not trained weights or evidence authority.

`build_partial_system_usage_training.py` invokes TrueCore's deterministic code
intake across each explicitly owned TrueSystem. It emits three separated layers:

1. exact source files, classes, functions, methods, inputs, outputs, state,
   errors, assertions, hashes, coordinates, schemas, configuration, and tests;
2. source-observed call relationships with explicit resolved, ambiguous, or
   external/dynamic status; and
3. partial operator trajectories derived from tests and CLI definitions.

Each record is a building block. It does not prove that a definition is a
public operation, that it ran successfully, or that it is an agent.

Generated datasets belong outside this repository. Example:

```bash
python training/build_partial_system_usage_training.py \
  --systems-root . \
  --output-root "/path/to/output" \
  --workers 24
```

The builder preserves case, punctuation, spelling, signatures, and docstrings
exactly as Python exposes them. It performs no word splitting, stop-word
removal, case folding, Unicode normalization, symbol allocation, relationship
construction, or model training. If the generated material is admitted into
TrueMem, it must enter through DocuFilm like every other authoritative source.

Both intake and release selection accept `--workers`. The measured default is
24 logical workers on this 32-thread machine; `--workers 1` is the deterministic
debug/reference path. CPU-bound AST and relationship-envelope work uses
processes. Input hashing uses at most eight bounded I/O workers. Ordered JSONL
publication and identity hashing remain serial so output bytes and hashes stay
stable.

Benchmark the deterministic process-parallel stages with:

```bash
python training/benchmark_parallel_training_prep.py \
  --systems-root . \
  --corpus-root "/path/to/intake-corpus" \
  --workers 16 24 28
```

The benchmark compares every worker count to a single-worker reference and
records wall time, aggregate CPU time, effective core use, machine utilization,
throughput, peak resident memory, and output hashes.

## External generic source intake

`build_external_source_intake.py` consumes a frozen, provenance-bound source
manifest and fixed raw JSONL slice. It publishes three isolated namespaces:

- `HF_LANGUAGE_GENERIC`
- `HF_CODE_GENERIC`
- `LANGUAGE_TO_LOCAL_BRIDGES`

Every external release remains `NOT_LOCAL_TRUTH`. Empty reserved releases are
published explicitly, local records are never mixed into them, and the builder
performs no model training. The language adapter accepts source-supplied
relations. The Python code adapter preserves exact source and source-supplied
tests, extracts syntax-backed relations, and leaves every record
`EXTERNAL_GENERIC_UNBOUND`; it neither executes code nor claims correctness.
The bridge adapter accepts only explicitly curated phrase spans bound to frozen
Level 1 or Level 2 record hashes. It re-verifies the complete frozen release
artifacts, target selection hashes, coordinates, and each stored parent edge.
Multiple plausible targets are quarantined and stale hashes are rejected. A
bridge can select existing machinery but cannot create an operation, assert
runtime success, mutate local truth, or bind through name similarity alone.

```bash
python training/build_external_source_intake.py \
  --source-manifest "/path/to/frozen-source/source-manifest.json" \
  --output-root "/path/to/output" \
  --workers 24
```

Run the same fixed source with `--workers 1` and `--workers 24`. All semantic
artifacts must be byte-identical; `performance-receipt.json` is measurement-only
and is excluded from equivalence.

## Read-only local bridge resolution

`evaluate_language_to_local_bridges.py` evaluates natural-language location
requests against one verified `LANGUAGE_TO_LOCAL_BRIDGES` release. That release
is the resolver's complete local binding authority. Exact full-word anchors,
frozen file locations, relation labels, and already-stored relationship paths
form the candidate evidence. Source text is never case-folded or rewritten.

The resolver returns a target only when one frozen bridge has unique sufficient
evidence. Other requests return `ambiguous`, `unsupported`, `stale`, or
`missing`. Results retain the frozen target and selection hashes, relationship
path, repository identity, coordinates, and evidence receipt. Evaluation does
not execute operations, create bridges, consult generic data as local truth,
modify local records, or train a model.

```bash
python training/evaluate_language_to_local_bridges.py \
  --bridge-release "/path/to/LANGUAGE_TO_LOCAL_BRIDGES" \
  --cases "/path/to/evaluation-cases.jsonl" \
  --output-root "/path/to/output" \
  --workers 24
```

## Steering-training prerequisites

`build_steering_prerequisites.py` freezes a phrase with a finite supplied set
of existing local or visual bridge records. Candidate-set identity hashes the
sorted bridge IDs, so input ordering cannot alter candidate identity or the
expected existing target. The representation permits a future model to score
only supplied candidates; it cannot generate identifiers, relationships,
operations, evidence, or authority.

Memberships are assigned from documented source provenance and explicit target
meaning, never string similarity. Source groups, paraphrase families, exact
phrases, targets, and relationship paths cannot cross splits. Training and
validation records are published separately. Evaluation content remains sealed
behind identity-only `EVALUATION_RESERVED` manifests, including ambiguity,
negation, stale, missing, unsupported, wrong-system, wrong-symbol, and visual-
meaning cases.

This builder does not contain a model, optimizer, training loop, checkpoint, or
authorization change.

A versioned source manifest may provide an explicit
`evaluation_paraphrase_extensions` artifact. Each extension must name an
existing evaluation-reserved bridge, retain its source group, paraphrase
family, target, candidates, and expected outcome, and provide a distinct exact
phrase with explicit user-authorized assignment evidence. Extensions cannot
enter training or validation. The original source manifest remains byte-
reproducible when no extension is supplied.

```bash
python training/build_steering_prerequisites.py \
  --source-manifest /path/to/frozen-source-manifest.json \
  --output-root /path/to/output \
  --workers 24
```

## SYL evidence construction

`build_syl_evidence.py` builds the deterministic five-channel SYL release over
the frozen steering bridges. Each exact bridge phrase enters through DocuFilm.
The release retains source-object provenance, dataset-local stable anchors,
signed 6-1-6 lanes, exact two/three-anchor fragments, and recurring identical
fragment patterns as separate fields. It performs no model training and does
not authorize another optimizer run.

```bash
python training/build_syl_evidence.py \
  --source-manifest /path/to/steering-source-manifest.json \
  --prerequisite-release /path/to/steering-prerequisite-release \
  --output /path/to/output \
  --workers 24
```

## Training coverage matrix

`build_training_coverage_matrix.py` inventories frozen local operational and
SYL releases against an explicit curriculum. It deliberately reports every
concept as `UNTAGGED_NOT_MEASURED` until examples receive an auditable concept
assignment. Raw source volume is never treated as proof of training coverage.
The builder performs no intake, selection, model training, or authority change.

```bash
python training/build_training_coverage_matrix.py \
  --release-manifest /path/to/release-set-manifest.json \
  --syl-manifest /path/to/syl/manifest.json \
  --output /external/test/library/output/coverage-release
```

`build_assigned_training_coverage.py` verifies manually authored concept
assignments against exact frozen release records. It also counts sealed
steering reservations without opening their payloads. External-topic matches
from local code are reported only as local seeds; they do not close external
foundation gaps. The resulting acquisition ledger is a gate, not permission to
download an unreviewed corpus.

```bash
python training/build_assigned_training_coverage.py \
  --release-root /path/to/training-release \
  --assignments training/coverage_assignments.json \
  --steering-root /path/to/steering-prerequisites \
  --output /external/test/library/output/assigned-coverage
```

## Symbolic-foundations source curation

`build_symbolic_foundations_curation.py` verifies every byte in the frozen
three-family source pilot and publishes accepted, quarantined, and rejected
ledgers. NetworkX implementation and test sources are accepted for a later
exact-AST fixture adapter. Mathlib Lean sources and DESPITE state/planning
fixtures remain quarantined until their dedicated adapters can prove exact
declaration or cross-file trace boundaries. Curation never creates training
records, local truth, TrueMem 6-1-6 geometry, or model authority.

```bash
python training/build_symbolic_foundations_curation.py \
  --source-root /external/test/library/output/symbolic-foundations-source \
  --output /external/test/library/output/symbolic-foundations-curation \
  --workers 24
```
## Symbolic-foundations preparation

`build_symbolic_foundations_adapter.py` retains accepted NetworkX sources as
exact external flat files and records Python AST observations without assigning
graph meaning. Separately, it maps four local TrueSystems contracts into an
isolated deterministic six-byte, signed 6-1-6 curriculum namespace. Its 13:1
schedule changes presentation frequency only; observed source counts remain
unchanged. Mathlib and DESPITE remain quarantined, and no training occurs.

```bash
python training/build_symbolic_foundations_adapter.py \
  --curation-root /external/curation-release \
  --source-root /external/frozen-source \
  --output /external/preparation-release \
  --workers 24 \
  --local-to-external 13
```

`build_symbolic_foundations_representation.py` creates separate supplied-
candidate representations for local signed 6-1-6 windows and external
NetworkX AST call sequences. Splits are assigned by indivisible source groups;
evaluation payloads are sealed behind hash-only reservations. The 13:1
presentation schedule applies to training only. Validation and evaluation keep
their natural, separately reported domain counts.

```bash
python training/build_symbolic_foundations_representation.py \
  --adapter-root /external/replacement-adapter-release \
  --output /external/representation-release \
  --local-to-external 13
```

`build_symbolic_foundations_preflight.py` freezes the two scorer identities,
their supplied-candidate objectives, the no-score-fusion weave, XPU-only device
law, optimizer settings, 13-epoch stopping rule, and independent checkpoint
selection. It verifies every representation artifact without reading sealed
evaluation payloads. Training remains forbidden until both exact scorers are
implemented and deterministic XPU equivalence is proven.

```bash
python training/build_symbolic_foundations_preflight.py \
  --representation-root /external/representation-release \
  --model-source /read-only/retained-model-source \
  --output /external/preflight-release
```

`build_symbolic_foundations_scorers.py` implements both frozen supplied-
candidate scorers without training. It loads the retained decoder only from an
isolated clean source copy, enforces that selected identities come from each
record's supplied field, and runs train/validation-only forward and loss smoke
checks. CPU repeatability and bounded XPU equivalence are recorded while all
1,098 evaluation records remain sealed. No optimizer step or checkpoint is
created.

```bash
PYTHONPATH=TrueCore python training/build_symbolic_foundations_scorers.py \
  --representation /external/representation-release \
  --adapter /external/replacement-adapter-release \
  --clean-model-source /external/isolated-model-source \
  --output /external/scorer-readiness-release
```

After a consumed evaluation exposes an identity outside the frozen external
field, `build_symbolic_foundations_replacement.py` creates a fresh reservation
that permanently excludes the consumed source groups and checkpoints. Its only
fallback identity is `UNSEEN_EXTERNAL_CALL`. The sentinel means solely that the
exact external call identity was unseen by this scorer; original strings,
source hashes, AST-unit identities, and coordinates remain in evidence. It is
forbidden from local candidates, equivalence, operation authority, and
generated resolution. The replacement release is not training authorization.

```bash
PYTHONPATH=TrueCore python training/build_symbolic_foundations_replacement.py \
  --adapter /external/replacement-adapter-release \
  --consumed-representation /external/consumed-representation \
  --failed-experiment /external/failed-experiment \
  --output /external/replacement-reservation
```

`run_symbolic_foundations_replacement_experiment.py` is the one-use bounded
runner for an explicitly authorized replacement preflight. It trains the local
and external scorers independently, selects each checkpoint using validation
loss only, then opens the sealed evaluation once. Known external identities and
`UNSEEN_EXTERNAL_CALL` are reported separately. Authorization is always
consumed and revoked; weights remain external and are never deployed.

The authoritative continuation method is the Windows-origin
`provisional-chat-v1` implementation at retained commit `170ad86c`.
`build_historical_method_preparation.py` imports that source byte-for-byte and
changes only the admitted source package and its derived maps. The Linux-only
runtime change is injection of a `Path` for the historical hard-coded Windows
`CORPUS` location. `build_historical_method_preflight.py` performs the original
batch-1 forward/backward/clip probe with zero optimizer updates. Candidate
scorers, GRUs, and their checkpoints are historical evidence only and forbidden
from reuse. `run_historical_method_linux.py` must not be invoked without a new
bounded authorization tied to the published preflight.
