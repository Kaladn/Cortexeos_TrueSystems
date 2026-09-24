# TrueMem/src/truemem/engine agent instructions

**DO NOT CREATE A NEW WORKFLOW UNTIL THE EXISTING ENTRYPOINT HAS BEEN TRACED.**

## Scope and governing parent

This file governs `TrueMem/src/truemem/engine/`. Read `TrueMem/AGENTS.md` and all ancestor
`AGENTS.md` files first. The code facts below do not establish effects or authority.

## Production entrypoint

`pipeline.py:docufilm_intake` constructs the admitted mapping path.
`evidence_retrieval.py:query_evidence_need_mapping` is the structured
EvidenceNeed retrieval callable imported by `cli.py`. Inspect
`evidence_need.py` validation, occurrence postings, relation persistence, and
return fields before use. `querying.py:direct_question_query_baseline` and
`deeper_wider_after_answer` are separate answer-shaped/diagnostic paths;
do not substitute them for EvidenceNeed retrieval.

## Local code-defined surface

- `__init__.py`.
- `anchor_focus.py`: build_anchor_focus (line 17), prepare_anchor_focus_index (line 112).
- `anchors.py`: anchorize (line 79), normalize_anchor (line 104), structural_anchor (line 109), anchor_kind (line 119), and 10 more source definitions.
- `answer_reasoning_reverse_walk.py`: run_answer_reasoning_reverse_walk (line 34).
- `base.py`: DatasetPaths (line 23), safe_id (line 43), dataset_paths (line 49), public_paths (line 71), and 6 more source definitions.
- `chat.py`: parse_chat_metadata_block (line 8), parse_chat_datetime (line 47), parse_filter_date (line 74), build_metadata_filter (line 82), and 1 more source definitions.
- `chat_counts.py`: default_chat_count_root (line 13), append_chat_count (line 20).
- `codex.py`: stage_codex_sessions (line 11), stage_codex_markdown_export (line 94), stage_chatgpt_export (line 155), read_codex_session_index (line 238), and 1 more source definitions.
- `context_clouds.py`: build_context_cloud (line 16), score_context_cloud_lane (line 62).
- `count_walk_speech.py`: count_walk_speech (line 13).
- `crosslinks.py`: build_citation_crosslinks (line 13), crosslink_candidate_rows (line 83), classify_crosslink (line 94), crosslink_confidence (line 104), and 2 more source definitions.
- `dataset_local_v2.py`: canonical_bytes (line 32), sha256_bytes (line 36), symbol_hex (line 40), symbol_raw (line 46), and 6 more source definitions.
- 35 additional direct source files; enumerate them before claiming complete coverage.

## Allowed and forbidden operations

Use only the exact callable reached through the applicable parent authority path; do not create a substitute wrapper or ingress. Do not infer inputs, effects, permissions, or safe retry from names.

## Inputs, outputs, authority boundary, and receipts

Inspect the selected signature, validator, callers, return branches, and
persistence code. Preserve native result fields, IDs, coordinates, status, and
receipts where present. A direct callable is not a system grant; follow the root
SecureCore authority law and any declared CompuCog observation requirement.

## Known staged or dead paths

`xpu_relationship_index.py` contains pairwise/scalar ranking; the audited
non-test import is under TrueCore training. `pipeline.py` also writes a
center-neighbor-signed-offset aggregate while exact occurrence postings
remain separate. Preserve that distinction. Trace current callers before
changing active/dead classification.

## Next contract to read

Read the selected source file, its caller, validator, return branch, and current runtime state. Use parent instructions
for cross-module handoffs. Mark unproven behavior `UNVERIFIED`.
