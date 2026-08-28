from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from .anchors import anchorize
from .base import COUNT_BACKEND, SYMBOL_BYTES, SYMBOL_SYSTEM, dataset_paths, safe_id, unique_stamp, utc_now, write_json
from .storage import read_blocks

SCHEMA = "special_search_run@1"


@dataclass(frozen=True)
class SearchBlock:
    block_ordinal: int
    block_id: str
    citation_id: str
    marker: str
    file_path: str
    line_start: int
    line_end: int
    text: str
    conversation_id: str | None
    message_id: str | None
    title: str | None
    speaker: str | None
    timestamp: str | None
    date: str | None

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@dataclass(frozen=True)
class SearchHit:
    anchor: str
    anchor_class: str
    block: SearchBlock
    positions: list[int]


def special_search(
    runtime_root: str | Path,
    dataset_id: str,
    trigger_list: str | Path,
    out: str | Path,
    *,
    expand_prev: int = 1,
    expand_next: int = 1,
    max_hits_per_anchor: int = 500,
) -> dict[str, Any]:
    """Run the locked JSON-list special search report path.

    This is read-only against AWEAR dataset artifacts. It writes receipts only
    under the requested output folder.
    """
    started = perf_counter()
    dataset = safe_id(dataset_id)
    runtime = Path(runtime_root).expanduser().resolve()
    output_dir = Path(out).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = dataset_paths(runtime, dataset)
    _require_ready(paths)

    payload = _load_trigger_payload(Path(trigger_list))
    trigger_payload = {
        "schema": "trigger_anchors@1",
        "source": str(Path(trigger_list).expanduser().resolve()),
        "count": len(payload["anchors"]),
        "anchors": payload["anchors"],
    }
    write_json(output_dir / "trigger_anchors.json", trigger_payload)
    _write_jsonl(output_dir / "unmatched_phrases.jsonl", payload["unmatched"], overwrite=True)

    blocks = _load_blocks(paths)
    blocks_by_ordinal = {block.block_ordinal: block for block in blocks}
    block_anchor_cache = {block.block_ordinal: [str(anchor).casefold() for anchor in anchorize(block.text)] for block in blocks}
    hits_path = output_dir / "trigger_hits.jsonl"
    expanded_path = output_dir / "trigger_expanded_blocks.jsonl"
    _clear_file(hits_path)
    _clear_file(expanded_path)

    hit_count = 0
    expanded_records: list[dict[str, Any]] = []
    for trigger in trigger_payload["anchors"]:
        hits = _search_solo_anchor(blocks, trigger, block_anchor_cache, max_hits=max_hits_per_anchor)
        for hit in hits:
            hit_count += 1
            _append_jsonl(hits_path, _hit_record(hit))
            expanded = _expand_hit(blocks_by_ordinal, hit, previous_blocks=expand_prev, next_blocks=expand_next)
            expanded_records.append(expanded)
            _append_jsonl(expanded_path, expanded)

    mini_counts = _build_mini_local_counts(expanded_records)
    graph = _build_temporal_causality_graph(expanded_records, mini_counts)
    mini_counts_path = output_dir / "mini-local-counts.json"
    graph_path = output_dir / "temporal_causality_graph.json"
    write_json(mini_counts_path, mini_counts)
    write_json(graph_path, graph)
    elapsed = max(0.000001, perf_counter() - started)
    summary_path = _write_summary(
        output_dir / "trigger_anchor_summary.md",
        trigger_count=trigger_payload["count"],
        unmatched_count=len(payload["unmatched"]),
        hit_count=hit_count,
        expanded_count=len(expanded_records),
        mini_counts=mini_counts,
        graph=graph,
        output_paths={
            "trigger_anchors": str(output_dir / "trigger_anchors.json"),
            "trigger_hits": str(hits_path),
            "trigger_expanded_blocks": str(expanded_path),
            "mini_local_counts": str(mini_counts_path),
            "temporal_causality_graph": str(graph_path),
            "trigger_anchor_summary": str(output_dir / "trigger_anchor_summary.md"),
            "unmatched_phrases": str(output_dir / "unmatched_phrases.jsonl"),
        },
        throughput_messages_per_second=len(blocks) / elapsed,
    )
    receipt = {
        "schema": SCHEMA,
        "created_at": utc_now(),
        "run_id": unique_stamp(),
        "runtime_root": str(runtime),
        "dataset_id": dataset,
        "trigger_list": str(Path(trigger_list).expanduser().resolve()),
        "messages_read": len(blocks),
        "trigger_anchor_count": trigger_payload["count"],
        "unmatched_phrase_count": len(payload["unmatched"]),
        "solo_hit_count": hit_count,
        "expanded_hit_count": len(expanded_records),
        "graph1_event_count": graph.get("event_count", 0),
        "count_backend": COUNT_BACKEND,
        "symbol_system": SYMBOL_SYSTEM,
        "symbol_bytes": SYMBOL_BYTES,
        "confidence_policy": "all_events_start_0.0",
        "review_policy": "all_events_need_review_true",
        "mutation": {
            "writes_core": False,
            "writes_aw_counts": False,
            "writes_aw_citations": False,
            "writes_aw_coordinates": False,
            "writes_report_output_only": True,
        },
        "output_paths": {
            "trigger_anchors": str(output_dir / "trigger_anchors.json"),
            "trigger_hits": str(hits_path),
            "trigger_expanded_blocks": str(expanded_path),
            "mini_local_counts": str(mini_counts_path),
            "temporal_causality_graph": str(graph_path),
            "trigger_anchor_summary": str(summary_path),
            "unmatched_phrases": str(output_dir / "unmatched_phrases.jsonl"),
            "run_receipt": str(output_dir / "run_receipt.json"),
        },
    }
    write_json(output_dir / "run_receipt.json", receipt)
    return receipt


