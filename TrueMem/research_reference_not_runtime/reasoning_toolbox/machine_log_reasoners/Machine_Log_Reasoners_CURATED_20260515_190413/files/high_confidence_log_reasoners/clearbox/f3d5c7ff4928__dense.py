"""Dense Embeddings Index — optional, graceful degradation.

Uses sentence-transformers + faiss-cpu for dense vector retrieval.
Both are lazy-imported: if unavailable, system runs sparse-only (BM25).
No error, no crash, just fewer retrieval signals.

Model: all-MiniLM-L6-v2 (22M params, 384-dim, fast on CPU).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

from lakespeak.schemas import ScoredChunk

logger = logging.getLogger(__name__)


class DenseIndex:
    """FAISS-based dense vector index with sentence-transformers embeddings.

    Lazy-loads all heavy deps. Gracefully returns empty results if deps
    are missing — system falls back to BM25-only mode.
    """

    _AVAILABLE: Optional[bool] = None

    def __init__(self, index_dir: Path = None, model_name: str = None):
        if index_dir is None:
            try:
                from security.data_paths import LAKESPEAK_DENSE_DIR
                index_dir = LAKESPEAK_DENSE_DIR
            except ImportError:
                index_dir = Path("lakespeak_dense")

        if model_name is None:
            try:
                from lakespeak.config import load_config
                cfg = load_config()
                model_name = cfg.get("dense_model", "all-MiniLM-L6-v2")
            except Exception:
                model_name = "all-MiniLM-L6-v2"

        self._index_dir = index_dir
        self._model_name = model_name
        self._model = None           # Lazy: SentenceTransformer
        self._index = None           # Lazy: faiss.IndexFlatIP
        self._chunk_ids: List[str] = []
        self._receipt_map: Dict[str, str] = {}
        self._loaded = False

    @classmethod
    def is_available(cls) -> bool:
        """Check if dense index deps are installed."""
        if cls._AVAILABLE is None:
            try:
                import sentence_transformers  # noqa: F401
                import faiss  # noqa: F401
                cls._AVAILABLE = True
            except ImportError:
                cls._AVAILABLE = False
        return cls._AVAILABLE

    @property
    def index_path(self) -> Path:
        return self._index_dir / "index.faiss"

    @property
    def id_map_path(self) -> Path:
        return self._index_dir / "id_map.json"

    @property
    def metadata_path(self) -> Path:
        return self._index_dir / "metadata.json"

    # ── Model Loading ────────────────────────────────────────

    def _ensure_model(self):
        """Lazy-load the sentence transformer model."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
        return self._model

    # ── Building ─────────────────────────────────────────────

    def build(
        self,
        chunk_texts: List[str],
        chunk_ids: List[str],
        receipt_ids: List[str],
    ) -> None:
        """Build dense index from chunk texts.

        Encodes all texts, normalizes vectors, creates FAISS IndexFlatIP.
        """
        import faiss
        import numpy as np

        if len(chunk_texts) != len(chunk_ids) or len(chunk_texts) != len(receipt_ids):
            raise ValueError("chunk_texts, chunk_ids, and receipt_ids must have same length")

        model = self._ensure_model()

        # Encode (normalize for cosine similarity via inner product)
        embeddings = model.encode(chunk_texts, show_progress_bar=False, normalize_embeddings=True)
        embeddings = np.array(embeddings, dtype=np.float32)

        # Create index
        dim = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(dim)
        self._index.add(embeddings)

        self._chunk_ids = list(chunk_ids)
        self._receipt_map = {cid: rid for cid, rid in zip(chunk_ids, receipt_ids)}
        self._loaded = True

        logger.info("Built dense index: %d vectors, %d dimensions", len(chunk_texts), dim)

    def save(self) -> None:
        """Persist dense index to disk."""
        import faiss

        if self._index is None:
            raise RuntimeError("Cannot save: dense index not built")

        self._index_dir.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self._index, str(self.index_path))

        id_map = {
            "chunk_ids": self._chunk_ids,
            "receipt_map": self._receipt_map,
        }
        with open(self.id_map_path, "w", encoding="utf-8") as f:
            json.dump(id_map, f, ensure_ascii=False, indent=2)

        metadata = {
            "model": self._model_name,
            "doc_count": len(self._chunk_ids),
            "dim": self._index.d,
        }
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        logger.info("Saved dense index to %s", self._index_dir)

    # ── Loading ──────────────────────────────────────────────

    def _ensure_loaded(self) -> bool:
        """Lazy-load dense index from disk."""
        if self._loaded:
            return True

        if not self.index_path.exists() or not self.id_map_path.exists():
            return False

        try:
            import faiss

            self._index = faiss.read_index(str(self.index_path))

            with open(self.id_map_path, "r", encoding="utf-8") as f:
                id_map = json.load(f)

            self._chunk_ids = id_map.get("chunk_ids", [])
            self._receipt_map = id_map.get("receipt_map", {})
            self._loaded = True
            logger.info("Loaded dense index: %d vectors", len(self._chunk_ids))
            return True

        except Exception as e:
            logger.error("Failed to load dense index: %s", e)
            return False

    # ── Querying ─────────────────────────────────────────────

    def query(self, query_text: str, topk: int = 20) -> List[ScoredChunk]:
        """Query the dense index.

        Returns empty list if index not built/loaded or deps unavailable.
        """
        if not self.is_available():
            return []

        if not self._ensure_loaded():
            return []

        import numpy as np

        model = self._ensure_model()
        q_emb = model.encode([query_text], normalize_embeddings=True)
        q_emb = np.array(q_emb, dtype=np.float32)

        k = min(topk, len(self._chunk_ids))
        if k == 0:
            return []

        scores, indices = self._index.search(q_emb, k)

        results: List[ScoredChunk] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self._chunk_ids):
                continue
            if score <= 0:
                continue
            chunk_id = self._chunk_ids[idx]
            results.append(ScoredChunk(
                chunk_id=chunk_id,
                receipt_id=self._receipt_map.get(chunk_id, ""),
                score=float(score),
                source="dense",
                bm25_score=0.0,
                dense_score=float(score),
                anchor_score=0.0,
            ))

        return results

    @property
    def doc_count(self) -> int:
        if self._ensure_loaded():
            return len(self._chunk_ids)
        return 0

    # ── Incremental Update ───────────────────────────────────

    def add_chunks(
        self,
        chunk_texts: List[str],
        chunk_ids: List[str],
        receipt_ids: List[str],
    ) -> None:
        """Add new chunks by rebuilding from all stored chunk texts.

        FAISS IndexFlatIP doesn't support efficient incremental add
        with consistent IDs, so we rebuild from the full corpus.
        """
        existing_texts: List[str] = []
        if self._ensure_loaded() and self._index is not None:
            existing_texts = self._load_all_chunk_texts()

        all_texts = existing_texts + list(chunk_texts)
        all_ids = list(self._chunk_ids) + list(chunk_ids)
        all_receipts = [self._receipt_map.get(cid, "") for cid in self._chunk_ids] + list(receipt_ids)

        self.build(all_texts, all_ids, all_receipts)

    def _load_all_chunk_texts(self) -> List[str]:
        """Load all chunk texts from the chunk store for rebuild."""
        import json
        texts: List[str] = []
        try:
            from security.data_paths import LAKESPEAK_CHUNKS_DIR
            loaded_receipts: Dict[str, Dict[str, str]] = {}
            for chunk_id in self._chunk_ids:
                receipt_id = self._receipt_map.get(chunk_id, "")
                if not receipt_id:
                    texts.append("")
                    continue
                if receipt_id not in loaded_receipts:
                    chunks_file = LAKESPEAK_CHUNKS_DIR / receipt_id / "chunks.jsonl"
                    loaded_receipts[receipt_id] = {}
                    if chunks_file.exists():
                        for line in chunks_file.read_text(encoding="utf-8").splitlines():
                            if not line.strip():
                                continue
                            chunk = json.loads(line)
                            loaded_receipts[receipt_id][chunk.get("chunk_id", "")] = chunk.get("text", "")
                texts.append(loaded_receipts[receipt_id].get(chunk_id, ""))
        except Exception as e:
            logger.error("Failed to load chunk texts for dense rebuild: %s", e)
            texts = [""] * len(self._chunk_ids)
        return texts
