"""6-1-6 Reasoning Engine V3 — full cloud reasoning, no shortcuts.

Reads ALL 12 positions. Classifies query intent. Compares clouds.
Extracts predicates from structural position, not fake verb lists.
Multi-anchor support. Bidirectional reasoning. Honest confidence.

Reads from:
  - Evidence store (cumulative 6-1-6 counts, all 12 positions)
  - LakeSpeak data lake (chunks, anchors — read-only)
  - Lexicon bridge (word ↔ hex resolution)

Does NOT: save anything, use LLM, modify any store.
"""
from __future__ import annotations

import asyncio
import logging
import math
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

LOGGER = logging.getLogger("ClearboxAI.reasoning_616")

# ── Stop words (structural noise, not content) ────────────────


# ── Position weight: closer = heavier ─────────────────────────

def _pos_weight(position: int) -> float:
    """Weight by proximity: position ±1 = 1.0, ±6 = 0.167."""
    return (7 - abs(position)) / 6.0


# ── Query intent classification ───────────────────────────────

QUERY_TYPES = {
    "what_does":    re.compile(r"what\s+does\s+(\w+)\s+do", re.I),
    "what_causes":  re.compile(r"what\s+causes?\s+(\w+)", re.I),
    "caused_by":    re.compile(r"(\w+)\s+(?:is\s+)?caused\s+by", re.I),
    "how_relate":   re.compile(r"how\s+(?:does?\s+|do\s+)?(\w+)\s+(?:and\s+|&\s*)(\w+)\s+relat", re.I),
    "difference":   re.compile(r"(?:difference|differ)\s+(?:between\s+)?(\w+)\s+(?:and\s+|&\s*)(\w+)", re.I),
    "what_is":      re.compile(r"what\s+is\s+(\w+)", re.I),
    "describe":     re.compile(r"(?:describe|explain|tell\s+me\s+about)\s+(\w+)", re.I),
}


@dataclass
class QueryIntent:
    qtype: str          # what_does, what_causes, how_relate, difference, describe, unknown
    anchors: List[str]  # resolved anchor words
    raw: str            # original question


def _classify_query(question: str) -> QueryIntent:
    """Classify query into intent type and extract anchor words."""
    for qtype, pattern in QUERY_TYPES.items():
        m = pattern.search(question)
        if m:
            anchors = [g.lower() for g in m.groups() if g]
            return QueryIntent(qtype=qtype, anchors=anchors, raw=question)

    # Fallback: extract content words as anchors
    words = re.findall(r"[a-z0-9_\-']+", question.lower())
    anchors = [w for w in words]
    return QueryIntent(qtype="describe", anchors=anchors[:3], raw=question)


# ── Cloud reading (FULL 12 positions) ─────────────────────────

@dataclass
class CloudEntry:
    word: str
    hex_addr: str
    count: int
    position: int
    weight: float       # count * pos_weight


@dataclass
class AnchorCloud:
    """Full 12-position context cloud for one anchor."""
    anchor: str
    hex_addr: str
    total_count: int
    roots: Dict[int, List[CloudEntry]]      # positions -6..-1
    branches: Dict[int, List[CloudEntry]]    # positions +1..+6
    all_neighbors: Dict[str, float]          # word → total weighted count across all positions

    @property
    def root_words(self) -> Set[str]:
        return {e.word for entries in self.roots.values() for e in entries}

    @property
    def branch_words(self) -> Set[str]:
        return {e.word for entries in self.branches.values() for e in entries}

    @property
    def all_words(self) -> Set[str]:
        return self.root_words | self.branch_words


# ── Answer frame ──────────────────────────────────────────────

@dataclass
class AnswerFrame:
    subject: str
    intent: str = "unknown"
    clouds: Dict[str, Dict] = field(default_factory=dict)       # anchor → cloud summary
    predicates: List[Dict] = field(default_factory=list)
    causes: List[Dict] = field(default_factory=list)
    relations: Dict = field(default_factory=dict)
    cascade_paths: List[Dict] = field(default_factory=list)
    lake_hits: List[Dict] = field(default_factory=list)
    confidence: Dict = field(default_factory=dict)
    surface_text: str = ""
    trace: Dict = field(default_factory=dict)


# ── Reasoning Service ─────────────────────────────────────────

