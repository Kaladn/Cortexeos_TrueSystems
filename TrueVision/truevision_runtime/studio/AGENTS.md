# TrueVision studio-tool instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

Read the root, `TrueVision/AGENTS.md`, and `TrueVision/truevision_runtime/AGENTS.md`.
This package describes studio tools and render presets.

## Production entrypoint and allowed operations

`studio_tooling.py:list_studio_tools`, `list_render_presets`,
`get_render_preset`, `save_render_preset`, `preset_to_template`, and
`build_studio_tool_plan` are the code-defined surfaces. The HTTP server is in
`scripts/truevision_studio_server.py`; trace its handler before claiming a
studio operation is reachable.

## Forbidden operations and authority boundary

`build_studio_tool_plan` returns a plan. `preset_to_template` returns a
template object. Neither proves an encoder ran. A preset's boundary text is
not execution or authorization evidence.

## Inputs, outputs, receipts, and provenance

Inspect preset ID, storage root, generated template, source path, and returned
result. Verify the saved preset file and later render separately. Preserve
synthetic-media classification and any returned receipt.

## Known staged paths and next contract

Trace the exact server route and selected studio callable, then observe its
real result before claiming it operates.
