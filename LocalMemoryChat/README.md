# Local Memory Chat

Local Memory Chat is a small local RAG + chat memory system.

It searches your own saved memory before asking the wider world or allowing a model to answer.

The model is voice, not authority.

The local memory packet is the authority for remembered facts.

## Product Promise

```text
A local chat app that searches your own saved memory first,
builds a cited packet,
then lets a model answer from that packet.
```

## Core Flow

```text
live intake
-> update hot count lane
-> update hot address lane
-> user question
-> classify memory intent
-> search current-day hot memory
-> use lifetime counts for field pressure when available
-> pinpoint exact source addresses
-> build cited memory packet
-> send packet + question to a renderer
-> validate returned memory citations
-> write receipt
```

## Two-Lane Memory Spine

```text
Count lane:
  hot counts, daily counts, lifetime counts
  knows pressure, relation, repetition, and anchor neighborhoods

Address lane:
  files, chats, receipts, packets
  knows source IDs, chunks, offsets, lines, and citations
```

Counts find the field.

Addresses prove the source.

Packets join them.

Renderers speak only from packets.

## First Boundaries

This repo starts with rules and synthetic demo data before code.

It ships with:

```text
docs/LOCAL_MEMORY_CHAT_V0_CONTRACT.md
docs/PRIVACY_BOUNDARY.md
data/demo/synthetic_chat.jsonl
```

It must not ship with:

```text
real user chats
private runtime memory
private receipts
API keys
machine-specific paths
```

## Planned v0 Slices

```text
1. Live-intake synthetic chat turns.
2. Live-intake synthetic files/notes.
3. Write normalized source records.
4. Build hot counts for same-session use.
5. Build hot address index with citeable source locations.
6. Search hot memory by default.
7. Build cited memory_packet.json.
8. Render from packet only.
9. Validate returned citation IDs.
10. Write memory_receipt.json.
11. Add lifetime merge after hot intake works.
12. Add warm/cold tiers after hot path works.
```

## Demo Run

From the repo root:

```powershell
python -m local_memory_chat.cli init --profile demo
python -m local_memory_chat.cli import-demo --profile demo
python -m local_memory_chat.cli add-file data/demo/project_note.md --profile demo --label project-note
python -m local_memory_chat.cli ask "what did we decide about render providers?" --profile demo
```

This writes ignored runtime files under:

```text
runtime/profiles/demo/
```

The expected proof:

```text
chat memory is searchable
file memory is searchable
citations are returned as MEMCIT-...
memory_packet.json is written
search receipt is written
git status stays clean except for tracked source changes
```

## Private Source Adapter v0

Attach first, index second:

```powershell
python -m local_memory_chat.cli attach-source --profile demo --path data/demo/project_note.md --source-type file --label project-note
python -m local_memory_chat.cli sources --profile demo
python -m local_memory_chat.cli index-source --profile demo --source-id <SRC-id> --hot
python -m local_memory_chat.cli ask "what do packets join?" --profile demo
python -m local_memory_chat.cli inspect-binary --profile demo --source-id <SRC-id>
python -m local_memory_chat.cli sqlite-support --profile demo --source-id <SQLITE-SRC-id>
```

Source types:

```text
file        normal text/markdown/json/csv/log file
file-root   directory of normal text/markdown/json/csv/log files
chat-binary attached read-only, status=attached_not_decoded until a decoder exists
```

Rules:

```text
attachment is runtime-only
source files are read-only
source hashes are recorded before and after indexing
runtime remains ignored by Git
chat binaries are not decoded in v0
inspect-binary reports size, SHA-256, first-byte hex, obvious magic/header format, sample offsets, and no-mutation status only
sqlite-support converts attached SQLite rows into an ignored runtime support binary plus a row index with SQLCIT citations
```

## Doctrine

```text
Find memory first.
Build evidence packet second.
Let the model speak third.
Receipt everything.
```
