# TrueCore/truecore/training agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and governing parent

This file governs `TrueCore/truecore/training/`. Read `TrueCore/truecore/AGENTS.md` and all ancestor
`AGENTS.md` files first. The code facts below do not establish effects or authority.

## Production entrypoint

This directory contains training code. No production invocation follows from these definitions.

## Local code-defined surface

- `__init__.py`.
- `bridge_resolver.py`: word_anchors (line 44), FrozenBridgeAuthority (line 70), resolve_query (line 135), BridgeResolverEvaluation (line 211), and 1 more source definitions.
- `code_cloud_scoring.py`: score_code_cloud_lane (line 10).
- `code_glyph_curriculum.py`: build_code_glyph_curriculum (line 98).
- `code_intake.py`: build_training_corpus (line 237).
- `coverage_assignment.py`: build_assigned_coverage (line 18).
- `coverage_matrix.py`: canonical (line 16), digest (line 20), build_coverage_matrix (line 79).
- `external_source_intake.py`: canonical (line 35), digest (line 39), ExternalSourceIntakeBuilder (line 376), build_external_source_intake (line 501).
- `function_method_curriculum.py`: build_function_method_curriculum (line 77).
- `historical_method_equivalence.py`: canonical (line 11), sha (line 12), rows (line 13), write (line 14), and 1 more source definitions.
- `historical_method_preflight.py`: build_historical_preflight (line 9).
- `historical_proof_of_use.py`: analyze (line 11).
- 17 additional direct source files; enumerate them before claiming complete coverage.

## Allowed and forbidden operations

Inspect code and current runtime state; do not promote training or experimental
calls into a production path by directory presence. Do not infer inputs,
effects, permissions, or safe retry from names.

## Inputs, outputs, authority boundary, and receipts

Inspect the selected signature, validator, callers, return branches, and
persistence code. Preserve native result fields, IDs, coordinates, status, and
receipts where present. A direct callable is not a system grant; follow the root
SecureCore authority law and any declared CompuCog observation requirement.

## Known staged or dead paths

Treat training output as nonruntime unless current code-bound registration,
authority admission, and an observed production result prove promotion.

## Next contract to read

Read the selected source file, its caller, validator, return branch, and current runtime state. Use parent instructions
for cross-module handoffs. Mark unproven behavior `UNVERIFIED`.
