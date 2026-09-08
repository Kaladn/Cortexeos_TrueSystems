"""Document-as-state-video reader utilities."""

from .contracts import (
    DOCUMENT_STATE_SCHEMA_VERSION,
    build_document_state_read,
    build_glyph_state_record,
)
from .document_video import build_document_video
from .document_state_movie import (
    CELL_FEATURE_NAMES,
    DOCUMENT_STATE_MOVIE_SCHEMA_VERSION,
    build_page_cell_state,
    extract_black_glyph_patterns_from_state_movie,
    extract_monospace_glyph_cells_from_state_movie,
    record_document_state_movie,
    replay_document_state_movie_frame,
    write_document_state_surface,
)
from .code_glyph_reader import build_code_deciphering_context, read_code_glyph_frame, read_code_state_movie
from .code_language_readers import read_code_language_structure
from .glyph_lexicon import GlyphLexicon, GlyphMatch, normalize_trim_pattern, pattern_hash
from .lifetime_counts import LifetimeCounts
from .state_reader import DocumentStateReader
from .intake_control import IntakeControl, intake_state_movie

__all__ = [
    "IntakeControl",
    "intake_state_movie",
    "CELL_FEATURE_NAMES",
    "DOCUMENT_STATE_SCHEMA_VERSION",
    "DOCUMENT_STATE_MOVIE_SCHEMA_VERSION",
    "DocumentStateReader",
    "GlyphLexicon",
    "GlyphMatch",
    "LifetimeCounts",
    "build_page_cell_state",
    "build_document_state_read",
    "build_document_video",
    "build_code_deciphering_context",
    "build_glyph_state_record",
    "extract_black_glyph_patterns_from_state_movie",
    "extract_monospace_glyph_cells_from_state_movie",
    "normalize_trim_pattern",
    "pattern_hash",
    "record_document_state_movie",
    "read_code_glyph_frame",
    "read_code_language_structure",
    "read_code_state_movie",
    "replay_document_state_movie_frame",
    "write_document_state_surface",
]
