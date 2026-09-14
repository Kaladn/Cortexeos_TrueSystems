# Genesis Citation Tool — Boundary Contract
# Version: 1.0 | Date: 2026-02-26 | Status: FROZEN

## What this plugin does

Read-only citation lookup for the Clearbox AI Studio Genesis training corpus.
Returns verifiable, auditable, deterministic citations anchored to block IDs.

## Invariants (never change without a new spec version)

1. **READ_ONLY** — no writes to TRAINING_CORPUS.md, GENESIS_SPEC.md, or any
   file outside `data/derived/genesis/`
2. **No network** — zero external calls; all data from local corpus file
3. **Fixed corpus path** — `CORPUS_PATH` is a module constant, never user-supplied
4. **Path injection** — any tag or query containing `/`, `\`, or `..` is rejected
5. **Deterministic** — same corpus file → same index → same results
6. **Cite only what the tool returns** — no inference from context

## Input → Output contract

```
direct("G-0017")     → {"ok": True, "result": {citation object}}
                       {"ok": False, "error": "NOT_FOUND"|"SPEC_VIOLATION"|"STALE_INDEX"}

search("query", ...)  → {"ok": True, "query": "...", "results": [{tag, title, score, ...}]}
```

## Citation object mandatory fields

tag, title, source, scope, date_range, write_perms, derived,
source_commit, block_hash, body (if requested), span, retrieved_at

## Index files (derived output only)

```
data/derived/genesis/
  corpus.index.json     ← block metadata (no bodies)
  bm25.index.pkl        ← BM25Okapi serialised model
  build_meta.json       ← source_commit, source_hash, built_at
```

## API surface (Bridge port 5050)

```
GET  /api/genesis/health
POST /api/genesis/cite       { mode: "direct"|"search", ...params }
GET  /api/genesis/cite/{tag}
GET  /api/genesis/list
```

## Full spec

See `docs/GENESIS/CITATION_TOOL_SPEC.md`
