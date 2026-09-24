# TrueVision UI instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

Read the root and `TrueVision/AGENTS.md`. This directory contains
`state_presentation_boardroom.html`, a presentation surface.

## Production entrypoint and allowed operations

Inspect the HTML and its data-loading code before claiming a live UI route.
Rendering a view does not invoke a TrueVision worker by itself.

## Forbidden operations and authority boundary

Do not promote displayed derived state to capture evidence, or treat UI controls
as system-authorized operations without tracing their actual caller.

## Inputs, outputs, receipts, and provenance

Preserve displayed source and artifact identities; verify any claimed update
in the underlying result and receipt, not just the page.

## Known staged paths and next contract

Whether this HTML is served by the live studio remains unverified here. Trace
the server route and file reference before advertising it.
