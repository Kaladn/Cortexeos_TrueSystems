# Evidence Formula Candidates

Status:

```text
diagnostic sandbox
not promoted core behavior
not final truth
```

Initial candidate:

```text
support_score =
  evidence_anchor_strength
+ citation_pressure
+ local_field_coherence
+ bridge_strength
- contradiction_pressure
- missing_required_anchor_penalty
```

## Boundaries

```text
no retrieval mutation
no ranking mutation
no qualification mutation
no speech mutation
no intake mutation
no final truth claim
no benchmark answer-key logic
```

This formula scores diagnostic rows after evidence has already been pulled and
classified. It does not decide admission, support, refusal, or speech.

Promotion requires a separate review, real-run receipts, and tests showing which
component changes should become base behavior.
