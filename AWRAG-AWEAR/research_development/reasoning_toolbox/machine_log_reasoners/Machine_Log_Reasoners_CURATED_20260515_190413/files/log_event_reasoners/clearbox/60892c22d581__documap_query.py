"""DocuMap read/query service for grove explorer endpoints."""
from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Dict

from fastapi import HTTPException

from bridges.helpers import _validate_path_id, _validate_path_within
from core.lakespeak.storage import iter_receipt_dirs, resolve_receipt_dir

logger = logging.getLogger(__name__)


class DocuMapQueryService:
    """Owns read-side DocuMap grove browsing and query shaping."""

    def __init__(self, *, chunks_dir: Path, index_dir: Path) -> None:
        self._chunks_dir = chunks_dir
        self._index_dir = index_dir

    async def docs(self, limit: int = 50, offset: int = 0) -> dict:
        limit = min(limit, 200)
        docs = []
        if self._chunks_dir.exists():
            receipt_dirs = sorted(iter_receipt_dirs(base_dir=self._chunks_dir), key=lambda item: item[1].name, reverse=True)
            for corpus_id, rdir in receipt_dirs:
                receipt_id = rdir.name
                chunks_file = rdir / "chunks.jsonl"
                anchors_file = rdir / "anchors.json"
                if not chunks_file.exists():
                    continue
                chunk_count = 0
                total_tokens = 0
                try:
                    with open(chunks_file, "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                chunk_count += 1
                                try:
                                    c = json.loads(line)
                                    total_tokens += c.get("token_count", 0)
                                except json.JSONDecodeError:
                                    pass
                except OSError:
                    pass
                anchor_count = 0
                if anchors_file.exists():
                    try:
                        adata = json.loads(anchors_file.read_text(encoding="utf-8"))
                        if isinstance(adata, list):
                            anchor_count = sum(a.get("anchor_count", 0) for a in adata)
                    except (json.JSONDecodeError, OSError):
                        pass
                docs.append(
                    {
                        "receipt_id": receipt_id,
                        "corpus_id": corpus_id,
                        "lake_path": str(rdir.resolve()),
                        "chunk_count": chunk_count,
                        "total_tokens": total_tokens,
                        "anchor_count": anchor_count,
                        "has_relations": (rdir / "relations.json").exists(),
                    }
                )
        total = len(docs)
        page = docs[offset: offset + limit]
        return {"docs": page, "total": total}

    async def doc_detail(self, receipt_id: str) -> dict:
        _validate_path_id(receipt_id, "receipt_id")
        resolved = resolve_receipt_dir(receipt_id, base_dir=self._chunks_dir)
        if not resolved:
            raise HTTPException(404, f"Receipt {receipt_id} not found in grove")
        corpus_id, rdir = resolved
        rdir = _validate_path_within(rdir, self._chunks_dir, "receipt_id")
        chunks_file = rdir / "chunks.jsonl"
        anchors_file = rdir / "anchors.json"
        result = {
            "receipt_id": receipt_id,
            "corpus_id": corpus_id,
            "lake_path": str(rdir.resolve()),
            "files": [f.name for f in rdir.iterdir()],
        }
        if chunks_file.exists():
            chunks = []
            with open(chunks_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            chunks.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
            result["chunk_count"] = len(chunks)
            result["total_tokens"] = sum(c.get("token_count", 0) for c in chunks)
            if chunks:
                result["source_hash"] = chunks[0].get("source_hash", "")
        if anchors_file.exists():
            try:
                adata = json.loads(anchors_file.read_text(encoding="utf-8"))
                if isinstance(adata, list):
                    result["anchor_count"] = sum(a.get("anchor_count", 0) for a in adata)
            except (json.JSONDecodeError, OSError):
                pass
        return result

    async def reconstruct(self, receipt_id: str) -> dict:
        _validate_path_id(receipt_id, "receipt_id")
        resolved = resolve_receipt_dir(receipt_id, base_dir=self._chunks_dir)
        if not resolved:
            raise HTTPException(404, f"Receipt {receipt_id} not found in grove")
        corpus_id, rdir = resolved
        rdir = _validate_path_within(rdir, self._chunks_dir, "receipt_id")
        chunks_file = rdir / "chunks.jsonl"
        anchors_file = rdir / "anchors.json"
        if not chunks_file.exists():
            raise HTTPException(404, f"Receipt {receipt_id} not found in grove")

        chunks = []
        with open(chunks_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        chunks.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        chunks.sort(key=lambda c: c.get("ordinal", 0))

        text_parts = []
        prev_end = 0
        for ch in chunks:
            span_start = ch.get("span_start", prev_end)
            chunk_text = ch.get("text", "")
            if span_start >= prev_end:
                text_parts.append(chunk_text)
            else:
                overlap = prev_end - span_start
                if overlap < len(chunk_text):
                    text_parts.append(chunk_text[overlap:])
            prev_end = max(prev_end, ch.get("span_end", span_start + len(chunk_text)))
        text = "".join(text_parts)

        anchors = []
        if anchors_file.exists():
            try:
                adata = json.loads(anchors_file.read_text(encoding="utf-8"))
                if isinstance(adata, list):
                    for chunk_anchors in adata:
                        for a in chunk_anchors.get("anchors", []):
                            anchors.append({"word": a.get("token", ""), "hex_addr": a.get("hex_addr", "")})
            except (json.JSONDecodeError, OSError):
                pass

        seen = set()
        unique_anchors = []
        for a in anchors:
            if a["word"] not in seen:
                seen.add(a["word"])
                unique_anchors.append(a)

        total_tokens = sum(c.get("token_count", 0) for c in chunks)
        return {
            "text": text,
            "lossy": False,
            "corpus_id": corpus_id,
            "lake_path": str(rdir.resolve()),
            "anchors": unique_anchors,
            "total_tokens": total_tokens,
            "anchor_count": len(unique_anchors),
            "chunk_count": len(chunks),
        }

    async def graph(self, receipt_id: str, max_nodes: int = 100, max_edges: int = 500) -> dict:
        _validate_path_id(receipt_id, "receipt_id")
        resolved = resolve_receipt_dir(receipt_id, base_dir=self._chunks_dir)
        if not resolved:
            raise HTTPException(404, f"Receipt {receipt_id} not found in grove")
        corpus_id, rdir = resolved
        rdir = _validate_path_within(rdir, self._chunks_dir, "receipt_id")
        anchors_file = rdir / "anchors.json"
        relations_file = rdir / "relations.json"

        anchor_freq: Dict[str, int] = {}
        anchor_addr: Dict[str, str] = {}
        if anchors_file.exists():
            try:
                adata = json.loads(anchors_file.read_text(encoding="utf-8"))
                if isinstance(adata, list):
                    for chunk_anchors in adata:
                        for a in chunk_anchors.get("anchors", []):
                            tok = a.get("token", "")
                            anchor_freq[tok] = anchor_freq.get(tok, 0) + 1
                            if tok not in anchor_addr:
                                anchor_addr[tok] = a.get("hex_addr", "")
            except (json.JSONDecodeError, OSError):
                pass

        sorted_anchors = sorted(anchor_freq.items(), key=lambda x: x[1], reverse=True)[:max_nodes]
        anchor_set = {a[0] for a in sorted_anchors}
        nodes = [{"data": {"id": tok, "label": tok, "freq": freq, "addr": anchor_addr.get(tok, "")}} for tok, freq in sorted_anchors]

        edges = []
        edge_count = 0
        if relations_file.exists():
            try:
                rdata = json.loads(relations_file.read_text(encoding="utf-8"))
                if isinstance(rdata, list):
                    for chunk_rels in rdata:
                        for rel in chunk_rels.get("relations", []):
                            src = rel.get("source_token", "")
                            tgt = rel.get("target_token", "")
                            weight = rel.get("co_occurrence_count", 1)
                            if src in anchor_set and tgt in anchor_set and src != tgt:
                                edges.append({"data": {"source": src, "target": tgt, "weight": weight}})
                                edge_count += 1
                                if edge_count >= max_edges:
                                    break
                        if edge_count >= max_edges:
                            break
            except (json.JSONDecodeError, OSError):
                pass

        return {
            "nodes": nodes,
            "edges": edges,
            "corpus_id": corpus_id,
            "lake_path": str(rdir.resolve()),
            "total_anchors": len(sorted_anchors),
            "capped": len(sorted_anchors) >= max_nodes,
        }

    async def anchor_cloud(self, anchor: str, receipt_id: str = "", topk: int = 20) -> dict:
        if not receipt_id:
            raise HTTPException(400, "receipt_id query param required")
        _validate_path_id(receipt_id, "receipt_id")
        resolved = resolve_receipt_dir(receipt_id, base_dir=self._chunks_dir)
        if not resolved:
            raise HTTPException(404, f"Receipt {receipt_id} not found in grove")
        corpus_id, rdir = resolved
        rdir = _validate_path_within(rdir, self._chunks_dir, "receipt_id")
        relations_file = rdir / "relations.json"

        cooccur: Dict[str, float] = {}
        if relations_file.exists():
            try:
                rdata = json.loads(relations_file.read_text(encoding="utf-8"))
                if isinstance(rdata, list):
                    for chunk_rels in rdata:
                        for rel in chunk_rels.get("relations", []):
                            src = rel.get("source_token", "")
                            tgt = rel.get("target_token", "")
                            count = rel.get("co_occurrence_count", 1)
                            if src == anchor and tgt != anchor:
                                cooccur[tgt] = cooccur.get(tgt, 0) + count
                            elif tgt == anchor and src != anchor:
                                cooccur[src] = cooccur.get(src, 0) + count
            except (json.JSONDecodeError, OSError):
                pass

        max_score = max(cooccur.values()) if cooccur else 1
        cloud = sorted(
            [{"anchor": k, "score": round(v / max_score, 3)} for k, v in cooccur.items()],
            key=lambda x: x["score"],
            reverse=True,
        )[:topk]
        return {
            "anchor": anchor,
            "topk": cloud,
            "receipt_id": receipt_id,
            "corpus_id": corpus_id,
            "lake_path": str(rdir.resolve()),
        }

    async def topk(self, limit: int = 200, sort: str = "cf") -> dict:
        limit = max(1, min(limit, 2000))
        stats_path = self._index_dir / "anchor_stats.json"
        if not stats_path.exists():
            return {"anchors": [], "doc_count": 0, "unique_anchors": 0}

        try:
            with open(stats_path, "r", encoding="utf-8") as _f:
                stats = json.load(_f)
        except (OSError, json.JSONDecodeError) as exc:
            raise HTTPException(500, f"Could not read anchor stats: {exc}")

        doc_count = stats.get("doc_count", 0)
        unique_anchors = stats.get("unique_anchors", 0)
        cf_map: Dict[str, int] = stats.get("cf", {})
        df_map: Dict[str, int] = stats.get("df", {})
        sort_key = (lambda t: df_map.get(t, 0)) if sort == "df" else (lambda t: cf_map.get(t, 0))
        top_tokens = sorted(cf_map.keys(), key=sort_key, reverse=True)[:limit]
        anchors = [{"anchor": t, "cf": cf_map.get(t, 0), "df": df_map.get(t, 0)} for t in top_tokens]
        return {"anchors": anchors, "doc_count": doc_count, "unique_anchors": unique_anchors}

    async def delete_receipt(self, receipt_id: str) -> dict:
        """Delete a document from the data lake.

        Removes the receipt directory and cleans search indexes.
        Does NOT touch evidence.bin, lexicon, or any other document.
        """
        if not receipt_id:
            raise HTTPException(400, "receipt_id is required")

        _validate_path_id(receipt_id, "receipt_id")

        # Find the receipt directory across all corpora
        receipt_dir = None
        corpus_id = None
        for cid, rdir in iter_receipt_dirs(base_dir=self._chunks_dir):
            if rdir.name == receipt_id:
                receipt_dir = rdir
                corpus_id = cid
                break

        if receipt_dir is None or not receipt_dir.exists():
            raise HTTPException(404, f"Receipt not found: {receipt_id}")

        # Safety: ensure path is within chunks dir
        _validate_path_within(receipt_dir, self._chunks_dir, "receipt_dir")

        # Count chunks before deletion for reporting
        chunks_removed = 0
        chunk_ids = []
        chunks_file = receipt_dir / "chunks.jsonl"
        if chunks_file.exists():
            try:
                with open(chunks_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            chunks_removed += 1
                            try:
                                chunk_ids.append(json.loads(line).get("chunk_id", ""))
                            except json.JSONDecodeError:
                                pass
            except OSError:
                pass

        # Journal: mark as deleting
        journal_path = self._index_dir / "delete_journal.jsonl"
        import datetime
        journal_entry = json.dumps({
            "receipt_id": receipt_id,
            "corpus_id": corpus_id,
            "status": "deleting",
            "chunks": chunks_removed,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })
        try:
            with open(journal_path, "a", encoding="utf-8") as jf:
                jf.write(journal_entry + "\n")
        except OSError as e:
            logger.warning("Could not write delete journal: %s", e)

        # Step 1: Remove receipt directory
        try:
            shutil.rmtree(receipt_dir)
            logger.info("Deleted receipt directory: %s", receipt_dir)
        except OSError as e:
            raise HTTPException(500, f"Failed to remove receipt directory: {e}")

        # Step 2: Clean BM25 search index
        if chunk_ids:
            try:
                from core.lakespeak.index.bm25 import BM25Index
                bm25 = BM25Index()
                bm25.remove_chunks(chunk_ids)
                bm25.save()
                logger.info("BM25 index cleaned: %d chunk_ids removed", len(chunk_ids))
            except Exception as e:
                logger.warning("BM25 cleanup failed (run /reindex): %s", e)

            # Step 3: Clean dense index
            try:
                from core.lakespeak.index.dense import DenseIndex
                if DenseIndex.is_available():
                    dense = DenseIndex()
                    dense.remove_chunks(chunk_ids)
                    dense.save()
                    logger.info("Dense index cleaned: %d chunk_ids removed", len(chunk_ids))
            except Exception as e:
                logger.warning("Dense index cleanup skipped: %s", e)

        # Step 4: Remove citation records tied to this receipt
        try:
            from security.data_paths import CITATION_DB_PATH
            import sqlite3
            if CITATION_DB_PATH.exists():
                conn = sqlite3.connect(str(CITATION_DB_PATH))
                cur = conn.cursor()
                cur.execute("DELETE FROM citations WHERE coord LIKE ?", (f"INGEST:{receipt_id}%",))
                deleted_cites = cur.rowcount
                conn.commit()
                conn.close()
                if deleted_cites:
                    logger.info("Removed %d citation records for receipt %s", deleted_cites, receipt_id)
        except Exception as e:
            logger.warning("Citation cleanup failed: %s", e)

        # Journal: mark complete
        complete_entry = json.dumps({
            "receipt_id": receipt_id,
            "status": "deleted",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })
        try:
            with open(journal_path, "a", encoding="utf-8") as jf:
                jf.write(complete_entry + "\n")
        except OSError:
            pass

        return {
            "ok": True,
            "receipt_id": receipt_id,
            "corpus_id": corpus_id,
            "chunks_removed": chunks_removed,
        }
