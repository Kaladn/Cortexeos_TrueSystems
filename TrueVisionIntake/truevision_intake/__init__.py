"""Authoritative DocuFilm document and glyph-state intake."""

from .docufilm_truemem import build_docufilm_truemem_hierarchy

__all__ = ["build_docufilm_truemem_hierarchy"]
from .structural_binding import compile_question_structures, compile_text_structures

__all__ = ["compile_question_structures", "compile_text_structures"]
