# TrueCore agent-manifest instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

Read ancestor `AGENTS.md` files. This directory contains `.agent.json`
manifests. Validate a selected manifest with
`TrueCore/truecore/live_agents/manifest.py`, inspect its executable command and
source hash, and trace its host grant and runner. A manifest without a command
is indexed but not callable. Keep `IMPLEMENTED_NOT_REGISTERED` as staged.
Preserve native result, worker envelope, and receipt; do not claim backend
effects from manifest text.
