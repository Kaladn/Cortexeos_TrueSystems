"""Package and statically catalog recovered code without executing it."""

from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import resource
import time
from typing import Any, Iterable
import warnings

from .code_intake import _component_records, _jsonl


PACKAGE_SCHEMA = "truecore_recovered_code_package@1"
CATALOG_SCHEMA = "truecore_code_archaeology@1"
SOURCE_SUFFIXES = {
    ".bash", ".bat", ".c", ".cc", ".cjs", ".cmd", ".cpp", ".cs", ".cxx",
    ".fish", ".fs", ".fsx", ".go", ".h", ".hh", ".hpp", ".hxx", ".java",
    ".js", ".jsx", ".kt", ".kts", ".lua", ".mjs", ".php", ".ps1", ".py",
    ".pyw", ".r", ".rb", ".rs", ".sh", ".sql", ".swift", ".ts", ".tsx",
    ".zsh",
}
SKIP_PARTS = {
    ".git", ".mypy_cache", ".nox", ".pytest_cache", ".ruff_cache", ".tox",
    "__pycache__", "build", "dist", "node_modules", "site-packages", "target",
}
LANGUAGES = {
    ".bash": "Shell", ".bat": "Windows Batch", ".c": "C", ".cc": "C++",
    ".cjs": "JavaScript", ".cmd": "Windows Command Script", ".cpp": "C++",
    ".cs": "C#", ".cxx": "C++", ".fish": "Fish Shell", ".fs": "F#",
    ".fsx": "F#", ".go": "Go", ".h": "C/C++ Header", ".hh": "C++ Header",
    ".hpp": "C++ Header", ".hxx": "C++ Header", ".java": "Java",
    ".js": "JavaScript", ".jsx": "JavaScript JSX", ".kt": "Kotlin",
    ".kts": "Kotlin Script", ".lua": "Lua", ".mjs": "JavaScript",
    ".php": "PHP", ".ps1": "PowerShell", ".py": "Python", ".pyw": "Python",
    ".r": "R", ".rb": "Ruby", ".rs": "Rust", ".sh": "Shell", ".sql": "SQL",
    ".swift": "Swift", ".ts": "TypeScript", ".tsx": "TypeScript TSX",
    ".zsh": "Z shell",
}
WINDOWS_PATTERNS = (
    ("windows_native_script", re.compile(r".*"), {".bat", ".cmd", ".ps1"}, "rewrite_or_linux_wrapper"),
    ("drive_letter_path", re.compile(r"(?<![A-Za-z0-9])[A-Za-z]:\\\\"), None, "replace_fixed_drive_path"),
    ("windows_environment_variable", re.compile(r"%(?:APPDATA|LOCALAPPDATA|USERPROFILE|PROGRAMFILES|TEMP)%", re.I), None, "replace_windows_environment_lookup"),
    ("windows_python_api", re.compile(r"\b(?:winreg|winsound|msvcrt|ctypes\.windll|os\.startfile|pywin32|win32api|win32com)\b"), None, "replace_or_gate_windows_api"),
    ("windows_process", re.compile(r"\b(?:cmd\.exe|powershell\.exe|pwsh\.exe|wsl\.exe|explorer\.exe|sc\.exe)\b", re.I), None, "replace_or_gate_windows_process"),
    ("windows_platform_branch", re.compile(r"(?:sys\.platform\s*==\s*['\"]win32|os\.name\s*==\s*['\"]nt['\"]|platform\.system\(\)\s*==\s*['\"]Windows['\"])", re.I), None, "review_platform_branch"),
    ("windows_registry", re.compile(r"\b(?:HKEY_[A-Z_]+|CurrentVersion\\\\Run)\b"), None, "replace_or_remove_registry_dependency"),
    ("windows_shell_command", re.compile(r"\b(?:taskkill|schtasks|reg\.exe|netsh|wmic|where\.exe)\b", re.I), None, "replace_windows_shell_command"),
)
RESEARCH_MARKERS = {
    "external_research", "research_development", "research_reference_not_runtime",
    "whole_pc_selected_references",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: bytes | dict | list) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else _canonical(value)).hexdigest()


