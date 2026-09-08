from __future__ import annotations

import json
import hashlib
import re
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterable

from .anchors import anchor_kind, anchorize
from .base import public_paths, safe_id, sha1_text, utc_now, unique_stamp, with_protected_notice
from .base import COUNT_BACKEND, dataset_paths, write_json
from .chat import parse_chat_metadata_block
from .hardware import MIN_RUNTIME_WORKERS, detect_system_resources, enforce_minimum_runtime_requirements
from .storage import (
    ensure_dataset,
    write_binary_counts,
    write_blocks_jsonl,
    write_chat_metadata_index,
    write_citation_jsonl,
    write_coordinate_index,
    write_lexicon,
)
from .symbolizer import allocate_dataset_symbols, update_dataset_manifest_symbol_allocation


TEXT_SOURCE_SUFFIXES = {
    ".bash", ".bat", ".c", ".cc", ".cjs", ".cmd", ".cpp", ".cs", ".cxx",
    ".fish", ".fs", ".fsx", ".go", ".h", ".hh", ".hpp", ".hxx", ".java",
    ".js", ".jsx", ".kt", ".kts", ".lua", ".mjs", ".php", ".ps1", ".py",
    ".pyw", ".r", ".rb", ".rs", ".sh", ".sql", ".swift", ".ts", ".tsx",
    ".zsh",
}
DOCUMENT_SUFFIXES = {".txt", ".md", ".markdown", ".rst", ".csv", ".json", ".jsonl"}


