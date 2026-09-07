"""Authoritative DocuFilm document and glyph-state intake."""

from .docufilm_truemem import build_docufilm_truemem_hierarchy
from .source_typing import SourceTypeRule, classify_source
from .tabular_intake import parse_tabular_source
from .typed_structural import compile_typed_structures

from .structural_binding import compile_question_structures, compile_text_structures

__all__ = [
    "SourceTypeRule",
    "build_docufilm_truemem_hierarchy",
    "classify_source",
    "compile_question_structures",
    "compile_text_structures",
    "compile_typed_structures",
    "parse_tabular_source",
]
