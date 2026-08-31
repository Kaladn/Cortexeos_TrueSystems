"""Query-only HotpotQA retrieval and citation-handoff evaluation."""
from __future__ import annotations

import hashlib
import json
import math
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


BLOCK_ANCHOR_RECORD = struct.Struct(">6sIH")
RELATION_RECORD = struct.Struct(">6s6shI")


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode() + b"\n"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _query_texts(query_parquet: Path, wanted: set[str]) -> dict[str, str]:
    try:
        import pyarrow.parquet as parquet
    except ImportError as error:
        raise RuntimeError("pyarrow is required; run with `uv run --with pyarrow`") from error
    result: dict[str, str] = {}
    source = parquet.ParquetFile(query_parquet)
    for batch in source.iter_batches(batch_size=8192, columns=["_id", "text"]):
        for row in batch.to_pylist():
            identity = str(row["_id"])
            if identity in wanted:
                result[identity] = str(row["text"] or "")
    if set(result) != wanted:
        raise RuntimeError(f"missing query rows: {len(wanted - set(result))}")
    return result


def _load_authority(test_manifest: Path, query_parquet: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in test_manifest.read_text().splitlines() if line.strip()]
    rows = sorted((row for row in rows if row["split"] == "test"), key=lambda row: row["query_id"])
    questions = _query_texts(query_parquet, {row["query_id"] for row in rows})
    for row in rows:
        row["question"] = questions[row["query_id"]]
        if hashlib.sha256(row["question"].encode()).hexdigest() != row["query_sha256"]:
            raise RuntimeError(f"query hash mismatch: {row['query_id']}")
    return rows


def _load_corpus_identity(provenance_path: Path) -> dict[tuple[str, int], dict[str, Any]]:
    result = {}
    for line in provenance_path.read_text().splitlines():
        row = json.loads(line)
        result[(row["docufilm_shard"], int(row["line_start"]))] = row
    return result


def _load_blocks(blocks_path: Path, provenance_path: Path) -> dict[int, dict[str, Any]]:
    provenance = _load_corpus_identity(provenance_path)
    blocks = {}
    for line in blocks_path.read_text().splitlines():
        row = json.loads(line)
        key = (Path(row["file_path"]).name, int(row["line_start"]))
        authority = provenance.get(key)
        if authority is None:
            raise RuntimeError(f"block has no passage provenance: {key}")
        row["corpus_id"] = authority["corpus_id"]
        row["source_row_sha256"] = authority["row_payload_sha256"]
        row["source_text_sha256"] = authority["text_sha256"]
        row["source_title_sha256"] = authority["title_sha256"]
        blocks[int(row["block_ordinal"])] = row
    return blocks


def _load_index(dataset_root: Path) -> dict[str, Any]:
    lexicon = json.loads((dataset_root / "state/dataset_lexicon.json").read_text())
    anchor_to_symbol = {row["anchor"]: bytes.fromhex(row["symbol"][2:]) for row in lexicon["anchors"]}
    symbol_to_anchor = {value: key for key, value in anchor_to_symbol.items()}
    postings: dict[bytes, list[int]] = defaultdict(list)
    posting_positions: dict[bytes, dict[int, list[int]]] = defaultdict(lambda: defaultdict(list))
    block_lengths: Counter[int] = Counter()
    posting_path = dataset_root / "counts/block_anchor_postings.awbin"
    with posting_path.open("rb") as stream:
        while raw := stream.read(BLOCK_ANCHOR_RECORD.size):
            symbol, block, position = BLOCK_ANCHOR_RECORD.unpack(raw)
            postings[symbol].append(int(block))
            posting_positions[symbol][int(block)].append(int(position))
            block_lengths[int(block)] += 1
    document_frequency = {symbol: len(set(values)) for symbol, values in postings.items()}
    relations: dict[bytes, Counter[bytes]] = defaultdict(Counter)
    signed_relations: dict[bytes, dict[int, Counter[bytes]]] = defaultdict(lambda: defaultdict(Counter))
    relation_path = dataset_root / "counts/relation_counts.awbin"
    with relation_path.open("rb") as stream:
        while raw := stream.read(RELATION_RECORD.size):
            center, neighbor, offset, observations = RELATION_RECORD.unpack(raw)
            relations[center][neighbor] += int(observations)
            signed_relations[center][int(offset)][neighbor] += int(observations)
    return {
        "anchor_to_symbol": anchor_to_symbol,
        "symbol_to_anchor": symbol_to_anchor,
        "postings": postings,
        "posting_positions": posting_positions,
        "document_frequency": document_frequency,
        "block_lengths": block_lengths,
        "relations": relations,
        "signed_relations": signed_relations,
        "artifact_hashes": {
            "dataset_lexicon.json": file_sha256(dataset_root / "state/dataset_lexicon.json"),
            "block_anchor_postings.awbin": file_sha256(posting_path),
            "relation_counts.awbin": file_sha256(relation_path),
            "blocks.jsonl": file_sha256(dataset_root / "state/blocks.jsonl"),
        },
    }


