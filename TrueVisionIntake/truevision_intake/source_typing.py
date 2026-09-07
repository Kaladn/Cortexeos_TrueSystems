"""Deterministic, extensible source typing for DocuFilm intake."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Iterable


CODE_LANGUAGES = {
    ".bash": "shell", ".bat": "windows_batch", ".c": "c", ".cc": "cpp",
    ".cjs": "javascript", ".cmd": "windows_command", ".cpp": "cpp", ".cs": "csharp",
    ".cxx": "cpp", ".fish": "fish", ".fs": "fsharp", ".fsx": "fsharp",
    ".go": "go", ".h": "c_cpp_header", ".hh": "cpp_header", ".hpp": "cpp_header",
    ".hxx": "cpp_header", ".java": "java", ".js": "javascript", ".jsx": "javascript_jsx",
    ".kt": "kotlin", ".kts": "kotlin_script", ".lua": "lua", ".mjs": "javascript",
    ".php": "php", ".ps1": "powershell", ".py": "python", ".pyw": "python",
    ".r": "r", ".rb": "ruby", ".rs": "rust", ".sh": "shell", ".sql": "sql",
    ".swift": "swift", ".ts": "typescript", ".tsx": "typescript_tsx", ".zsh": "zsh",
}


@dataclass(frozen=True)
class SourceTypeRule:
    rule_id: str
    source_type: str
    role: str
    capabilities: tuple[str, ...]
    path_markers: tuple[str, ...] = ()
    filename_markers: tuple[str, ...] = ()
    suffixes: tuple[str, ...] = ()


DEFAULT_SOURCE_TYPE_RULES = (
    SourceTypeRule(
        "guidance_path_v1", "investigation_guidance", "method_and_claim_boundary",
        ("guide_dataset_investigation", "constrain_claims"), path_markers=("00-guidance",),
    ),
    SourceTypeRule(
        "capability_catalog_path_v1", "capability_catalog", "derived_static_evidence_view",
        ("locate_capabilities", "trace_static_evidence"), path_markers=("20-catalog",),
    ),
    SourceTypeRule(
        "provenance_path_v1", "provenance_record", "custody_identity_and_verification",
        ("verify_source_identity", "verify_dataset_membership"), path_markers=("30-provenance",),
    ),
    SourceTypeRule(
        "report_filename_v1", "investigation_report", "method_and_findings_report",
        ("guide_dataset_investigation",), filename_markers=("report", "results", "summary", "guide"),
        suffixes=(".md", ".markdown", ".rst", ".txt"),
    ),
    SourceTypeRule(
        "source_code_suffix_v1", "source_code", "historical_source_evidence",
        ("inspect_static_source",), suffixes=tuple(sorted(CODE_LANGUAGES)),
    ),
    SourceTypeRule(
        "structured_record_v1", "structured_records", "dataset_records",
        ("grow_columns_to_observed_width", "parse_tabular_grid", "query_structured_records", "retain_cell_value_anchor_weight"),
        suffixes=(".csv", ".jsonl"),
    ),
    SourceTypeRule(
        "structured_document_v1", "structured_document", "dataset_document",
        ("grow_columns_to_observed_width", "inspect_structured_document", "parse_tabular_grid", "retain_cell_value_anchor_weight"),
        suffixes=(".json",),
    ),
    SourceTypeRule(
        "text_document_v1", "text_document", "document_evidence",
        ("inspect_document_text",), suffixes=(".md", ".markdown", ".rst", ".txt"),
    ),
)


def _content_format(suffix: str, sample: str) -> tuple[str, str]:
    stripped = sample.lstrip()
    if suffix == ".json":
        try:
            json.loads(sample)
        except (json.JSONDecodeError, ValueError):
            return "application/json", "suffix_only_invalid_or_partial_json"
        return "application/json", "parsed_json"
    if suffix == ".jsonl":
        lines = [line for line in sample.splitlines() if line.strip()][:16]
        try:
            for line in lines:
                json.loads(line)
        except (json.JSONDecodeError, ValueError):
            return "application/x-ndjson", "suffix_only_invalid_or_partial_jsonl"
        return "application/x-ndjson", "sampled_json_lines_parsed"
    if suffix == ".csv":
        return "text/csv", "suffix_and_record_shape"
    if suffix in CODE_LANGUAGES:
        shebang = stripped.startswith("#!")
        return f"text/x-{CODE_LANGUAGES[suffix]}", "suffix_and_shebang" if shebang else "suffix"
    if suffix in {".md", ".markdown"}:
        return "text/markdown", "suffix"
    return "text/plain", "suffix"


def classify_source(
    path: str | Path,
    text: str,
    *,
    root: str | Path | None = None,
    rules: Iterable[SourceTypeRule] = DEFAULT_SOURCE_TYPE_RULES,
) -> dict:
    source = Path(path)
    relative = source.relative_to(Path(root)) if root is not None else source
    path_parts = tuple(part.casefold() for part in relative.parts)
    filename = source.name.casefold()
    suffix = source.suffix.casefold()
    selected = None
    match_basis = []
    for rule in rules:
        path_matches = [marker for marker in rule.path_markers if marker.casefold() in path_parts]
        filename_matches = [marker for marker in rule.filename_markers if marker.casefold() in filename]
        suffix_match = suffix in rule.suffixes if rule.suffixes else False
        if rule.path_markers and not path_matches:
            continue
        if rule.filename_markers and not filename_matches:
            continue
        if rule.suffixes and not suffix_match:
            continue
        selected = rule
        match_basis = [*(f"path:{value}" for value in path_matches), *(f"filename:{value}" for value in filename_matches)]
        if suffix_match:
            match_basis.append(f"suffix:{suffix}")
        break
    if selected is None:
        selected = SourceTypeRule(
            "unclassified_text_v1", "unclassified_text", "unresolved",
            ("inspect_text",),
        )
        match_basis = [f"suffix:{suffix or '<none>'}"]
    content_format, content_basis = _content_format(suffix, text[:65536])
    capabilities = sorted({
        "cite_source_blocks", "compile_truevision_structure", "index_dataset_anchors",
        *selected.capabilities,
    })
    return {
        "schema": "truevision_source_type@1",
        "rule_id": selected.rule_id,
        "source_type": selected.source_type,
        "role": selected.role,
        "language": CODE_LANGUAGES.get(suffix),
        "content_format": content_format,
        "capabilities": capabilities,
        "classification_basis": [*match_basis, f"content:{content_basis}"],
        "semantic_inference": False,
        "rule": asdict(selected),
    }