def docufilm_intake(
    runtime_root: str | Path,
    dataset_id: str,
    source: str | Path,
    *,
    owner: str = "operator_defined",
    window: int = 6,
    workers: int | str = "auto",
    reserve_ram_fraction: float = 0.0,
    ram_budget_gb: float | None = None,
    show_progress: bool = False,
    debug_tiny_single_core: bool = False,
    output_format: str = "split",
) -> dict[str, Any]:
    if output_format not in {"split", "native"}:
        raise ValueError("output_format must be split or native")
    source_path = Path(source).expanduser().resolve()
    _refuse_adapter_workspace_root(source_path)
    files = list(iter_files(source_path))
    native_attachments = _native_attachment_files(source_path)
    candidates = [source_path] if source_path.is_file() else sorted(source_path.rglob("*"))
    admitted = set(files) | (set(native_attachments) if output_format == "native" else set())
    unsupported = [str(item) for item in candidates if item.is_file()
                   and not any(part.startswith(".") for part in item.relative_to(source_path).parts[:-1])
                   and item not in admitted]
    if unsupported:
        raise ValueError("UNSUPPORTED_INTAKE_SOURCES: " + json.dumps(unsupported))
    if not files:
        raise FileNotFoundError(source_path)
    if window <= 0:
        raise ValueError("window must be positive")

    anchor_observations: Counter[str] = Counter()
    relation_observations: Counter[tuple[str, str, int]] = Counter()
    block_anchor_rows: list[tuple[str, int, int]] = []
    block_rows: list[dict[str, Any]] = []
    chat_metadata_rows: list[dict[str, Any]] = []
    source_receipts: list[dict[str, Any]] = []
    structural_compilations: list[dict[str, Any]] = []
    structural_keys: set[str] = set()
    resource_plan = _build_intake_resource_plan(
        files=files,
        requested_workers=workers,
        reserve_ram_fraction=reserve_ram_fraction,
        ram_budget_gb=ram_budget_gb,
        debug_tiny_single_core=debug_tiny_single_core,
    )
    effective_workers = int(resource_plan["effective_workers"])
    ensure_dataset(runtime_root, dataset_id, owner=owner)
    paths = dataset_paths(runtime_root, dataset_id)

    file_results = _process_intake_files(files, window=window, workers=effective_workers, show_progress=show_progress)
    work_unit_count = sum(int(result["source_receipt"]["block_count"]) for result in file_results)
    resource_plan["work_unit_count"] = int(work_unit_count)
    resource_plan["parallel_execution_possible"] = bool(work_unit_count >= effective_workers and effective_workers > 1)
    if work_unit_count < effective_workers and effective_workers > 1:
        resource_plan["safety_decisions"].append("work_unit_count_underfeeds_worker_pool")
    for result in sorted(file_results, key=lambda item: int(item["file_order"])):
        source_receipts.append(result["source_receipt"])
        anchor_observations.update(result["anchor_observations"])
        relation_observations.update(result["relation_observations"])
        local_to_global: dict[int, int] = {}
        for block in result["blocks"]:
            local_ordinal = int(block.pop("local_block_ordinal"))
            block_ordinal = len(block_rows)
            local_to_global[local_ordinal] = block_ordinal
            block["block_ordinal"] = block_ordinal
            block_rows.append(block)
            chat_metadata = block.get("chat_metadata")
            if chat_metadata:
                chat_metadata_rows.append({
                    "schema": "truemem_chat_metadata_index_row@1",
                    "dataset_id": safe_id(dataset_id),
                    "scope": "dataset_local",
                    "block_ordinal": block_ordinal,
                    "block_id": block["block_id"],
                    "citation_id": block["citation_id"],
                    "marker": block["marker"],
                    "file_path": block["file_path"],
                    "line_start": block["line_start"],
                    "line_end": block["line_end"],
                    **chat_metadata,
                })
        for compilation in result.get("structural_compilations") or []:
            local_ordinal = int(compilation["block_ordinal"])
            compilation["block_ordinal"] = local_to_global[local_ordinal]
            for structure in compilation["structures"]:
                structure["block_ordinal"] = local_to_global[local_ordinal]
                structural_keys.add(str(structure["structure_key"]))
            for relation in compilation["relations"]:
                relation["block_ordinal"] = local_to_global[local_ordinal]
            structural_compilations.append(compilation)
        for anchor, local_block_ordinal, position in result["block_anchor_rows"]:
            block_anchor_rows.append((anchor, local_to_global[int(local_block_ordinal)], int(position)))

    allocation_observations = anchor_observations.copy()
    for structure_key_value in structural_keys:
        allocation_observations.setdefault(structure_key_value, 0)
    symbol_allocation = allocate_dataset_symbols(runtime_root, dataset_id, allocation_observations)
    symbol_map = symbol_allocation["symbol_map"]
    write_binary_counts(paths, anchor_observations, relation_observations, block_anchor_rows, symbol_map=symbol_map)
    write_blocks_jsonl(paths, block_rows)
    write_lexicon(paths, allocation_observations, symbol_map=symbol_map, symbol_allocation=symbol_allocation)
    from .structural_storage import write_structural_graph
    structural_manifest = write_structural_graph(paths, structural_compilations, symbol_map)
    from .structural_storage import verify_structural_graph
    structural_verification = verify_structural_graph(paths)
    if structural_verification["status"] != "PASS":
        raise RuntimeError(f"STRUCTURAL_GRAPH_VERIFICATION_FAILED: {structural_verification['failures']}")
    update_dataset_manifest_symbol_allocation(paths, symbol_allocation)
    write_citation_jsonl(paths, block_rows)
    write_coordinate_index(paths, block_rows)
    write_chat_metadata_index(paths, chat_metadata_rows)

    native_publication = None
    if output_format == "native":
        from .native_publication import publish_native_dataset

        native_publication = publish_native_dataset(
            paths,
            [*files, *native_attachments],
            paths.root / "combined" / f"{safe_id(dataset_id)}.lxhcc",
        )

    source_type_counts = Counter(
        str(row["source_profile"]["source_type"]) for row in source_receipts
    )
    source_capability_counts = Counter(
        capability
        for row in source_receipts
        for capability in row["source_profile"]["capabilities"]
    )
    receipt = {
        "schema": "truemem_intake_receipt@1",
        "intake_authority": "TrueVision.DocuFilm",
        "created_at": utc_now(),
        "dataset_id": safe_id(dataset_id),
        "scope": "dataset_local",
        "source": str(source_path),
        "source_file_count": len(files),
        "native_attachment_count": len(native_attachments),
        "native_attachments": [
            {"path": str(path), "bytes": path.stat().st_size, "sha256": _sha256_file(path)}
            for path in native_attachments
        ],
        "block_count": len(block_rows),
        "citation_count": len(block_rows),
        "chat_metadata_row_count": len(chat_metadata_rows),
        "unique_anchor_count": len(anchor_observations),
        "structural_symbol_count": len(structural_keys),
        "structural_graph": structural_manifest,
        "structural_graph_verification": structural_verification,
        "symbol_start": symbol_allocation["symbol_start"],
        "symbol_end": symbol_allocation["symbol_end"],
        "symbol_count": symbol_allocation["symbol_count"],
        "symbols_created": symbol_allocation["symbol_count"],
        "last_assigned_symbol_before": symbol_allocation["last_assigned_symbol_before"],
        "last_assigned_symbol_after": symbol_allocation["last_assigned_symbol_after"],
        "symbolizer_state_path": symbol_allocation["symbolizer_state_path"],
        "symbolizer_state_receipt": symbol_allocation["symbolizer_state_receipt"],
        "symbol_allocator_kind": symbol_allocation["allocator_kind"],
        "collision_count": 0,
        "anchor_observation_count": sum(anchor_observations.values()),
        "anchor_kind_observation_counts": dict(sorted(Counter(
            {kind: sum(count for anchor, count in anchor_observations.items() if anchor_kind(anchor) == kind)
             for kind in ("content", "relation", "glue", "boundary", "object")}
        ).items())),
        "complete_anchor_preservation": True,
        "glue_anchors_deleted": False,
        "punctuation_stored_as_structural_anchors": True,
        "hyphenated_words_remain_one_anchor": True,
        "relation_observation_count": sum(relation_observations.values()),
        "count_backend": COUNT_BACKEND,
        "persistent_memory": False,
        "promotion_allowed": False,
        "intake_engine": "docufilm_truemem_debug_tiny_block_intake@1" if debug_tiny_single_core else "docufilm_truemem_parallel_block_intake@1",
        "production_ingest": not debug_tiny_single_core,
        "debug_tiny_single_core": bool(debug_tiny_single_core),
        "workers_requested": str(workers),
        "workers_effective": effective_workers,
        "workers_actual": effective_workers,
        "parallel_execution": bool(resource_plan["parallel_execution"]),
        "parallel_execution_possible": bool(resource_plan["parallel_execution_possible"]),
        "resource_plan": resource_plan,
        "sources": source_receipts,
        "source_typing_authority": "TrueVision.DocuFilm",
        "source_typing_schema": "truevision_source_type@1",
        "source_type_counts": dict(sorted(source_type_counts.items())),
        "source_capability_counts": dict(sorted(source_capability_counts.items())),
        "paths": public_paths(paths),
        "requested_output_format": output_format,
        "runtime_authority_format": "split",
        "native_query_backend_active": False,
        "native_publication": native_publication,
    }
    receipt_path = paths.receipts / f"intake_{unique_stamp()}.json"
    write_json(receipt_path, receipt)
    receipt["receipt_path"] = str(receipt_path)
    return with_protected_notice(receipt)


