# Pressure Coordination Agent

Lane name:

```text
pressure-coordination-audit
```

Purpose:

```text
existing reverse-walk trace
-> real system as-is lane
-> REAPER-only pressure mutation lane
-> combined strengths lane
```

This is a live side module. It does not replace retrieval, qualification, reverse
walk, or speech. It reads existing traces and writes a separate pressure
coordination audit.

## Command

```text
truemem pressure-coordination-audit --trace <ANSWER_REASONING_REVERSE_WALK_TRACE.jsonl> --out <folder>
```

## Outputs

```text
real_system_as_is/REAL_SYSTEM_TRACE.jsonl
reaper_only/REAPER_PRESSURE_MUTATION_TRACE.jsonl
combined_strengths/COMBINED_STRENGTH_TRACE.jsonl
PRESSURE_COORDINATION_SUMMARY.json
PRESSURE_COORDINATION_SUMMARY.md
receipts/run_receipt.json
receipts/no_mutation_receipt.json
```

## Rules

```text
real_system_as_is preserves the original support decision
reaper_only may mutate the judgment in its special file only
combined_strengths compares both lanes without overwriting either lane
```

## Boundaries

```text
no retrieval
no topK
no intake
no ranking mutation
no dataset mutation
no speech mutation
no model calls
no answer generation
no benchmark-specific field names
```

## Pressure Families

The v0 coordinator scores:

```text
anchor_pressure
citation_pressure
field_pressure
bridge_pressure
scenario_gap_pressure
contradiction_pressure
```

The reported `contradiction_pressure` remains a pressure value where high means
danger. For support-strength calculation, absence of contradiction contributes
positive strength.

## REAPER v1 Cap Rule

The first tuning rule is deliberately small:

```text
bridge_answerability_score(trace) -> 0.0..1.0
```

It uses only existing trace fields:

```text
matched question anchors
missing question anchors
local neighborhood blocks
pressure links
citations
```

Cap:

```text
if real_system_decision == needs_bridge
and bridge_answerability_score < 0.72:
    reaper_pressure_decision cannot exceed needs_bridge
```

This lets REAPER promote strong partial support, but stops it from declaring a
bridge complete before the trace has enough bridge answerability.
