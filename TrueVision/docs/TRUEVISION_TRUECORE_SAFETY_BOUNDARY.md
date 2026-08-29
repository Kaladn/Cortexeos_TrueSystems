# TrueVision TrueCore Safety Boundary

## Purpose

Define TrueCore's relationship to TrueVision.

```text
TrueCore is not the middleman brain.
TrueCore is the guardrail, policy gate, receipt layer, and runtime safety wrapper.
```

## TrueVision Must Not

- make security decisions
- promote observed state into operational truth
- retain raw/detail logs without a retention rule
- mutate policy
- control browsers or desktop windows without explicit operator-approved tooling
- write outside declared storage/output paths

## TrueCore Provides

```text
policy gate
permission boundary
retention rule
receipt validation
runtime health check
forensic preservation when suspicious
```

## Retention Law

```text
Normal time becomes receipts.
Suspicious time becomes evidence.
Everything else expires.
```

## Integration Rule

TrueVision writes manifests and receipts. TrueCore may verify them, gate retention, and preserve suspicious windows.

TrueVision does not become TrueCore.
