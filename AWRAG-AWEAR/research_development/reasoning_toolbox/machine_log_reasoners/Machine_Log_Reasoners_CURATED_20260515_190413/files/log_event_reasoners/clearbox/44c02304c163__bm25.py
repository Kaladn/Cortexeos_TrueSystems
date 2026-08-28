"""BM25 Sparse Index — lazy-loaded, pickle-persisted.

Primary retrieval index for LakeSpeak Phase A (always available).
Heavy dependency (rank_bm25) is lazy-imported on first query/build.
"""

from __future__ import annotations

import io
import json
import logging
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ── Safe Pickle Deserialization ───────────────────────────────
# Restrict unpickling to only the modules BM25Okapi actually needs,
# preventing arbitrary code execution from tampered index files.

_PICKLE_ALLOWED_MODULES = frozenset({
    "rank_bm25",
    "rank_bm25.rank_bm25",
    "numpy",
    "numpy.core",
    "numpy.core.multiarray",
    "numpy.core.numeric",
    "numpy.core._multiarray_umath",
    "numpy._core",
    "numpy._core.multiarray",
    "numpy._core._multiarray_umath",
    "builtins",
    "collections",
    "copyreg",
})


class _RestrictedUnpickler(pickle.Unpickler):
    """Unpickler that only allows BM25/numpy/builtins classes."""

    def find_class(self, module: str, name: str):
        if module not in _PICKLE_ALLOWED_MODULES:
            raise pickle.UnpicklingError(
                f"Blocked unsafe pickle class: {module}.{name}"
            )
        return super().find_class(module, name)


def _safe_pickle_load(f) -> object:
    """Load pickle with restricted class allowlist."""
    return _RestrictedUnpickler(f).load()

from ..schemas import ScoredChunk
from ..storage import DEFAULT_CORPUS_ID
from ..text.normalize import tokenize as _canonical_tokenize

logger = logging.getLogger(__name__)


