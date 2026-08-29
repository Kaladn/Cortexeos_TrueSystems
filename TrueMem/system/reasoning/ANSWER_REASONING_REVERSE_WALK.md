# Answer Reasoning Reverse Walk

Lane name:

```text
answer-reasoning-reverse-walk
```

Purpose:

```text
supplied answer
-> answer anchor extraction
-> reverse topK search into corpus
-> candidate evidence passages
-> local neighborhood pressure
-> compare back to question anchors
-> support decision
```

This is not answer generation. It is a sidecar audit that checks whether a supplied claim can walk back to cited dataset evidence and then back toward the original question.

## Modes

`blind_reverse_walk`

Uses `supplied_answer` as the starting claim. It does not seed retrieval from an expected passage or benchmark label.

`paired_set_verify`

Uses a generic `audit_reference` to verify a named evidence item after the answer-rooted walk. This is support validation, not retrieval scoring.

## Boundaries

```text
no LLM
no model call
no answer generation
no benchmark answer leakage into intake
no ranking mutation
no dataset mutation
no speech mutation
adapter owns benchmark metadata
core receives generic claim packets
```

## Claim Packet Shape

Core accepts JSONL claim packets with generic fields:

```json
{
  "claim_id": "q1",
  "question": "...",
  "supplied_answer": "...",
  "audit_reference": {"kind": "passage_id", "value": "..."},
  "metadata": {}
}
```

Benchmark adapters may translate dataset-specific fields into this shape. The core sidecar does not name benchmark gold fields.

