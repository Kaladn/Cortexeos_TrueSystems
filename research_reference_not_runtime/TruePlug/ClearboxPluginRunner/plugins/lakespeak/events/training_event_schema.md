# training_event@1 — Frozen Schema

**Status:** FROZEN. Do not change field names or nesting without bumping schema_version.
**Consumer:** Plugin #3 (LakeSpeak-Train).

## Storage

- Zone: `WriteZone.LAKESPEAK_EVENTS`
- File: `%LOCALAPPDATA%\ForestAI\lakespeak\events\training_events_{YYYY-MM-DD}.jsonl`
- Write mode: append only
- Rotation: daily (new file per UTC day, old files sealed)
- One event per line

## Event ID Rules

- `event_id = "ev_" + uuid4().hex[:16]`
- `query_id = "q_" + uuid4().hex[:16]`
- Reproducibility comes from hashes, not IDs.

## Required Hashes

Every query event MUST include:

1. **`lake_snapshot_id`** — String identifying lake state (`snapshot_{hash_prefix}` or `snapshot_none`)
2. **`index_hash`** — SHA-256 of index metadata (chunk_id list + source hashes + version)
3. **`evidence_set_hash`** — SHA-256 of retrieved candidates (chunk_id, coord, score, source_hash; sorted by rank asc, chunk_id asc)
4. **`answer_hash`** — SHA-256 of answer_text exactly as returned

Hash algorithm: SHA-256 hex, prefixed with `sha256:`.

## Deterministic Hashing Spec

- Normalize JSON: sorted keys, UTF-8, no whitespace
- `evidence_set_hash`: sha256 of JSON array of `{chunk_id, coord, score, source_hash}` sorted by `(rank asc, chunk_id asc)`
- `answer_hash`: sha256 of UTF-8 `answer_text` exactly as returned (before UI stripping)
- `index_hash`: sha256 of `{version, chunk_ids (sorted), source_hashes (sorted)}`

## Full Schema (JSON per line)

```json
{
  "schema_version": "training_event@1",

  "event_id": "ev_0123abcd4567ef89",
  "event_type": "query",

  "timestamp_utc": "2026-02-15T19:45:12.123456+00:00",
  "session_id": "ui|cli|<opaque>",
  "user_id": "human|system|ai",

  "query_id": "q_89ef0123abcd4567",
  "query_text": "forest",
  "requested_mode": "grounded|allow_fallback",

  "grounding_policy": {
    "grounded_required": true,
    "min_score": 0.10,
    "topk": 8
  },

  "lexicon_probe": {
    "present": ["forest"],
    "absent": [],
    "version": "",
    "probe_ms": 3
  },

  "retrieval": {
    "lake_snapshot_id": "snapshot_ab12cd34ef567890",
    "index_hash": "sha256:...",
    "retrieval_ms": 21,

    "bm25": {
      "enabled": true,
      "hits": 8
    },
    "dense": {
      "enabled": false,
      "hits": 0,
      "embed_model": null
    },

    "candidates": [
      {
        "rank": 1,
        "chunk_id": "ch_abcdef0123456789",
        "coord": "INGEST:rcpt_20260215_193000_ab12cd34#ch_abcdef0123456789",
        "score": 0.42,
        "source_type": "ingest",
        "source_hash": "sha256:..."
      }
    ],

    "evidence_set_hash": "sha256:..."
  },

  "rerank": {
    "anchor_rerank_enabled": true,
    "anchors_used": ["forest"],
    "rerank_ms": 4,
    "final_topk": [
      { "rank": 1, "chunk_id": "ch_...", "score": 0.51 }
    ]
  },

  "decision": {
    "grounded": true,
    "refused": false,
    "refusal_reason": null,
    "suggested_next_mode": null
  },

  "model": {
    "provider": null,
    "model_name": null,
    "model_hash": null,
    "temperature": null,
    "top_p": null
  },

  "output": {
    "answer_text": "...",
    "answer_hash": "sha256:...",
    "citations_emitted": [
      {
        "cite_id": "cite_...",
        "coord": "INGEST:rcpt_...",
        "source": "lakespeak",
        "unresolved": true,
        "subject": null
      }
    ]
  },

  "timing": {
    "total_ms": 80
  }
}
```

## Invariants (Non-negotiable)

1. `schema_version` must equal `"training_event@1"` exactly.
2. Must always include `query_text`, `requested_mode`, `retrieval.candidates` (can be `[]`), and `decision`.
3. If `retrieval.candidates` is empty:
   - `decision.grounded` must be `false`
   - `decision.refused` depends on policy (`grounded_required`)
   - `suggested_next_mode` must be `"llm"` if fallback allowed
4. `citations_emitted[]` must match what was actually stored via Phase-1 intake (same coords, same cite_ids).
5. `index_hash` and `evidence_set_hash` must be present even if candidates empty (hash empty list deterministically).

## Non-Query Event Types

For `event_type` values other than `"query"` (ingest, reindex, feedback, eval), the event uses a flat `payload` dict:

```json
{
  "schema_version": "training_event@1",
  "event_id": "ev_...",
  "event_type": "ingest",
  "timestamp_utc": "...",
  "session_id": null,
  "query_id": null,
  "receipt_id": "rcpt_...",
  "payload": {
    "source_type": "text",
    "chunk_count": 12,
    "anchor_count": 45,
    "relation_count": 120,
    "source_hash": "sha256:..."
  }
}
```

## Implementation

- Hashing: `lakespeak/events/hashing.py`
- Logger: `lakespeak/events/training_logger.py` (method: `log_query_structured()`)
- Caller: `lakespeak/retrieval/query.py` (method: `_log_structured_event()`)