def _atomic_json(path: Path, value: Any) -> dict[str, Any]:
    payload = _canonical(value) + b"\n"
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_bytes(payload)
    os.replace(temporary, path)
    return {"path": path.name, "sha256": _digest(payload), "bytes": len(payload)}


def _atomic_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    count = 0
    for row in rows:
        writer.writerow(row)
        count += 1
    payload = stream.getvalue().encode("utf-8")
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_bytes(payload)
    os.replace(temporary, path)
    return {"path": path.name, "sha256": _digest(payload), "bytes": len(payload), "records": count}


def _atomic_text(path: Path, value: str) -> dict[str, Any]:
    payload = value.encode("utf-8")
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_bytes(payload)
    os.replace(temporary, path)
    return {"path": path.name, "sha256": _digest(payload), "bytes": len(payload)}


def _excluded(parts: tuple[str, ...]) -> str | None:
    for part in parts:
        lowered = part.casefold()
        if lowered in SKIP_PARTS:
            return f"excluded_directory:{lowered}"
        if lowered in {"venv", ".venv"} or lowered.startswith(("venv-", ".venv-")):
            return "excluded_directory:virtual_environment"
    return None


def _source_candidates(source_root: Path) -> tuple[list[Path], list[dict[str, Any]]]:
    included: list[Path] = []
    excluded: list[dict[str, Any]] = []
    paths = sorted(source_root.rglob("*"), key=lambda item: item.relative_to(source_root).as_posix())
    for path in paths:
        if not path.is_file() or path.suffix.casefold() not in SOURCE_SUFFIXES:
            continue
        relative = path.relative_to(source_root)
        reason = _excluded(relative.parts)
        if reason:
            excluded.append({"source_relative_path": relative.as_posix(), "reason": reason})
        else:
            included.append(path)
    return included, excluded


