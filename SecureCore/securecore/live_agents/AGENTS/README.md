# AGENTS

Repo-local SecureCore agent artifacts for the recovered security toolkit.

## SecureCore Layout

- `catalog/agent_catalog.csv` follows the SecureCore `agent_catalog.csv` schema.
- `catalog/securecore_agents.csv` contains the lower-risk deployable set.
- `catalog/securecore_restricted.csv` contains the firewall mutating agent.
- `catalog/securecore_export.json` follows the documented ingestion JSON shape.
- `agents/*.agent.json` contains repo-local execution metadata.
- `runner/securecore_agent_runner.py` is the human-approval gate and executor.
- `recovered-security/` contains the recovered PowerShell script, reports, and evidence snapshots.

## Agents

Linux catalog capabilities can be materialized as real agents with:

```sh
python3 -m securecore.live_agents.creator \
  --catalog /path/to/agent_catalog.csv \
  --source-root /path/to/SecureCore \
  --agent-dir /path/to/generated/agents \
  --output-catalog /path/to/generated/catalog.csv \
  --operator-id <operator_id>
```

The creator verifies the local source file and AST symbol, hashes the source,
writes a validated manifest, and registers it in a runner-compatible catalog.
The shared Linux runtime imports and invokes that exact source symbol; it does
not generate substitute capability code.

`recovered_security_snapshot`

- Runs `recovered-security/check-connections-enhanced.ps1` in report-only mode.
- Destruction score: `3`
- Reason: writes timestamped evidence files.
- Requires exact approval phrase: `APPROVE recovered_security_snapshot`

`recovered_security_firewall_enforcer`

- Runs the same script with `-BlockEgyptIP -BlockMeta`.
- Destruction score: `4`
- Reason: writes evidence files and adds Windows Firewall rules.
- Requires exact approval phrase: `APPROVE recovered_security_firewall_enforcer`
- Listed in `securecore_restricted.csv`.

`temporal_causality_log_checker`

- Runs `temporal-causality/temporal_causality_log_checker.py` against a JSONL/Forge-style event log.
- Destruction score: `1`
- Reason: read-only log verification and stdout diagnostic reporting.
- Focus: temporal coherence, Lamport-style causality, replay safety, hash-chain integrity, and breach/error lead-up chains.
- No approval phrase is required for default read-only execution.

## Safe Inspection

List agents:

```powershell
python AGENTS\runner\securecore_agent_runner.py list
```

Preview a command without running it:

```powershell
python AGENTS\runner\securecore_agent_runner.py run recovered_security_snapshot --dry-run
```

Preview temporal checker:

```powershell
python AGENTS\runner\securecore_agent_runner.py run temporal_causality_log_checker --param log_path=path\to\events.jsonl --dry-run
```

## Approved Execution

Report-only snapshot:

```powershell
python AGENTS\runner\securecore_agent_runner.py run recovered_security_snapshot --approve "APPROVE recovered_security_snapshot"
```

Firewall enforcement:

```powershell
python AGENTS\runner\securecore_agent_runner.py run recovered_security_firewall_enforcer --approve "APPROVE recovered_security_firewall_enforcer"
```

All new output defaults to `AGENTS/recovered-security/runtime`.
