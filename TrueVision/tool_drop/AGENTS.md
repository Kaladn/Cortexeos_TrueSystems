# TrueVision tool-drop instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

Read the root and `TrueVision/AGENTS.md`. This tree groups tool catalogs and
handoff material by concern. `tool_harness/tool_selector.py:load_tool_catalog`
can read the catalog, but selection only creates a plan; it does not invoke a
tool. Trace a selected tool to a current implementation, caller, permission,
result, and receipt before calling it active. Material under parked or copy-only
lanes is not promoted by directory placement.
