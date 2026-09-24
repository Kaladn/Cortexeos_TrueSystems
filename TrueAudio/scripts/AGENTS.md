# TrueAudio/scripts agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and governing parent

This file governs `TrueAudio/scripts/`. Read `TrueAudio/AGENTS.md` and all ancestor
`AGENTS.md` files first. The source facts below are extracted from definitions
in this directory; they do not establish callability, effects, or authority.

## Production entrypoint

The source definitions below identify local code surfaces, not a proven production caller. Trace the incoming caller, validation, and return branch before using one.

## Local code-defined surface

- `trueaudio_log_file_replayable.py`: main (line 13).
- `trueaudio_log_machine_pre_sound.py`: main (line 13).
- `trueaudio_log_machine_replayable.py`: main (line 13).
- `trueaudio_log_pre_sound.py`: main (line 13).
- `trueaudio_replay_replayable.py`: main (line 13).
- `trueaudio_replay_state.py`: main (line 13).

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
