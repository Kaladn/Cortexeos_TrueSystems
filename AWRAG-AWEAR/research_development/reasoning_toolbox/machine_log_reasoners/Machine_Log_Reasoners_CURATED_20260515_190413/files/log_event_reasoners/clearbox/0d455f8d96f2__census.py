"""Census Index — 6-1-6 adjacency co-occurrence scoring.

No models. No embeddings. Pure positional counts from Lee's 6-1-6 maps.

Census scoring:
  1. During ingest, RelationEdge records capture co-occurrence in 6-1-6 windows:
     source_token + target_token + distance (1-6) + direction (before/after)
  2. Census builds a global adjacency map from all chunk relations.
  3. At query time:
     - Tokenize query
     - For each query token, get its adjacency neighborhood
     - For each chunk, count how many chunk tokens appear in the neighborhood
     - Weight by position: L1/R1=6, L2/R2=5, L3/R3=4, L4/R4=3, L5/R5=2, L6/R6=1
     - Apply IDF de-weighting: 1.0 / (1.0 + log(1 + token_freq))
     - Sum = census score

Weight: 0.60 (confirmed, locked). BM25 gets 0.40.
"""

from __future__ import annotations

import json
import logging
import math
import pickle
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from lakespeak.schemas import ScoredChunk
from lakespeak.text.normalize import tokenize as _canonical_tokenize

logger = logging.getLogger(__name__)

# Position weights: distance 1 = weight 6, distance 6 = weight 1
POSITION_WEIGHT = {1: 6, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1}


