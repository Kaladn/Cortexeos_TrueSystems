# Codex Update: LocalMemoryChat Relational v2

**Date:** 2026-09-18  
**Status:** Additive handoff note; no TrueSystems runtime change requested

When returning to the LocalMemoryChat work, start with:

`/home/lamercey/local-memory-chat-distro/LOCAL_MEMORY_CHAT_CURRENT_MASTER.md`

## Current boundary

LocalMemoryChat is being completed as a standalone deterministic relational
memory layer beside LM Studio/Qwen. It must not be routed through or made
dependent on Clearbox Chat-Chain, TrueVision/TrueVisionIntake, TrueMem
production runtime, TrueCore, AnchorWorks, AWRAG, embeddings, or a new UI.
TrueSystems material is reference material only.

## Current work state

The candidate path is:

```text
source
-> structured intake
-> occurrences
-> counts/relationships
-> deterministic retrieval
-> bounded cited packet
-> OpenAI-compatible gateway
-> LM Studio/Qwen
```

The historical LocalMemoryChat `:1235` path and 12-line index remain
historical comparison evidence. Relational v2 on `:1236` is the candidate
active development path. Memory retrieval is opt-in through the explicit
working-dataset request; ordinary model requests must pass through without
retrieval.

## Searchable document library addendum

The phone documents and other approved engineering documents should become
deliberate search options, not automatic prompt content. Keep three scopes:

```text
ACTIVE / HOT
DOCUMENT LIBRARY
HISTORICAL CHAT / COLD
```

Hot memory is the explicitly admitted working dataset. Document-library search
may discover relevant sections, paragraphs, or objects when hot traversal is
insufficient, but discovery alone does not make them active. Selected results
must retain source identity, coordinates, parent path, and citation, then be
explicitly admitted into the working dataset before counts/relationships are
updated and traversal continues. Historical chat follows the same deliberate
admission rule.

Treat Markdown and DOCX as source-preserving document intake, not arbitrary
line-window chunking. DOCX originals remain authoritative; extracted text is
derived state. Embedded images and other binary children remain raw and
uninterpreted. Search results remain untrusted evidence and cannot become
instructions, tool authority, file permissions, or secret-disclosure requests.

## Required next actions

- Finish the live LM Studio/Qwen A-H acceptance matrix.
- Record evidence paths, coordinates, packet bounds, HTTP status,
  `finish_reason`, prompt usage, and visible model output.
- Complete `LOCAL_MEMORY_RELATIONAL_V2_ACCEPTANCE.md`.
- Keep retrieved text untrusted and out of system/developer authority.
- Preserve conflicts, unknowns, source identity, parent paths, and citations.
- Treat 6-1-6 as an optional projection, not universal storage geometry.
- Use four-byte values only as dataset-local symbols bound to a frozen
  lexicon/manifest; never use them for object, parent, citation, or hash
  identity.
- Do not claim decay/re-cay or a production pressure traversal unless the
  standalone implementation and tests actually prove them.
- Do not bulk-ingest the 58 private sources or modify the original archive.
- Audit for credentials, private data, runtime databases, absolute local paths,
  escaping symlinks, generated files, and hidden TrueSystems dependencies.
- Keep document-library discovery separate from hot-memory admission and bound
  every selected evidence set before model invocation.

## Relationship to TrueSystems

The current TrueSystems documents reinforce useful laws for this work:

- persistent logs and admitted source state are the evidence boundary;
- model output is not the memory authority;
- retrieval/investigation must remain separate from answer formation;
- parent/child and temporal relationships should remain explicit;
- integrity and provenance must be observable;
- hot working state is a bounded operational view over durable evidence.

These laws may guide standalone equivalents, but no TrueSystems production
package should be imported merely to obtain them.

**Codex instruction:** update this note and the standalone master when the
LocalMemoryChat acceptance state materially changes. Keep this note additive;
do not use it as permission to alter the TrueSystems runtime or private source
archives.
