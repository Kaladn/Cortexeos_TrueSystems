# training agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and governing parent

This file governs `training/`. Read `AGENTS.md` and all ancestor
`AGENTS.md` files first. The source facts below are extracted from definitions
in this directory; they do not establish callability, effects, or authority.

## Production entrypoint

This directory contains training code. No production invocation follows from these definitions; trace an admitted caller before any runtime claim.

## Local code-defined surface

- `analyze_historical_proof_of_use.py`.
- `benchmark_parallel_training_prep.py`: measured (line 21), parse_tasks (line 31), run_parse (line 42), relationship_tasks (line 50), and 2 more source definitions.
- `build_assigned_training_coverage.py`.
- `build_external_source_intake.py`: main (line 18).
- `build_historical_method_preflight.py`.
- `build_historical_method_preparation.py`.
- `build_hotpotqa_evidence_speech.py`.
- `build_hotpotqa_rag_benchmark.py`: main (line 7).
- `build_partial_system_usage_training.py`: main (line 18).
- `build_steering_prerequisites.py`: main (line 9).
- `build_syl_evidence.py`: main (line 7).
- `build_symbolic_foundations_adapter.py`.
- 15 additional direct source files; enumerate them before claiming complete coverage.

## Allowed and forbidden operations

Inspect code and current runtime state. Do not promote training or experimental calls to a production agent path by directory presence. Do not infer input meaning, output success, permissions, or safe
retry from a symbol name or catalog description.

## Inputs, outputs, authority boundary, and receipts

Read the selected function signature, validator, callers, return branches, and
persistence code before invoking it. Preserve returned IDs, coordinates,
status, native output, and receipts when present. Follow the root SecureCore
authority rule and any declared CompuCog observation requirement;
a direct callable is not a system grant.

## Known staged or dead paths

Treat training outputs as nonruntime unless current code-bound registration,
authority admission, and an observed production result prove promotion.

## Next contract to read

Open the selected source file, its caller, validator, return branch, and current runtime state. Use parent
instructions for cross-module handoffs. Record any unresolved behavior as
`UNVERIFIED`, not as an invented operation.
