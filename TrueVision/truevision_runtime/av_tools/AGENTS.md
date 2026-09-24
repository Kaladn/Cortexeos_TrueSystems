# TrueVision AV tool instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

Read the root, `TrueVision/AGENTS.md`, and `TrueVision/truevision_runtime/AGENTS.md`.
This package defines the AV tool registry, policy, runner, recalibration, and
receipt writer.

## Production entrypoint and allowed operations

`av_tool_runner.py:run_av_tool_call` validates through
`av_tool_policy.py:validate_tool_call` and dispatches in `_execute_validated_tool`.
`run_av_tool_job` groups 1–64 calls under one outer receipt. The studio server's
`_handle_av_tool_call` is one caller. Check that the named registry entry has a
dispatch branch before calling it.

## Forbidden operations and authority boundary

`video_render_preview` calls `_prepare_render_job` and returns a prepared
manifest. `video_execute_full_render` returns `execution_gated`; its registry
description is not proof of execution. Do not claim either branch rendered a
video. Validation and a component receipt do not replace system admission.

## Inputs, outputs, receipts, and provenance

Use the exact tool-call JSON accepted by policy; keep storage root and tool
arguments within that policy. Read `ok`, `execution_status`, result, receipt,
and `receipt_publication` separately. Receipt publication can be `unverified`
after an operation ran; do not auto-retry on that basis.

## Known staged paths and next contract

Inspect the dispatch and selected handler, then observe the actual operation
and receipt before relying on a registry description.
