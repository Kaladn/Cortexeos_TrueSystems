# TrueVision script entrypoint instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

Read the root and `TrueVision/AGENTS.md`. Scripts are component entrypoints for
different concerns; their similar names do not make them interchangeable.

## Production entrypoints and allowed operations

- Capture: inspect `truevision_record.py`, `truevision_state_video_watcher.py`,
  and the native capture crate before choosing an observed-state path.
- Audio-driven rendering: `truevision_render_template.py:main` calls
  `render_template`; `truevision_edge_audio_river.py:main` calls
  `generate_edge_audio_river`; `render_seven_sector_rave_reactor.py` uses the
  separate seven-sector renderer. Choose by the actual requested output.
- Studio: `truevision_studio_server.py:run` serves routes that call runtime
  tooling. Inspect the exact handler before use.
- Replay/upsampling: `trueframegen_*.py` call `trueframegen/` functions and
  produce derived output, not original capture.

## Forbidden operations and authority boundary

Do not infer that every script is a registered system worker or that a plan
script rendered pixels. Never use a script as a bypass around root admission.
Do not rewrite flat scripts into a new framework merely to group them.

## Inputs, outputs, receipts, and provenance

Read each selected parser and callee, inspect source and output paths, and
verify returned manifests, files, status, and receipt. Keep generated media and
operation receipts outside the source repository.

## Known staged paths and next contract

Research-intake and experiment scripts are not automatically live production
routes. Read the matching runtime leaf instructions and source before use.
