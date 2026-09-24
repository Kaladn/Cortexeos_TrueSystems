# TrueVisionIntake/truevision_intake/document_state agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and governing parent

This file governs `TrueVisionIntake/truevision_intake/document_state/`. Read `TrueVisionIntake/AGENTS.md` and all ancestor
`AGENTS.md` files first. The code facts below do not establish effects or authority.

## Production entrypoint

`state_reader.py:DocumentStateReader.read_page_frame` reads page state with a
glyph lexicon and lifetime counts. `intake_control.py:IntakeControl` records
state transitions; `intake_state_movie` coordinates a bounded read.
`document_state_movie.py` records/replays state frames and glyph extraction.
Trace source typing and the TrueMem handoff before calling a document admitted.

## Local code-defined surface

- `__init__.py`.
- `code_glyph_reader.py`: build_code_deciphering_context (line 25), read_code_state_movie (line 98), read_code_glyph_frame (line 209).
- `code_language_readers.py`: read_code_language_structure (line 90).
- `contracts.py`: build_glyph_state_record (line 17), build_document_state_read (line 64).
- `document_state_movie.py`: record_document_state_movie (line 35), build_page_cell_state (line 208), replay_document_state_movie_frame (line 248), write_document_state_surface (line 274), and 2 more source definitions.
- `document_video.py`: build_document_video (line 9).
- `glyph_lexicon.py`: normalize_trim_pattern (line 9), pattern_hash (line 20), GlyphMatch (line 25), GlyphLexicon (line 33).
- `hashing.py`: stable_hash (line 8).
- `intake_control.py`: digest (line 16), context (line 20), transition (line 27), IntakeControl (line 100), and 1 more source definitions.
- `lifetime_counts.py`: LifetimeCounts (line 6).
- `state_reader.py`: DocumentStateReader (line 10).

## Allowed and forbidden operations

Use only the exact callable reached through the applicable parent authority path; do not create a substitute wrapper or ingress. Do not infer inputs, effects, permissions, or safe retry from names.

## Inputs, outputs, authority boundary, and receipts

Inspect the selected signature, validator, callers, return branches, and
persistence code. Preserve native result fields, IDs, coordinates, status, and
receipts where present. A direct callable is not a system grant; follow the root
SecureCore authority law and any declared CompuCog observation requirement.

## Known staged or dead paths

Registration and dead-code status are unresolved from this local inventory. Trace non-test callers and verify an actual run.

## Next contract to read

Read the selected source file, its caller, validator, return branch, and current runtime state. Use parent instructions
for cross-module handoffs. Mark unproven behavior `UNVERIFIED`.
