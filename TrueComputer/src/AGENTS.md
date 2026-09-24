# TrueComputer/src agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and governing parent

This file governs `TrueComputer/src/`. Read `TrueComputer/AGENTS.md` and all ancestor
`AGENTS.md` files first. The code facts below do not establish effects or authority.

## Production entrypoint

`main.rs:run` parses `inspect`, `validate`, and `execute` requests.
`validate` checks the typed request against a live Hyprland snapshot;
`perform` delegates a fixed action; `verify_postcondition` checks the
observable result; `write_json_atomic` publishes the redacted receipt.
Read `TrueComputer/AGENTS.md` before constructing or executing a request.

## Local code-defined surface

- `main.rs`.

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
