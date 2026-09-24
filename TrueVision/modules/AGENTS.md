# TrueVision screen-grid module instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

Read the root and `TrueVision/AGENTS.md`. This directory currently contains
`screen_grid_mapper.py:ScreenGridMapper`.

## Production entrypoint and allowed operations

Inspect the class constructor and the actual caller before using its mapping.
The class definition alone does not establish a live capture or render route.

## Forbidden operations and authority boundary

Do not treat a grid mapping as raw pixels, observed capture, or a permission to
record a screen. Preserve source coordinates and the root admission boundary.

## Inputs, outputs, receipts, and provenance

Use the class's code-defined dimensions and mapping result. Compare against
the selected implementation and real input for bounds. No receipt
claim follows from a pure mapping call.

## Known staged paths and next contract

Production reachability remains unverified until the incoming caller is traced.
