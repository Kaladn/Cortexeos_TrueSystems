# AGENTS

Repo-local TrueCore coded-agent artifacts.

## TrueCore Layout

- `catalog/agent_catalog.csv` follows the TrueCore `agent_catalog.csv` schema.
- `catalog/truecore_agents.csv` contains the lower-risk deployable set.
- `catalog/truecore_export.json` follows the documented ingestion JSON shape.
- `catalog/skill_index.json` is the manifest-derived system-wide worker index.
- `agents/*.agent.json` contains repo-local execution metadata.
- `runner/truecore_agent_runner.py` is the human-approval gate and executor.

All executions leaving the runner use `truecore.worker_result@1`. See
`../../../../../docs/TRUECORE_WORKER_RESULT_AND_SKILL_INDEX_CONTRACT.md`. New
worker families must use that envelope and regenerate the skill index.

The model-facing route to eligible read-only registered workers is
`truecore.registered_worker_bridge`. It retains this runner as the only worker
execution doorway and replaces model-supplied paths, modules and commands with
host-owned grants and resource bindings. See
`../../../../../docs/MODEL_REGISTERED_WORKER_BRIDGE.md`.

## Agents

Linux catalog capabilities can be materialized as real agents with:

```sh
python3 -m truecore.live_agents.creator \
  --catalog /path/to/agent_catalog.csv \
  --source-root /path/to/TrueCore \
  --agent-dir /path/to/generated/agents \
  --output-catalog /path/to/generated/catalog.csv \
  --operator-id <operator_id>
```

The creator verifies the local source file and AST symbol, hashes the source,
writes a validated manifest, and registers it in a runner-compatible catalog.
Creation also embeds exact code-derived usage and hashes in that manifest.
Set `TRUECORE_HELP_AGENT_DIR` to the selected `--agent-dir` so existing
`truecore help show agent:<operator_id> --tier 3` and TrueCore `help.query`
can read it. Help facts come from source, not catalog prose. Missing semantics
remain unresolved. Changing source invalidates the generated help until the
agent is recreated and reviewed; creation is not backend qualification.
The shared Linux runtime imports and invokes that exact source symbol; it does
not generate substitute capability code.

`temporal_causality_log_checker`

- Runs `temporal-causality/temporal_causality_log_checker.py` against a JSONL/Forge-style event log.
- Destruction score: `1`
- Reason: read-only log verification and stdout diagnostic reporting.
- Focus: temporal coherence, Lamport-style causality, replay safety, hash-chain integrity, and breach/error lead-up chains.
- No approval phrase is required for default read-only execution.

## Safe Inspection

List agents:

```bash
python AGENTS\runner\truecore_agent_runner.py list
```

Preview a command without running it:

```bash
python AGENTS\runner\truecore_agent_runner.py run temporal_causality_log_checker --param log_path=path\to\events.jsonl --dry-run
```
