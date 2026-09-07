"""Fail-closed code transcription and syntax reading from DocuFilm glyph state."""

from __future__ import annotations

import ast
import io
import keyword
import token
import tokenize
from typing import Any

from .hashing import stable_hash
from .glyph_lexicon import GlyphLexicon, normalize_trim_pattern
from .lifetime_counts import LifetimeCounts
from .state_reader import DocumentStateReader
from .code_language_readers import read_code_language_structure


SCHEMA = "truevision_code_glyph_read@1"
CONTEXT_SCHEMA = "truevision_code_deciphering_context@1"
PYTHON_LANGUAGE_NAMES = {"python", "py"}
VISUAL_OBJECT_KINDS = {"source_code_file", "editor_code_region", "terminal_code_listing", "document_code_block"}


def build_code_deciphering_context(
    *,
    source_identity: dict[str, Any],
    source_profile: dict[str, Any],
    visual_object_kind: str,
    source_type_authority: str,
    glyph_lexicon_records: list[dict[str, Any]],
    monospace_calibration: dict[str, Any],
    view: dict[str, Any],
) -> dict[str, Any]:
    """Freeze what the machine is looking at before glyph interpretation."""

    reasons = []
    if source_profile.get("schema") != "truevision_source_type@1":
        reasons.append("invalid_source_profile_schema")
    if source_profile.get("source_type") != "source_code":
        reasons.append("source_type_is_not_source_code")
    if not source_profile.get("language"):
        reasons.append("source_language_is_unknown")
    if visual_object_kind not in VISUAL_OBJECT_KINDS:
        reasons.append("visual_object_kind_is_unknown")
    if source_type_authority not in {"verified_source_profile", "human_declared_visual_code"}:
        reasons.append("source_type_authority_is_not_accepted")
    if not source_identity or not any(source_identity.get(key) for key in ("path", "sha256", "source_id")):
        reasons.append("source_identity_is_missing")
    approved_records = [
        {
            "glyph_id": str(row.get("glyph_id") or ""),
            "display": str(row.get("display") or ""),
            "trim_pattern": list(normalize_trim_pattern(list(row.get("trim_pattern") or []))),
        }
        for row in glyph_lexicon_records if row.get("promotion_status") == "approved"
    ]
    approved_records.sort(key=lambda row: (row["glyph_id"], row["display"], row["trim_pattern"]))
    glyph_lexicon_id = stable_hash({"approved_glyph_records": approved_records}) if approved_records else ""
    calibration = {
        "origin": list(monospace_calibration.get("origin") or []),
        "cell_shape": list(monospace_calibration.get("cell_shape") or []),
        "grid_shape": list(monospace_calibration.get("grid_shape") or []),
        "luma_threshold": float(monospace_calibration.get("luma_threshold", 128.0)),
    }
    monospace_calibration_id = stable_hash(calibration) if all(len(calibration[key]) == 2 for key in ("origin", "cell_shape", "grid_shape")) else ""
    if not glyph_lexicon_id:
        reasons.append("glyph_lexicon_identity_is_missing")
    if not monospace_calibration_id:
        reasons.append("monospace_calibration_identity_is_missing")
    if not bool(view.get("code_region_isolated")):
        reasons.append("code_region_is_not_isolated")
    if not bool(view.get("line_number_gutter_excluded")):
        reasons.append("line_number_gutter_is_not_excluded")
    if bool(view.get("soft_wrapped")):
        reasons.append("soft_wrapped_visual_lines_are_ambiguous")
    if view.get("completeness") not in {"complete_file", "complete_snippet"}:
        reasons.append("view_completeness_is_unknown")
    body = {
        "schema": CONTEXT_SCHEMA,
        "source_identity": dict(source_identity),
        "source_profile": dict(source_profile),
        "visual_object_kind": visual_object_kind,
        "source_type_authority": source_type_authority,
        "glyph_lexicon_id": glyph_lexicon_id,
        "approved_glyph_count": len(approved_records),
        "monospace_calibration_id": monospace_calibration_id,
        "monospace_calibration": calibration,
        "view": dict(view),
        "deciphering_status": "ready" if not reasons else "not_ready",
        "blocking_reasons": reasons,
        "language_inferred_from_glyphs": False,
    }
    body["context_hash"] = stable_hash(body)
    return body


