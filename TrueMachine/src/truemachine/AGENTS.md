# TrueMachine/src/truemachine agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and governing parent

This file governs `TrueMachine/src/truemachine/`. Read `TrueMachine/AGENTS.md` and all ancestor
`AGENTS.md` files first. The code facts below do not establish effects or authority.

## Production entrypoint

`cli.py:main` dispatches TrueMachine commands. `repository_map.py:main`
builds the repository graph, while `repository_views.py` serves its views.
The TrueCore registered repository-map worker invokes this family through a
separate host-bound path. Trace the selected caller; a direct CLI command is
not proof of a model-facing admission route.

## Local code-defined surface

- `__init__.py`.
- `__main__.py`.
- `cli.py`: parser (line 15), main (line 55).
- `clock.py`: format_utc_ns (line 14), TimeSample (line 21), Clock (line 34).
- `command_observation.py`: run (line 66).
- `engine.py`: Collector (line 16), TemporalEngine (line 24).
- `fusion.py`: canonical_json (line 18), FusionStore (line 22).
- `model.py`: Observation (line 12), FusionPack (line 29).
- `navigation.py`: NavigationError (line 25), run (line 170).
- `repository_integrity.py`: canonical (line 27), digest_bytes (line 31), digest_file (line 35), create_snapshot (line 97), and 4 more source definitions.
- `repository_map.py`: canonical (line 44), stable_id (line 48), sha256 (line 53), git (line 57), and 20 more source definitions.
- `repository_views.py`: validate_scopes (line 22), run_view (line 320).
- 1 additional direct source files; enumerate them before claiming complete coverage.

## Allowed and forbidden operations

Use only the exact callable reached through the applicable parent authority path; do not create a substitute wrapper or ingress. Do not infer inputs, effects, permissions, or safe retry from names.

## Inputs, outputs, authority boundary, and receipts

Inspect the selected signature, validator, callers, return branches, and
persistence code. Preserve native result fields, IDs, coordinates, status, and
receipts where present. A direct callable is not a system grant; follow the root
SecureCore authority law and any declared CompuCog observation requirement.

## Known staged or dead paths

Registration and dead-code status are unresolved from this local inventory. Trace non-test callers and verify an actual run.

## Next contract to read

Read the selected source file, its caller, validator, return branch, and current runtime state. Use parent instructions
for cross-module handoffs. Mark unproven behavior `UNVERIFIED`.
