# TrueVision tool-harness instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

Read the root and `TrueVision/AGENTS.md`. This directory selects tools from a
scene/effect contract and writes a proposed invocation plan.

## Production entrypoint and allowed operations

`truevision_tool_harness.py:run_harness` reads a scene contract and tool
catalog, calls `tool_selector.py:select_tools_for_scene`, and writes selected,
rejected, plan, and harness-receipt JSON. `build_invocation_plan` sets
`invoke_now=false`, `mode=planned_not_executed`, and `tools_invoked=false`.

## Forbidden operations and authority boundary

A selected tool is not an executed worker. A harness receipt records planning,
not media generation or external service calls. Do not use this harness as a
new ingress around the existing TrueVision or root boundary.

## Inputs, outputs, receipts, and provenance

Preserve scene contract, catalog, selected/rejected tool IDs, plan, and
planning receipt. Verify those files on disk; do not report rendered output
from their existence.

## Known staged paths and next contract

Read the selector and causality policy source for exact selection behavior;
selection alone is not tool execution.