def _process_intake_files(files: list[Path], *, window: int, workers: int, show_progress: bool) -> list[dict[str, Any]]:
    file_results: dict[int, dict[str, Any]] = {}
    jobs: list[tuple[int, str, str, int, int, dict[str, Any], dict[str, Any], dict[str, Any], int]] = []
    for file_order, path in enumerate(files):
        file_digest = sha1_text(str(path))
        text = path.read_text(encoding="utf-8", errors="replace")
        source_profile = _classify_truevision_source(path, text)
        blocks = split_record_blocks(text) if path.suffix.lower() in {".csv", ".jsonl"} else split_blocks(text)
        tabular_profile, tabular_rows = _parse_truevision_tabular_source(path, text)
        if path.suffix.lower() in {".csv", ".jsonl"}:
            if len(tabular_rows) != len(blocks):
                raise ValueError(f"TrueVision tabular row count mismatch: {path}")
            for block, tabular_row in zip(blocks, tabular_rows):
                block["tabular_row"] = tabular_row
        elif tabular_rows and blocks:
            blocks[0]["tabular_rows"] = tabular_rows
        file_results[file_order] = {
            "file_order": int(file_order),
            "source_receipt": {
                "path": str(path),
                "block_count": len(blocks),
                "source_profile": source_profile,
                "tabular_profile": tabular_profile,
            },
            "blocks": [],
            "anchor_observations": Counter(),
            "relation_observations": Counter(),
            "block_anchor_rows": [],
            "structural_compilations": [],
        }
        active_chat_metadata: dict[str, Any] = {}
        for block_index, block in enumerate(blocks, start=1):
            parsed_metadata = parse_chat_metadata_block(block["text"])
            if parsed_metadata:
                active_chat_metadata = parsed_metadata
            jobs.append((
                file_order,
                str(path),
                file_digest,
                block_index,
                block_index - 1,
                block,
                dict(active_chat_metadata),
                source_profile,
                window,
            ))

    if not jobs:
        return [file_results[index] for index in sorted(file_results)]

    block_results: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        future_map = {pool.submit(_process_intake_block, *job): job[0] for job in jobs}
        for future in _progress_iter(as_completed(future_map), total=len(future_map), enabled=show_progress):
            block_results.append(future.result())

    for block_result in sorted(block_results, key=lambda item: (int(item["file_order"]), int(item["local_block_ordinal"]))):
        file_result = file_results[int(block_result["file_order"])]
        file_result["blocks"].append(block_result["block"])
        file_result["anchor_observations"].update(block_result["anchor_observations"])
        file_result["relation_observations"].update(block_result["relation_observations"])
        file_result["block_anchor_rows"].extend(block_result["block_anchor_rows"])
        file_result["structural_compilations"].append(block_result["structural_compilation"])
    return [file_results[index] for index in sorted(file_results)]


