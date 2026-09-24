# TrueCore agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

This file governs `TrueCore/`; read the repository-root `AGENTS.md` and each
narrower file on the path to the source. SecureCore is the sole operational
authority: it owns host-admitted identity and policy, permissions, agent
initiation, dispatch, registered coded workers, and receipts. CompuCog returns
observation and security findings; it does not authorize or dispatch work.

## Production entrypoints and allowed operations

`truecore/cli/main.py:main` defines the component CLI. Model-facing requests
enter `truecore/operator_boundary.py:OperatorBoundary.handle`; registered
worker calls pass through `truecore/registered_worker_bridge.py:RegisteredWorkerBridge.invoke`.
Inspect the current operation contract, host grants, resource bindings,
manifest validation, and worker result before claiming a worker can execute.
`truecore/live_agents/skill_index.py:build_index` marks callability from a
validated manifest's command; it does not prove backend effects.

## Forbidden operations and authority boundary

Do not call a component directly because its Python class exists. Do not turn
`IMPLEMENTED_NOT_REGISTERED`, proposed capabilities, static code help, or a
manifest without a runnable command into a live agent. Do not let model input
choose filesystem paths, modules, commands, or grants where the host owns them.

## Inputs, outputs, receipts, and provenance

Keep exact request, admitted resource IDs, worker identity and hashes, native
result, `truecore.worker_result@1` envelope, and terminal receipt. A receipt
records publication; verify the effect separately. Read the code-bound
operation schema and narrower module instructions before invocation.

## Known staged paths and next contracts

`truecore/live_agents/AGENTS/` is a manifest/catalog directory, not a
governing `AGENTS.md`. `evidence_workspace_agent.agent.json` states
`IMPLEMENTED_NOT_REGISTERED`. Read `docs/TRUECORE_BOUNDED_JOBS_CONTRACT.md` and
the source named above for the exact current host-admitted surface.
