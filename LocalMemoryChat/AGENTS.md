# LocalMemoryChat agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

Read the repository-root `AGENTS.md`, then instructions under the package path
being used. LocalMemoryChat owns cited local-memory packets, not general truth.
The checkout has both `src/local_memory_chat/` and `local_memory_chat/`; do not
assume they are interchangeable without inspecting imports and the running
entrypoint.

## Production entrypoints and allowed operations

`src/local_memory_chat/cli.py:main` dispatches the CLI;
`src/local_memory_chat/memory.py:ask` builds the memory answer packet.
`src/local_memory_chat/gateway.py:inject_memory` is a separate gateway path.
Trace the caller and selected runtime profile before access.

## Forbidden operations and authority boundary

Do not replace TrueMem evidence retrieval with a memory packet or turn a cited
memory hit into source truth. A direct CLI or gateway call does not itself
establish the root system authorization route.

## Inputs, outputs, receipts, and provenance

Preserve memory profile, attached source identity, citation/address, packet
status, and receipt. Inspect returned records and files rather than assuming
that an import, index, or ask completed from a process exit alone.

## Known staged paths and next contract

Resolve the duplicate package layout against the actual import path before
editing or invoking. Read the chosen source and inspect real output for exact behavior.
