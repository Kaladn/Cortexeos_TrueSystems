# TrueVision native capture instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

Read the root, `TrueVision/AGENTS.md`, and `TrueVision/native/AGENTS.md`.
This Rust crate contains the native
capture binary and separate state-generation binaries under `src/bin/`.

## Production entrypoint and allowed operations

`src/main.rs:main` calls `run`, which parses capture args, requests the Wayland
ScreenCast portal stream, samples through GStreamer, writes native cell chunks,
JSONL frame-state records, and a manifest. The `src/bin/` programs have their
own `main` functions; inspect each separately before use.

## Forbidden operations and authority boundary

Do not call derived state-generation binaries observed capture. Do not assume
portal approval from an executable's presence or treat a process exit as proof
that frames were captured. System admission remains governed by root policy.

## Inputs, outputs, receipts, and provenance

Preserve approved source, resolution/grid, FPS, frame numbers, source region,
run ID, native `.tvcells` chunks, JSONL, manifest, and receipt. Inspect the
returned paths and recorded frame count. Use an external `CARGO_TARGET_DIR` so
build output stays out of this repository.

## Known staged paths and next contract

Read `docs/RUST_COMPILED_CAPTURE_LANE.md` as navigation and verify the current
Rust parser and observed native operation before claiming a capability.