def _process_intake_block(
    file_order: int,
    file_path: str,
    file_digest: str,
    block_index: int,
    local_block_ordinal: int,
    block: dict[str, Any],
    active_chat_metadata: dict[str, Any],
    source_profile: dict[str, Any],
    window: int,
) -> dict[str, Any]:
    anchor_observations: Counter[str] = Counter()
    relation_observations: Counter[tuple[str, str, int]] = Counter()
    block_anchor_rows: list[tuple[str, int, int]] = []
    block_id = f"{file_digest}:{block_index}"
    anchors = anchorize(block["text"])
    structural_compilation = _compile_truevision_structures(
        block["text"], source_identity=block_id, block_ordinal=local_block_ordinal,
        source_profile=source_profile,
        tabular=bool("tabular_row" in block or "tabular_rows" in block),
    )
    citation_id = f"TMCIT-{sha1_text(block_id)[:10]}"
    block_row = {
        "local_block_ordinal": int(local_block_ordinal),
        "block_id": block_id,
        "file_path": str(file_path),
        "line_start": block["line_start"],
        "line_end": block["line_end"],
        "text": block["text"],
        "citation_id": citation_id,
        "marker": f"[{citation_id}]",
        "text_hash": sha1_text(block["text"]),
        "sentences": numbered_sentences(block["text"]),
        "source_profile": source_profile,
    }
    if active_chat_metadata:
        block_row["chat_metadata"] = dict(active_chat_metadata)
    if "tabular_row" in block:
        block_row["tabular_row"] = block["tabular_row"]
    if "tabular_rows" in block:
        block_row["tabular_rows"] = block["tabular_rows"]
    for position, anchor in enumerate(anchors):
        anchor_observations[anchor] += 1
        block_anchor_rows.append((anchor, local_block_ordinal, position))
        for offset in range(-window, window + 1):
            if offset == 0:
                continue
            neighbor_index = position + offset
            if 0 <= neighbor_index < len(anchors):
                relation_observations[(anchor, anchors[neighbor_index], offset)] += 1
    return {
        "file_order": int(file_order),
        "local_block_ordinal": int(local_block_ordinal),
        "block": block_row,
        "anchor_observations": anchor_observations,
        "relation_observations": relation_observations,
        "block_anchor_rows": block_anchor_rows,
        "structural_compilation": structural_compilation,
    }


