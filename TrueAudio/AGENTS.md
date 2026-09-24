# TrueAudio agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

Read the repository-root `AGENTS.md`, then narrower instructions under
`trueaudio_runtime/` or `scripts/`. TrueAudio owns derived audio state and its
replay; TrueVision may consume returned state but does not become its owner.

## Production entrypoints and allowed operations

`scripts/trueaudio_*.py:main` calls functions in `trueaudio_runtime/logging.py`,
`replayable.py`, and `replay.py`. Code-defined operations include
`log_pre_sound_state`, `log_machine_pre_sound_state`,
`log_file_replayable_audio_state`, `log_machine_replayable_audio_state`, and
`replay_replayable_audio_state`. Trace the selected script to its function and
the system-level caller before invoking it.

## Forbidden operations and authority boundary

Do not call replayed or sonified output the original source audio. Do not infer
speech transcript or human permission from audio state. A callable script does
not by itself satisfy the root authorization route.

## Inputs, outputs, receipts, and provenance

Use the selected function's declared source path or machine input, storage
root, sampling parameters, and limits. Inspect returned state, manifest,
receipt, and exact output files before reporting success. Preserve the source
identity and distinguish recorded state from reconstructed audio.

## Known staged paths and next contract

No production activation claim follows from a script filename alone. Read the
relevant runtime code and observed output for the exact selected operation.
