# REAPER Pressure Coordination Notes

Status:

```text
research note
not product runtime
not promoted core behavior
```

Source references:

```text
research_reference_not_runtime/reasoning_toolbox/imported_reference_code/05_reaper_multi_anchor_scoring/reaper_cognitive_engine.py
research_reference_not_runtime/reasoning_toolbox/whole_pc_selected_references/phone_download_mtp/reaper_launcher.py
```

## What REAPER Is

The useful REAPER reference is a multi-anchor scoring coordinator.

It does this:

```text
event
-> multiple anchor analyzers
-> score + confidence per anchor
-> grouped dimensional vector
-> coherence / variance / consensus checks
-> state classification
-> persisted trace
```

It is not useful to AWEAR as a security launcher. The Guardian launcher is a
CortexOS/security entrypoint and depends on modules that are not present in this
repo. It should remain reference-only.

## Useful Transfer

REAPER's useful idea is not the threat labels.

The useful idea is:

```text
multiple anchor families can independently score the same event,
then a coordinator can decide whether the field is coherent enough
to admit a state.
```

For AWEAR, the translation is:

```text
event -> evidence packet or claim packet
anchor analyzers -> pressure analyzers
resonance vector -> pressure vector
threat/authentic/suspicious -> supported / partial / needs_bridge / contradicted
human likelihood -> evidence support likelihood
cognitive coherence -> evidence-field coherence
anomaly ratio -> contradiction or missing-bridge ratio
```

## AW-Native Pressure Vector

Candidate v0 shape:

```text
anchor_pressure
  evidence_anchor_coverage
  scenario_anchor_pressure
  ambiguity_pressure

citation_pressure
  cited_candidate_count
  coordinate_support
  local_window_support

field_pressure
  deeper_local_coherence
  wider_field_coherence
  bridge_presence
  contradiction_pressure

qualification_pressure
  support_likelihood
  confidence
  variance
  consensus_strength
```

This should remain a sidecar until proven.

## Coordinator Rule

The REAPER-style coordinator should not retrieve new evidence by itself.

It should read an existing packet or reverse-walk trace and ask:

```text
Do independent pressure families agree?
Is disagreement caused by scenario anchors, missing bridge, contradiction, or weak evidence?
Is the field coherent enough to admit support?
```

## Boundaries

```text
no model calls
no answer generation
no ranking mutation
no intake mutation
no benchmark-specific field names in core
no threat/security vocabulary in AW support decisions
no importing REAPER reference files into src/awrag
```

## Best First Sidecar

Name:

```text
pressure-coordination-audit
```

Input:

```text
existing answer-reasoning-reverse-walk trace
or existing AWEAR query packet
```

Output:

```text
pressure_vector
pressure_family_scores
consensus_strength
variance
bridge_needed
contradiction_pressure
support_decision
receipts
```

This is the cleanest way to use REAPER's structure without dragging in its
domain-specific authentication/security code.
