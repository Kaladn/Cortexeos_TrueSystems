# TrueVision state-pattern instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

Read the root, `TrueVision/AGENTS.md`, and `TrueVision/truevision_runtime/AGENTS.md`.
This package holds reusable signal-to-state patterns and atmosphere profiles.

## Production entrypoint and allowed operations

`audio_video_patterns.py:list_state_patterns` returns copies of declared
patterns; `choose_patterns_for_signal` selects from peak, valley, and level
summary fields. `atmosphere_weather.py:build_atmosphere_profile_from_native_capture`
reads native capture state and `build_atmosphere_toolset` creates reusable
state tools. Trace the calling AV tool or script for each operation.

## Forbidden operations and authority boundary

A selected pattern is a plan, not a rendered frame or observed fact. A derived
atmosphere profile cannot replace its source capture. No pattern grants tool
execution or SecureCore/TrueCore admission.

## Inputs, outputs, receipts, and provenance

Retain signal summary, pattern IDs, native capture identity, frame coordinates,
derived profile, and any written manifest. Check exact function result and
persisted output before reporting a toolset exists.

## Known staged paths and next contract

Trace the caller and selected mapping in code. Observe the real result before
claiming a pattern executes; pattern prose is not runtime evidence.
