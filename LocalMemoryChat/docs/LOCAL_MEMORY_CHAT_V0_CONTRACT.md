# Local Memory Chat v0 Contract

## Purpose

Local Memory Chat is a small local RAG + chat memory system.

It searches the user's own local memory before asking the wider world or allowing an LLM to answer.

The LLM is voice, not authority.

The local memory packet is the authority for remembered facts.

## Core Doctrine

```text
Before asking the world, search the user's own memory.
Before letting the LLM answer, build the evidence packet.
The LLM renders from evidence. It does not invent memory.
```

## Core Flow

```text
live intake
-> update hot count lane
-> update hot address lane
-> user question
-> classify memory intent
-> search current-day hot memory
-> search warm memory when needed
-> search cold memory only on recall/deep-search intent
-> use lifetime counts for field pressure when available
-> pinpoint exact source addresses
-> build cited memory packet
-> send packet + question to OpenAI or a local renderer
-> receive rendered answer
-> validate cited memory IDs
-> write receipt
```

## Intake Doctrine

Intake is the product spine.

When a chat turn or file is added, it should become useful immediately in hot memory.

Same-day usability must not wait for an overnight lifetime-count merge.

```text
file/chat added
-> record source manifest
-> extract addressable chunks
-> update temporary hot counts
-> update hot address postings
-> become searchable and citeable in the same session
-> merge into lifetime later by explicit consolidation
```

## Two-Lane Memory Spine

### Count Field Lane

The count lane contains hot counts, daily counts, and later lifetime counts.

It knows:

```text
what appears
what repeats
what clusters
what relates
what has pressure
what belongs near what
```

Counts can suggest likely memory areas and answer direction, but counts alone are not citation-safe.

### Address Lane

The address lane contains source records for files, chats, receipts, and packets.

It knows:

```text
source_id
chunk_id
source_type
path or source label
timestamp
offsets
line numbers where available
citations
source hashes
```

The address lane turns count pressure into citeable evidence.

```text
Counts find the field.
Addresses prove the source.
Packets join them.
Renderers speak only from packets.
```

## Memory Tiers

### Hot Memory

Current and immediately useful context.

Includes:

```text
current session
current-day chat turns
files explicitly added to the session
open project files
recently edited files
recent chats
pinned facts
active project notes
active decisions
recent receipts
current packets
```

Hot memory is searched by default.

### Warm Memory

Organized project/topic/month bins.

Includes:

```text
project summaries
topic bins
monthly conversation bins
prior decisions
saved operator notes
```

Warm memory is searched when hot memory is insufficient or the question references a known project/topic.

### Cold Memory

Full archive.

Includes:

```text
older raw imports
long-term chat history
archived project logs
deep storage bins
```

Cold memory is not searched by default.

Cold memory is searched only when the user signals recall/deep search, such as:

```text
I remember once...
we talked about...
find the time when...
search my old chats...
deep search memory...
```

## Inputs

```text
user_question: string
runtime_root: path
memory_profile_id: string
optional_project_id: string | null
optional_deep_search: bool
```

Live intake inputs:

```text
chat_turn: {speaker, timestamp, text, source_label}
file_path: path
source_type: chat | file | note | receipt | packet | synthetic_demo
memory_profile_id: string
optional_project_id: string | null
```

## Outputs

```text
memory_packet.json
rendered_answer.json
memory_receipt.json
```

Live intake outputs:

```text
source_manifest.jsonl
hot_counts.*
hot_address_index.jsonl
intake_receipt.json
```

## Memory Packet Shape

```json
{
  "schema": "local_memory_packet@0",
  "question": "...",
  "memory_profile_id": "...",
  "search_policy": {
    "hot_searched": true,
    "warm_searched": true,
    "cold_searched": false,
    "cold_search_reason": null
  },
  "evidence_items": [
    {
      "memory_id": "MEM-...",
      "tier": "hot | warm | cold",
      "source_type": "chat | note | project | receipt | synthetic_demo",
      "source_label": "...",
      "timestamp": "...",
      "snippet": "...",
      "citation": "MEMCIT-...",
      "score": 0.0
    }
  ],
  "missing_evidence": [],
  "render_policy": "renderer_packet_only"
}
```

## Receipt Shape

```json
{
  "schema": "local_memory_receipt@0",
  "question_hash": "...",
  "memory_packet_hash": "...",
  "rendered_answer_hash": "...",
  "memory_items_used": ["MEMCIT-..."],
  "model": "...",
  "renderer_search_allowed": false,
  "new_citations_allowed": false,
  "unknown_citation_rejected": true,
  "private_data_exported": false
}
```

## Storage Rules

```text
JSON = manifests, receipts, small demo data, readable packet files
Binary/index files = counts, postings, fast lookup structures
Raw private memory = runtime only, never committed
Synthetic demo memory = allowed in repo
```

Live intake storage rules:

```text
hot counts = same-day/session search field
hot address index = same-day/session citation surface
lifetime counts = durable field after explicit consolidation
lifetime merge = later, not v0 live-intake
original files = never mutated
source hashes = recorded before indexing
```

## Repository Ships With

```text
synthetic demo chat
sample project notes
import format
operator guide
memory tier notes
tests
```

## Repository Must Not Ship With

```text
real user chats
private runtime
private receipts
API keys
personal project memory
machine-specific paths
```

## Forbidden Behavior

```text
Do not let the LLM answer before memory search.
Do not let a renderer invent memory citations.
Do not let a renderer search the web by default.
Do not store private chat in the repo.
Do not mix demo memory with private runtime memory.
Do not summarize away citations.
Do not treat old memory as guaranteed current truth.
Do not search cold archive unless intent requires it.
Do not silently mutate imported memory.
Do not wait for lifetime merge before hot memory can be searched.
Do not cite counts alone without an address record.
Do not mutate original files during intake.
```

## Failure States

```text
no_memory_found
hot_memory_insufficient
warm_memory_insufficient
cold_search_required_but_disabled
memory_packet_empty
renderer_failed
unknown_citation_returned
receipt_write_failed
source_hash_mismatch
address_record_missing
hot_count_update_failed
hot_address_update_failed
```

## v0 Test Proof

The first implementation must prove:

```text
1. Synthetic chat live-intakes successfully.
2. Synthetic file/note live-intakes successfully.
3. Hot counts update during intake.
4. Hot address records update during intake.
5. Newly added memory is searchable in the same session.
6. File/chat search returns citeable source addresses.
7. Hot memory is searched by default.
8. Cold memory is not searched by default.
9. Recall phrasing triggers cold-memory eligibility.
10. Memory packet contains cited snippets.
11. Renderer receives only the memory packet and question.
12. Returned citations must already exist in the packet.
13. Receipt records packet hash, model, policy, and citations used.
14. Private runtime paths are ignored by git.
15. Demo works without private user data.
```

## Product Boundary

Local Memory Chat is not TrueMem.

It borrows the same doctrine:

```text
find evidence first
then let the model speak from evidence
receipt everything
```

But it is a smaller public-use system:

```text
local chat memory
local project memory
cited packet
renderer answer
receipt
```
