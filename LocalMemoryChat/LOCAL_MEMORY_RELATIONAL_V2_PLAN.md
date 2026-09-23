# LocalMemoryChat Relational v2 Plan

Status: implementation checkpoint. This document does not migrate or rebuild the
historical estate. The 2026-09-19 adapter checkpoint currently persists signed
±6 measurements during admission; the accepted next correction is a durable
flat sentence/occurrence authority with query-scoped temporary relationship
projection. See `../docs/LOCAL_MEMORY_CHAT_CHECKPOINT_2026-09-19.md`.

## A. Exact old components retained

1. `attach_source()` and its read-only source admission, source hashing,
   pre/post hash check, and receipts.
2. Runtime profile isolation and ignored private runtime directories.
3. The existing OpenAI-compatible gateway behavior:
   model/API forwarding, upstream API-key forwarding, `/v1` path handling,
   streaming forwarding, and LM Studio compatibility.
4. Citation-oriented memory packets as the gateway's input boundary.
5. Receipt-first operational style and deterministic IDs where compatible.
6. The original 58 source files as the new intake authority; the old index is
   retained as historical evidence only.

## B. Exact old components retired from active use

1. Fixed 12-line windows as the primary memory object.
2. `add_file()`'s generic plain-text chunking for structured chat sources.
3. Global lexical-pressure scoring as the retrieval algorithm.
4. Full copied snippets in an unbounded durable query packet.
5. The old `hot_address_index.jsonl` as an authority for new retrieval.
6. Silent treatment of JSON/JSONL as undifferentiated text.

The historical v0 code and runtime remain available for compatibility review
and rollback. They are not deleted or rewritten.

## C. Current TrueSystems functions/contracts being borrowed

Borrow only pure, standalone methods and data laws:

- `truemem.engine.anchors.anchorize()`, `anchor_kind()`, and exact-form
  symbol derivation. Observed forms remain distinct; no silent normalization.
- `truemem.engine.relationship_graph.RelationshipGraph` measurements:
  signed distance, lane totals, conditional probability, background
  probability, lift, direction consistency, and deterministic path ordering.
- `truemem.engine.chat.parse_chat_metadata_block()` and
  `parse_chat_datetime()` for already structured metadata conventions.
- `truemem.engine.chat_counts.append_chat_count()` as prior art for
  append-only live chat events and daily count partitioning.
- TrueMem's canonical block/citation/coordinate separation as a schema
  principle, not as a dependency on its storage runtime.
- Current parent/child ownership and explicit unresolved/unknown status laws.

The standalone implementation may reproduce the minimal equivalent locally
when importing a production package would create a runtime dependency.

## D. Runtime dependencies intentionally NOT imported

The v2 runtime will not import or route through:

- Clearbox Chat-Chain;
- TrueVision or TrueVisionIntake DocuFilm;
- TrueMem dataset initialization, production CLI, native count files, query
  server, or production runtime;
- TrueCore, AnchorWorks, AWRAG production/runtime layers;
- any LLM, embedding model, vector database, or remote service.

The gateway remains the only model-facing integration. Qwen/LM Studio is a
renderer over a packet, never an evidence or memory authority.

## E. New standalone intake schema

The first implementation uses a SQLite relational store plus JSON receipts.
SQLite is local, transactional, queryable, and supports incremental admission
without rewriting the complete archive.

Core tables:

```sql
sources(
  source_id PRIMARY KEY, source_path, source_type, source_hash,
  size_bytes, admitted_at, source_label, private, status
)
documents(
  document_id PRIMARY KEY, source_id, document_ordinal, title,
  content_hash, metadata_json
)
objects(
  object_id PRIMARY KEY, source_id, document_id, parent_id,
  object_type, ordinal, role, speaker, timestamp, source_line_start,
  source_line_end, source_char_start, source_char_end, source_byte_start,
  source_byte_end, exact_text_hash, text, metadata_json
)
object_edges(parent_id, child_id, edge_type, ordinal, PRIMARY KEY(...))
anchors(anchor_id PRIMARY KEY, surface, symbol, kind)
occurrences(occurrence_id PRIMARY KEY, object_id, anchor_id, ordinal,
  char_start, char_end, byte_start, byte_end)
relations(relation_id PRIMARY KEY, source_id, object_id, center_anchor_id,
  neighbor_anchor_id, dimension, signed_distance, count)
```

The source file remains outside the runtime store and is identified by its
whole-file hash. `text` is copied for bounded evidence display, while source
coordinates and exact text hashes bind it back to the admitted file. Invalid
encoding is an explicit admission error for structured source types; no
replacement decoding is allowed in the v2 authority path.

## F. Parent/child schema

Natural parent identities are explicit:

```text
source
  -> document
      -> conversation
          -> branch
              -> turn
                  -> message
                      -> block/paragraph
                          -> sentence/object
                              -> artifact [RAW]
```

The hierarchy is source-dependent. Missing parent identities remain `UNKNOWN`;
the intake does not invent conversation, branch, or turn IDs. Children remain
individually retrievable; parent summaries are compact context only.

## G. Relationship schema

Relationships are measured from admitted observations, never guessed:

- `frequency`: anchor observations and object recurrence;
- `cooccurrence`: anchors observed in the same object or bounded local field;
- `signed_position`: exact ordinal/anchor offset where a linear neighborhood
  exists;
