# TrueVision preset instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

Read the root and `TrueVision/AGENTS.md`. Preset data supplies parameters for
studio or renderer calls; it does not execute a renderer. Check the selected
loader and validator in `truevision_runtime/studio/studio_tooling.py` or the
actual renderer before use. Preserve preset identity and source; verify output
media and receipt separately.
