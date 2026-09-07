"""Prepare tensor-ready visual code literacy examples from verified source bytes."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont


SCHEMA = "truesystems_code_glyph_curriculum@1"
SPLITS = {"train": 0, "validation": 1, "test": 2}
GRAMMAR_LABELS = {
    "LANGUAGE_ADAPTER_NOT_IMPLEMENTED_EXACT_BYTES_RETAINED": 0,
    "PYTHON_AST_PARSED": 1,
    "PYTHON_SYNTAX_ERROR": 2,
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _split(digest: str) -> str:
    bucket = int(digest[:8], 16) % 20
    return "train" if bucket < 16 else "validation" if bucket < 18 else "test"


def _strings(values: list[str]) -> tuple[np.ndarray, np.ndarray]:
    encoded = [value.encode("utf-8") for value in values]
    offsets = np.zeros(len(encoded) + 1, dtype=np.uint64)
    for index, value in enumerate(encoded):
        offsets[index + 1] = offsets[index] + len(value)
    payload = np.frombuffer(b"".join(encoded), dtype=np.uint8).copy()
    return payload, offsets


def _artifact(path: Path) -> dict[str, Any]:
    return {"path": path.name, "bytes": path.stat().st_size, "sha256": _sha256(path)}


def _glyph_atlas(codepoints: list[int], font_path: Path, output: Path) -> dict[str, Any]:
    images = []
    targets = []
    font_sizes = []
    x_offsets = []
    y_offsets = []
    for size in (16, 20, 24):
        font = ImageFont.truetype(str(font_path), size=size)
        for y_offset in (1, 2):
            for x_offset in (1, 2):
                for codepoint in codepoints:
                    value = chr(codepoint)
                    if not value.isprintable() or value.isspace():
                        continue
                    image = Image.new("L", (40, 40), 0)
                    ImageDraw.Draw(image).text((x_offset, y_offset), value, font=font, fill=255)
                    images.append(np.asarray(image, dtype=np.uint8))
                    targets.append(codepoint)
                    font_sizes.append(size)
                    x_offsets.append(x_offset)
                    y_offsets.append(y_offset)
    tensor = np.stack(images) if images else np.zeros((0, 40, 40), dtype=np.uint8)
    pattern_groups: dict[str, set[int]] = defaultdict(set)
    for image, target in zip(tensor, targets):
        pattern_groups[hashlib.sha256(image.tobytes()).hexdigest()].add(target)
    ambiguous = {target for members in pattern_groups.values() if len(members) > 1 for target in members}
    np.savez_compressed(
        output,
        glyph_images=tensor,
        target_codepoint=np.asarray(targets, dtype=np.uint32),
        font_size=np.asarray(font_sizes, dtype=np.uint16),
        x_offset=np.asarray(x_offsets, dtype=np.uint8),
        y_offset=np.asarray(y_offsets, dtype=np.uint8),
        classification_eligible=np.asarray([target not in ambiguous for target in targets], dtype=np.bool_),
    )
    return {
        "sample_count": len(targets),
        "codepoint_count": len(set(targets)),
        "ambiguous_codepoint_count": len(ambiguous),
        "font_path": str(font_path),
        "font_sha256": _sha256(font_path),
        "cell_shape": [40, 40],
        "font_sizes": [16, 20, 24],
        "subpixel_integer_offsets": [[1, 1], [1, 2], [2, 1], [2, 2]],
    }


def build_code_glyph_curriculum(
    *,
    source_root: Path,
    catalog_csv: Path,
    font_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    """Build one deterministic, duplicate-isolated curriculum; perform no training."""

    source_root = source_root.resolve()
    catalog_csv = catalog_csv.resolve()
    font_path = font_path.resolve()
    output_root = output_root.resolve()
    if output_root.exists():
        raise FileExistsError(output_root)
    output_root.mkdir(parents=True)

    with catalog_csv.open(encoding="utf-8", newline="") as handle:
        catalog = list(csv.DictReader(handle))
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in catalog:
        grouped[(row["source_sha256"], row["language"])].append(row)

    languages = sorted({language for _digest, language in grouped})
    language_ids = {value: index for index, value in enumerate(languages)}
    source_payloads: list[bytes] = []
    source_hashes = []
    source_language = []
    source_split = []
    source_grammar = []
    source_occurrences = []
    source_terminal_newline = []
    path_values = []
    path_source = []
    line_source = []
    line_number = []
    line_byte_start = []
    line_byte_length = []
    line_ending = []
    line_anchor_start = [0]
    line_anchor_ids = []
    anchor_ids: dict[str, int] = {}
    anchor_values: list[str] = []
    codepoint_counts = {name: Counter() for name in SPLITS}
    exclusions = []

    from truemem.engine.anchors import anchorize

    for (expected_hash, language), rows in sorted(grouped.items()):
        paths = sorted(row["source_relative_path"] for row in rows)
        source = source_root / paths[0]
        raw = source.read_bytes()
        actual_hash = hashlib.sha256(raw).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError(f"source hash mismatch: {source}")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            exclusions.append({"source_sha256": expected_hash, "language": language, "reason": "invalid_utf8", "paths": paths})
            continue
        source_index = len(source_payloads)
        split = _split(expected_hash)
        statuses = sorted({row["parse_status"] for row in rows})
        grammar_label = GRAMMAR_LABELS.get(statuses[0], 0) if len(statuses) == 1 else 0
        source_payloads.append(raw)
        source_hashes.append(bytes.fromhex(expected_hash))
        source_language.append(language_ids[language])
        source_split.append(SPLITS[split])
        source_grammar.append(grammar_label)
        source_occurrences.append(len(rows))
        source_terminal_newline.append(raw.endswith((b"\n", b"\r")))
        for value in paths:
            path_values.append(value)
            path_source.append(source_index)
        absolute = 0
        for number, raw_line in enumerate(raw.splitlines(keepends=True), start=1):
            if raw_line.endswith(b"\r\n"):
                content, ending = raw_line[:-2], 2
            elif raw_line.endswith(b"\n") or raw_line.endswith(b"\r"):
                content, ending = raw_line[:-1], 1
            else:
                content, ending = raw_line, 0
            value = content.decode("utf-8")
            line_source.append(source_index)
            line_number.append(number)
            line_byte_start.append(absolute)
            line_byte_length.append(len(content))
            line_ending.append(ending)
            for anchor in anchorize(value):
                if anchor not in anchor_ids:
                    anchor_ids[anchor] = len(anchor_values)
                    anchor_values.append(anchor)
                line_anchor_ids.append(anchor_ids[anchor])
            line_anchor_start.append(len(line_anchor_ids))
            absolute += len(raw_line)
        codepoint_counts[split].update(map(ord, text))

    source_bytes = b"".join(source_payloads)
    source_offsets = np.zeros(len(source_payloads) + 1, dtype=np.uint64)
    for index, value in enumerate(source_payloads):
        source_offsets[index + 1] = source_offsets[index] + len(value)
    language_blob, language_offsets = _strings(languages)
    path_blob, path_offsets = _strings(path_values)
    anchor_blob, anchor_offsets = _strings(anchor_values)
    curriculum_path = output_root / "code-curriculum.npz"
    np.savez_compressed(
        curriculum_path,
        source_utf8=np.frombuffer(source_bytes, dtype=np.uint8).copy(),
        source_offsets=source_offsets,
        source_sha256=np.frombuffer(b"".join(source_hashes), dtype=np.uint8).reshape((-1, 32)),
        source_language_id=np.asarray(source_language, dtype=np.uint16),
        source_split=np.asarray(source_split, dtype=np.uint8),
        source_grammar_label=np.asarray(source_grammar, dtype=np.uint8),
        source_duplicate_multiplicity=np.asarray(source_occurrences, dtype=np.uint32),
        source_terminal_newline=np.asarray(source_terminal_newline, dtype=np.bool_),
        language_utf8=language_blob,
        language_offsets=language_offsets,
        path_utf8=path_blob,
        path_offsets=path_offsets,
        path_source_index=np.asarray(path_source, dtype=np.uint32),
        line_source_index=np.asarray(line_source, dtype=np.uint32),
        line_number=np.asarray(line_number, dtype=np.uint32),
        line_byte_start=np.asarray(line_byte_start, dtype=np.uint64),
        line_byte_length=np.asarray(line_byte_length, dtype=np.uint32),
        line_ending=np.asarray(line_ending, dtype=np.uint8),
        line_anchor_start=np.asarray(line_anchor_start, dtype=np.uint64),
        line_anchor_id=np.asarray(line_anchor_ids, dtype=np.uint32),
        anchor_utf8=anchor_blob,
        anchor_offsets=anchor_offsets,
    )

    codepoints = sorted(set().union(*(set(counts) for counts in codepoint_counts.values())))
    glyph_path = output_root / "glyph-atlas.npz"
    glyph_summary = _glyph_atlas(codepoints, font_path, glyph_path)
    counts_path = output_root / "codepoint-counts.npz"
    np.savez_compressed(
        counts_path,
        codepoint=np.asarray(codepoints, dtype=np.uint32),
        train_count=np.asarray([codepoint_counts["train"][value] for value in codepoints], dtype=np.uint64),
        validation_count=np.asarray([codepoint_counts["validation"][value] for value in codepoints], dtype=np.uint64),
        test_count=np.asarray([codepoint_counts["test"][value] for value in codepoints], dtype=np.uint64),
    )
    from .function_method_curriculum import build_function_method_curriculum

    function_path = output_root / "function-method-curriculum.npz"
    function_summary = build_function_method_curriculum(
        source_root=source_root,
        catalog_csv=catalog_csv,
        output_path=function_path,
    )
    split_counts = {
        name: sum(1 for value in source_split if value == split_id)
        for name, split_id in SPLITS.items()
    }
    manifest = {
        "schema": SCHEMA,
        "classification": "PREPARED_TENSOR_CURRICULUM_NOT_TRAINED",
        "source_root": str(source_root),
        "catalog_csv": str(catalog_csv),
        "catalog_sha256": _sha256(catalog_csv),
        "catalog_path_count": len(catalog),
        "admitted_source_group_count": len(source_payloads),
        "excluded_group_count": len(exclusions),
        "line_example_count": len(line_source),
        "anchor_vocabulary_count": len(anchor_values),
        "anchor_observation_count": len(line_anchor_ids),
        "codepoint_count": len(codepoints),
        "languages": languages,
        "array_codebooks": {
            "source_language_id": {str(index): value for value, index in language_ids.items()},
            "source_split": {str(value): name for name, value in SPLITS.items()},
            "source_grammar_label": {
                "0": "grammar_unavailable",
                "1": "python_ast_parsed",
                "2": "python_syntax_rejected",
            },
            "line_ending": {
                "0": "none",
                "1": "single_byte_lf_or_cr",
                "2": "crlf",
            },
        },
        "split_counts": split_counts,
        "split_law": "source_sha256_first_32_bits_modulo_20: 0-15 train, 16-17 validation, 18-19 test",
        "duplicate_law": "exact source SHA families never cross splits; multiplicity is provenance, not training weight",
        "label_law": {
            "visual": "exact UTF-8 source characters and line coordinates",
            "anchors": "complete TrueMem anchorize output; no deletion or normalization",
            "python_positive": "PYTHON_AST_PARSED",
            "python_rejection": "PYTHON_SYNTAX_ERROR means parser rejection only",
            "other_languages": "glyph and lexical supervision only until a real grammar adapter exists",
        },
        "glyph_atlas": glyph_summary,
        "function_method_curriculum": function_summary,
        "cloud_preparation": {
            "schema": "truesystems_code_cloud_preparation@1",
            "source_arrays": ["line_anchor_start", "line_anchor_id", "source_grammar_label", "source_split"],
            "cloud_law": "each anchor occurrence is the center of its available signed -6..-1,+1..+6 neighbors within the same line",
            "training_counts_only": True,
            "accepted_label": "python_ast_parsed",
            "rejected_label": "python_syntax_rejected",
            "score_callable": "truecore.training.code_cloud_scoring.score_code_cloud_lane",
            "score_name": "parser_acceptance_association_not_behavioral_correctness",
            "weights": {
                "content": 1.0, "relation": 0.5, "object": 0.65, "glue": 0.0, "boundary": 0.0,
                "distance_proximity": "(7 - abs(signed_offset)) / 6",
                "sample_confidence": "1 - exp(-(accepted_edge + rejected_edge) / 8)",
                "beta_prior": 1.0
            },
            "validation_and_test_labels_opened_for_weight_fitting": False,
            "cloud_weights_computed": False
        },
        "exclusions": exclusions,
        "artifacts": {
            "curriculum": _artifact(curriculum_path),
            "glyph_atlas": _artifact(glyph_path),
            "codepoint_counts": _artifact(counts_path),
            "function_method_curriculum": _artifact(function_path),
        },
        "model_training_performed": False,
        "optimizer_updates": 0,
        "checkpoint_created": False,
        "authority_created": False,
    }
    manifest["release_id"] = hashlib.sha256(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    (output_root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