def _require_ready(paths: Any) -> None:
    required = [paths.lexicon_path, paths.blocks_path, paths.anchor_counts_path, paths.relation_counts_path, paths.block_anchor_path]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("AWEAR dataset is missing required files: " + ", ".join(missing))


def _load_trigger_payload(path: Path) -> dict[str, Any]:
    raw = json.loads(path.expanduser().read_text(encoding="utf-8"))
    rows: list[Any]
    source = "json_root"
    if isinstance(raw, list):
        rows = raw
    elif isinstance(raw, dict):
        if isinstance(raw.get("anchors"), list):
            rows = raw["anchors"]
            source = "anchors"
        elif isinstance(raw.get("entries"), list):
            rows = raw["entries"]
            source = "entries"
        else:
            rows = [raw]
    else:
        raise ValueError("trigger list must be a JSON object or list")

    anchors: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        entry = _coerce_trigger_entry(row, index=index, source=source)
        anchor_stream = _entry_anchor_stream(entry["anchor"])
        if len(anchor_stream) != 1:
            unmatched.append(_unmatched(entry, anchor_stream, reason="not_a_solo_anchor"))
            continue
        anchor = anchor_stream[0]
        if anchor in seen:
            continue
        seen.add(anchor)
        clean = dict(entry)
        clean["anchor"] = anchor
        clean.setdefault("class", "special_search")
        clean.setdefault("needs_review", True)
        clean.setdefault("confidence", 0.0)
        anchors.append(clean)
        for surface in entry.get("source_surfaces") or []:
            stream = _entry_anchor_stream(surface)
            if len(stream) != 1 or stream[0] != anchor:
                unmatched.append({
                    "schema": "special_search_unmatched_phrase@1",
                    "surface": surface,
                    "anchor_stream": stream,
                    "mapped_anchor": anchor,
                    "class": clean.get("class"),
                    "reason": "source_surface_not_solo_anchor",
                })
    return {"anchors": anchors, "unmatched": unmatched}


def _coerce_trigger_entry(row: Any, *, index: int, source: str) -> dict[str, Any]:
    if isinstance(row, str):
        return {"anchor": row, "class": "special_search", "source_index": index, "source": source}
    if not isinstance(row, dict):
        return {"anchor": str(row), "class": "special_search", "source_index": index, "source": source}
    anchor = row.get("anchor") or row.get("surface") or row.get("phrase") or row.get("text") or ""
    out = dict(row)
    out["anchor"] = str(anchor)
    out.setdefault("source_index", index)
    out.setdefault("source", source)
    return out


def _entry_anchor_stream(value: Any) -> list[str]:
    return [str(anchor).casefold() for anchor in anchorize(str(value or ""))]


def _unmatched(entry: dict[str, Any], anchor_stream: list[str], *, reason: str) -> dict[str, Any]:
    return {
        "schema": "special_search_unmatched_phrase@1",
        "surface": entry.get("anchor"),
        "anchor_stream": anchor_stream,
        "class": entry.get("class"),
        "source_index": entry.get("source_index"),
        "reason": reason,
    }


