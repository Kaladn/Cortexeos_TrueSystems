# TrueCore materialized-agent directory instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

Read the root, `TrueCore/AGENTS.md`, `TrueCore/truecore/AGENTS.md`, and
`TrueCore/truecore/live_agents/AGENTS.md`. This directory named `AGENTS` stores
worker code, manifests, and a catalog; its name is not a governing file.

## Production entrypoint and allowed operations

`truecore/live_agents/manifest.py:load_agent_manifest` validates individual
manifests; `skill_index.py:build_index` derives a callability field from a
validated manifest's command. Inspect runner invocation and actual receipt
before calling any worker active.

## Forbidden operations and authority boundary

Do not infer activation from a manifest, catalog row, source hash, or directory
presence. Do not edit a generated hash by hand to make validation pass.

## Inputs, outputs, receipts, and provenance

Preserve manifest identity, source/entrypoint hash, command binding,
`truecore.worker_result@1` output, and terminal receipt. Verify the native
effect separately.

## Known staged paths and next contract

Read the specific `.agent.json`, code entrypoint, validator, host grant, and
observed result. Candidate or `IMPLEMENTED_NOT_REGISTERED` status remains
non-callable.
