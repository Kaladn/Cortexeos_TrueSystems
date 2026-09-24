# control-api/src/truesystems_api agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and governing parent

This file governs `control-api/src/truesystems_api/`. Read `control-api/AGENTS.md` and all ancestor
`AGENTS.md` files first. The code facts below do not establish effects or authority.

## Production entrypoint

`server.py:Handler.do_GET` and `do_POST` dispatch routes into `runtime.py`.
`runtime.py:truemem_query` calls TrueMem retrieval directly;
`truemachine_pulse`, `memory_ask`, and chat routes likewise call components
without TrueCore admission in the current code. These are active alternate
routes, not proof of an authorized bot path. Follow the parent stop rule.

## Local code-defined surface

- `__init__.py`.
- `help.py`: Reference (line 18), Topic (line 24), list_topics (line 117), answer_help (line 125), and 1 more source definitions.
- `runtime.py`: install_component_paths (line 16), system_status (line 32), truemachine_verify (line 45), truemachine_pulse (line 57), and 4 more source definitions.
- `server.py`: Handler (line 25), serve (line 77), main (line 83).

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
