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