def _classify_truevision_source(path: Path, text: str) -> dict[str, Any]:
    """Delegate source typing to the TrueVision intake authority."""
    try:
        from truevision_intake.source_typing import classify_source
    except ModuleNotFoundError:
        intake_root = Path(__file__).resolve().parents[4] / "TrueVisionIntake"
        if not intake_root.is_dir():
            raise RuntimeError("TRUEVISION_SOURCE_TYPING_UNAVAILABLE")
        sys.path.insert(0, str(intake_root))
        from truevision_intake.source_typing import classify_source
    return classify_source(path, text)


def _parse_truevision_tabular_source(path: Path, text: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Delegate sparse-grid parsing to the TrueVision intake authority."""
    try:
        from truevision_intake.tabular_intake import parse_tabular_source
    except ModuleNotFoundError:
        intake_root = Path(__file__).resolve().parents[4] / "TrueVisionIntake"
        if not intake_root.is_dir():
            raise RuntimeError("TRUEVISION_TABULAR_INTAKE_UNAVAILABLE")
        sys.path.insert(0, str(intake_root))
        from truevision_intake.tabular_intake import parse_tabular_source
    return parse_tabular_source(path, text)


def _compile_truevision_structures(
    text: str,
    *,
    source_identity: str,
    block_ordinal: int,
    source_profile: dict[str, Any],
    tabular: bool,
) -> dict[str, Any]:
    """Delegate structural compilation to the sole TrueVision intake owner."""
    try:
        from truevision_intake.typed_structural import compile_typed_structures
    except ModuleNotFoundError:
        intake_root = Path(__file__).resolve().parents[4] / "TrueVisionIntake"
        if not intake_root.is_dir():
            raise RuntimeError("TRUEVISION_STRUCTURAL_COMPILER_UNAVAILABLE")
        sys.path.insert(0, str(intake_root))
        from truevision_intake.typed_structural import compile_typed_structures
    return compile_typed_structures(
        text,
        source_identity=source_identity,
        block_ordinal=block_ordinal,
        source_profile=source_profile,
        tabular=tabular,
    )

def iter_files(path: Path) -> Iterable[Path]:
    suffixes = DOCUMENT_SUFFIXES | TEXT_SOURCE_SUFFIXES
    if path.is_file() and path.suffix.lower() in suffixes:
        yield path
        return
    if path.is_dir():
        for item in sorted(path.rglob("*")):
            relative = item.relative_to(path)
            hidden_directory = any(part.startswith(".") for part in relative.parts[:-1])
            if item.is_file() and item.suffix.lower() in suffixes and not hidden_directory:
                yield item


def _refuse_adapter_workspace_root(source_path: Path) -> None:
    manifest_path = source_path / "STAGING_MANIFEST.json"
    if not source_path.is_dir() or not manifest_path.exists():
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(manifest, dict):
        return
    ingest_source = manifest.get("ingest_source_dir")
    if not ingest_source:
        return
    ingest_path = Path(str(ingest_source)).expanduser().resolve()
    if source_path == ingest_path:
        return
    raise RuntimeError(
        "ADAPTER_WORKSPACE_NOT_INGEST_SOURCE: "
        f"source={source_path}; use ingest_source_dir={ingest_path}"
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _native_attachment_files(source_path: Path) -> list[Path]:
    if not source_path.is_dir():
        return []
    manifest_path = source_path / "STAGING_MANIFEST.json"
    if not manifest_path.is_file():
        return []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    declared = manifest.get("native_attachment_paths") or []
    if not isinstance(declared, list):
        raise ValueError("native_attachment_paths must be a list")
    files = []
    for value in declared:
        target = (source_path / str(value)).resolve()
        try:
            target.relative_to(source_path)
        except ValueError as error:
            raise ValueError("native attachment escapes intake source") from error
        candidates = [target] if target.is_file() else sorted(item for item in target.rglob("*") if item.is_file())
        if not candidates:
            raise FileNotFoundError(f"native attachment path is empty or missing: {target}")
        files.extend(candidates)
    return sorted(set(files), key=str)

def split_blocks(text: str) -> list[dict[str, Any]]:
    lines = text.splitlines()
    blocks: list[dict[str, Any]] = []
    current: list[str] = []
    start = 1
    for index, line in enumerate(lines, start=1):
        if line.strip():
            if not current:
                start = index
            current.append(line)
            continue
        if current:
            blocks.extend(chunk_block(current, start))
            current = []
    if current:
        blocks.extend(chunk_block(current, start))
    if not blocks and text:
        blocks.append({"line_start": 1, "line_end": max(1, len(lines)), "text": text})
    return blocks


def split_record_blocks(text: str) -> list[dict[str, Any]]:
    """Keep one serialized table record inside one cited evidence block."""
    return [
        {"line_start": index, "line_end": index, "text": line}
        for index, line in enumerate(text.splitlines(), start=1)
        if line.strip()
    ]

def chunk_block(lines: list[str], start_line: int) -> list[dict[str, Any]]:
    # One nonblank paragraph is one authoritative block. Length never splits it.
    return [{
        "line_start": start_line,
        "line_end": start_line + len(lines) - 1,
        "text": "\n".join(lines),
    }]


def numbered_sentences(text: str) -> list[dict[str, Any]]:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])(?:\s+|$)", text) if part.strip()]
    if not parts and text.strip():
        parts = [text.strip()]
    return [
        {
            "sentence_ordinal": ordinal,
            "text": sentence,
            "text_hash": sha1_text(sentence),
            "anchors": anchorize(sentence),
        }
        for ordinal, sentence in enumerate(parts, start=1)
    ]


def _build_intake_resource_plan(
    *,
    files: list[Path],
    requested_workers: int | str,
    reserve_ram_fraction: float,
    ram_budget_gb: float | None,
    debug_tiny_single_core: bool = False,
) -> dict[str, Any]:
    if not 0 <= reserve_ram_fraction < 1:
        raise ValueError("reserve_ram_fraction must be between 0 and 1")
    if ram_budget_gb is not None and ram_budget_gb <= 0:
        raise ValueError("ram_budget_gb must be positive")

    resources = _detect_system_resources()
    gpu_requirement_enforced = False
    if not debug_tiny_single_core:
        enforce_minimum_runtime_requirements(resources, require_gpu=gpu_requirement_enforced)
    cpu_count = max(1, int(resources.get("logical_cpu_count") or 1))
    requested_label = str(requested_workers)
    if isinstance(requested_workers, str):
        requested_text = requested_workers.lower()
        if requested_text == "auto":
            requested_count = 1 if debug_tiny_single_core else max(MIN_RUNTIME_WORKERS, cpu_count)
            auto_workers = True
        else:
            requested_count = int(requested_workers)
            auto_workers = False
    else:
        requested_count = int(requested_workers)
        auto_workers = False
    if requested_count <= 0:
        raise ValueError("workers must be positive or auto")
    if requested_count < MIN_RUNTIME_WORKERS and not debug_tiny_single_core:
        raise ValueError(f"DocuFilm intake requires at least {MIN_RUNTIME_WORKERS} workers; single-core/low-core execution is not allowed")
    if requested_count > cpu_count:
        raise RuntimeError(f"requested workers={requested_count} exceeds logical cpu count={cpu_count}")

    total_ram = resources.get("total_ram_bytes")
    available_ram = resources.get("available_ram_bytes")
    reserve_ram_bytes = int(total_ram * reserve_ram_fraction) if isinstance(total_ram, int) else 0
    available_after_reserve = max(0, int(available_ram) - reserve_ram_bytes) if isinstance(available_ram, int) else None
    requested_budget_bytes = int(ram_budget_gb * 1024 * 1024 * 1024) if ram_budget_gb is not None else None
    allocatable_bytes = available_after_reserve
    if allocatable_bytes is not None and requested_budget_bytes is not None:
        allocatable_bytes = min(allocatable_bytes, requested_budget_bytes)
    elif allocatable_bytes is None and requested_budget_bytes is not None:
        allocatable_bytes = requested_budget_bytes

    largest_file_bytes = max((path.stat().st_size for path in files), default=0)
    estimated_worker_bytes = max(
        256 * 1024 * 1024,
        min(2 * 1024 * 1024 * 1024, largest_file_bytes * 3 + 128 * 1024 * 1024),
    )
    ram_worker_cap = None
    if allocatable_bytes is not None:
        ram_worker_cap = max(1, int(allocatable_bytes // estimated_worker_bytes))

    caps = [requested_count, cpu_count]
    if ram_worker_cap is not None:
        caps.append(ram_worker_cap)
    effective_workers = max(1, min(caps))
    if effective_workers < MIN_RUNTIME_WORKERS and not debug_tiny_single_core:
        raise RuntimeError(
            "DocuFilm intake cannot honor the operator compute rule with current CPU/RAM limits; "
            "single-core/low-core execution is not allowed"
        )
    if not auto_workers and effective_workers != requested_count:
        raise RuntimeError(
            f"requested workers={requested_count} cannot be honored under current CPU/RAM limits; "
            f"effective workers would be {effective_workers}"
        )

    safety_decisions: list[str] = []
    if auto_workers:
        safety_decisions.append("debug_tiny_auto_selected_single_worker" if debug_tiny_single_core else "workers_auto_selected_from_system_resources")
    if ram_worker_cap is not None and ram_worker_cap < requested_count:
        safety_decisions.append("worker_count_limited_by_ram_budget")
    if reserve_ram_bytes > 0:
        safety_decisions.append("ram_reserved_for_system_and_operator")
    if debug_tiny_single_core:
        safety_decisions.append("debug_tiny_single_core_nonproduction")

    return {
        "schema": "truemem_intake_resource_plan@1",
        "created_at": utc_now(),
        "preflight_name": "TrueMem RESOURCE PREFLIGHT",
        "resources": resources,
        "source_file_count": len(files),
        "work_unit_count": None,
        "requested_workers": requested_label,
        "effective_workers": int(effective_workers),
        "workers_actual": int(effective_workers),
        "cpu_worker_cap": int(cpu_count),
        "ram_worker_cap": int(ram_worker_cap) if ram_worker_cap is not None else None,
        "reserve_ram_fraction": float(reserve_ram_fraction),
        "reserve_ram_bytes": int(reserve_ram_bytes),
        "ram_budget_gb": float(ram_budget_gb) if ram_budget_gb is not None else None,
        "ram_budget_bytes": int(requested_budget_bytes) if requested_budget_bytes is not None else None,
        "allocatable_ram_bytes_after_reserve": int(allocatable_bytes) if allocatable_bytes is not None else None,
        "largest_file_bytes": int(largest_file_bytes),
        "estimated_worker_bytes": int(estimated_worker_bytes),
        "parallel_execution": effective_workers > 1,
        "parallel_execution_possible": None,
        "production_parallel_supported": not debug_tiny_single_core,
        "production_ingest": not debug_tiny_single_core,
        "debug_tiny_single_core": bool(debug_tiny_single_core),
        "minimum_runtime_requirements_enforced": not debug_tiny_single_core,
        "gpu_requirement_enforced": gpu_requirement_enforced,
        "minimum_runtime_requirements": {
            "min_workers": MIN_RUNTIME_WORKERS,
            "min_system_ram_gib": 8,
            "min_gpu_ram_gib": 8,
        },
        "gpu_lane_active": False,
        "gpu_usage": "unused_by_intake",
        "single_core_allowed": bool(debug_tiny_single_core),
        "safety_decisions": safety_decisions,
    }


def _detect_system_resources() -> dict[str, Any]:
    return detect_system_resources()


def _progress_iter(iterable: Iterable[Any], *, total: int, enabled: bool) -> Iterable[Any]:
    if not enabled:
        return iterable
    try:
        from tqdm import tqdm
    except Exception:  # pragma: no cover - fallback only when tqdm is unavailable
        return iterable
    return tqdm(iterable, total=total, desc="DocuFilm intake", unit="file")
