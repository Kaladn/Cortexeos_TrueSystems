"""Ingest Pipeline — orchestrates: input -> chunks -> anchors -> store -> receipt.

This is the main entry point for ingesting text/files into the LakeSpeak data lake.
Anchor extraction uses the Forest lexicon bridge (lazy-loaded).
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from lakespeak.schemas import (
    ChunkRef, ChunkAnchors, ChunkRelations, AnchorRecord,
    ANCHORS_VERSION, RELATIONS_VERSION,
)
from lakespeak.ingest.chunker import chunk_text
from lakespeak.ingest.receipt import make_receipt_id, source_hash, create_receipt
from lakespeak.text.normalize import tokenize as _canonical_tokenize

logger = logging.getLogger(__name__)


def _extract_anchors_for_chunk(
    chunk: ChunkRef,
    bridge: Any,
) -> ChunkAnchors:
    """Extract anchors from a chunk using the Forest lexicon bridge.

    An anchor is a token that:
      - exists in the lexicon (bridge.word_index)
      - has len >= 3
      - is not in the deterministic stop list

    Also computes anchor_counts: {token: raw_frequency_in_chunk}.
    """
    from collections import Counter
    from lakespeak.index.anchor_reranker import STOP_TOKENS

    tokens = _canonical_tokenize(chunk.text)
    anchors: List[AnchorRecord] = []

    for pos, token in enumerate(tokens):
        if len(token) < 3:
            continue
        if token in STOP_TOKENS:
            continue

        # Check lexicon
        if hasattr(bridge, "word_index") and token in bridge.word_index:
            hex_addr = bridge.word_index[token]
            entry = bridge.entries.get(hex_addr)
            font_symbol = None
            freq = 0

            if entry is not None:
                font_symbol = entry.payload.get("font_symbol") if hasattr(entry, "payload") else None
                freq = bridge.frequency.get(token, 0)

            anchors.append(AnchorRecord(
                token=token,
                hex_addr=hex_addr,
                symbol=font_symbol,
                position=pos,
                frequency=freq,
            ))

    # Materialize anchor_counts: how many times each anchor token appears
    anchor_counts = dict(Counter(a.token for a in anchors))

    return ChunkAnchors(
        schema_version=ANCHORS_VERSION,
        chunk_id=chunk.chunk_id,
        receipt_id=chunk.receipt_id,
        anchor_count=len(anchors),
        anchors=anchors,
        anchor_counts=anchor_counts,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
    )


def _extract_relations_for_chunk(
    chunk: ChunkRef,
    anchors: ChunkAnchors,
    bridge: Any = None,
    window: int = 6,
) -> ChunkRelations:
    """Extract 6-1-6 co-occurrence relations using the bridge's window counter.

    Calls compute_window_counts() from forest_gpu.py via the bridge's
    tokenizer and vocab index. Produces real co-occurrence counts — no faking.

    Only anchor tokens (tokens in the lexicon) become relation edges.
    Non-anchor tokens participate in windows but don't emit edges.
    """
    from lakespeak.schemas import RelationEdge, RELATIONS_VERSION

    if bridge is None or not hasattr(bridge, "word_index") or anchors.anchor_count == 0:
        return ChunkRelations(
            schema_version=RELATIONS_VERSION,
            chunk_id=chunk.chunk_id,
            receipt_id=chunk.receipt_id,
            relation_count=0,
            relations=[],
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        )

    # Tokenize using the canonical path (same normalization as anchor extraction)
    from core.services.compute import ComputeService
    tokens = ComputeService.tokenize(chunk.text)
    if len(tokens) < 2:
        return ChunkRelations(
            schema_version=RELATIONS_VERSION,
            chunk_id=chunk.chunk_id,
            receipt_id=chunk.receipt_id,
            relation_count=0,
            relations=[],
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        )

    # Build set of anchor tokens for fast lookup
    anchor_tokens = {a.token for a in anchors.anchors}
    anchor_hex = {a.token: a.hex_addr for a in anchors.anchors}

    # Encode tokens and compute window counts via ComputeService seam
    try:
        token_ids = bridge._encode_tokens(tokens)
        counts = ComputeService.compute_window_counts(token_ids, window, bridge.device_info)
    except Exception as e:
        logger.warning("compute_window_counts failed for chunk %s: %s", chunk.chunk_id, e)
        return ChunkRelations(
            schema_version=RELATIONS_VERSION,
            chunk_id=chunk.chunk_id,
            receipt_id=chunk.receipt_id,
            relation_count=0,
            relations=[],
            created_at_utc=datetime.now(timezone.utc).isoformat(),
        )

    # Convert raw counts to RelationEdge objects.
    # Only emit edges where BOTH focus and context are anchor tokens.
    edges: List[RelationEdge] = []
    seen: Dict[tuple, RelationEdge] = {}  # (src, tgt, dist, dir) -> edge (dedup/sum)

    for offset, triples in counts.items():
        direction = "before" if offset < 0 else "after"
        distance = abs(offset)
        for focus_idx, ctx_idx, count in triples:
            focus_word = bridge._decode_index(focus_idx)
            ctx_word = bridge._decode_index(ctx_idx)

            # Both must be anchor tokens
            if focus_word not in anchor_tokens or ctx_word not in anchor_tokens:
                continue
            if focus_word == ctx_word:
                continue  # Self-loops not useful

            key = (focus_word, ctx_word, distance, direction)
            if key in seen:
                seen[key].co_occurrence_count += count
            else:
                edge = RelationEdge(
                    source_token=focus_word,
                    target_token=ctx_word,
                    distance=distance,
                    direction=direction,
                    co_occurrence_count=count,
                    source_hex=anchor_hex.get(focus_word, ""),
                    target_hex=anchor_hex.get(ctx_word, ""),
                )
                seen[key] = edge

    edges = list(seen.values())
    # Sort deterministically: source ASC, target ASC, distance ASC, direction ASC
    edges.sort(key=lambda e: (e.source_token, e.target_token, e.distance, e.direction))

    return ChunkRelations(
        schema_version=RELATIONS_VERSION,
        chunk_id=chunk.chunk_id,
        receipt_id=chunk.receipt_id,
        relation_count=len(edges),
        relations=edges,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
    )


def _governed_write(name: str, content: str, gateway_obj, zone) -> None:
    """Write via gateway if available, else direct I/O."""
    if gateway_obj is not None and zone is not None:
        result = gateway_obj.write(
            caller="system", zone=zone, name=name,
            content=content, encrypt=False,
        )
        if not getattr(result, "success", True):
            raise IOError(f"Gateway write failed for {name}: {getattr(result, 'error', 'unknown')}")
    else:
        try:
            from security.data_paths import LAKESPEAK_CHUNKS_DIR
        except ImportError:
            raise IOError("No gateway and no data_paths — cannot write")
        dest = LAKESPEAK_CHUNKS_DIR / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")


def _store_chunks(
    receipt_id: str,
    chunks: List[ChunkRef],
    all_anchors: List[ChunkAnchors],
    all_relations: List[ChunkRelations],
) -> None:
    """Persist chunks, anchors, and relations to the chunk store."""
    _gw = None
    _zone = None
    try:
        from security.gateway import gateway as _gw, WriteZone
        _zone = WriteZone.LAKESPEAK_INDEX
    except ImportError:
        logger.warning("Gateway not available — using direct file I/O")

    # Ensure receipt directory exists (gateway.write handles parent creation
    # for its zone root, but we need the receipt subdirectory)
    try:
        from security.data_paths import LAKESPEAK_CHUNKS_DIR
        receipt_dir = LAKESPEAK_CHUNKS_DIR / receipt_id
        receipt_dir.mkdir(parents=True, exist_ok=True)
    except ImportError:
        pass

    # Write chunks.jsonl
    chunks_content = "\n".join(
        json.dumps(asdict(c), ensure_ascii=False, separators=(",", ":"))
        for c in chunks
    ) + "\n"
    _governed_write(f"chunks/{receipt_id}/chunks.jsonl", chunks_content, _gw, _zone)

    # Write anchors.json
    anchors_content = json.dumps(
        [asdict(a) for a in all_anchors], ensure_ascii=False, indent=2,
    )
    _governed_write(f"chunks/{receipt_id}/anchors.json", anchors_content, _gw, _zone)

    # Write relations.json
    relations_content = json.dumps(
        [asdict(r) for r in all_relations], ensure_ascii=False, indent=2,
    )
    _governed_write(f"chunks/{receipt_id}/relations.json", relations_content, _gw, _zone)

    logger.info("Stored %d chunks for receipt %s (governed=%s)", len(chunks), receipt_id, _gw is not None)


def _update_anchor_stats(new_anchors: List[ChunkAnchors]) -> None:
    """Incrementally update corpus-level anchor stats (df/cf).

    Reads existing anchor_stats.json, merges in new chunk data, writes back.
    Stats:
      df[token] = number of chunks the token appears in
      cf[token] = total count of token across all chunks
      doc_count = total chunks with at least 1 anchor

    Stored at: LAKESPEAK_INDEX_DIR/anchor_stats.json
    """
    try:
        from security.data_paths import LAKESPEAK_INDEX_DIR
    except ImportError:
        logger.warning("Cannot update anchor stats — security.data_paths not available")
        return

    stats_path = LAKESPEAK_INDEX_DIR / "anchor_stats.json"

    # Load existing stats
    if stats_path.exists():
        try:
            existing = json.loads(stats_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}
    else:
        existing = {}

    df: Dict[str, int] = existing.get("df", {})
    cf: Dict[str, int] = existing.get("cf", {})
    doc_count: int = existing.get("doc_count", 0)

    # Merge new chunk data
    for ca in new_anchors:
        if ca.anchor_count == 0:
            continue
        doc_count += 1
        # Unique tokens in this chunk (for df — count once per chunk)
        seen_tokens: set = set()
        for anchor in ca.anchors:
            token = anchor.token
            cf[token] = cf.get(token, 0) + 1
            if token not in seen_tokens:
                df[token] = df.get(token, 0) + 1
                seen_tokens.add(token)

    # Write back
    stats = {
        "doc_count": doc_count,
        "unique_anchors": len(df),
        "df": df,
        "cf": cf,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    stats_path.write_text(
        json.dumps(stats, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    logger.info(
        "Anchor stats updated: doc_count=%d, unique_anchors=%d",
        doc_count, len(df),
    )


def rebuild_anchor_stats() -> Dict[str, Any]:
    """Full rebuild of anchor_stats.json from all stored anchor files.

    One pass over every receipt's anchors.json. Use after re-ingesting
    or if the incremental stats get out of sync.
    """
    try:
        from security.data_paths import LAKESPEAK_CHUNKS_DIR, LAKESPEAK_INDEX_DIR
    except ImportError:
        return {"error": "security.data_paths not available"}

    df: Dict[str, int] = {}
    cf: Dict[str, int] = {}
    doc_count = 0
    receipt_count = 0

    for receipt_dir in sorted(LAKESPEAK_CHUNKS_DIR.iterdir()):
        anchors_file = receipt_dir / "anchors.json"
        if not anchors_file.exists():
            continue
        receipt_count += 1

        try:
            data = json.loads(anchors_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        for chunk_entry in data:
            anchors = chunk_entry.get("anchors", [])
            if not anchors:
                continue
            doc_count += 1

            seen_tokens: set = set()
            for a in anchors:
                token = a.get("token", "")
                if not token:
                    continue
                cf[token] = cf.get(token, 0) + 1
                if token not in seen_tokens:
                    df[token] = df.get(token, 0) + 1
                    seen_tokens.add(token)

    stats = {
        "doc_count": doc_count,
        "unique_anchors": len(df),
        "receipt_count": receipt_count,
        "df": df,
        "cf": cf,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    stats_path = LAKESPEAK_INDEX_DIR / "anchor_stats.json"
    stats_path.write_text(
        json.dumps(stats, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    logger.info(
        "Anchor stats rebuilt: %d receipts, %d chunks with anchors, %d unique anchor tokens",
        receipt_count, doc_count, len(df),
    )
    return stats


def ingest_text(
    text: str,
    source_type: str = "text",
    source_path: Optional[str] = None,
    bridge: Any = None,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    skip_mapped_guard: bool = False,
) -> Dict[str, Any]:
    """Ingest text into the LakeSpeak data lake.

    Pipeline:
      1. Generate receipt ID
      2. Chunk text with overlap
      3. Extract anchors per chunk (via bridge lexicon)
      4. Extract relations per chunk (6-1-6 window)
      5. Store chunks + anchors + relations
      6. Create ingest receipt
      7. Log training event

    Args:
        text: Raw text to ingest
        source_type: "text" | "file" | "url" | "chat_export"
        source_path: Original file path (if file)
        bridge: ForestLexiconBridge instance (optional, for anchor extraction)
        chunk_size: Tokens per chunk
        chunk_overlap: Tokens of overlap

    Returns:
        Dict with ingest_receipt@1 fields.
    """
    # ── Ingestion guard: block 6-1-6 mapped documents ───────────
    # skip_mapped_guard=True when explicitly committing mapped data to grove
    fingerprint = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if skip_mapped_guard:
        logger.info("Ingestion guard bypassed (explicit grove commit) for %s", fingerprint[:12])
    else:
        try:
            from security.data_paths import STATE_DIR as _guard_state_dir
            _guard_ledger = _guard_state_dir / "documap_jobs.jsonl"
            if _guard_ledger.exists():
                _mapped = set()
                with open(_guard_ledger, "r", encoding="utf-8") as _lf:
                    for _line in _lf:
                        _line = _line.strip()
                        if not _line:
                            continue
                        _evt = json.loads(_line)
                        _fp = _evt.get("fingerprint")
                        _st = _evt.get("event")
                        if _fp and _st == "completed":
                            _mapped.add(_fp)
                        elif _fp and _st == "failed":
                            _mapped.discard(_fp)
                if fingerprint in _mapped:
                    logger.info("Ingestion blocked: document %s is 6-1-6 mapped", fingerprint[:12])
                    return {
                        "status": "blocked",
                        "reason": "Document is 6-1-6 mapped — blocked from grove ingestion",
                        "fingerprint": fingerprint,
                    }
        except Exception as e:
            logger.warning("Could not check documap ledger for ingestion guard: %s", e)

    receipt_id = make_receipt_id()
    src_hash = source_hash(text)

    # 1. Chunk
    chunks = chunk_text(
        text=text,
        receipt_id=receipt_id,
        source_hash=src_hash,
        chunk_size=chunk_size,
        overlap=chunk_overlap,
    )

    if not chunks:
        logger.warning("No chunks produced from input text (length=%d)", len(text))

    # 2. Extract anchors and relations
    all_anchors: List[ChunkAnchors] = []
    all_relations: List[ChunkRelations] = []
    total_anchor_count = 0
    total_relation_count = 0

    for chunk in chunks:
        if bridge is not None:
            chunk_anchors = _extract_anchors_for_chunk(chunk, bridge)
            chunk_relations = _extract_relations_for_chunk(chunk, chunk_anchors, bridge=bridge)

            # Backfill window_counts: how many distinct windows each anchor
            # appears in (as source or target in a relation edge).
            if chunk_relations.relation_count > 0:
                from collections import Counter as _Counter
                wc: Dict[str, set] = {}
                for edge in chunk_relations.relations:
                    wc.setdefault(edge.source_token, set()).add(
                        (edge.target_token, edge.distance, edge.direction)
                    )
                    wc.setdefault(edge.target_token, set()).add(
                        (edge.source_token, edge.distance, edge.direction)
                    )
                chunk_anchors.window_counts = {t: len(wins) for t, wins in wc.items()}
        else:
            # No bridge — empty anchors/relations (still valid schema)
            chunk_anchors = ChunkAnchors(
                schema_version=ANCHORS_VERSION,
                chunk_id=chunk.chunk_id,
                receipt_id=receipt_id,
                anchor_count=0,
                anchors=[],
                created_at_utc=datetime.now(timezone.utc).isoformat(),
            )
            chunk_relations = ChunkRelations(
                schema_version=RELATIONS_VERSION,
                chunk_id=chunk.chunk_id,
                receipt_id=receipt_id,
                relation_count=0,
                relations=[],
                created_at_utc=datetime.now(timezone.utc).isoformat(),
            )

        all_anchors.append(chunk_anchors)
        all_relations.append(chunk_relations)
        total_anchor_count += chunk_anchors.anchor_count
        total_relation_count += chunk_relations.relation_count

    # 3. Store
    _store_chunks(receipt_id, chunks, all_anchors, all_relations)

    # 3b. Update corpus-level anchor stats (df/cf)
    if total_anchor_count > 0:
        try:
            _update_anchor_stats(all_anchors)
        except Exception as e:
            logger.warning("Anchor stats update failed: %s", e)

    # 4. Create receipt
    lexicon_version = ""
    if bridge is not None and hasattr(bridge, "get_config"):
        cfg = bridge.get_config()
        lexicon_version = cfg.get("lexicon_root", "")

    receipt = create_receipt(
        receipt_id=receipt_id,
        source_type=source_type,
        raw_text=text,
        chunk_count=len(chunks),
        anchor_count=total_anchor_count,
        relation_count=total_relation_count,
        lexicon_version=lexicon_version,
        source_path=source_path,
    )

    # 5. Log training event
    try:
        from lakespeak.events.training_logger import TrainingEventLogger
        logger_inst = TrainingEventLogger()
        logger_inst.log_ingest(asdict(receipt))
    except Exception as e:
        logger.warning("Failed to log ingest event: %s", e)

    # 6. Update indexes so queries find new chunks immediately
    if chunks:
        chunk_texts_list = [c.text for c in chunks]
        chunk_ids_list = [c.chunk_id for c in chunks]
        receipt_ids_list = [c.receipt_id for c in chunks]

        # BM25 (always)
        try:
            from lakespeak.index.bm25 import BM25Index
            bm25 = BM25Index()
            bm25.add_chunks(chunk_texts_list, chunk_ids_list, receipt_ids_list)
            bm25.save()
            logger.info("BM25 index updated with %d new chunks", len(chunks))
        except Exception as e:
            logger.warning("BM25 index update failed (run /reindex manually): %s", e)

        # Census (6-1-6 adjacency co-occurrence index)
        try:
            from lakespeak.index.census import CensusIndex
            census = CensusIndex()
            census.add_chunks(chunk_texts_list, chunk_ids_list, receipt_ids_list)
            census.save()
            logger.info("Census index updated with %d new chunks", len(chunks))
        except Exception as e:
            logger.warning("Census index update skipped: %s", e)

    return asdict(receipt)


def _read_file_strict(path: Path) -> tuple:
    """Read a file with strict ordered decode policy.

    Tries encodings in order: utf-8-sig, utf-8, cp1252.
    Returns (text, encoding_used, decode_lossy, replacement_count).
    """
    for enc in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            text = path.read_text(encoding=enc)
            repl_count = text.count("\ufffd")
            return text, enc, False, repl_count
        except (UnicodeDecodeError, ValueError):
            continue

    # Last resort: utf-8 with replacement (lossy)
    text = path.read_text(encoding="utf-8", errors="replace")
    repl_count = text.count("\ufffd")
    return text, "utf-8", True, repl_count


def ingest_file(
    file_path: str,
    bridge: Any = None,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> Dict[str, Any]:
    """Ingest a file into the data lake.

    Uses strict ordered decode policy (utf-8-sig > utf-8 > cp1252).
    Records encoding metadata in the receipt.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    text, encoding_used, decode_lossy, replacement_count = _read_file_strict(path)

    if replacement_count > 0:
        logger.warning(
            "File %s: %d replacement characters (encoding=%s, lossy=%s)",
            path.name, replacement_count, encoding_used, decode_lossy,
        )

    result = ingest_text(
        text=text,
        source_type="file",
        source_path=str(path.resolve()),
        bridge=bridge,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    # Attach encoding metadata to receipt
    result["source_encoding"] = encoding_used
    result["decode_lossy"] = decode_lossy
    result["replacement_char_count"] = replacement_count

    return result
