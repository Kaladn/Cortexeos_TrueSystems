"""Prepare a source-backed BEIR HotpotQA retrieval benchmark.

This module does not train a model.  It freezes a deterministic corpus slice,
materializes DocuFilm source shards, and builds the exact source package used by
the unchanged historical provisional-chat preparation method.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "truesystems_hotpotqa_rag_benchmark@1"
CORPUS_REVISION = "a7e8bab212f5a89f9be1bc9b654aa6dfa317f32b"
QRELS_REVISION = "b15429e9244c8ec966985d7778427c3b1543b314"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def file_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def _qrels(path: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            if int(row["score"]) > 0:
                result[row["query-id"]].append(row["corpus-id"])
    return {key: sorted(set(values), key=lambda value: (len(value), value)) for key, values in result.items()}


def _stable_rank(value: str) -> tuple[str, str]:
    return digest(("hotpotqa-rag-corpus-v1\0" + value).encode("utf-8")), value


def _iter_parquet(path: Path, columns: list[str]) -> Iterable[dict[str, Any]]:
    try:
        import pyarrow.parquet as parquet
    except ImportError as error:
        raise RuntimeError("pyarrow is required; run this builder with `uv run --with pyarrow`") from error
    source = parquet.ParquetFile(path)
    for batch in source.iter_batches(batch_size=8192, columns=columns):
        yield from batch.to_pylist()


def build_benchmark_source(
    frozen_root: Path,
    output: Path,
    *,
    corpus_size: int = 100_000,
    shard_size: int = 250,
    train_session_limit: int = 2_000,
    validation_session_limit: int = 250,
    sealed_test_session_limit: int = 250,
) -> dict[str, Any]:
    """Create exact source shards and a leakage-bounded historical source package."""
    if output.exists():
        raise FileExistsError(output)
    corpus_file = frozen_root / "corpus/corpus/corpus-00000-of-00001.parquet"
    query_file = frozen_root / "corpus/queries/queries-00000-of-00001.parquet"
    qrels_root = frozen_root / "qrels"
    required = [corpus_file, query_file, *(qrels_root / f"{name}.tsv" for name in ("train", "dev", "test"))]
    if not all(path.is_file() for path in required):
        raise FileNotFoundError("frozen BEIR HotpotQA inputs are incomplete")
    corpus_file_sha256 = file_digest(corpus_file)

    qrels = {name: _qrels(qrels_root / f"{name}.tsv") for name in ("train", "dev", "test")}
    qrel_limits = {"train": train_session_limit, "dev": validation_session_limit, "test": sealed_test_session_limit}
    reserved_queries: dict[str, list[tuple[str, list[str]]]] = {}
    for name in ("train", "dev", "test"):
        ranked = sorted(qrels[name].items(), key=lambda item: (digest((name + "\0" + item[0]).encode()), item[0]))
        reserved_queries[name] = ranked[: qrel_limits[name]]
    all_test_targets = {doc for values in qrels["test"].values() for doc in values}
    required_targets = all_test_targets | {
        doc for values in reserved_queries.values() for _, targets in values for doc in targets
    }
    if len(required_targets) > corpus_size:
        raise ValueError("corpus_size is smaller than the test authority set")

    # Select every sealed-test target first, then deterministic distractors.
    distractor_budget = corpus_size - len(required_targets)
    distractors: list[tuple[tuple[str, str], str]] = []
    for row in _iter_parquet(corpus_file, ["_id"]):
        identity = str(row["_id"])
        if identity not in required_targets:
            distractors.append((_stable_rank(identity), identity))
    distractors.sort(key=lambda item: item[0])
    selected = required_targets | {identity for _, identity in distractors[:distractor_budget]}
    del distractors

    output.mkdir(parents=True)
    shards = output / "docufilm-source-shards"
    shards.mkdir()
    passage_rows: list[dict[str, Any]] = []
    selected_payload: dict[str, tuple[str, str]] = {}
    handles: dict[int, Any] = {}
    try:
        ordinal = 0
        for row in _iter_parquet(corpus_file, ["_id", "title", "text"]):
            identity = str(row["_id"])
            if identity not in selected:
                continue
            title, text = str(row["title"] or ""), str(row["text"] or "")
            selected_payload[identity] = (title, text)
            shard_index = ordinal // shard_size
            handle = handles.get(shard_index)
            if handle is None:
                handle = (shards / f"passages-{shard_index:06d}.txt").open("w", encoding="utf-8", newline="\n")
                handles[shard_index] = handle
            block = title + "\n" + text
            if ordinal % shard_size:
                handle.write("\n\n")
            line_start = (ordinal % shard_size) * 3 + 1
            handle.write(block)
            passage_rows.append({
                "corpus_id": identity,
                "corpus_revision": CORPUS_REVISION,
                "parquet_sha256": corpus_file_sha256,
                "row_payload_sha256": digest(canonical({"_id": identity, "title": title, "text": text})),
                "docufilm_shard": f"passages-{shard_index:06d}.txt",
                "block_ordinal_in_shard": ordinal % shard_size,
                "line_start": line_start,
                "line_end": line_start + 1,
                "title_sha256": digest(title.encode("utf-8")),
                "text_sha256": digest(text.encode("utf-8")),
                "test_relevant": identity in all_test_targets,
            })
            ordinal += 1
    finally:
        for handle in handles.values():
            handle.close()
    if len(passage_rows) != corpus_size:
        raise RuntimeError(f"selected passage count mismatch: {len(passage_rows)} != {corpus_size}")

    query_payload = {str(row["_id"]): str(row["text"] or "") for row in _iter_parquet(query_file, ["_id", "text"])}
    source_package = output / "historical-source-package"
    source_package.mkdir()
    split_sources = {"train": "train", "validation": "dev", "test": "test"}
    package_hashes: dict[str, str] = {}
    split_manifest: list[dict[str, Any]] = []
    for split in ("train", "validation", "test"):
        qrel_name = split_sources[split]
        candidates = []
        for query_id, targets in reserved_queries[qrel_name]:
            if query_id not in query_payload or not all(target in selected_payload for target in targets):
                continue
            candidates.append((digest((qrel_name + "\0" + query_id).encode()), query_id, targets))
        candidates.sort()
        payload = bytearray()
        for _, query_id, targets in candidates:
            parts = [query_payload[query_id]]
            for target in targets:
                title, text = selected_payload[target]
                parts.append(title + "\n" + text)
            content = "\n\n".join(parts)
            session_id = digest(canonical({"split": split, "query_id": query_id, "targets": targets}))
            payload.extend(canonical({"session_id": session_id, "messages": [{"role": "user", "content": content}]}))
            split_manifest.append({
                "split": split,
                "session_id": session_id,
                "query_id": query_id,
                "target_corpus_ids": targets,
                "query_sha256": digest(query_payload[query_id].encode()),
                "content_sha256": digest(content.encode()),
                "authority": "EXTERNAL_NOT_LOCAL_TRUTH",
            })
        name = f"{split}.jsonl"
        (source_package / name).write_bytes(bytes(payload))
        package_hashes[name] = digest(bytes(payload))
    (source_package / "sha256_manifest.json").write_bytes(canonical(package_hashes))
    (output / "passage-provenance.jsonl").write_bytes(b"".join(canonical(row) for row in sorted(passage_rows, key=lambda row: int(row["corpus_id"]))))
    (output / "source-split-manifest.jsonl").write_bytes(b"".join(canonical(row) for row in sorted(split_manifest, key=lambda row: (row["split"], row["query_id"]))))

    artifacts = {}
    for path in sorted(output.rglob("*")):
        if path.is_file():
            artifacts[str(path.relative_to(output))] = {"sha256": file_digest(path), "size_bytes": path.stat().st_size}
    manifest = {
        "schema": SCHEMA,
        "classification": "EXTERNAL_NOT_LOCAL_TRUTH_PREPARED_NOT_TRAINED",
        "source": {
            "corpus_repository": "BeIR/hotpotqa",
            "corpus_revision": CORPUS_REVISION,
            "qrels_repository": "BeIR/hotpotqa-qrels",
            "qrels_revision": QRELS_REVISION,
            "license": "CC-BY-SA-4.0",
        },
        "selection": {
            "available_corpus_rows": 5_233_329,
            "selected_passages": corpus_size,
            "law": "all positive test-qrel targets, all targets for the fixed train/validation/test session reservations, then lowest deterministic SHA-256 ranked non-target distractors",
            "test_target_count": len(all_test_targets),
            "required_target_count": len(required_targets),
        },
        "sessions": {split: sum(row["split"] == split for row in split_manifest) for split in ("train", "validation", "test")},
        "sealed_test_payload_created_not_opened_by_training": True,
        "docufilm_source_shards": len(handles),
        "artifact_hashes": artifacts,
        "source_text_normalization": "none",
        "model_training_performed": False,
        "optimizer_updates": 0,
        "local_authority_created": False,
    }
    manifest["release_id"] = digest(canonical(manifest))
    (output / "manifest.json").write_bytes(canonical(manifest))
    return manifest
