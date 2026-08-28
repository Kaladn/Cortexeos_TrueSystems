# TopK Ladder Diagnostic

Status:

```text
diagnostic sidecar
not promoted core behavior
not final truth
```

Purpose:

```text
question
-> existing AWEAR query or batch packet
-> classify question anchors
-> preserve TopK pulled passages
-> classify evidence anchors
-> cross-classify question against evidence
-> walk rank 1 across all questions, then rank 2, through rank N
-> recount local TopK evidence only
-> report bridge / gap / conflict status
```

## Command

```text
awear topk-diagnostic --batch-summary <batch_run_summary.json> --out <folder> --max-rank 5
awear topk-diagnostic --packet <query-output.json> --out <folder> --max-rank 5
```

## Outputs

```text
TOPK_DIAGNOSTIC_PACKETS.jsonl
TOPK_LADDER_SUMMARY.json
TOPK_LADDER_SUMMARY.md
RUN_RECEIPT.json
rank_layers/TOPK_LAYER_1.jsonl
rank_layers/TOPK_LAYER_2.jsonl
rank_layers/TOPK_LAYER_3.jsonl
rank_layers/TOPK_LAYER_4.jsonl
rank_layers/TOPK_LAYER_5.jsonl
```

## Law

```text
No refusal for this diagnostic run.
No fake certainty.
Diagnostic packet, not final truth.
TopK evidence is preserved exactly as pulled.
Speech is per-rank diagnostic speech, not final answer speech.
```

## Typed Anchors

Legal words can change meaning by local shape:

```text
word != anchor
word + legal shape = typed anchor
```

Examples:

```text
section -> authority_anchor -> cite_statute_or_section
means -> definition_anchor -> definition_controls_meaning
unless -> exception_anchor -> check_if_exception_applies
shall / must / requires -> duty_anchor -> prove_required_condition
may -> discretion_anchor -> prove_allowed_not_required
```

Typed anchors are diagnostic metadata only.

## Boundaries

```text
no retrieval
no intake
no ranking mutation
no dataset mutation
no benchmark answer-key logic
no promotion into qualification
no speech renderer mutation
no final truth claim
```

Promotion requires a separate review after real run receipts show the diagnostic
is useful.
