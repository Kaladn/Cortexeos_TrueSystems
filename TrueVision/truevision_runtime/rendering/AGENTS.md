# TrueVision rendering instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

Read the root, `TrueVision/AGENTS.md`, and `TrueVision/truevision_runtime/AGENTS.md`.
This package contains executable renderers, distinct from AV-tool planning.

## Production entrypoint and allowed operations

`template_renderer.py:render_template` is called by
`scripts/truevision_render_template.py:main`; it decodes audio, measures
features, encodes frames, writes a thumbnail, and optionally muxes audio.
`avatar_film_renderer.py:render_project`,
`seven_sector_rave.py:render_seven_sector_rave`, and
`markdown_frame_renderer.py:render_markdown_frame_set` are separate paths;
trace their caller and input contract independently.

## Forbidden operations and authority boundary

`render_template` currently accepts only `mirror_maze_realism` and
`storm_ember_city` visual modes. Do not assume an AV-tool draft naming
`edge_audio_river` can be passed directly to this renderer. Encoded synthetic
media is not observed capture. Component scripts do not grant system admission.

## Inputs, outputs, receipts, and provenance

For `render_template`, input is a template path; `--max-seconds` can shorten
the run and `--visual-only` disables muxing. Verify the returned paths, media
files, state trace, manifest, and encoder status. Preserve source audio and
template identity. Review the selected renderer's exact return branch.

## Known staged paths and next contract

Trace the selected renderer and its caller, then inspect real output media.
Do not infer support for other modes from a shared renderer label.
