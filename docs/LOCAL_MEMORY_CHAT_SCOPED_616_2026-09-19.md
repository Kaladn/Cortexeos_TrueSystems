# LocalMemoryChat scoped 6-1-6 checkpoint

Date: 2026-09-19

This checkpoint makes the chat relationship boundary executable.

## Durable chat memory

Native Codex, OpenAI export, and LM Studio adapters reconstruct one selected
chat into immutable conversation, turn, message, paragraph block, and sentence
objects. Each observed token surface is stored exactly as written. Each
occurrence keeps both sentence-local and block-local order. Native intake writes
no relationship graph rows.

The obsolete generic JSONL intake command was removed because it hashed chat
surfaces and persisted expanded relationship rows. Native source adapters are
the only relational-v2 chat admission path.

## Temporary relationship work

`relational-v2-project` requires immutable block or sentence IDs before it can
run. It scans only those admitted sentences, compares the exact requested
surface, and counts neighbors in explicit signed lanes. Its default lanes are
`-6..-1` and `+1..+6`.

Complete candidate counts and supporting occurrence identities are produced
before an optional Top-K display is taken. Optional positional mass is derived
from the exact lane counts. The projection never crosses a sentence boundary.

The admitted SQLite database is opened read-only during projection and is
hashed before and after. The only persisted projection output is a compact
provenance receipt under the runtime projection-receipt directory. No expanded
graph row is admitted back into chat memory.

## Qualified behavior

The external focused fixture proves that `blue` occurs twice and `green` once
at lane `+3` after exact surface `AnchorWorks`; Top-K 1 displays only `blue`
without discarding the complete counts. It separately proves that lower-case
`anchorworks` remains distinct, sentence boundaries stop expansion, sentence
scope excludes adjacent sentences, repeat projection is deterministic, and the
flat database remains byte-identical.

The three-adapter acceptance was rerun against representative Codex, official
OpenAI export, and LM Studio chats. It proves source immutability, one-chat-only
admission, paragraph and sentence reconstruction, first-class tools and raw
artifacts, exact-surface occurrences, zero durable relationship rows, and
duplicate logical-source collapse.

## Deliberate limits

This checkpoint does not build a permanent graph, run automatic two-hop walks,
add semantic normalization, implement decay, or alter retrieval admission.
Additional relationship work can compose new scoped projections from selected
locations when a task explicitly requires it.