- `ordered_neighborhood`: source-order adjacency and minimal spans;
- `parent_child`: explicit ownership;
- `source_locality`, `document_locality`, `conversation_locality`,
  `turn_locality`, and `message_locality`;
- `temporal`: timestamp ordering only when timestamps are present;
- `recurrence`: repeated exact observed forms;
- `decay`: only if a current measured definition is adopted and disclosed;
- DK/re-K: `UNKNOWN` until a concrete current implementation and applicability
  are established.

Intake preserves native occurrence order and records measured relationships
without pre-shaping the data into 6-1-6. A linear message/block can expose
signed distances between every observed pair; chat additionally uses hierarchy
and timestamp/order edges. A six-prior/center/six-future view is an optional
deterministic query projection generated later from the stored occurrences and
relationships. Other source shapes may use other projections.

## H. Retrieval algorithm

For a query:

1. Admit exact query anchors without destructive normalization.
2. Find direct anchor occurrences.
3. Generate candidate objects from direct matches and their measured parent,
   child, locality, and ordered-neighborhood relations.
4. Require explicit query-anchor coverage where possible.
5. Compute a deterministic evidence record containing:
   direct matches, co-occurrence support, signed-position support, minimal
   source span, parent path, source locality, temporal locality, and unknowns.
6. Rank lexicographically by disclosed measurements:
   query coverage descending, direct occurrence count descending, relation
   support descending, minimal span ascending, parent/source locality
   descending, source coordinates ascending, object ID ascending.
7. Select a bounded number of objects and bounded text bytes before packet
   creation.

No arbitrary semantic importance weight is introduced. Frequency is reported
as commonality, not significance. A relationship cannot be returned as fact
unless its observed path exists in the store.

## I. Bounded memory packet schema

```json
{
  "schema": "local_memory_packet@2",
  "query": "...",
  "query_anchors": ["..."],
  "evidence": [
    {
      "object_id": "...",
      "parent_path": ["..."],
      "source": {"source_id": "...", "path": "...", "hash": "..."},
      "coordinates": {"line_start": 1, "line_end": 2, "byte_start": 0, "byte_end": 120},
      "text": "...",
      "citation": "MEMCIT-...",
      "retrieval": {
        "direct_anchors": ["..."],
        "relationship_path": ["..."],
        "measured_reason": "..."
      }
    }
  ],
  "unknowns": ["..."],
  "bounds": {"max_items": 8, "max_chars": 24000},
  "model_authority": "renderer_only"
}
```

The packet is bounded by object count and total characters before the gateway
is called. The gateway may apply a second defensive bound, but that is not the
primary selector.

## J. Incremental live-chat admission

Completed turns are admitted transactionally as soon as a turn is complete.
Admission is idempotent by `(source_id, object_id, exact_text_hash)`. New turns
append source/object/occurrence/relation rows and update measured counters;
existing source objects are not rebuilt. Daily views are query projections, not
separate authority stores.

## K. Raw visual/binary artifact handling

Images, audio, video, archives, and other non-text files are copied or
referenced only as unchanged raw artifacts according to the caller's custody
policy. The memory store records:

```text
artifact_id, parent_id, source_path, source_hash, media_type,
byte_size, original_ordinal, relationship, timestamp, raw_status
```

`raw_status` is `RAW_UNINTERPRETED`. No pixels, audio, video, OCR, or semantic
claims are generated by this system.

## L. Migration path from the 58 original sources

1. Preserve the current LocalMemoryChat runtime and 12-line index unchanged.
2. Verify the original 58 source paths and whole-source hashes.
3. Select one real JSONL chat source for the first vertical slice.
4. Parse only fields present in that source; absent conversation/branch/turn
   identifiers remain `UNKNOWN`.
5. Validate object counts, ordering, coordinates, and source hash.
6. Build relational counts/index for that source only.
7. Run one known query and inspect its deterministic evidence path.
8. Create a bounded v2 packet and send it through the existing gateway.
9. Expand source adapters one at a time after acceptance; do not bulk ingest
   until the slice passes.

The v2 store is a new authority. It is not produced by converting old chunks.

## M. Acceptance tests

The first acceptance test must prove, from one original source:

- source bytes/hash remain unchanged;
- one conversation and its available turn/message metadata are preserved;
- speaker/role, order, block coordinates, and parent/child rows are present;
- exact observed forms remain distinct;
- anchor frequency and measured relationships are deterministic;
- one known question returns the correct source object;
- the packet includes source identity, coordinates, citation, and retrieval
  reason;
- packet bounds hold before gateway invocation;
- the gateway reaches LM Studio/Qwen with HTTP 200;
- the model receives evidence but is not treated as authority.

Additional tests cover JSON, Markdown, unknown fields, raw artifacts,
duplicate admission, malformed source handling, query ties, and incremental
turn admission.

## N. Implementation phases

1. Plan and boundary freeze.
2. Standalone SQLite schema, source hashing, exact JSONL chat adapter, and
   object hierarchy.
3. Anchor occurrence and measured relationship index for one source.
4. Deterministic retrieval and pre-bounded v2 packet.
5. Existing gateway adapter for v2 packets, without changing the gateway
   transport contract.
6. One-source acceptance trace against LM Studio/Qwen.
7. Additional source adapters and incremental live-chat admission.
8. Controlled migration of the 58 original sources, only after repeated
   acceptance passes.
