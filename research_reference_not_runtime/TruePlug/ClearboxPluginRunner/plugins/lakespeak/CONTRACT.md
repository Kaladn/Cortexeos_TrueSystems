# LakeSpeak Plugin Boundary Contract

**Version:** lakespeak_query@1 / lakespeak_answer@1
**Status:** FROZEN. Base only calls `plugin.query()` and renders outputs.

## Plugin Architecture

```
Plugin 1 — LakeSpeak (Grounded Retrieval + Citations)
Plugin 2 — LakeSpeak-Eval (Metrics + Drift + Proof)
Plugin 3 — LakeSpeak-Train (Training Everything)
```

All three are independent. Base never knows Plugin 2 or 3 exist.

## Request Envelope (lakespeak_query@1)

What base sends to the plugin:

```json
{
  "schema_version": "lakespeak_query@1",
  "query": "forest",
  "mode": "grounded|allow_fallback",
  "topk": 8,
  "session_id": "ui",
  "caller": "human|system|ai"
}
```

### Mode Semantics

- `mode=grounded` — No ungrounded answers. If no evidence, REFUSE.
- `mode=allow_fallback` — May serve ungrounded with explicit caveats.

## Response Envelope (lakespeak_answer@1)

What the plugin returns to base:

```json
{
  "schema_version": "lakespeak_answer@1",
  "source": "lakespeak",
  "answer_text": "...",
  "grounded": true,
  "refused": false,
  "refusal_reason": null,
  "suggested_next_mode": null,

  "citations": [
    { "coord": "INGEST:rcpt_...", "subject": null, "note": "Retrieval score: 0.42" }
  ],

  "caveats": [],

  "trace": { "schema_version": "reasoning_trace@1", "...": "..." },

  "receipt": {
    "lake_snapshot_id": "snapshot_...",
    "index_hash": "sha256:...",
    "evidence_set_hash": "sha256:..."
  }
}
```

## Refusal Semantics

### No hits, lexicon confirms term, fallback allowed:
- `grounded=false`, `refused=false`
- `suggested_next_mode="llm"`
- `answer_text`: "No map hits for 'forest', although it does appear in the lexicon. Would you like to query the LLM?"

### No hits, lexicon confirms term, grounded mode (strict):
- `grounded=false`, `refused=true`
- `refusal_reason="No retrieval hits found for your query."`
- `suggested_next_mode=null`

### No hits, term absent from lexicon:
- `grounded=false`, `refused=true` (grounded) or `refused=false` (allow_fallback)
- `answer_text`: "No map hits for 'quantum'. The terms are not in the lexicon either. Try refining your query or queue a mapping request."
- `suggested_next_mode="queue_mapping"`

### Hits found, low confidence:
- `grounded=false`, `refused=false`
- `caveats`: ["Confidence is low -- treat this response with caution."]
- `suggested_next_mode="refine_query"`

## What Base Must NEVER Do

1. Base never invents citations.
2. Base never mutates prompts to "inject 616 map".
3. Base never stores training events.
4. Base only:
   - Calls `plugin.query()`
   - Renders `answer_text`
   - Sends `citations[]` through Phase-1 intake
   - Optionally renders `trace` if Evidence Mode is on

## Citation Coord Types

LakeSpeak emits INGEST coords:
- `INGEST:<receipt_id>` — references an ingest receipt
- `INGEST:<receipt_id>#<chunk_id>` — references a specific chunk

These flow through the Phase-1 citation intake gate (`citation_intake.py`).
The intake gate validates format and stores the citation record.

## Kill Switches (forest.config.json)

```json
{
  "lakespeak": {
    "enabled": true,
    "dense_enabled": true
  }
}
```

- `enabled: false` — Plugin returns empty results, base unaffected
- `dense_enabled: false` — Sparse-only mode (BM25 only)

Future:
- `LAKESPEAK_TRAINING_ENABLED` — Plugin #3 can be off forever without impact

## Plugin #3 Data Contract

Plugin #3 reads ONLY:
1. `training_event@1` JSONL (see `training_event_schema.md`)
2. Chunk stores by receipt/snapshot ID (`LAKESPEAK_CHUNKS_DIR/{receipt_id}/`)

No CRUD apps needed. No admin UI required. Batch + receipts + hashes.

## Frozen IDs

- `training_event@1` schema: FROZEN
- `receipt_id` format: `rcpt_{YYYYMMDD}_{HHMMSS}_{hex8}` — FROZEN
- `chunk_id` format: `ch_{sha256(receipt_id:ordinal)[:16]}` — FROZEN
- Snapshot/index hash policy: SHA-256 hex — FROZEN
- Event ID format: `ev_{uuid4.hex[:16]}` — FROZEN
- Query ID format: `q_{uuid4.hex[:16]}` — FROZEN

## API Endpoints

```
POST /api/lakespeak/query     — Query pipeline
POST /api/lakespeak/ingest    — Ingest text
POST /api/lakespeak/reindex   — Rebuild indexes
GET  /api/lakespeak/status    — System status
POST /api/chat/send           — mode:"grounded" routes through plugin
```

## Implementation Files

```
lakespeak/
  __init__.py                         Package init, VERSION
  schemas.py                          7 pinned schema dataclasses
  config.py                           Config loader
  CONTRACT.md                         This file

  ingest/
    chunker.py                        Deterministic text chunker
    receipt.py                        Receipt ID generation
    pipeline.py                       Ingest orchestrator

  index/
    bm25.py                           BM25 sparse index
    dense.py                          Dense embeddings (optional)
    hybrid.py                         RRF merge
    anchor_reranker.py                6-1-6 anchor reranking

  retrieval/
    query.py                          LakeSpeakEngine (main orchestrator)
    quality_gate.py                   ACCEPTABLE/TRASH verdict
    grounding_policy.py               Grounded vs fallback decisions
    trace.py                          ReasoningTrace builder

  events/
    training_logger.py                Frozen JSONL writer
    hashing.py                        Deterministic hashing
    eval_harness.py                   Evaluation metrics
    training_event_schema.md          Frozen schema documentation

  api/
    router.py                         FastAPI router
    models.py                         Pydantic request/response
```