def _load_blocks(paths: Any) -> list[SearchBlock]:
    blocks = []
    for ordinal, row in sorted(read_blocks(paths).items()):
        meta = row.get("chat_metadata") or {}
        row_date = str(meta.get("date") or "") or None
        blocks.append(SearchBlock(
            block_ordinal=int(ordinal),
            block_id=str(row.get("block_id") or ""),
            citation_id=str(row.get("citation_id") or ""),
            marker=str(row.get("marker") or ""),
            file_path=str(row.get("file_path") or ""),
            line_start=int(row.get("line_start") or 0),
            line_end=int(row.get("line_end") or 0),
            text=str(row.get("text") or ""),
            conversation_id=str(meta.get("conversation_id") or "") or None,
            message_id=str(meta.get("message_id") or "") or None,
            title=str(meta.get("title") or "") or None,
            speaker=str(meta.get("speaker") or "") or None,
            timestamp=str(meta.get("created_at") or meta.get("created_at_original") or "") or None,
            date=row_date,
        ))
    return blocks


def _search_solo_anchor(blocks: list[SearchBlock], trigger: dict[str, Any], anchor_cache: dict[int, list[str]], *, max_hits: int) -> list[SearchHit]:
    wanted = str(trigger.get("anchor") or "").casefold().strip()
    if not wanted:
        return []
    hits = []
    for block in blocks:
        anchors = anchor_cache.get(block.block_ordinal, [])
        positions = [index for index, anchor in enumerate(anchors) if anchor == wanted]
        if not positions:
            continue
        hits.append(SearchHit(anchor=wanted, anchor_class=str(trigger.get("class") or "special_search"), block=block, positions=positions))
        if len(hits) >= max_hits:
            break
    return hits


def _hit_record(hit: SearchHit) -> dict[str, Any]:
    block = hit.block
    return {
        "schema": "trigger_hit@1",
        "anchor": hit.anchor,
        "anchor_class": hit.anchor_class,
        "block_ordinal": block.block_ordinal,
        "message_id": block.message_id,
        "conversation_id": block.conversation_id,
        "timestamp": block.timestamp,
        "date": block.date,
        "role": block.speaker,
        "positions": hit.positions,
        "citation": block.marker,
        "needs_review": True,
        "confidence": 0.0,
    }


def _expand_hit(blocks_by_ordinal: dict[int, SearchBlock], hit: SearchHit, *, previous_blocks: int, next_blocks: int) -> dict[str, Any]:
    ordinal = hit.block.block_ordinal
    previous = [blocks_by_ordinal[offset].to_dict() for offset in range(ordinal - previous_blocks, ordinal) if offset in blocks_by_ordinal]
    nxt = [blocks_by_ordinal[offset].to_dict() for offset in range(ordinal + 1, ordinal + next_blocks + 1) if offset in blocks_by_ordinal]
    block = hit.block
    return {
        "schema": "trigger_expanded_block@1",
        "anchor": hit.anchor,
        "anchor_class": hit.anchor_class,
        "hit_message_id": block.message_id,
        "conversation_id": block.conversation_id,
        "timestamp": block.timestamp,
        "date": block.date,
        "role": block.speaker,
        "positions": hit.positions,
        "previous_blocks": previous,
        "hit_block": block.to_dict(),
        "next_blocks": nxt,
        "citation": _citation(block),
        "needs_review": True,
        "confidence": 0.0,
    }


def _citation(block: SearchBlock) -> dict[str, Any]:
    return {
        "citation_id": block.citation_id,
        "marker": block.marker,
        "block_ordinal": block.block_ordinal,
        "block_id": block.block_id,
        "file_path": block.file_path,
        "line_start": block.line_start,
        "line_end": block.line_end,
        "timestamp": block.timestamp,
        "date": block.date,
        "conversation_id": block.conversation_id,
        "message_id": block.message_id,
    }


