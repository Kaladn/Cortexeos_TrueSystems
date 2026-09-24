# TrueCore/truecore agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and governing parent

This file governs `TrueCore/truecore/`. Read `TrueCore/AGENTS.md` and all ancestor
`AGENTS.md` files first. The code facts below do not establish effects or authority.

## Production entrypoint

`operator_boundary.py:OperatorBoundary.handle` accepts only the operations in
its `OPERATIONS` mapping and checks host grants before dispatch.
`registered_worker_bridge.py:RegisteredWorkerBridge.invoke` validates a
host-bound resource and registered worker. These are the current model-facing
mechanics to trace; do not infer a component route that is absent from the
operation map. `cli/main.py:main` is a separate component CLI.

## Local code-defined surface

- `__init__.py`.
- `app.py`: create_app (line 175).
- `bounded_jobs.py`: canonical (line 41), sha (line 45), regular (line 49), atomic (line 63), and 8 more source definitions.
- `config.py`: load_settings (line 9), validate_settings (line 26).
- `machine_navigation_bridge.py`: MachineNavigationBridgeError (line 49), MachineNavigationBridge (line 179).
- `model_host.py`: ModelHost (line 12), main (line 56).
- `openai_session.py`: OpenAIKeySession (line 23), OpenAIKeyVault (line 32).
- `operator_boundary.py`: strict_json (line 30), canonical (line 42), digest (line 45), Rejected (line 48), and 1 more source definitions.
- `operator_contracts.py`: contracts (line 37).
- `operator_workers.py`: dispatch_read_worker (line 18).
- `receipt_store.py`: digest (line 14), private_path (line 18), atomic_json (line 27), read_json (line 50), and 1 more source definitions.
- `registered_worker_bridge.py`: RegisteredWorkerBridgeError (line 32), RegisteredWorkerBridge (line 100).
- 2 additional direct source files; enumerate them before claiming complete coverage.

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