class ReasoningService:
    """6-1-6 V3 reasoning. Full cloud, all 12 positions, intent-driven."""

    def __init__(self) -> None:
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        try:
            from bridges.evidence_store import get_evidence_store
            return get_evidence_store().count() > 0
        except Exception:
            return False

    # ── Lexicon helpers ───────────────────────────────────────

    def _resolve(self, word: str, bridge) -> Optional[str]:
        if bridge and hasattr(bridge, "word_index"):
            return bridge.word_index.get(word.lower())
        return None

    def _reverse(self, hex_addr: str, bridge) -> Optional[str]:
        if bridge and hasattr(bridge, "entries") and hex_addr in bridge.entries:
            e = bridge.entries[hex_addr]
            return e.word if hasattr(e, "word") else None
        return None

    # ── Cloud builder (reads ALL 12 positions) ────────────────

    def _build_cloud(self, anchor: str, hex_addr: str, bridge) -> Optional[AnchorCloud]:
        """Read full evidence cell, build structured cloud."""
        from bridges.evidence_store import get_evidence_store
        cell = get_evidence_store().read_cell(hex_addr)
        if cell is None:
            return None

        roots: Dict[int, List[CloudEntry]] = {}
        branches: Dict[int, List[CloudEntry]] = {}
        all_neighbors: Dict[str, float] = {}

        for offset, entries in cell.buckets.items():
            bucket: List[CloudEntry] = []
            for e in entries:
                word = self._reverse(e.hex_addr, bridge)
                if not word:
                    continue
                w = e.count * _pos_weight(offset)
                entry = CloudEntry(
                    word=word, hex_addr=e.hex_addr,
                    count=e.count, position=offset, weight=round(w, 3),
                )
                bucket.append(entry)
                all_neighbors[word] = all_neighbors.get(word, 0) + w

            bucket.sort(key=lambda x: x.weight, reverse=True)

            if offset < 0:
                roots[offset] = bucket
            else:
                branches[offset] = bucket

        return AnchorCloud(
            anchor=anchor, hex_addr=hex_addr,
            total_count=cell.total_count,
            roots=roots, branches=branches,
            all_neighbors=all_neighbors,
        )

    # ── Predicate extraction (branches: what does X do?) ──────

    def _extract_predicates(self, cloud: AnchorCloud, top_k: int = 8) -> List[Dict]:
        """Find structurally strong branch words — these are what X DOES.

        Not: "is this a verb?" (fake semantics)
        Instead: "what occupies strong branch positions consistently?"

        Looks at ALL after-positions (+1 through +6), weighted by proximity.
        """
        if not cloud.branches:
            return []

        # Collect all branch entries, score by weight
        candidates: Dict[str, Dict] = {}
        for pos, entries in cloud.branches.items():
            for e in entries:
                key = e.word
                if key not in candidates:
                    candidates[key] = {
                        "word": key, "hex": e.hex_addr,
                        "total_weight": 0, "total_count": 0,
                        "positions": [], "best_position": pos,
                    }
                candidates[key]["total_weight"] += e.weight
                candidates[key]["total_count"] += e.count
                candidates[key]["positions"].append(pos)

        ranked = sorted(candidates.values(), key=lambda x: x["total_weight"], reverse=True)

        predicates = []
        for c in ranked[:top_k]:
            predicates.append({
                "word": c["word"],
                "weight": round(c["total_weight"], 3),
                "count": c["total_count"],
                "positions": sorted(c["positions"]),
                "best_position": min(c["positions"], key=abs),
                "direction": "branch",
            })
        return predicates

    # ── Cause extraction (roots: what causes X?) ──────────────

    def _extract_causes(self, cloud: AnchorCloud, top_k: int = 8) -> List[Dict]:
        """Find structurally strong root words — these are what CAUSES X.

        Reads ALL before-positions (-1 through -6), weighted by proximity.
        """
        if not cloud.roots:
            return []

        candidates: Dict[str, Dict] = {}
        for pos, entries in cloud.roots.items():
            for e in entries:
                key = e.word
                if key not in candidates:
                    candidates[key] = {
                        "word": key, "hex": e.hex_addr,
                        "total_weight": 0, "total_count": 0,
                        "positions": [], "best_position": pos,
                    }
                candidates[key]["total_weight"] += e.weight
                candidates[key]["total_count"] += e.count
                candidates[key]["positions"].append(pos)

        ranked = sorted(candidates.values(), key=lambda x: x["total_weight"], reverse=True)

        causes = []
        for c in ranked[:top_k]:
            causes.append({
                "word": c["word"],
                "weight": round(c["total_weight"], 3),
                "count": c["total_count"],
                "positions": sorted(c["positions"]),
                "best_position": max(c["positions"], key=lambda p: -abs(p)),
                "direction": "root",
            })
        return causes

    # ── Cloud comparison (how do X and Y relate?) ─────────────

    def _compare_clouds(self, cloud_a: AnchorCloud, cloud_b: AnchorCloud) -> Dict:
        """Compare two anchor clouds across all 12 positions.

        Returns: shared neighbors, exclusives, overlap score, directional bias.
        """
        a_all = cloud_a.all_neighbors
        b_all = cloud_b.all_neighbors

        shared_words = set(a_all.keys()) & set(b_all.keys())
        a_exclusive = set(a_all.keys()) - set(b_all.keys())
        b_exclusive = set(b_all.keys()) - set(a_all.keys())

        # Overlap score: sum of min weights for shared words / sum of max weights
        if not shared_words:
            overlap_score = 0.0
        else:
            shared_min_sum = sum(min(a_all[w], b_all[w]) for w in shared_words)
            total_max_sum = sum(max(a_all.get(w, 0), b_all.get(w, 0))
                                for w in set(a_all.keys()) | set(b_all.keys()))
            overlap_score = shared_min_sum / total_max_sum if total_max_sum > 0 else 0.0

        # Directional bias: do they share more roots or branches?
        shared_roots = cloud_a.root_words & cloud_b.root_words
        shared_branches = cloud_a.branch_words & cloud_b.branch_words

        # Top shared by weight
        shared_ranked = sorted(
            shared_words,
            key=lambda w: min(a_all[w], b_all[w]),
            reverse=True,
        )[:10]

        return {
            "overlap_score": round(overlap_score, 4),
            "shared_count": len(shared_words),
            "a_exclusive_count": len(a_exclusive),
            "b_exclusive_count": len(b_exclusive),
            "shared_roots": len(shared_roots),
            "shared_branches": len(shared_branches),
            "top_shared": [
                {"word": w, "a_weight": round(a_all[w], 3), "b_weight": round(b_all[w], 3)}
                for w in shared_ranked
            ],
            "a_exclusive_top": sorted(
                [{"word": w, "weight": round(a_all[w], 3)} for w in a_exclusive],
                key=lambda x: x["weight"], reverse=True,
            )[:5],
            "b_exclusive_top": sorted(
                [{"word": w, "weight": round(b_all[w], 3)} for w in b_exclusive],
                key=lambda x: x["weight"], reverse=True,
            )[:5],
        }

    # ── Cascade (graph traversal with decay) ──────────────────

    def _cascade(self, hex_addr: str, bridge, hops: int = 2, top_k: int = 6, decay: float = 0.75) -> List[Dict]:
        """Walk evidence graph. Every neighbor is a potential anchor."""
        from bridges.evidence_store import get_evidence_store
        store = get_evidence_store()

        paths = []
        visited = {hex_addr}

        cell = store.read_cell(hex_addr)
        if cell is None:
            return []

        # Hop 1
        hop1 = []
        for offset, entries in cell.buckets.items():
            for e in entries:
                word = self._reverse(e.hex_addr, bridge)
                if not word or e.hex_addr in visited:
                    continue
                w = e.count * _pos_weight(offset)
                hop1.append({"word": word, "hex": e.hex_addr, "position": offset,
                             "count": e.count, "weight": round(w, 3), "decayed": round(w, 3)})

        hop1.sort(key=lambda x: x["weight"], reverse=True)
        hop1 = hop1[:top_k]
        paths.extend([{"hop": 1, **h} for h in hop1])

        if hops >= 2:
            for h1 in hop1:
                visited.add(h1["hex"])
                cell2 = store.read_cell(h1["hex"])
                if not cell2:
                    continue
                for offset, entries in cell2.buckets.items():
                    for e in entries[:3]:
                        word = self._reverse(e.hex_addr, bridge)
                        if not word or e.hex_addr in visited:
                            continue
                        w = e.count * _pos_weight(offset)
                        decayed = h1["decayed"] * decay + w
                        paths.append({"hop": 2, "word": word, "hex": e.hex_addr, "via": h1["word"],
                                      "position": offset, "count": e.count,
                                      "weight": round(w, 3), "decayed": round(decayed, 3)})

        paths.sort(key=lambda x: x.get("decayed", 0), reverse=True)
        return paths

    # ── Lake search (read-only) ───────────────────────────────

    def _search_lake(self, query: str, top_k: int = 5) -> List[Dict]:
        try:
            from core.lakespeak.retrieval.query import LakeSpeakEngine
            result = LakeSpeakEngine().query(query, mode="allow_fallback", topk=top_k)
            return [{"snippet": (c.get("snippet") or c.get("text") or "")[:200],
                      "score": round(c.get("score", 0), 4),
                      "receipt": c.get("receipt_id", "")[:20]}
                     for c in (result.citations or [])[:top_k]]
        except Exception:
            return []

    # ── Confidence (honest, not decorative) ───────────────────

    def _compute_confidence(self, cloud: Optional[AnchorCloud], predicates: List, causes: List) -> Dict:
        """Evidence-based confidence, not a normalized score."""
        if cloud is None:
            return {"support": 0, "positions_active": 0, "answerability": 0.0}

        positions_active = len(cloud.roots) + len(cloud.branches)
        total_neighbors = len(cloud.all_neighbors)
        predicate_count = len(predicates)
        cause_count = len(causes)

        # Support: how much evidence exists
        support = cloud.total_count

        # Consistency: are neighbors spread across positions or concentrated?
        position_spread = positions_active / 12.0

        # Answerability: can we actually say something useful?
        has_predicates = predicate_count > 0
        has_causes = cause_count > 0
        has_neighbors = total_neighbors > 3
        answerability = sum([has_predicates, has_causes, has_neighbors, position_spread > 0.3]) / 4.0

        return {
            "support": support,
            "positions_active": positions_active,
            "total_neighbors": total_neighbors,
            "position_spread": round(position_spread, 3),
            "predicate_count": predicate_count,
            "cause_count": cause_count,
            "answerability": round(answerability, 3),
        }

    # ── Main query dispatch ───────────────────────────────────

    async def query(self, question: str, top_k: int = 8) -> AnswerFrame:
        return await asyncio.to_thread(self._query_sync, question, top_k)

    def _query_sync(self, question: str, top_k: int = 8) -> AnswerFrame:
        intent = _classify_query(question)

        # Get bridge
        bridge = None
        try:
            from core.lakespeak.retrieval.query import LakeSpeakEngine
            bridge = LakeSpeakEngine()._ensure_bridge()
        except Exception:
            pass

        # Resolve all anchors to hex
        resolved: List[Tuple[str, str]] = []  # (word, hex)
        for anchor in intent.anchors:
            h = self._resolve(anchor, bridge)
            if h:
                resolved.append((anchor, h))

        trace = {
            "intent": intent.qtype,
            "raw_anchors": intent.anchors,
            "resolved": [(w, h[:12]) for w, h in resolved],
        }

        # No anchors resolved
        if not resolved:
            lake_hits = self._search_lake(question, 5)
            subject = " + ".join(intent.anchors) if intent.anchors else question[:40]
            return AnswerFrame(
                subject=subject, intent=intent.qtype,
                lake_hits=lake_hits,
                surface_text=f"No anchors resolved from '{subject}'. {len(lake_hits)} lake hits.",
                trace=trace,
            )

        # Build clouds for all resolved anchors
        clouds: Dict[str, AnchorCloud] = {}
        cloud_summaries: Dict[str, Dict] = {}
        for word, hex_addr in resolved:
            cloud = self._build_cloud(word, hex_addr, bridge)
            if cloud:
                clouds[word] = cloud
                cloud_summaries[word] = {
                    "total_count": cloud.total_count,
                    "root_positions": len(cloud.roots),
                    "branch_positions": len(cloud.branches),
                    "unique_neighbors": len(cloud.all_neighbors),
                    "top_roots": [{"word": e.word, "weight": e.weight}
                                  for entries in cloud.roots.values()
                                  for e in entries[:2]][:6],
                    "top_branches": [{"word": e.word, "weight": e.weight}
                                     for entries in cloud.branches.values()
                                     for e in entries[:2]][:6],
                }

        if not clouds:
            lake_hits = self._search_lake(question, 5)
            subject = " + ".join(intent.anchors)
            return AnswerFrame(
                subject=subject, intent=intent.qtype,
                lake_hits=lake_hits,
                surface_text=f"Anchors in lexicon but no evidence counts yet.",
                trace=trace, clouds=cloud_summaries,
            )

        # ── Intent-driven reasoning ──────────────────────────

        primary_word, primary_hex = resolved[0]
        primary_cloud = clouds[primary_word]
        subject = " + ".join(w for w, _ in resolved)

        predicates = []
        causes = []
        relations = {}
        cascade_paths = []

        if intent.qtype in ("what_does", "describe", "what_is"):
            predicates = self._extract_predicates(primary_cloud, top_k)
            causes = self._extract_causes(primary_cloud, top_k)
            cascade_paths = self._cascade(primary_hex, bridge, hops=2, top_k=6)

        elif intent.qtype in ("what_causes", "caused_by"):
            causes = self._extract_causes(primary_cloud, top_k)
            predicates = self._extract_predicates(primary_cloud, top_k)

        elif intent.qtype in ("how_relate", "difference"):
            if len(resolved) >= 2:
                word_a, hex_a = resolved[0]
                word_b, hex_b = resolved[1]
                cloud_a = clouds.get(word_a)
                cloud_b = clouds.get(word_b)
                if cloud_a and cloud_b:
                    relations = self._compare_clouds(cloud_a, cloud_b)
                    relations["anchor_a"] = word_a
                    relations["anchor_b"] = word_b
            # Also get predicates for context
            predicates = self._extract_predicates(primary_cloud, top_k)
            causes = self._extract_causes(primary_cloud, top_k)

        else:
            # Unknown — full analysis
            predicates = self._extract_predicates(primary_cloud, top_k)
            causes = self._extract_causes(primary_cloud, top_k)
            cascade_paths = self._cascade(primary_hex, bridge, hops=2, top_k=6)

        lake_hits = self._search_lake(question, 5)
        confidence = self._compute_confidence(primary_cloud, predicates, causes)

        # ── Build surface text ───────────────────────────────

        surface_parts = []

        if intent.qtype in ("what_does", "describe", "what_is"):
            if predicates:
                branch_summary = ", ".join(p["word"] for p in predicates[:4])
                surface_parts.append(f"{primary_word}: branches toward {branch_summary}.")
            if causes:
                root_summary = ", ".join(c["word"] for c in causes[:4])
                surface_parts.append(f"Rooted in: {root_summary}.")

        elif intent.qtype in ("what_causes", "caused_by"):
            if causes:
                root_summary = ", ".join(c["word"] for c in causes[:4])
                surface_parts.append(f"{primary_word} is rooted in: {root_summary}.")
            if predicates:
                branch_summary = ", ".join(p["word"] for p in predicates[:3])
                surface_parts.append(f"Branches toward: {branch_summary}.")

        elif intent.qtype in ("how_relate", "difference"):
            if relations:
                overlap = relations.get("overlap_score", 0)
                shared = relations.get("shared_count", 0)
                surface_parts.append(
                    f"{relations.get('anchor_a')} and {relations.get('anchor_b')}: "
                    f"overlap {overlap:.1%} ({shared} shared neighbors)."
                )
                if relations.get("top_shared"):
                    shared_words = ", ".join(s["word"] for s in relations["top_shared"][:4])
                    surface_parts.append(f"Shared context: {shared_words}.")
                if intent.qtype == "difference":
                    a_exc = relations.get("a_exclusive_top", [])
                    b_exc = relations.get("b_exclusive_top", [])
                    if a_exc:
                        surface_parts.append(f"{relations.get('anchor_a')} exclusive: {', '.join(x['word'] for x in a_exc[:3])}.")
                    if b_exc:
                        surface_parts.append(f"{relations.get('anchor_b')} exclusive: {', '.join(x['word'] for x in b_exc[:3])}.")

        if not surface_parts:
            surface_parts.append(f"'{subject}' has evidence at {confidence.get('positions_active', 0)} positions "
                                 f"({confidence.get('total_neighbors', 0)} neighbors).")

        if lake_hits:
            surface_parts.append(f"[{len(lake_hits)} lake hits]")

        surface = " ".join(surface_parts)

        trace["predicates_found"] = len(predicates)
        trace["causes_found"] = len(causes)
        trace["has_relations"] = bool(relations)
        trace["cascade_paths"] = len(cascade_paths)
        trace["lake_hits"] = len(lake_hits)
        trace["confidence"] = confidence

        return AnswerFrame(
            subject=subject,
            intent=intent.qtype,
            clouds=cloud_summaries,
            predicates=predicates,
            causes=causes,
            relations=relations,
            cascade_paths=cascade_paths[:top_k],
            lake_hits=lake_hits,
            confidence=confidence,
            surface_text=surface,
            trace=trace,
        )
