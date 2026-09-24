# TrueVision Generation Operational Truth Lock

- Created: 2026-05-24
- Authority: code, tests, receipts, and this document outrank older planning docs when they conflict.
- Scope: TrueVision Generation only.

This document describes component-local media behavior. A local renderer or
AV tool being callable does not prove a system-level SecureCore/TrueCore and
TrueMachine admission path. Follow the repository-root and TrueVision
`AGENTS.md` files for current operating policy, and inspect executing code for
the exact path. The AV tool named `video_render_preview` currently prepares a
manifest, while `video_execute_full_render` returns `execution_gated` in
`truevision_runtime/av_tools/av_tool_runner.py`; neither branch proves a
rendered video.

## Core Law

```text
Record state.
Plan state.
Transform state.
Render pixels last.
Prove every run.
```

## Stack Boundary

```text
TrueVision is a local usable stack, not a platform backend.
Generation is an output lane, not the whole purpose.
New ideas enter as bounded workers with contracts, tests, manifests, and receipts.
No worker becomes a platform until local repeatability proves it needs one.
```

The stack exists to make media state usable by later tooling:

```text
capture/log
-> meter
-> profile
-> transform
-> validate
-> render or export
-> receipt
```

Platform-style plans, account systems, remote orchestration, and browser-control
detours stay out unless a proven local worker cannot operate without them.

## Current Live Abilities

```text
Rust native capture emits .tvcells state chunks
TrueFrameGen streaming renderer exists
SegmentField A-to-B transition method exists
state-media rendering lanes exist
audio feature extraction tools exist
TrueAudio analysis state exists
TrueAudio replayable spectral state exists
TrueSpeech speech/background timing exists
lyrics/script alignment candidates exist
AV-only tool registry exists
local studio/server exists
generated media remains out of git
```

Timing lock:

```text
Frame index and FPS are the clock.
Wall time is performance, not timeline truth.
Full-frame downstream tooling requires state_log_every = 1.
Sampled logs may be exact, but they are not full-frame truth.
```

## Parked Or Separate

```text
TrueAudio is a top-level sibling under `../TrueAudio/`.
TrueSpeech is a top-level sibling under `../TrueSpeech/`.
DocuFilm document/glyph intake is a top-level sibling under `../TrueVisionIntake/`.
AnchorWorks may consume symbols/state later, not raw audio.
TrueCore may gate retention later, not own audio replay.
UI product work is parked.
Generated videos/audio/state artifacts are local outputs, not repo truth.
Platform backend work is parked.
```

## Current Staged Work

```text
voice_state_v1 format
canonical audio feature contract
FFmpeg discovery normalization
script/lyrics manual correction path
audio-to-video sync contract
state-media element learning intake
```

## Boundary With AnchorWorks

TrueVision Generation can teach AnchorWorks method discipline:

```text
state first
render later
manifest every run
retain native write proof
one outer receipt per bounded job
do not claim what state does not prove
```

It does not become AnchorWorks intake authority directly.

## Boundary With TrueCore

TrueVision Generation is not a security logger.

```text
TrueCore logs security/ops.
TrueVision Generation records and renders media state.
Cross-system use must pass through validated state packets.
```

## Future Ability Area

```text
product-grade studio UI
long-run chunk rendering
selected-window capture
GPU capture/render acceleration beyond encode
voice timing editor
manual correction UI
cross-system harness proof
```

## Tiny Lock

```text
State is the source.
Pixels are the last mile.
Receipts separate proof from excitement.
```

## Bounded outer receipts

`run_av_tool_call` preserves each tool's native result, state, manifests and typed
proof. Its standalone outer receipt is compact and omits raw call/result/error
copies. Successful inventory reads return an ephemeral result without a durable
snapshot. `run_av_tool_job` groups up to 64 explicit independent calls into one
outer terminal receipt; the state-video watcher's post-capture calls use it.
A failed independent call does not silently suppress the remaining calls.

Operation execution and outer receipt publication are separate. A receipt write
failure cannot turn already completed media work into a rejected operation.
Unpublished proof remains explicit. A pending job reserves its identity and
cannot be automatically rerun; automated crash reconciliation is not qualified.
Native media validation, calibration, state/replay formats and source retention
remain separate. Teacher-state purge is not receipt housekeeping.
