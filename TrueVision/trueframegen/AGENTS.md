# TrueFrameGen instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

Read the root and `TrueVision/AGENTS.md`. This package consumes existing
TrueVision state for reconstruction, interpolation, projection, and replay.

## Production entrypoint and allowed operations

`frame_upsampler.py:upsample_truevision_capture` and
`stream_upsample_truevision_capture` are called by corresponding
`scripts/trueframegen_*.py` entrypoints. `frame_gap_filler.py:fill_truevision_capture`
fills gaps in a state sequence. `temporal_causality_projector.py:project_capture_to_audio`
is a separate audio-conditioned projection. Trace the chosen script and source
state before running any of them.

## Forbidden operations and authority boundary

Interpolated, filled, or projected frames are derived media, not observed
capture. Do not claim a missing frame was recovered from source evidence.
State transformation does not grant system authorization.

## Inputs, outputs, receipts, and provenance

Keep original capture state, frame numbers/FPS, audio source where used,
interpolation/projector settings, output paths, manifests, and verification
result. Inspect written media and state logs before reporting completion.

## Known staged paths and next contract

Trace the selected projector or upsampler and its current caller. Do not infer
that all algorithms share the same input schema.
