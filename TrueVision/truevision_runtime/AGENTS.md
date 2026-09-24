# TrueVision runtime instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

Read the repository-root and `TrueVision/AGENTS.md` before this file, then the
leaf instructions for `av_tools`, `llm_adapter`, `rendering`, `state_patterns`,
`studio`, or `learning_intake`.

## Production entrypoint and allowed operations

This package holds code called by `TrueVision/scripts/` and the studio server.
Trace the chosen script or HTTP handler through validation and the exact runtime
function. Importability is not evidence of production registration.

## Forbidden operations and authority boundary

Do not substitute state-recognition, a tool plan, a template, or a receipt for
pixel render or observed capture. Preserve the root system-admission boundary.

## Inputs, outputs, receipts, and provenance

The selected leaf function owns its schema and output. Preserve native media
state, frame index/FPS, source identity, generated-artifact classification,
manifest, and receipt; inspect files after execution.

## Known staged paths and next contract

Read the narrower `AGENTS.md` and matching source. Treat standalone
functions outside these packages as component callables whose incoming route
must still be traced.