def _build_mini_local_counts(expanded_records: list[dict[str, Any]]) -> dict[str, Any]:
    anchor_counts: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()
    prior_counts: dict[str, Counter[str]] = defaultdict(Counter)
    next_counts: dict[str, Counter[str]] = defaultdict(Counter)
    role_counts: dict[str, Counter[str]] = defaultdict(Counter)
    date_counts: dict[str, Counter[str]] = defaultdict(Counter)
    for record in expanded_records:
        trigger = str(record.get("anchor") or "").casefold()
        cls = str(record.get("anchor_class") or "special_search")
        if not trigger:
            continue
        class_counts[cls] += 1
        role_counts[trigger][str(record.get("role") or "unknown")] += 1
        date_counts[str(record.get("date") or "unknown")][trigger] += 1
        for block in record.get("previous_blocks") or []:
            for anchor in _block_anchors(block):
                anchor_counts[anchor] += 1
                prior_counts[trigger][anchor] += 1
        for anchor in _block_anchors(record.get("hit_block") or {}):
            anchor_counts[anchor] += 1
        for block in record.get("next_blocks") or []:
            for anchor in _block_anchors(block):
                anchor_counts[anchor] += 1
                next_counts[trigger][anchor] += 1
    return {
        "schema": "mini_local_counts@1",
        "source": "trigger_expanded_blocks",
        "counts": {
            "anchor_counts": dict(anchor_counts.most_common()),
            "anchor_class_counts": dict(class_counts.most_common()),
            "trigger_to_prior_anchor_counts": _nested_counter(prior_counts),
            "trigger_to_next_anchor_counts": _nested_counter(next_counts),
            "trigger_to_role_counts": _nested_counter(role_counts),
            "date_to_trigger_counts": _nested_counter(date_counts),
        },
    }


def _block_anchors(block: dict[str, Any]) -> list[str]:
    out = []
    for anchor in anchorize(str(block.get("text") or "")):
        value = str(anchor).strip().casefold()
        if len(value) >= 2:
            out.append(value)
    return out


def _build_temporal_causality_graph(expanded_records: list[dict[str, Any]], mini_counts: dict[str, Any]) -> dict[str, Any]:
    events = []
    for index, record in enumerate(expanded_records, start=1):
        events.append({
            "schema": "temporal_causality_event@1",
            "event_id": f"tcg-{index:06d}",
            "date": record.get("date"),
            "timestamp": record.get("timestamp"),
            "trigger_anchor": record.get("anchor"),
            "trigger_class": record.get("anchor_class"),
            "prior_context_anchors": _top_context_anchors(record.get("previous_blocks") or []),
            "hit_context_anchors": _top_context_anchors([record.get("hit_block") or {}]),
            "next_context_anchors": _top_context_anchors(record.get("next_blocks") or []),
            "inferred_event_shape": "candidate_contextual_state_signal",
            "citations": [record.get("citation")],
            "confidence": 0.0,
            "needs_review": True,
            "diagnostic_warning": "Candidate temporal state event only; review expanded context before interpretation.",
        })
    return {
        "schema": "temporal_causality_graph@1",
        "event_count": len(events),
        "events": events,
        "count_refs": {
            "anchor_class_counts": mini_counts.get("counts", {}).get("anchor_class_counts", {}),
            "date_to_trigger_counts": mini_counts.get("counts", {}).get("date_to_trigger_counts", {}),
        },
    }


def _top_context_anchors(blocks: list[dict[str, Any]], *, limit: int = 12) -> list[str]:
    counts: Counter[str] = Counter()
    for block in blocks:
        counts.update(_block_anchors(block))
    return [key for key, _value in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def _nested_counter(rows: dict[str, Counter[str]], *, limit: int = 50) -> dict[str, dict[str, int]]:
    return {key: dict(counter.most_common(limit)) for key, counter in sorted(rows.items())}


def _write_summary(path: Path, *, trigger_count: int, unmatched_count: int, hit_count: int, expanded_count: int, mini_counts: dict[str, Any], graph: dict[str, Any], output_paths: dict[str, str], throughput_messages_per_second: float) -> Path:
    class_counts = mini_counts.get("counts", {}).get("anchor_class_counts", {})
    top_anchors = list(mini_counts.get("counts", {}).get("anchor_counts", {}).items())[:20]
    lines = [
        "# Special Search CLI Report",
        "",
        "JSON-list driven AWEAR special search. Candidate labels are not truth, diagnosis, or promotion.",
        "",
        f"Trigger anchors: {trigger_count}",
        f"Unmatched phrases: {unmatched_count}",
        f"Solo hits: {hit_count}",
        f"Expanded neighborhoods: {expanded_count}",
        f"Graph 1 events: {graph.get('event_count', 0)}",
        f"Throughput messages/sec: {throughput_messages_per_second:.2f}",
        "",
        "## Anchor Class Counts",
    ]
    for key, value in class_counts.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Top Context Anchors"])
    for key, value in top_anchors:
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Output Paths"])
    for key, value in output_paths.items():
        lines.append(f"- {key}: `{value}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _clear_file(path: Path) -> None:
    if path.exists():
        path.unlink()


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _write_jsonl(path: Path, rows: list[dict[str, Any]], *, overwrite: bool = False) -> None:
    if overwrite:
        _clear_file(path)
    for row in rows:
        _append_jsonl(path, row)
    if not rows:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
