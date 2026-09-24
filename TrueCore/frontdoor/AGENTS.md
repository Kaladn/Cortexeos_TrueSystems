# TrueCore frontdoor instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

Read the root and `TrueCore/AGENTS.md`. This Rust crate has its own executable
entrypoint in `src/main.rs`.

## Production entrypoint and allowed operations

Inspect `src/main.rs:main`, its request parsing, downstream call, and real output
before claiming a frontdoor operation works. Compilation alone does not prove
an authorization or output contract.

## Forbidden operations and authority boundary

Do not infer that this frontdoor makes every Python TrueCore capability
model-facing. Preserve the host-grant and worker-registration rules in
`TrueCore/AGENTS.md`.

## Inputs, outputs, receipts, and provenance

Preserve exact request and response fields and verify any receipt or side
effect separately. Use an external Cargo target directory.

## Known staged paths and next contract

Inspect the Rust source and current runtime state; no broader activation follows from
the crate name.