class CensusIndex:
    """6-1-6 adjacency co-occurrence scorer.

    Replaces DenseIndex. No sentence-transformers. No FAISS. No models.
    Pure positional co-occurrence counts from the 6-1-6 adjacency map.
    """

    def __init__(self, index_dir: Path = None):
        if index_dir is None:
            try:
                from security.data_paths import LAKESPEAK_CENSUS_DIR
                index_dir = LAKESPEAK_CENSUS_DIR
            except ImportError:
                index_dir = Path("lakespeak_census")

        self._index_dir = index_dir

        # Global adjacency map: {token -> {neighbor_token -> weighted_count}}
        # Weighted count = sum of (co_occurrence_count * position_weight) across all positions
        self._adjacency: Dict[str, Dict[str, float]] = {}

        # Per-chunk token sets: {chunk_id -> set of tokens in that chunk}
        self._chunk_tokens: Dict[str, Set[str]] = {}

        # Token frequencies across all chunks (for IDF)
        self._token_freq: Dict[str, int] = defaultdict(int)

        # Chunk metadata
        self._chunk_ids: List[str] = []
        self._receipt_map: Dict[str, str] = {}
        self._loaded = False

    @property
    def index_path(self) -> Path:
        return self._index_dir / "census.pkl"

    @property
    def metadata_path(self) -> Path:
        return self._index_dir / "metadata.json"

    @classmethod
    def is_available(cls) -> bool:
        """Census is always available — no external deps."""
        return True

    # ── Building ─────────────────────────────────────────────

    def build(
        self,
        chunk_texts: List[str],
        chunk_ids: List[str],
        receipt_ids: List[str],
        chunk_relations: Optional[Dict[str, List[dict]]] = None,
    ) -> None:
        """Build census index from chunk texts and their 6-1-6 relations.

        Args:
            chunk_texts: Raw text for each chunk.
            chunk_ids: Parallel list of chunk IDs.
            receipt_ids: Parallel list of receipt IDs.
            chunk_relations: {chunk_id: [RelationEdge-like dicts]} from ingest.
                Each dict has: source_token, target_token, distance, direction,
                co_occurrence_count.
        """
        if len(chunk_texts) != len(chunk_ids) or len(chunk_texts) != len(receipt_ids):
            raise ValueError("chunk_texts, chunk_ids, and receipt_ids must have same length")

        self._adjacency = defaultdict(lambda: defaultdict(float))
        self._chunk_tokens = {}
        self._token_freq = defaultdict(int)
        self._chunk_ids = list(chunk_ids)
        self._receipt_map = {cid: rid for cid, rid in zip(chunk_ids, receipt_ids)}

        # Build per-chunk token sets and global token frequency
        for i, (text, cid) in enumerate(zip(chunk_texts, chunk_ids)):
            tokens = set(_canonical_tokenize(text))
            self._chunk_tokens[cid] = tokens
            for token in tokens:
                self._token_freq[token] += 1

        # Build adjacency map from relations
        if chunk_relations:
            for cid, relations in chunk_relations.items():
                for rel in relations:
                    src = rel.get("source_token", "")
                    tgt = rel.get("target_token", "")
                    dist = rel.get("distance", 1)
                    count = rel.get("co_occurrence_count", 1)

                    if not src or not tgt:
                        continue

                    weight = POSITION_WEIGHT.get(dist, 1)
                    weighted = count * weight

                    # Bidirectional: if A sees B at distance 2, B also relates to A
                    self._adjacency[src][tgt] += weighted
                    self._adjacency[tgt][src] += weighted

        # If no relations provided, build adjacency from raw text windows
        if not chunk_relations:
            self._build_adjacency_from_texts(chunk_texts, chunk_ids)

        # Convert defaultdicts to regular dicts for pickling
        self._adjacency = {k: dict(v) for k, v in self._adjacency.items()}
        self._token_freq = dict(self._token_freq)
        self._loaded = True

        logger.info(
            "Built census index: %d chunks, %d tokens in adjacency, %d total token types",
            len(chunk_ids), len(self._adjacency), len(self._token_freq),
        )

    def _build_adjacency_from_texts(
        self,
        chunk_texts: List[str],
        chunk_ids: List[str],
    ) -> None:
        """Build 6-1-6 adjacency directly from chunk texts when no relations exist.

        Slides a 13-token window (6-1-6) across each chunk's tokens.
        Each co-occurrence within the window creates an adjacency entry.
        """
        for text, cid in zip(chunk_texts, chunk_ids):
            tokens = _canonical_tokenize(text)
            n = len(tokens)

            for anchor_pos in range(n):
                anchor = tokens[anchor_pos]

                # Look at positions 1-6 before and after
                for dist in range(1, 7):
                    weight = POSITION_WEIGHT[dist]

                    # Before (L1..L6)
                    before_pos = anchor_pos - dist
                    if before_pos >= 0:
                        neighbor = tokens[before_pos]
                        self._adjacency[anchor][neighbor] += weight
                        self._adjacency[neighbor][anchor] += weight

                    # After (R1..R6)
                    after_pos = anchor_pos + dist
                    if after_pos < n:
                        neighbor = tokens[after_pos]
                        self._adjacency[anchor][neighbor] += weight
                        self._adjacency[neighbor][anchor] += weight

    def save(self) -> None:
        """Persist census index to disk."""
        if not self._loaded:
            raise RuntimeError("Cannot save: census index not built")

        self._index_dir.mkdir(parents=True, exist_ok=True)

        data = {
            "adjacency": self._adjacency,
            "chunk_tokens": {cid: list(tokens) for cid, tokens in self._chunk_tokens.items()},
            "token_freq": self._token_freq,
            "chunk_ids": self._chunk_ids,
            "receipt_map": self._receipt_map,
        }
        with open(self.index_path, "wb") as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

        metadata = {
            "doc_count": len(self._chunk_ids),
            "adjacency_tokens": len(self._adjacency),
            "total_token_types": len(self._token_freq),
        }
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        logger.info("Saved census index to %s", self._index_dir)

    # ── Loading ──────────────────────────────────────────────

    def _ensure_loaded(self) -> bool:
        """Lazy-load census index from disk."""
        if self._loaded:
            return True

        if not self.index_path.exists():
            return False

        try:
            with open(self.index_path, "rb") as f:
                data = pickle.load(f)

            self._adjacency = data["adjacency"]
            self._chunk_tokens = {
                cid: set(tokens) for cid, tokens in data["chunk_tokens"].items()
            }
            self._token_freq = data["token_freq"]
            self._chunk_ids = data["chunk_ids"]
            self._receipt_map = data["receipt_map"]
            self._loaded = True

            logger.info("Loaded census index: %d chunks", len(self._chunk_ids))
            return True

        except Exception as e:
            logger.error("Failed to load census index: %s", e)
            return False

    # ── Querying ─────────────────────────────────────────────

    def query(self, query_text: str, topk: int = 20) -> List[ScoredChunk]:
        """Score chunks by 6-1-6 adjacency co-occurrence with query tokens.

        Algorithm:
          For each query token q:
            Get adjacency[q] = {neighbor -> weighted_count}
            For each chunk c:
              intersection = chunk_tokens[c] ∩ adjacency[q].keys()
              For each token t in intersection:
                score += adjacency[q][t] * idf_weight(t)
          Normalize scores, return top-K.
        """
        if not self._ensure_loaded():
            return []

        query_tokens = _canonical_tokenize(query_text)
        if not query_tokens:
            return []

        # Score each chunk
        chunk_scores: Dict[str, float] = defaultdict(float)

        for q_token in query_tokens:
            neighbors = self._adjacency.get(q_token, {})
            if not neighbors:
                continue

            idf_q = self._idf_weight(q_token)

            for cid, c_tokens in self._chunk_tokens.items():
                # Intersection of chunk tokens with query token's neighborhood
                overlap = c_tokens & neighbors.keys()
                if not overlap:
                    continue

                for t in overlap:
                    idf_t = self._idf_weight(t)
                    # Score = adjacency strength * IDF of both query and target token
                    chunk_scores[cid] += neighbors[t] * idf_q * idf_t

        if not chunk_scores:
            return []

        # Sort by score descending
        sorted_chunks = sorted(chunk_scores.items(), key=lambda x: -x[1])
        top = sorted_chunks[:topk]

        # Normalize to [0, 1]
        max_score = top[0][1] if top else 1.0
        if max_score <= 0:
            max_score = 1.0

        results: List[ScoredChunk] = []
        for cid, raw_score in top:
            if raw_score <= 0:
                continue
            results.append(ScoredChunk(
                chunk_id=cid,
                receipt_id=self._receipt_map.get(cid, ""),
                score=raw_score / max_score,
                source="census",
                bm25_score=0.0,
                census_score=raw_score / max_score,
                anchor_score=0.0,
            ))

        return results

    def _idf_weight(self, token: str) -> float:
        """IDF de-weighting: discounts high-frequency tokens.

        Formula: 1.0 / (1.0 + log(1 + token_freq))
        From SWAP_2 pseudocode, confirmed by Lee.
        """
        freq = self._token_freq.get(token, 0)
        return 1.0 / (1.0 + math.log(1 + freq))

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
        chunk_relations: Optional[Dict[str, List[dict]]] = None,
    ) -> None:
        """Add new chunks by rebuilding. Census index is small enough to rebuild."""
        existing_texts: List[str] = []
        if self._ensure_loaded():
            existing_texts = self._load_all_chunk_texts()

        all_texts = existing_texts + list(chunk_texts)
        all_ids = list(self._chunk_ids) + list(chunk_ids)
        all_receipts = (
            [self._receipt_map.get(cid, "") for cid in self._chunk_ids]
            + list(receipt_ids)
        )

        # Merge relations
        merged_relations = {}
        if chunk_relations:
            merged_relations.update(chunk_relations)

        self.build(all_texts, all_ids, all_receipts, merged_relations or None)

    def _load_all_chunk_texts(self) -> List[str]:
        """Load all chunk texts from the chunk store for rebuild."""
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
                texts.append(loaded_receipts.get(receipt_id, {}).get(chunk_id, ""))
        except Exception as e:
            logger.error("Failed to load chunk texts for census rebuild: %s", e)
            texts = [""] * len(self._chunk_ids)
        return texts