def read_code_state_movie(
    *,
    manifest_path: str,
    frame_index: int,
    page_number: int,
    glyph_lexicon_records: list[dict[str, Any]],
    lifetime_count_records: list[dict[str, Any]],
    deciphering_context: dict[str, Any],
) -> dict[str, Any]:
    """Run the complete stored-state code-reading boundary without raw pixels."""

    from .document_state_movie import extract_monospace_glyph_cells_from_state_movie

    rebuilt = build_code_deciphering_context(
        source_identity=deciphering_context.get("source_identity") or {},
        source_profile=deciphering_context.get("source_profile") or {},
        visual_object_kind=str(deciphering_context.get("visual_object_kind") or ""),
        source_type_authority=str(deciphering_context.get("source_type_authority") or ""),
        glyph_lexicon_records=glyph_lexicon_records,
        monospace_calibration=deciphering_context.get("monospace_calibration") or {},
        view=deciphering_context.get("view") or {},
    )
    if rebuilt.get("context_hash") != deciphering_context.get("context_hash"):
        raise ValueError("deciphering context does not match glyph lexicon or calibration")
    calibration = deciphering_context["monospace_calibration"]
    glyph_cells = extract_monospace_glyph_cells_from_state_movie(
        manifest_path=manifest_path,
        frame_index=frame_index,
        origin=tuple(calibration["origin"]),
        cell_shape=tuple(calibration["cell_shape"]),
        grid_shape=tuple(calibration["grid_shape"]),
        luma_threshold=float(calibration["luma_threshold"]),
    )
    identity = deciphering_context["source_identity"]
    source_id = str(identity.get("source_id") or identity.get("path") or identity.get("sha256"))
    return read_code_glyph_frame(
        reader=DocumentStateReader(
            lexicon=GlyphLexicon.from_records(glyph_lexicon_records),
            lifetime_counts=LifetimeCounts.from_records(lifetime_count_records),
        ),
        source_id=source_id,
        frame_id=f"docufilm:{frame_index}",
        page_number=page_number,
        glyph_cells=glyph_cells,
        grid_shape=tuple(calibration["grid_shape"]),
        deciphering_context=deciphering_context,
    )