def _direction_anchors(question: str) -> list[str]:
    from truemem.engine.anchors import anchorize, answer_direction_anchors
    return answer_direction_anchors(anchorize(question))


def _native_neighbors(query_symbols: set[bytes], index: dict[str, Any], limit: int = 16) -> list[bytes]:
    scores: Counter[bytes] = Counter()
    for symbol in query_symbols:
        scores.update(index["relations"].get(symbol, {}))
    for symbol in query_symbols:
        scores.pop(symbol, None)
    return [symbol for symbol, _score in scores.most_common(limit)]


def _rank(
    question: str,
    index: dict[str, Any],
    blocks: dict[int, dict[str, Any]],
    *,
    model_anchors: list[str] | None = None,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    query = _direction_anchors(question)
    query_counts = Counter(query)
    query_symbols = {
        symbol for anchor in query_counts if (symbol := index["anchor_to_symbol"].get(anchor)) is not None
    }
    weights: Counter[bytes] = Counter()
    for anchor, count in query_counts.items():
        symbol = index["anchor_to_symbol"].get(anchor)
        if symbol is not None:
            weights[symbol] += 80 * count
    for position, symbol in enumerate(_native_neighbors(query_symbols, index)):
        weights[symbol] += max(1, 4 - position // 4)
    admitted_model_anchors = []
    for position, anchor in enumerate(model_anchors or []):
        symbol = index["anchor_to_symbol"].get(anchor)
        if symbol is None or symbol in query_symbols:
            continue
        admitted_model_anchors.append(anchor)
        weights[symbol] += max(1, 8 - position // 4)

    scores: Counter[int] = Counter()
    direct_hits: Counter[int] = Counter()
    matched: dict[int, set[bytes]] = defaultdict(set)
    for symbol, weight in weights.items():
        df = index["document_frequency"].get(symbol, 0)
        if not df:
            continue
        adjusted = float(weight) / math.sqrt(df)
        for block in set(index["postings"].get(symbol, [])):
            scores[block] += adjusted
            matched[block].add(symbol)
            if symbol in query_symbols:
                direct_hits[block] += 1
    ranked = sorted(
        scores,
        key=lambda block: (
            -direct_hits[block],
            -(scores[block] / math.sqrt(max(1, index["block_lengths"][block]))),
            -scores[block],
            block,
        ),
    )
    out = []
    for block_ordinal in ranked[:top_k]:
        block = blocks[block_ordinal]
        out.append({
            "rank": len(out) + 1,
            "corpus_id": block["corpus_id"],
            "block_ordinal": block_ordinal,
            "citation_id": block["citation_id"],
            "citation_marker": block["marker"],
            "source_file": block["file_path"],
            "line_start": block["line_start"],
            "line_end": block["line_end"],
            "source_row_sha256": block["source_row_sha256"],
            "source_text_sha256": block["source_text_sha256"],
            "truemem_text_hash": block["text_hash"],
            "text": block["text"],
            "score": float(scores[block_ordinal]),
            "direct_hit_count": int(direct_hits[block_ordinal]),
            "matched_anchors": sorted(index["symbol_to_anchor"].get(value, value.hex()) for value in matched[block_ordinal]),
        })
    return out


class ModelGuide:
    def __init__(self, clean_method: Path, prepared: Path, checkpoint: Path):
        import torch
        sys.path.insert(0, str(clean_method / "src"))
        from awrag_location_model.modeling import provisional_chat as method
        self.torch = torch
        self.method = method
        self.device = torch.device("xpu:0")
        if not torch.xpu.is_available() or torch.xpu.get_device_name(0) != "Intel(R) Arc(TM) Pro B70 Graphics":
            raise RuntimeError("RESOURCE_GPU_UNVERIFIED")
        self.mapping = json.loads((prepared / "symbol-index-mapping.json").read_text())
        self.perm_to_dense = {row["permanent_value"]: row["dense_model_index"] for row in self.mapping["entries"]}
        self.dense_to_surface = {row["dense_model_index"]: row["surface"] for row in self.mapping["entries"]}
        self.surface_to_perm = {row["surface"]: row["permanent_value"] for row in self.mapping["entries"]}
        self.model = method.ChatDecoder(len(self.mapping["entries"]), self.device)
        self.field = method.ChatLocationField(prepared / "M002.jsonl.gz", self.perm_to_dense, self.device)
        self.inputs = method.ChatLocationInput(self.model.embedding, self.field)
        payload = torch.load(checkpoint, map_location=self.device, weights_only=False)
        self.model.load_state_dict(payload["model"])
        self.model.eval()
        self.checkpoint_update = int(payload["update"])
        self.checkpoint_validation_loss = float(payload["validation_loss"])

    def predict(self, question: str, max_new_anchors: int = 24) -> list[str]:
        path, _stats = self.method.session_surfaces({"messages": [{"role": "user", "content": question}]})
        unknown = self.method.SPECIAL["<UNKNOWN>"]
        dense = [self.perm_to_dense.get(self.surface_to_perm.get(surface, unknown), self.perm_to_dense[unknown]) for surface in path]
        generated = []
        with self.torch.no_grad():
            for _ in range(max_new_anchors):
                context = dense[-512:]
                x = self.torch.tensor(context, device=self.device).view(1, -1)
                valid = self.torch.ones_like(x, dtype=self.torch.bool)
                choice = int(self.model.decode(self.inputs(x), valid)[0, -1].argmax().item())
                surface = self.dense_to_surface[choice]
                dense.append(choice)
                if surface == "<END_SESSION>":
                    break
                if not surface.startswith("<"):
                    generated.append(surface)
        self.torch.xpu.synchronize()
        return generated


def _aggregate(rows: list[dict[str, Any]], lane: str, ks: tuple[int, ...]) -> dict[str, Any]:
    result = {"queries": len(rows)}
    for k in ks:
        hits = []
        recalls = []
        precisions = []
        all_targets = []
        for row in rows:
            targets = set(row["target_corpus_ids"])
            retrieved = [item["corpus_id"] for item in row[lane][:k]]
            relevant = sum(item in targets for item in retrieved)
            hits.append(relevant > 0)
            all_targets.append(relevant == len(targets))
            recalls.append(relevant / len(targets))
            precisions.append(relevant / max(1, len(retrieved)))
        result[f"any_relevant_accuracy@{k}"] = sum(hits) / len(hits)
        result[f"all_relevant_exact_block_accuracy@{k}"] = sum(all_targets) / len(all_targets)
        result[f"citation_recall@{k}"] = sum(recalls) / len(recalls)
        result[f"citation_precision@{k}"] = sum(precisions) / len(precisions)
    result["citation_handoff_complete_rate"] = sum(
        all(item.get("citation_id") and item.get("source_row_sha256") and item.get("source_file") and item.get("line_start") for item in row[lane])
        for row in rows
    ) / len(rows)
    return result


def evaluate(
    *,
    dataset_root: Path,
    preparation_root: Path,
    frozen_root: Path,
    prepared_model: Path,
    checkpoint: Path,
    clean_method: Path,
    output: Path,
    limit: int = 250,
) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    authority = _load_authority(
        preparation_root / "source-split-manifest.jsonl",
        frozen_root / "corpus/queries/queries-00000-of-00001.parquet",
    )[:limit]
    blocks = _load_blocks(dataset_root / "state/blocks.jsonl", preparation_root / "passage-provenance.jsonl")
    index = _load_index(dataset_root)
    guide = ModelGuide(clean_method, prepared_model, checkpoint)
    rows = []
    for ordinal, authority_row in enumerate(authority):
        predicted = guide.predict(authority_row["question"])
        baseline = _rank(authority_row["question"], index, blocks)
        assisted = _rank(authority_row["question"], index, blocks, model_anchors=predicted)
        row = {
            "query_ordinal": ordinal,
            "query_id": authority_row["query_id"],
            "query_sha256": authority_row["query_sha256"],
            "question": authority_row["question"],
            "target_corpus_ids": authority_row["target_corpus_ids"],
            "model_predicted_anchors": predicted,
            "deterministic_results": baseline,
            "model_assisted_results": assisted,
        }
        rows.append(row)
        with (output / "query-results.jsonl").open("ab") as stream:
            stream.write(canonical(row))
    ks = (1, 5, 10)
    baseline_metrics = _aggregate(rows, "deterministic_results", ks)
    assisted_metrics = _aggregate(rows, "model_assisted_results", ks)
    comparison = {
        key: assisted_metrics[key] - baseline_metrics[key]
        for key in baseline_metrics
        if key != "queries" and isinstance(baseline_metrics[key], (int, float))
    }
    report = {
        "schema": "truesystems_hotpotqa_query_only_retrieval_evaluation@1",
        "classification": "EXTERNAL_NOT_LOCAL_TRUTH_SEALED_QUERY_ONLY_EVALUATION",
        "device": "Intel(R) Arc(TM) Pro B70 Graphics",
        "model_checkpoint": str(checkpoint),
        "model_checkpoint_sha256": file_sha256(checkpoint),
        "model_checkpoint_update": guide.checkpoint_update,
        "model_checkpoint_validation_loss": guide.checkpoint_validation_loss,
        "query_count": len(rows),
        "retrieval_corpus_blocks": len(blocks),
        "model_guidance": "24 deterministic argmax anchors from query-only prefix; admitted dataset-native anchors boost native retrieval with fixed decaying weights",
        "baseline": "deterministic query anchors plus native signed 6-1-6 relation neighbors",
        "deterministic_metrics": baseline_metrics,
        "model_assisted_metrics": assisted_metrics,
        "model_minus_deterministic": comparison,
        "sentence_accuracy": None,
        "sentence_accuracy_reason": "BEIR HotpotQA qrels authorize passage IDs, not sentence-level supporting facts",
        "unsupported_citation_count": sum(
            item["corpus_id"] not in set(row["target_corpus_ids"])
            for row in rows for item in row["model_assisted_results"][:5]
        ),
        "index_artifact_hashes": index["artifact_hashes"],
        "query_results_sha256": file_sha256(output / "query-results.jsonl"),
        "sealed_test_opened_by_historical_runner_before_this_evaluation": True,
        "prose_generation_scored": False,
    }
    report["evaluation_id"] = hashlib.sha256(canonical(report)).hexdigest()
    (output / "report.json").write_bytes(canonical(report))
    return report
