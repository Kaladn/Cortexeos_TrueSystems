# Chat lexicon, binary, and query contract

## Authority

This contract fixes the intended machine-facing path for chats. It does not
authorize Chat-Chain to implement TrueMem, DocuFilm, retrieval, or answer
composition internally.

## Daily chat custody

- One calendar day is one logical chat, regardless of how many models speak.
- SQLite owns the exact ordered chat record for that day.
- Each message retains its exact text, original timestamp, stable order,
  participant identity, provider, and model.
- At 00:01 local machine time on the following day, the prior day is sealed.
- A sealed day is immutable but remains readable, selectable, and copyable.
- Copied historical text may be pasted into the current day as a new message.
  Copying never changes the historical record.
- Chat history has no inline note or citation creation path.

## Automatic binary conversion

Sealing must automatically enqueue the daily SQLite record for
DocuFilm/TrueMem conversion. This is a machine operation, not a UI command.

The conversion must:

1. Read messages in stable SQLite row order.
2. Preserve every admitted source form with zero normalization.
3. Admit complete words, glue/directional words, punctuation boundaries,
   objects, parent anchors, and contained anchors.
4. Reuse the existing Chat-dataset symbol for an exact anchor string.
5. Assign the next unused Chat-dataset symbol only for an unseen exact string.
6. Build positions, occurrences, signed 6-1-6 relationships, and native binary
   postings.
7. Store addresses that resolve every binary result back to the exact SQLite
   file, table, row, message identity, and source position.
8. Verify the sealed source hash and binary-address round trip.
9. Write a deterministic conversion receipt.

A failed conversion never changes or unlocks the sealed SQLite source. It
remains queued for deterministic retry.

## Dataset-local symbol law

Every approved dataset owns its own lexicon and symbol field. Symbol values do
not cross dataset boundaries.

For an exact admitted string `A`:

```text
Chat dataset        A -> Chat-local symbol
TrueCore dataset    A -> TrueCore-local symbol
TrueMachine dataset A -> TrueMachine-local symbol
```

The exact string is the cross-dataset joining identity. A symbol from one
dataset must never be interpreted as the same-numbered symbol in another.
TrueSystems returns strings with their dataset-qualified symbols; it never
returns naked symbols as cross-dataset meaning.

## Query path

```text
User
  -> Codex
  -> TrueSystems query router
  -> approved dataset lexicons
  -> dataset-local binary and relationship searches
  -> exact strings + dataset symbols + measurements + source locations
  -> Codex source verification and answer composition
  -> User
```

TrueSystems resolves the question independently against every approved dataset.
Each result remains dataset-qualified and includes enough source address data
to open the original record. Agreement or disagreement may be reported across
datasets, but their symbol spaces and relationship graphs are not silently
merged.

Returned machine records must retain at least:

```text
dataset_id
anchor_string
dataset_symbol
relationship_measurements
source_file
source_table_or_native_container
source_row_or_native_coordinate
message_id_when_applicable
source_hash
supporting_exact_string
```

The model-facing handoff uses exact strings and locations. Symbols remain an
internal navigation mechanism.

## Current implementation boundary

As of 2026-08-29, Chat-Chain implements the daily logical conversation,
participant identities, message display, Send, and existing backend
continuation compatibility. It still uses one SQLite database and does not yet
implement per-day SQLite rotation, 00:01 sealing, immutable historical-day
enforcement, automatic DocuFilm/TrueMem conversion, or the binary-to-SQLite
address verifier. Those items remain required work and must not be claimed as
implemented until their executable path, authority admission, real observed
effect, and external operation receipts exist.

The dataset-local symbol law above specifies the unimplemented chat-conversion
shape. It does not describe the active general `docufilm-intake` storage format,
which currently allocates non-overlapping six-byte dataset ranges from one
workspace-monotonic symbolizer. That distinction and its migration boundary are
recorded in `TRUEMEM_RELATIONSHIP_TRAINING_SHAPE.md`.
