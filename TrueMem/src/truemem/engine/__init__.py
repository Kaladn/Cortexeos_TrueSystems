from __future__ import annotations

from .anchors import (
    GLUE_ANCHORS,
    RELATION_ANCHORS,
    WORD_RE,
    anchorize,
    anchor_kind,
    answer_direction_anchors,
    anchors_to_text,
    direction_weight,
    assert_no_symbol_collisions,
    expand_query_anchors,
    normalize_anchor,
    symbol_bytes,
    symbol_for,
    symbol_hex,
)
from .answer_reasoning_reverse_walk import run_answer_reasoning_reverse_walk
from .base import (
    COPYRIGHT,
    COUNT_BACKEND,
    FACSIMILE_WARNING,
    LICENSE_REF,
    MAX_BLOCK_LINES,
    SYMBOL_BYTES,
    SYMBOL_HEX_CHARS,
    SYMBOL_SYSTEM,
    WATERMARK,
    DatasetPaths,
    dataset_paths,
    protected_notice,
    public_paths,
    safe_id,
    sha1_text,
    unique_stamp,
    utc_now,
    with_protected_notice,
    write_json,
)
from .chat import (
    apply_block_metadata_filter,
    build_metadata_filter,
    parse_chat_datetime,
    parse_chat_metadata_block,
    parse_filter_date,
)
from .chat_counts import append_chat_count, default_chat_count_root
from .codex import (
    codex_message_from_row,
    read_codex_session_index,
    stage_chatgpt_export,
    stage_codex_markdown_export,
    stage_codex_sessions,
)
from .crosslinks import (
    build_citation_crosslinks,
    classify_crosslink,
    crosslink_anchor_set,
    crosslink_candidate_rows,
    crosslink_confidence,
    evidence_text_only,
)
from .count_walk_speech import count_walk_speech
from .context_clouds import build_context_cloud, score_context_cloud_lane
from .determinism import (
    determinism_receipt,
    directory_hashes,
    file_receipt,
    load_receipt_questions,
    query_receipt,
    repo_receipt,
    sha256_file,
)
from .dataset_overview import dataset_overview
from .evidence_cloud_speech import run_evidence_cloud_speech
from .evidence_need import AnchorGroup, EvidenceNeed, EVIDENCE_NEED_SCHEMA
from .evidence_retrieval import query_evidence_need, query_evidence_need_mapping
from .evidence_formula import build_topk_pressure_trellis, score_evidence_formula
from .forensic import (
    FORENSIC_LADDER,
    build_forensic_support_receipt,
    forensic_conclusion,
    forensic_support_level,
)
from .pipeline import chunk_block, docufilm_intake, iter_files, split_blocks
from .packet_speech import run_packet_speech
from .pressure_probe import build_pressure_probe_record, run_pressure_probe
from .qualification import (
    contains_true_path_or_endpoint,
    contains_unqualified_slash_phrase,
    has_path_or_config_intent,
    is_broad_heading,
    is_heading_only,
    qualify_candidate,
    qualify_evidence,
    significant_question_terms,
)
from .qa_ledger import append_query_record, export_ledger, recent_questions, show_record
from .relationship_graph import RelationshipCount, RelationshipGraph, SIGNED_LANES
from .query_ruling import (
    SUPPORTED_OPERATIONS,
    build_anchor_structure_sheet,
    relationship_demands,
    validate_ruling_anchor_groups,
)
from .query_pressure_plan import compile_query_pressure_plan
from .operator_skills import available_operator_skills, execute_operator_skill
from .evidence_operands import (
    bind_operator_operands,
    execute_anchor_sheet_capability,
    execute_bound_operator_skill,
    run_anchor_sheet_capability,
)
from .querying import direct_question_batch_baseline, deeper_wider_after_answer, score_blocks, top_relation_neighbors

# Public query is the same hard EvidenceNeed boundary used by CLI and API.
query = query_evidence_need
from .resonance_adapter import adapt_resonance_sample
from .special_search import special_search
from .system_metrics import system_metrics
from .symbolizer import allocate_dataset_symbols, scan_active_symbol_ranges, symbol_hex_from_int
from .topk_diagnostic import build_rank_layer_walk, build_topk_diagnostic_packet, run_topk_diagnostic, write_topk_ladder_outputs
from .storage import (
    ANCHOR_RECORD,
    BLOCK_ANCHOR_RECORD,
    RELATION_RECORD,
    ensure_dataset,
    index_readiness,
    iter_anchor_records,
    iter_relation_records,
    jsonl_count,
    read_block_anchor_rows,
    read_blocks,
    read_anchor_to_symbol,
    read_symbol_to_anchor,
    record_count,
    status,
    touch_binary_files,
    write_binary_counts,
    write_blocks_jsonl,
    write_chat_metadata_index,
    write_citation_jsonl,
    write_coordinate_index,
    write_lexicon,
)

__all__ = [name for name in globals() if not name.startswith("_")]
