# TrueVision prompt-to-state adapter instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

Read the root, `TrueVision/AGENTS.md`, and `TrueVision/truevision_runtime/AGENTS.md`.
This package translates a user prompt into validated state JSON.

## Production entrypoint and allowed operations

`prompt_to_state_adapter.py:PromptToStateAdapter.translate` calls the supplied
`model_generate`, parses JSON, and invokes
`schema_validator.py:validate_state_request`; it can request bounded repairs.
`prompt_context_builder.py` builds context and a system prompt. Trace the
application caller supplying the model function before claiming this runs in
the live studio.

## Forbidden operations and authority boundary

The model draft is untrusted. Translation neither renders pixels nor grants
tool authorization. Do not pass invalid JSON to a renderer or interpret a
validated state request as observed evidence.

## Inputs, outputs, receipts, and provenance

Input is prompt plus optional project context; the result is `AdapterResult`
with `ok`, normalized `state`, `errors`, and `attempts`. The validator requires
scene, allowed renderer, positive duration, FPS 1–120, and
`safety_boundary.evidence=false`. Inspect these fields before handoff.

## Known staged paths and next contract

Read `instructions/LLM_TRUEVISION_STATE_MEDIA_INSTRUCTIONS.md` as guidance;
the actual validator and observed production call decide the current accepted
shape.
