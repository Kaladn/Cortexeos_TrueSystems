# TrueAudio/trueaudio_runtime agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and governing parent

This file governs `TrueAudio/trueaudio_runtime/`. Read `TrueAudio/AGENTS.md` and all ancestor
`AGENTS.md` files first. The source facts below are extracted from definitions
in this directory; they do not establish callability, effects, or authority.

## Production entrypoint

The source definitions below identify local code surfaces, not a proven production caller. Trace the incoming caller, validation, and return branch before using one.

## Local code-defined surface

- `__init__.py`.
- `ffmpeg.py`: find_media_executable (line 13), probe_audio (line 28), decode_pcm_f32_stereo (line 63).
- `logging.py`: utc_now (line 16), safe_slug (line 20), sha256_file (line 25), sha256_bytes (line 33), and 3 more source definitions.
- `machine.py`: capture_linux_pipewire_loopback (line 14).
- `replay.py`: replay_trueaudio_state (line 109).
- `replayable.py`: write_replayable_audio_state (line 98), replay_replayable_audio_state (line 201), log_file_replayable_audio_state (line 284), log_machine_replayable_audio_state (line 330).

## Allowed and forbidden operations

Inspect and use only the exact code-defined callable reached through the applicable parent authority path; do not create a substitute wrapper or ingress. Do not infer input meaning, output success, permissions, or safe
retry from a symbol name or catalog description.

## Inputs, outputs, authority boundary, and receipts

Read the selected function signature, validator, callers, return branches, and
persistence code before invoking it. Preserve returned IDs, coordinates,
status, native output, and receipts when present. Follow the root SecureCore
authority rule and any declared CompuCog observation requirement;
a direct callable is not a system grant.

## Known staged or dead paths

Runtime registration and dead-code status are unresolved from this local inventory. Search non-test callers and validate an actual run before assigning either status.

## Next contract to read

Open the selected source file, its caller, validator, return branch, and current runtime state. Use parent
instructions for cross-module handoffs. Record any unresolved behavior as
`UNVERIFIED`, not as an invented operation.
