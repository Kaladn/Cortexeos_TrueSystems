# TrueCore Truth And Stability Audit Rail

Purpose:

This is the short TrueCore audit rail. The full introspection prompt pack is the closer. Daily TrueCore work uses only the parts that protect system truth, stability, persistence, and code-trace receipts.

## Core Law

```text
Truth first.
Stability second.
Persistence third.
Every claim needs a code trace receipt.
```

## Use This When

```text
- inspecting whether a system is real or only planned
- checking whether a write path is safe
- checking whether a logger/reader/writer bridge is actually connected
- checking whether a model, agent, or tool has authority it should not have
- checking whether persistence can survive restart, crash, or bridge failure
- preparing a report before build, commit, or handoff
```

## Required Report Shape

For every important claim, include:

```text
claim:
status: implemented | partial | planned | blocked | unknown
file:
line/range:
code_trace:
persistence_trace:
stability_risk:
receipt:
```

Definitions:

```text
code_trace      = the exact code path that proves the claim
persistence_trace = where durable state is written, read, verified, or replayed
stability_risk  = what breaks if this part fails
receipt         = command, test, hash, output file, or direct source citation
```

## Hard Rules

```text
Do not infer runtime behavior from names.
Do not call a system active unless an entrypoint and call path prove it.
Do not call data durable unless a write/read/replay path proves it.
Do not call a bridge safe unless failure isolation is visible.
Do not call a model authorized unless identity and policy gates prove it.
Do not call a report truthful unless it cites source events or reader bundles.
Do not mark a TODO done without a receipt.
```

## Stability Checks

Ask these first:

```text
What happens if this component dies?
Can unrelated components keep running?
Can this bridge restart from durable state?
Is there a cursor, sequence, receipt, checkpoint, or replay path?
Can the writer prove what was written?
Can the reader prove what it read?
Can the report prove what it says?
```

## TrueCore Authority Boundaries

```text
Logs observe.
Forge orders.
Readers gather.
Agents investigate.
Models interpret.
Central Writer reports.
Policy Gate controls action.
User owns final authority.
```

## Model Rule

```text
An LLM may interpret shaped TrueCore data and help the local system.
It may not own truth, approve action, mutate state, call tools directly, or bypass policy.
```

## Bridge Rule

```text
No god bridge.
Each bridge has one job, one contract, one durable cursor or receipt path, and one failure boundary.
```

## Final Line For Reports

```text
END OF TRUECORE TRUTH REPORT
```
