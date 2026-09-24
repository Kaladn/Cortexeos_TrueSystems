# Clearbox Chat-Chain agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

Read the repository-root `AGENTS.md` and the exact selected server or core
entrypoint source before planning.
Chat-Chain owns durable conversation, turn, branch, and continuation order.

## Production entrypoint and allowed operations

`src/clearbox_chat_chain/server.py:Handler` dispatches the local HTTP service
to `core.py:ChatChain` and its `Repository`. Inspect the called method and
database binding for each operation before claiming a conversation changed.

## Forbidden operations and authority boundary

`core.py` also has direct echo and OpenAI-compatible model adapters. Their
presence does not establish TrueCore admission or TrueMem evidence. Do not
present generic chat output as cited evidence or use the service as an
alternate system authority route.

## Inputs, outputs, receipts, and provenance

Preserve conversation/turn IDs, ordering, branch/continuation relation, storage
status, and any returned receipt. Verify persistence before reporting a turn
saved or continued.

## Known staged paths and next contract

Read the current server/core code and observed persistence. The proposed automatic daily-chat
sealing lifecycle is not established by this module's current HTTP routes.