def _duplicate_groups(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        grouped[row["source_sha256"]].append(row["source_relative_path"])
    output = {}
    for digest, members in sorted(grouped.items()):
        if len(members) < 2:
            continue
        members.sort()
        group_id = _digest({"kind": "exact_file_bytes", "sha256": digest, "members": members})
        output[digest] = {"duplicate_group_id": group_id, "canonical_path": members[0], "members": members}
    return output


def build_package(source_root: Path, output_root: Path) -> dict[str, Any]:
    """Copy selected recovered source bytes into an atomically published package."""

    source_root = source_root.resolve()
    output_root = output_root.resolve()
    if not source_root.is_dir():
        raise FileNotFoundError(f"source root is not a directory: {source_root}")
    if output_root.exists():
        raise FileExistsError(f"output root already exists: {output_root}")
    stage = output_root.with_name(f".{output_root.name}.partial-{os.getpid()}")
    if stage.exists():
        raise FileExistsError(f"staging root already exists: {stage}")
    started = time.perf_counter()
    files, excluded = _source_candidates(source_root)
    (stage / "files").mkdir(parents=True)
    rows = []
    for source in files:
        relative = source.relative_to(source_root)
        raw = source.read_bytes()
        packaged = stage / "files" / relative
        packaged.parent.mkdir(parents=True, exist_ok=True)
        packaged.write_bytes(raw)
        rows.append({
            "schema": f"{PACKAGE_SCHEMA}:source_file",
            "source_relative_path": relative.as_posix(),
            "packaged_relative_path": f"files/{relative.as_posix()}",
            "source_sha256": _digest(raw),
            "byte_size": len(raw),
            "suffix": source.suffix.casefold(),
            "language": LANGUAGES[source.suffix.casefold()],
            "custody": "recovered_undelete_copy",
            "authority": "historical_source_evidence_not_runtime",
        })
    duplicates = _duplicate_groups(rows)
    for row in rows:
        group = duplicates.get(row["source_sha256"])
        row["duplicate_group_id"] = group["duplicate_group_id"] if group else None
    listing = _jsonl(stage / "deterministic-file-list.jsonl", rows)
    excluded_listing = _jsonl(stage / "excluded-code-candidates.jsonl", excluded)
    duplicate_listing = _jsonl(stage / "exact-duplicate-groups.jsonl", duplicates.values())
    package_basis = {
        "schema": PACKAGE_SCHEMA,
        "source_classification": "recovered_historical_code",
        "source_root": str(source_root),
        "ordering": "source_relative_path_unicode_codepoint",
        "selection": {
            "included_suffixes": sorted(SOURCE_SUFFIXES),
            "excluded_directory_parts": sorted(SKIP_PARTS),
            "virtual_environment_rule": "venv/.venv exact or hyphen-prefixed directory",
        },
        "files": len(rows),
        "bytes": sum(row["byte_size"] for row in rows),
        "excluded_code_candidates": len(excluded),
        "exact_duplicate_groups": len(duplicates),
        "artifacts": [listing, excluded_listing, duplicate_listing],
    }
    package_basis["package_id"] = _digest({key: value for key, value in package_basis.items() if key != "source_root"})
    _atomic_json(stage / "manifest.json", package_basis)
    _atomic_json(stage / "performance-receipt.json", {
        "schema": f"{PACKAGE_SCHEMA}:performance_receipt",
        "elapsed_wall_seconds": time.perf_counter() - started,
        "files_per_second": len(rows) / max(time.perf_counter() - started, 1e-9),
    })
    os.replace(stage, output_root)
    return package_basis


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _verify_package(package_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest_path = package_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != PACKAGE_SCHEMA:
        raise ValueError("unsupported recovered-code package schema")
    rows = _load_jsonl(package_root / "deterministic-file-list.jsonl")
    if len(rows) != manifest.get("files"):
        raise ValueError("package file count does not match manifest")
    for row in rows:
        path = (package_root / row["packaged_relative_path"]).resolve()
        try:
            path.relative_to(package_root)
        except ValueError as error:
            raise ValueError("packaged path escapes package root") from error
        raw = path.read_bytes()
        if len(raw) != row["byte_size"] or _digest(raw) != row["source_sha256"]:
            raise ValueError(f"package hash mismatch: {row['source_relative_path']}")
    return manifest, rows


def _declared_purpose(text: str, suffix: str) -> str | None:
    if suffix not in {".py", ".pyw"}:
        return None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            value = ast.get_docstring(ast.parse(text), clean=False)
    except SyntaxError:
        return None
    return value


def _first_line(value: str | None) -> str:
    return value.strip().splitlines()[0] if value and value.strip() else ""


def _summary_markdown(manifest: dict[str, Any], windows_files: int) -> str:
    lines = [
        "# Recovered Code Capability Catalog",
        "",
        "Static evidence only. No recovered code was imported, executed, admitted, or assigned to a TrueSystems component.",
        "",
        "## Coverage",
        "",
        f"- Files cataloged: {manifest['source_files']:,}",
        f"- Declared code units: {manifest['code_units']:,}",
        f"- Static call edges: {manifest['call_edges']:,}",
        f"- Files requiring Windows-to-Linux review: {windows_files:,}",
        "",
        "## Languages",
        "",
        "| Language | Files |",
        "|---|---:|",
    ]
    lines.extend(f"| {name} | {count:,} |" for name, count in manifest["language_counts"].items())
    lines.extend([
        "",
        "## Outputs",
        "",
        "- `CAPABILITY_INDEX.csv`: compact one-row-per-file inventory for sorting and review.",
        "- `WINDOWS_TO_LINUX_QUEUE.jsonl`: only files with explicit Windows evidence, including line-level evidence and conversion actions.",
        "- `MASTER_CODE_ARCHAEOLOGY.jsonl`: complete file records, declared purposes, symbols, inputs, calls, state access, duplicates, and claim boundaries.",
        "- `RecoveredCode/`: native TrueCore static literacy, relationship, and partial-trajectory layers.",
        "",
        "## Interpretation limits",
        "",
        "- A declared function or call is a source-code candidate, not proof that it works.",
        "- No observed Windows dependency does not establish Linux compatibility.",
        "- Conversion actions are review categories, not completed ports.",
        "- Purpose is reported only from declarations and structure; missing semantics are left unresolved.",
        "- Exact duplicate groups are byte identity only, not inferred semantic equivalence.",
        "",
    ])
    return "\n".join(lines)


def _windows_evidence(text: str, suffix: str) -> list[dict[str, Any]]:
    evidence = []
    for evidence_type, pattern, suffixes, action in WINDOWS_PATTERNS:
        if suffixes is not None:
            if suffix in suffixes:
                evidence.append({"type": evidence_type, "line": 1, "conversion_action": action})
            continue
        for match in pattern.finditer(text):
            evidence.append({
                "type": evidence_type,
                "line": text.count("\n", 0, match.start()) + 1,
                "conversion_action": action,
            })
    unique = {(row["type"], row["line"], row["conversion_action"]): row for row in evidence}
    return [unique[key] for key in sorted(unique)]


def _research_role(relative: str) -> str:
    lowered = {part.casefold() for part in Path(relative).parts}
    return "RESEARCH_REFERENCE" if lowered & RESEARCH_MARKERS else "UNCLASSIFIED_RECOVERED_CODE"


def _usage() -> tuple[float, float, int]:
    self_usage = resource.getrusage(resource.RUSAGE_SELF)
    child_usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = self_usage.ru_utime + self_usage.ru_stime + child_usage.ru_utime + child_usage.ru_stime
    return time.perf_counter(), cpu, max(self_usage.ru_maxrss, child_usage.ru_maxrss)


def analyze_package(package_root: Path, output_root: Path, workers: int = 16) -> dict[str, Any]:
    """Run TrueCore static intake and emit a review-oriented master catalog."""

    package_root = package_root.resolve()
    output_root = output_root.resolve()
    if output_root.exists():
        raise FileExistsError(f"output root already exists: {output_root}")
    if workers < 1:
        raise ValueError("workers must be at least 1")
    stage = output_root.with_name(f".{output_root.name}.partial-{os.getpid()}")
    if stage.exists():
        raise FileExistsError(f"staging root already exists: {stage}")
    stage.mkdir(parents=True)
    wall_start, cpu_start, _ = _usage()
    package_manifest, package_rows = _verify_package(package_root)
    files, units, edges, trajectories = _component_records("RecoveredCode", package_root / "files", None, workers)
    component = stage / "RecoveredCode"
    component.mkdir()
    standard_artifacts = [
        _jsonl(component / "level-1-code-literacy.jsonl", sorted([*files, *units], key=_canonical)),
        _jsonl(component / "level-2-operational-relationships.jsonl", sorted(edges, key=lambda row: row["record_id"])),
        _jsonl(component / "level-3-operator-trajectories.partial.jsonl", sorted(trajectories, key=_canonical)),
    ]
    file_records = {row["repository_relative_file"]: row for row in files}
    units_by_file: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for unit in units:
        units_by_file[unit["repository_relative_file"]].append(unit)
    failures_by_file: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in trajectories:
        if row.get("schema", "").endswith(":failure"):
            failures_by_file[row["path"]].append(row)
    duplicate_groups = {row["duplicate_group_id"]: row for row in _load_jsonl(package_root / "exact-duplicate-groups.jsonl")}
    master = []
    portability_counts: Counter[str] = Counter()
    parse_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()
    for source in package_rows:
        relative = source["source_relative_path"]
        packaged = package_root / source["packaged_relative_path"]
        raw = packaged.read_bytes()
        try:
            text = raw.decode("utf-8")
            text_status = "UTF8"
        except UnicodeDecodeError:
            text = ""
            text_status = "INVALID_UTF8"
        suffix = source["suffix"]
        observed_units = sorted(units_by_file.get(relative, []), key=lambda row: (row["line_start"], row["symbol"]))
        failures = failures_by_file.get(relative, [])
        if text_status == "INVALID_UTF8":
            parse_status = "INVALID_UTF8_EXACT_BYTES_RETAINED"
        elif suffix in {".py", ".pyw"} and failures:
            parse_status = "PYTHON_SYNTAX_ERROR"
        elif suffix in {".py", ".pyw"}:
            parse_status = "PYTHON_AST_PARSED"
        else:
            parse_status = "LANGUAGE_ADAPTER_NOT_IMPLEMENTED_EXACT_BYTES_RETAINED"
        windows = _windows_evidence(text, suffix) if text_status == "UTF8" else []
        portability = "WINDOWS_TO_LINUX_REVIEW_REQUIRED" if windows else "NO_EXPLICIT_WINDOWS_DEPENDENCY_OBSERVED"
        role = _research_role(relative)
        group = duplicate_groups.get(source.get("duplicate_group_id"))
        capabilities = []
        for unit in observed_units:
            capabilities.append({
                "capability_id": unit["record_id"],
                "symbol": unit["symbol"],
                "symbol_type": unit["symbol_type"],
                "line_start": unit["line_start"],
                "line_end": unit["line_end"],
                "declared_purpose": unit.get("docstring"),
                "inputs": unit.get("inputs", []),
                "output_annotation": unit.get("output_annotation"),
                "observed_calls": unit.get("calls", []),
                "state_read": unit.get("state_read", []),
                "state_written": unit.get("state_written", []),
                "status": "STATIC_SOURCE_CANDIDATE_NOT_EXECUTED",
            })
        basis = {"schema": f"{CATALOG_SCHEMA}:file", "source_relative_path": relative, "source_sha256": source["source_sha256"]}
        master.append({
            **basis,
            "catalog_entry_id": _digest(basis),
            "packaged_relative_path": source["packaged_relative_path"],
            "byte_size": source["byte_size"],
            "language": source["language"],
            "source_custody": source["custody"],
            "authority": source["authority"],
            "archaeology_role": role,
            "text_status": text_status,
            "parse_status": parse_status,
            "declared_module_purpose": _declared_purpose(text, suffix) if text_status == "UTF8" else None,
            "imports": file_records.get(relative, {}).get("imports", []),
            "capabilities": capabilities,
            "capability_count": len(capabilities),
            "windows_dependency_evidence": windows,
            "portability_status": portability,
            "linux_conversion_status": "REVIEW_REQUIRED" if windows else "NOT_ESTABLISHED",
            "exact_duplicate": ({"duplicate_group_id": group["duplicate_group_id"], "canonical_path": group["canonical_path"]} if group else None),
            "current_true_system_fit": {"status": "UNRESOLVED_REQUIRES_FILE_REVIEW", "candidate_systems": []},
            "semantic_summary": {"status": "NOT_DERIVED_BY_STATIC_INTAKE", "text": None},
            "failures": failures,
            "claim_boundary": [
                "Recovered code is historical evidence, not current runtime authority.",
                "Static symbols and calls are candidates, not proof of successful execution.",
                "No Windows evidence observed does not prove Linux compatibility.",
                "TrueSystems placement requires human/operator review of the file evidence.",
            ],
        })
        portability_counts[portability] += 1
        parse_counts[parse_status] += 1
        role_counts[role] += 1
        language_counts[source["language"]] += 1
    master.sort(key=lambda row: row["source_relative_path"])
    master_artifact = _jsonl(stage / "MASTER_CODE_ARCHAEOLOGY.jsonl", master)
    index_fields = [
        "catalog_entry_id", "source_relative_path", "source_sha256", "byte_size", "language",
        "archaeology_role", "parse_status", "declared_module_purpose", "capability_count",
        "capability_symbols", "portability_status", "windows_evidence_types",
        "linux_conversion_actions", "exact_duplicate_group_id", "current_true_system_fit",
    ]
    index_rows = []
    windows_queue = []
    for row in master:
        windows_types = sorted({item["type"] for item in row["windows_dependency_evidence"]})
        conversion_actions = sorted({item["conversion_action"] for item in row["windows_dependency_evidence"]})
        index_rows.append({
            "catalog_entry_id": row["catalog_entry_id"],
            "source_relative_path": row["source_relative_path"],
            "source_sha256": row["source_sha256"],
            "byte_size": row["byte_size"],
            "language": row["language"],
            "archaeology_role": row["archaeology_role"],
            "parse_status": row["parse_status"],
            "declared_module_purpose": _first_line(row["declared_module_purpose"]),
            "capability_count": row["capability_count"],
            "capability_symbols": " | ".join(item["symbol"] for item in row["capabilities"]),
            "portability_status": row["portability_status"],
            "windows_evidence_types": " | ".join(windows_types),
            "linux_conversion_actions": " | ".join(conversion_actions),
            "exact_duplicate_group_id": (row["exact_duplicate"] or {}).get("duplicate_group_id", ""),
            "current_true_system_fit": row["current_true_system_fit"]["status"],
        })
        if row["windows_dependency_evidence"]:
            windows_queue.append({
                "catalog_entry_id": row["catalog_entry_id"],
                "source_relative_path": row["source_relative_path"],
                "source_sha256": row["source_sha256"],
                "language": row["language"],
                "declared_module_purpose": row["declared_module_purpose"],
                "capabilities": row["capabilities"],
                "windows_dependency_evidence": row["windows_dependency_evidence"],
                "linux_conversion_actions": conversion_actions,
                "conversion_status": "REVIEW_REQUIRED_NOT_CONVERTED",
                "claim_boundary": row["claim_boundary"],
            })
    index_artifact = _atomic_csv(stage / "CAPABILITY_INDEX.csv", index_fields, index_rows)
    windows_artifact = _jsonl(stage / "WINDOWS_TO_LINUX_QUEUE.jsonl", windows_queue)
    manifest = {
        "schema": CATALOG_SCHEMA,
        "classification": "STATIC_RECOVERED_CODE_CATALOG_NOT_ADMITTED_NOT_EXECUTED",
        "package_id": package_manifest["package_id"],
        "package_manifest_sha256": _digest((package_root / "manifest.json").read_bytes()),
        "deterministic_order": "source_relative_path_unicode_codepoint",
        "source_files": len(master),
        "code_units": len(units),
        "call_edges": len(edges),
        "partial_trajectories_and_failures": len(trajectories),
        "language_counts": dict(sorted(language_counts.items())),
        "parse_status_counts": dict(sorted(parse_counts.items())),
        "portability_status_counts": dict(sorted(portability_counts.items())),
        "archaeology_role_counts": dict(sorted(role_counts.items())),
        "likeness_scope": "exact_byte_duplicates_only",
        "semantic_mapping_performed": False,
        "code_execution_performed": False,
        "artifacts": {
            "master_catalog": master_artifact,
            "capability_index": index_artifact,
            "windows_to_linux_queue": windows_artifact,
            "truecore_static_intake": standard_artifacts,
        },
    }
    summary_artifact = _atomic_text(stage / "CAPABILITY_SUMMARY.md", _summary_markdown(manifest, len(windows_queue)))
    manifest["artifacts"]["human_summary"] = summary_artifact
    manifest_artifact = _atomic_json(stage / "manifest.json", manifest)
    wall_end, cpu_end, maximum_resident = _usage()
    _atomic_json(stage / "performance-receipt.json", {
        "schema": f"{CATALOG_SCHEMA}:performance_receipt",
        "elapsed_wall_seconds": wall_end - wall_start,
        "aggregate_cpu_seconds": cpu_end - cpu_start,
        "workers": workers,
        "maximum_resident_kib": maximum_resident,
        "records_per_second": (len(master) + len(units) + len(edges)) / max(wall_end - wall_start, 1e-9),
        "manifest": manifest_artifact,
    })
    os.replace(stage, output_root)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    package_parser = subparsers.add_parser("package")
    package_parser.add_argument("--source-root", type=Path, required=True)
    package_parser.add_argument("--output-root", type=Path, required=True)
    analyze_parser = subparsers.add_parser("analyze")
    analyze_parser.add_argument("--package-root", type=Path, required=True)
    analyze_parser.add_argument("--output-root", type=Path, required=True)
    analyze_parser.add_argument("--workers", type=int, default=16)
    args = parser.parse_args(argv)
    if args.command == "package":
        result = build_package(args.source_root, args.output_root)
    else:
        result = analyze_package(args.package_root, args.output_root, args.workers)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
