# TrueCore agent-catalog instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

Read ancestor `AGENTS.md` files. `skill_index.json` is derived by
`TrueCore/truecore/live_agents/skill_index.py:build_index` from validated
manifests. It reports declared identity, hashes, and whether a command list is
present. It does not prove a worker ran, succeeded, or is authorized for this
caller. Refresh through the existing builder after a manifest/source change;
do not invent capability descriptions from catalog prose.
