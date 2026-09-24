# Control API agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

This file governs `control-api/`; read the repository-root `AGENTS.md` and the
narrower API package instructions. The API transports requests and results;
it does not own component authority.

## Production entrypoint and allowed operations

`src/truesystems_api/server.py:Handler.do_GET` and `do_POST` dispatch HTTP
routes to `src/truesystems_api/runtime.py`. Inspect each route's exact callee
before advertising it as a bot operation.

## Forbidden operations and authority boundary

The current `runtime.py:truemem_query` calls TrueMem directly; other routes
call TrueMachine, LocalMemoryChat, and ChatChain directly. The current handler
and runtime code show a query can reach TrueMem without SecureCore admission.
Do not describe those routes as SecureCore-admitted or use them to satisfy the
root operation law until the actual authorized path is connected and observed
through real operation. Do not create an alternate ingress to work around this
gap.

## Inputs, outputs, receipts, and provenance

Keep the original request and the component's structured result, IDs,
coordinates, status, and receipt intact. An HTTP 200 alone proves neither
authorization nor downstream effect.

## Known staged paths and next contract

The direct routes are active alternate paths, not dead code. Read
`control-api/src/truesystems_api/AGENTS.md` and the current server/runtime source before
changing a route.
