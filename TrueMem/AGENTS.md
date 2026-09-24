# TrueMem agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and parent

This file governs `TrueMem/`; read the repository-root `AGENTS.md` and the
narrower source-directory instructions. TrueMem owns dataset symbols, exact
occurrences, signed 6-1-6 relationships, traversal, coordinates, and citations.

## Production entrypoints and allowed operations

`src/truemem/cli.py:main` exposes component commands. The public EvidenceNeed
path is implemented under `src/truemem/engine/`; inspect its typed input
validation and exact return fields before querying. A component CLI or UI route
is not by itself an authorized bot/system route. Trace the actual SecureCore
caller and any operation-specific CompuCog observation requirement
before claiming integration.

## Forbidden operations and authority boundary

Do not feed a raw question, expected answer, or benchmark target into the
EvidenceNeed argument. Do not replace signed origin-preserving occurrences
with pair totals, aggregate scores, or the legacy answer-shaped ranked path.
TrueVision Intake/DocuFilm owns document and glyph admission; TrueMem does not
invent source bytes or final prose answers.

## Inputs, outputs, receipts, and provenance

Preserve admitted dataset/source identity, source hash, block/sentence or
native coordinates, occurrence IDs, signed offsets, relationship records, and
citation fields. Check active persistence and query code; a passing no-pair
test does not prove every alternate route is free of aggregation.

## Known staged paths and next contracts

`src/truemem/engine/xpu_relationship_index.py` contains pairwise ranking code;
the audited non-test import was training-only. Do not promote it into the public
retrieval path. Read `system/contracts/RELATIONSHIP_GRAPH_616.md` and the
narrower engine instructions, then verify current code.