def _python_name(node: ast.AST | None) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _python_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def _python_syntax(text: str) -> dict[str, Any]:
    try:
        tokens = [
            {
                "kind": token.tok_name.get(item.type, str(item.type)),
                "exact": item.string,
                "start": list(item.start),
                "end": list(item.end),
            }
            for item in tokenize.generate_tokens(io.StringIO(text).readline)
        ]
        tree = ast.parse(text, filename="<docufilm-glyph-state>", type_comments=True)
    except (SyntaxError, tokenize.TokenError, IndentationError) as error:
        return {
            "status": "syntax_rejected",
            "parser": "python_stdlib_ast_tokenize",
            "error_type": type(error).__name__,
            "line": getattr(error, "lineno", None),
            "column": getattr(error, "offset", None),
            "execution_performed": False,
        }

    definitions = []
    imports = []
    calls = []
    for node in ast.walk(tree):
        span = {
            "line_start": getattr(node, "lineno", None),
            "column_start": getattr(node, "col_offset", None),
            "line_end": getattr(node, "end_lineno", None),
            "column_end": getattr(node, "end_col_offset", None),
        }
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definitions.append({"kind": type(node).__name__, "name": node.name, **span})
        elif isinstance(node, ast.Import):
            imports.extend({"module": name.name, "alias": name.asname, **span} for name in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.append({"module": node.module or "", "names": [name.name for name in node.names], **span})
        elif isinstance(node, ast.Call):
            calls.append({"callee_surface": _python_name(node.func), **span})
    return {
        "status": "syntax_verified",
        "parser": "python_stdlib_ast_tokenize",
        "tokens": tokens,
        "definitions": sorted(definitions, key=lambda row: (row["line_start"] or 0, row["column_start"] or 0)),
        "imports": sorted(imports, key=lambda row: (row["line_start"] or 0, row["column_start"] or 0)),
        "calls": sorted(calls, key=lambda row: (row["line_start"] or 0, row["column_start"] or 0)),
        "keyword_vocabulary": sorted(keyword.kwlist),
        "execution_performed": False,
        "behavior_proven": False,
    }


def read_code_glyph_frame(
    *,
    reader: DocumentStateReader,
    source_id: str,
    frame_id: str,
    page_number: int,
    glyph_cells: list[dict[str, Any]],
    grid_shape: tuple[int, int],
    deciphering_context: dict[str, Any],
) -> dict[str, Any]:
    """Transcribe calibrated glyph cells and parse only a complete exact read."""

    row_count, column_count = int(grid_shape[0]), int(grid_shape[1])
    if min(row_count, column_count) <= 0:
        raise ValueError("code grid shape must be positive")
    if deciphering_context.get("schema") != CONTEXT_SCHEMA:
        raise ValueError("code read requires a TrueVision deciphering context")
    if deciphering_context.get("deciphering_status") != "ready":
        raise ValueError(f"code deciphering context is not ready: {deciphering_context.get('blocking_reasons')}")
    source_profile = deciphering_context["source_profile"]
    declared_language = str(source_profile["language"])
    state_read = reader.read_page_frame(
        source_id=source_id,
        frame_id=frame_id,
        page_number=page_number,
        glyph_cells=glyph_cells,
    )
    layout: dict[tuple[int, int], dict[str, Any]] = {}
    for record in state_read["glyph_records"]:
        position = record.get("layout_position") or {}
        if "row" not in position or "column" not in position:
            raise ValueError("every code glyph requires explicit row and column")
        location = int(position["row"]), int(position["column"])
        if not (0 <= location[0] < row_count and 0 <= location[1] < column_count):
            raise ValueError("code glyph lies outside declared grid")
        if location in layout:
            raise ValueError("multiple code glyphs occupy one visual cell")
        layout[location] = record

    matrix = [[" " for _column in range(column_count)] for _row in range(row_count)]
    unknown_cells = []
    invalid_symbols = []
    for (row, column), record in layout.items():
        symbol = str(record.get("glyph_symbol") or "")
        if record.get("recognition_status") != "recognized":
            matrix[row][column] = "\ufffd"
            unknown_cells.append({"row": row, "column": column, "pattern_hash": record.get("pattern_hash")})
        elif len(symbol) != 1:
            matrix[row][column] = "\ufffd"
            invalid_symbols.append({"row": row, "column": column, "glyph_id": record.get("glyph_id"), "display": symbol})
        else:
            matrix[row][column] = symbol

    visual_lines = ["".join(row) for row in matrix]
    transcription_lines = [line.rstrip(" ") for line in visual_lines]
    transcription = "\n".join(transcription_lines)
    complete = not unknown_cells and not invalid_symbols
    from truemem.engine.anchors import anchor_kind, anchorize

    text_anchors = anchorize(transcription) if complete else []
    glyph_object_anchors = [
        f"object:glyph:{record['state_hash']}" for record in state_read["glyph_records"]
    ]
    whitespace_runs = []
    for row, line in enumerate(visual_lines):
        start = None
        for column, value in enumerate(f"{line}\0"):
            if value == " " and start is None:
                start = column
            elif value != " " and start is not None:
                whitespace_runs.append({"row": row, "column_start": start, "column_end_exclusive": column})
                start = None
    language = declared_language.strip().casefold()
    if not complete:
        syntax = {"status": "not_attempted_incomplete_glyph_coverage", "execution_performed": False}
        language_structure = {"status": "not_attempted_incomplete_glyph_coverage"}
    elif language in PYTHON_LANGUAGE_NAMES:
        syntax = _python_syntax(transcription)
        language_structure = read_code_language_structure(transcription, language)
    else:
        language_structure = read_code_language_structure(transcription, language)
        syntax = language_structure["grammar"]

    result = {
        "schema": SCHEMA,
        "source_id": source_id,
        "frame_id": frame_id,
        "page_number": page_number,
        "declared_language": declared_language,
        "language_inferred": False,
        "deciphering_context": dict(deciphering_context),
        "deciphering_context_hash": deciphering_context["context_hash"],
        "grid_shape": [row_count, column_count],
        "glyph_state_read_hash": state_read["read_hash"],
        "glyph_cell_count": len(glyph_cells),
        "recognized_glyph_count": len(glyph_cells) - len(unknown_cells) - len(invalid_symbols),
        "unknown_cells": unknown_cells,
        "invalid_lexicon_symbols": invalid_symbols,
        "glyph_coverage_complete": complete,
        "transcription_status": "complete_exact_glyph_read" if complete else "incomplete_unknown_glyphs",
        "visual_lines": visual_lines,
        "derived_code_text": transcription if complete else None,
        "diagnostic_transcription_with_unknown_markers": transcription,
        "terminal_newline_status": "unobservable_from_static_visual_frame",
        "anchor_admission": {
            "authority": "TrueMem_after_TrueVision_DocuFilm",
            "glyph_object_anchors": glyph_object_anchors,
            "text_anchors": text_anchors,
            "text_anchor_kinds": [anchor_kind(value) for value in text_anchors],
            "all_observed_glyphs_accepted": len(glyph_object_anchors) == len(glyph_cells),
            "complete_anchor_preservation": complete,
            "glue_anchors_deleted": False,
            "punctuation_deleted": False,
            "whitespace_symbols": 0,
            "whitespace_structure": whitespace_runs,
            "dataset_symbols_allocated": False,
        },
        "syntax": syntax,
        "language_structure": language_structure,
        "truth_boundary": {
            "source_truth_is_docufilm_glyph_state": True,
            "code_text_is_derived": True,
            "unknown_glyphs_are_never_guessed": True,
            "whitespace_comes_only_from_declared_grid_cells": True,
            "language_is_caller_declared": True,
            "visual_object_type_known_before_recognition": True,
            "syntax_does_not_prove_runtime_behavior": True,
            "syntax_never_replaces_complete_anchors": True,
            "execution_import_eval_and_compile_performed": False,
        },
    }
    result["read_hash"] = stable_hash(result)
    return result
