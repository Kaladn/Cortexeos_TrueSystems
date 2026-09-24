# TrueVision agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

This file governs `TrueVision/`. Read the repository-root `AGENTS.md` first,
then the narrower `AGENTS.md` for the source directory being used. The source
files named below identify component behavior to trace; they do not grant a
caller permission to bypass the root operation boundary.

## Production entrypoints and allowed operations

- `scripts/truevision_studio_server.py:run` starts the local studio HTTP server;
  its `_handle_av_tool_call` calls `truevision_runtime.av_tools.av_tool_runner.run_av_tool_call`.
- `scripts/truevision_render_template.py:main` calls
  `truevision_runtime.rendering.template_renderer.render_template`, which
  encodes frames and can mux audio. `--max-seconds` limits a render.
- `scripts/truevision_edge_audio_river.py:main` calls
  `generate_edge_audio_river`, another concrete audio-reactive renderer.
- `native/truevision_capture_rs/src/main.rs` is the native capture binary.
  Read its local instructions before treating capture output as observed state.

These are component entrypoints, not proof that the system-level caller has
passed SecureCore admission. Trace the actual caller and any operation-specific
CompuCog observation requirement for each requested operation. Use the existing
path when it is qualified; report the missing edge when it is not.

## Forbidden operations and authority boundary

Do not substitute the AV-tool preview planner for a rendered video. In
`truevision_runtime/av_tools/av_tool_runner.py`, `video_render_preview` writes a
prepared job manifest and `video_execute_full_render` returns
`execution_gated`; neither branch itself proves a video was rendered. Do not
promote generated media into capture evidence or give TrueVision security,
desktop-action, document-intake, or audio/speech ownership.

## Inputs, outputs, receipts, and provenance

Inspect the selected entrypoint's signature and validator before supplying
media, templates, capture state, or output paths. Render output is synthetic;
capture state is observed. Verify the returned artifact and manifest on disk,
and distinguish execution status from receipt publication. Generated media and
operation receipts and generated media belong outside source control under the applicable contract.

## Known staged paths and next contracts

`transfer_to_truecore/truevision_agent_candidates/` contains candidate agent
handoff material, not registration proof. Read `docs/ACTIVE_TOOL_SURFACE.md`,
`docs/TRUEVISION_GENERATION_OPERATIONAL_TRUTH_LOCK.md`, and the narrower local
instructions as navigation; resolve any claim against executing code and observed runtime state.
