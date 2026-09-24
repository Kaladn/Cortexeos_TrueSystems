# TrueCore/truecore/live_agents agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and governing parent

This file governs `TrueCore/truecore/live_agents/`. Read `TrueCore/truecore/AGENTS.md` and all ancestor
`AGENTS.md` files first. The code facts below do not establish effects or authority.

## Production entrypoint

`creator.py:materialize` writes source-bound manifests;
`manifest.py:validate_agent_manifest` checks them;
`skill_index.py:build_index` derives an index; the runner under
`AGENTS/runner/truecore_agent_runner.py` controls one execution path. These are different stages. Index
membership and static usage help do not prove a worker was invoked or its
backend effect verified.

## Local code-defined surface

- `__init__.py`.
- `creator.py`: sha256_file (line 24), module_name (line 32), symbol_exists (line 42), load_rows (line 57), and 3 more source definitions.
- `generated_runtime.py`: resolve_callable (line 13), invoke (line 29), main (line 37).
- `manifest.py`: AgentManifestError (line 43), load_agent_manifest (line 47), validate_agent_manifest (line 54).
- `skill_index.py`: build_index (line 19), main (line 53).
- `worker_result.py`: WorkerResultError (line 44), canonical (line 48), digest (line 52), build_result (line 56), and 2 more source definitions.

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
