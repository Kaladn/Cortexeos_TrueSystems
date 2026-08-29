# TrueVision Agent Candidates For TrueCore

This package stages TrueCore-bound agents only.

Workers stay in the organ repos. TrueVision workers stay with TrueVision.
TrueCore receives coordinating, reasoning, and zero-tolerance gate agents that
look across worker outputs.

```text
TrueVision logs.
TrueVision workers inspect.
TrueCore agents coordinate/gate.
Operators approve.
Receipts prove.
```

## Package Shape

```text
AGENTS/
  agents/
    *.agent.json
  catalog/
    agent_catalog.csv
    truecore_agents.csv
    truecore_export.json
  truevision-agents/
    *.py
HANDOFF_REPORT.md
```

The `*.agent.json` files mirror TrueCore's live-agent manifest contract:

```text
D:\TrueCore_Workspace\TrueCore\truecore\live_agents\manifest.py
```

## Boundary

These agents are staged candidates. Directory presence does not activate them.
TrueCore still owns promotion, registration, policy gates, and runtime tests.

## Zero-Tolerance Rule

```text
Only agents go to TrueCore.
Workers remain close to the organs.
No prompt-only agents.
No fake hashes.
No mutation without TrueCore approval.
```

