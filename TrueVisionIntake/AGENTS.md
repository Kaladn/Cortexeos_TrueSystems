# TrueVision Intake / DocuFilm agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

Read the repository-root `AGENTS.md`, then instructions under
`truevision_intake/` and `document_state/`. This component owns document and
glyph-state reading and the bounded handoff to TrueMem.

## Production entrypoints and allowed operations

`truevision_intake/document_state/state_reader.py:DocumentStateReader` reads
document state. `document_state/intake_control.py:IntakeControl` and
`intake_state_movie` govern stored-state progression. The handoff helper
`truevision_intake/docufilm_truemem.py:build_docufilm_truemem_hierarchy` builds
parent/contained structure for TrueMem. Trace the actual caller and source
typing before treating an input as admitted.

## Forbidden operations and authority boundary

Do not let TrueMem, TrueVision Generation, or an LLM silently replace DocuFilm
as document/glyph intake authority. A typed source candidate is not an
admitted dataset. Do not claim unsupported media recognition from a native
attachment or a filename.

## Inputs, outputs, receipts, and provenance

Preserve source bytes/hash, declared source type, page/glyph coordinates,
parent bindings, and handoff records. Inspect returned status and durable
state before claiming intake or publication completed.

## Known staged paths and next contract

Read `docs/INTAKE_CONTROL.md` for the documented state control, then verify
the selected reader and handoff in code and observed output.
