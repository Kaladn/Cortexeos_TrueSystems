# Live Intake v0 Roadmap

## Goal

Make newly added chat turns and files useful immediately.

Live intake updates two isolated hot lanes:

```text
hot count lane
hot address lane
```

Lifetime merge is deferred.

Renderer work is deferred until packets exist.

## Core Law

```text
Counts find the field.
Addresses prove the source.
Packets join them.
Renderers speak only from packets.
```

## v0 Scope

Implement only:

```text
add synthetic chat turn
add synthetic file/note
normalize source record
write source manifest
update hot counts
update hot address index
search hot memory
build memory packet with citations
write intake/search receipts
```

Do not implement:

```text
lifetime count merge
warm/cold archive search
renderer calls
private chat import
web search
database server
GUI
```

## Runtime Shape

```text
runtime/
  profiles/
    <memory_profile_id>/
      sources/
        source_manifest.jsonl
      hot/
        hot_counts.json
        hot_address_index.jsonl
      packets/
        memory_packet_<id>.json
      receipts/
        intake_receipt_<id>.json
        search_receipt_<id>.json
```

This JSON shape is allowed for v0 because the demo is small and inspectable.

Binary counts are a later promotion after the semantics are proven.

## Source Record

```json
{
  "schema": "local_memory_source_record@0",
  "source_id": "SRC-...",
  "memory_profile_id": "demo",
  "source_type": "chat | file | note | receipt | packet | synthetic_demo",
  "source_label": "...",
  "timestamp": "...",
  "content_hash": "...",
  "chunk_count": 1,
  "private": false,
  "synthetic": true
}
```

## Address Record

```json
{
  "schema": "local_memory_address_record@0",
  "memory_id": "MEM-...",
  "source_id": "SRC-...",
  "chunk_id": "CHUNK-...",
  "tier": "hot",
  "source_type": "synthetic_demo",
  "source_label": "...",
  "timestamp": "...",
  "line_start": 1,
  "line_end": 1,
  "char_start": 0,
  "char_end": 120,
  "snippet": "...",
  "citation": "MEMCIT-..."
}
```

## Hot Counts

The first implementation may use readable JSON counts:

```json
{
  "schema": "local_memory_hot_counts@0",
  "anchors": {
    "memory": 4,
    "packet": 3
  },
  "cohabitation": {
    "memory|packet|+1": 2
  }
}
```

Promotion target later:

```text
binary counts
postings
lifetime merge receipts
```

## Search v0

Search hot memory by:

```text
normalize question anchors
score address records by anchor overlap
include hot count pressure where available
return cited snippets
write search receipt
```

No renderer call.

No cold archive.

No private data.

## Memory Packet v0

```json
{
  "schema": "local_memory_packet@0",
  "question": "...",
  "memory_profile_id": "demo",
  "search_policy": {
    "hot_searched": true,
    "warm_searched": false,
    "cold_searched": false,
    "cold_search_reason": null
  },
  "evidence_items": [],
  "missing_evidence": [],
  "render_policy": "renderer_packet_only"
}
```

## Acceptance Tests

```text
synthetic chat turn creates source record
synthetic file/note creates source record
hot counts update after intake
hot address index updates after intake
same-session search finds newly added chat memory
same-session search finds newly added file memory
memory packet contains citations
search receipt records hot-only policy
cold memory is not searched by default
private/runtime paths are ignored by git
```

## Stop Line

When this works, stop.

Do not build lifetime merge until hot intake/search receipts are boring and trustworthy.
