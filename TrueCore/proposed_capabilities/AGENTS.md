# Proposed TrueCore capabilities instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

Read the root and `TrueCore/AGENTS.md`. `catalog.json` lists proposed,
non-callable capabilities; read this directory's README before changing one.
Do not describe a placeholder, graph archive policy, or plan as a registered
worker. Promotion requires a current executable entrypoint, validation,
authorization, an observed production effect, and an external receipt.

For the dataset currently in focus, `GRAPH_ARCHIVE_POLICY.md` requires a
losslessly verified ZIP of prior graph snapshots with dataset, scope, snapshot,
known source commit, manifest hash, and UTC archive time in provenance. Keep
native manifests and member hashes. Do not silently delete pinned originals or
put archival work in the AV/intake hot path. The policy does not establish an
implemented archive worker. Proposed catalog records remain non-callable;
read this directory's README before any promotion. New implementations belong
outside this repository in the refactored PluginRunner; historical reference
code remains inactive.