class BM25Index:
    """BM25Okapi-based sparse retrieval index.

    Lazy-loads rank_bm25 on first use. Persists corpus as pickle.
    Stores metadata (chunk_id -> receipt_id mapping, build timestamp).
    """

    def __init__(self, index_dir: Path = None):
        if index_dir is None:
            try:
                from security.data_paths import LAKESPEAK_BM25_DIR
                index_dir = LAKESPEAK_BM25_DIR
            except ImportError:
                index_dir = Path("lakespeak_bm25")

        self._index_dir = index_dir
        self._bm25 = None               # Lazy: BM25Okapi instance
        self._chunk_ids: List[str] = []  # Parallel to corpus: chunk_ids[i] = chunk_id
        self._receipt_map: Dict[str, str] = {}  # chunk_id -> receipt_id
        self._corpus_map: Dict[str, str] = {}  # chunk_id -> corpus_id
        self._loaded = False

    @property
    def corpus_path(self) -> Path:
        return self._index_dir / "corpus.pkl"

    @property
    def metadata_path(self) -> Path:
        return self._index_dir / "metadata.json"

    # ── Building ─────────────────────────────────────────────

    def build(
        self,
        chunk_texts: List[str],
        chunk_ids: List[str],
        receipt_ids: List[str],
        corpus_ids: Optional[List[str]] = None,
    ) -> None:
        """Build BM25 index from chunk texts.

        Args:
            chunk_texts: Raw text for each chunk.
            chunk_ids: Parallel list of chunk IDs.
            receipt_ids: Parallel list of receipt IDs.
        """
        from rank_bm25 import BM25Okapi  # Lazy import

        if len(chunk_texts) != len(chunk_ids) or len(chunk_texts) != len(receipt_ids):
            raise ValueError("chunk_texts, chunk_ids, and receipt_ids must have same length")
        if corpus_ids is not None and len(chunk_texts) != len(corpus_ids):
            raise ValueError("chunk_texts, chunk_ids, receipt_ids, and corpus_ids must have same length")

        # Tokenize for BM25 (simple whitespace + lowercase)
        tokenized = [self._tokenize(t) for t in chunk_texts]

        self._bm25 = BM25Okapi(tokenized)
        self._chunk_ids = list(chunk_ids)
        self._receipt_map = {cid: rid for cid, rid in zip(chunk_ids, receipt_ids)}
        if corpus_ids is None:
            corpus_ids = [DEFAULT_CORPUS_ID] * len(chunk_ids)
        self._corpus_map = {cid: corpus_ids[i] for i, cid in enumerate(chunk_ids)}
        self._loaded = True

        logger.info("Built BM25 index with %d documents", len(chunk_texts))

    def save(self) -> None:
        """Persist BM25 index to disk."""
        if self._bm25 is None:
            raise RuntimeError("Cannot save: BM25 index not built")

        self._index_dir.mkdir(parents=True, exist_ok=True)

        # Save BM25 corpus
        with open(self.corpus_path, "wb") as f:
            pickle.dump(self._bm25, f, protocol=pickle.HIGHEST_PROTOCOL)

        # Save metadata
        metadata = {
            "doc_count": len(self._chunk_ids),
            "chunk_ids": self._chunk_ids,
            "receipt_map": self._receipt_map,
            "corpus_map": self._corpus_map,
        }
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        logger.info("Saved BM25 index to %s", self._index_dir)

    # ── Loading ──────────────────────────────────────────────

    def _ensure_loaded(self) -> bool:
        """Lazy-load BM25 from disk. Returns True if loaded."""
        if self._loaded:
            return True

        if not self.corpus_path.exists() or not self.metadata_path.exists():
            return False

        try:
            from rank_bm25 import BM25Okapi  # noqa: F401 — needed for unpickle

            with open(self.corpus_path, "rb") as f:
                self._bm25 = _safe_pickle_load(f)

            with open(self.metadata_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            self._chunk_ids = metadata.get("chunk_ids", [])
            self._receipt_map = metadata.get("receipt_map", {})
            self._corpus_map = metadata.get("corpus_map", {})
            self._loaded = True
            logger.info("Loaded BM25 index: %d documents", len(self._chunk_ids))
            return True

        except Exception as e:
            logger.error("Failed to load BM25 index: %s", e)
            return False

    # ── Querying ─────────────────────────────────────────────

    def query(
        self,
        query_text: str,
        topk: int = 20,
        corpora: Optional[set[str]] = None,
    ) -> List[ScoredChunk]:
        """Query the BM25 index.

        Args:
            query_text: Raw query string.
            topk: Maximum number of results.

        Returns:
            List of ScoredChunk sorted by score DESC.
            Empty list if index not built/loaded.
        """
        if not self._ensure_loaded():
            return []

        tokens = self._tokenize(query_text)
        if not tokens:
            return []

        scores = self._bm25.get_scores(tokens)

        # Get top-k indices
        indexed_scores = []
        for idx, score in enumerate(scores):
            chunk_id = self._chunk_ids[idx]
            corpus_id = self._corpus_map.get(chunk_id) or DEFAULT_CORPUS_ID
            if corpora and corpus_id not in corpora:
                continue
            indexed_scores.append((idx, score))
        indexed_scores.sort(key=lambda x: -x[1])
        top = indexed_scores[:topk]

        results: List[ScoredChunk] = []
        for idx, score in top:
            chunk_id = self._chunk_ids[idx]
            results.append(ScoredChunk(
                chunk_id=chunk_id,
                receipt_id=self._receipt_map.get(chunk_id, ""),
                corpus_id=self._corpus_map.get(chunk_id) or DEFAULT_CORPUS_ID,
                score=score,
                source="bm25",
                bm25_score=score,
                dense_score=0.0,
                anchor_score=0.0,
            ))

        return results

    @property
    def doc_count(self) -> int:
        """Number of documents in the index."""
        if self._ensure_loaded():
            return len(self._chunk_ids)
        return 0

    # ── Tokenizer ────────────────────────────────────────────

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Canonical tokenizer — delegates to lakespeak.text.normalize."""
        return _canonical_tokenize(text)

    # ── Incremental Update ───────────────────────────────────

    def add_chunks(
        self,
        chunk_texts: List[str],
        chunk_ids: List[str],
        receipt_ids: List[str],
        corpus_ids: Optional[List[str]] = None,
    ) -> None:
        """Add new chunks to existing index by rebuilding.

        BM25Okapi doesn't support incremental add, so we rebuild
        from the full corpus. For large indices, this should be
        batched during ingest and saved once.
        """
        # Load existing corpus from metadata
        existing_texts: List[str] = []
        if self._ensure_loaded() and self._bm25 is not None:
            # We need the original texts — stored separately
            chunks_store = self._load_all_chunk_texts()
            existing_texts = chunks_store

        # Merge
        all_texts = existing_texts + list(chunk_texts)
        all_ids = list(self._chunk_ids) + list(chunk_ids)
        all_receipts = [self._receipt_map.get(cid, "") for cid in self._chunk_ids] + list(receipt_ids)
        if corpus_ids is None:
            corpus_ids = [DEFAULT_CORPUS_ID] * len(chunk_ids)
        all_corpora = [self._corpus_map.get(cid) or DEFAULT_CORPUS_ID for cid in self._chunk_ids] + list(corpus_ids)

        self.build(all_texts, all_ids, all_receipts, all_corpora)

    def _load_all_chunk_texts(self) -> List[str]:
        """Load all chunk texts from the chunk store for rebuild."""
        texts: List[str] = []
        try:
            from ..storage import resolve_receipt_dir
            for chunk_id in self._chunk_ids:
                receipt_id = self._receipt_map.get(chunk_id, "")
                corpus_id = self._corpus_map.get(chunk_id) or DEFAULT_CORPUS_ID
                if not receipt_id:
                    texts.append("")
                    continue
                resolved = resolve_receipt_dir(receipt_id, corpus_id=corpus_id)
                chunks_file = resolved[1] / "chunks.jsonl" if resolved else None
                if chunks_file and chunks_file.exists():
                    for line in chunks_file.read_text(encoding="utf-8").splitlines():
                        if not line.strip():
                            continue
                        chunk = json.loads(line)
                        if chunk.get("chunk_id") == chunk_id:
                            texts.append(chunk.get("text", ""))
                            break
                    else:
                        texts.append("")
                else:
                    texts.append("")
        except Exception as e:
            logger.error("Failed to load chunk texts for rebuild: %s", e)
            # Return empty texts as fallback
            texts = [""] * len(self._chunk_ids)
        return texts
