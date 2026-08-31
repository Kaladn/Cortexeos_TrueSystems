"""Dataset-native XPU relationship qualification over any TrueMem map."""
from __future__ import annotations

import json
import gzip
import math
import struct
from pathlib import Path
from typing import Any

import torch
import numpy as np

from .query_ruling import relationship_demands

POSTING = struct.Struct(">6sIH")


def _assert_xpu(*values: torch.Tensor) -> None:
    if not values or any(value.device.type != "xpu" for value in values):
        raise RuntimeError("XPU_STAGE_FELL_BACK_OR_RETURNED_NON_XPU_TENSOR")


def _lexicographic_order(keys: list[torch.Tensor]) -> torch.Tensor:
    """Stable ascending lexicographic ordering performed wholly on XPU."""
    order = torch.arange(keys[0].numel(), device=keys[0].device)
    for key in reversed(keys):
        order = order[torch.argsort(key[order], stable=True)]
    _assert_xpu(order)
    return order


class XpuRelationshipIndex:
    def __init__(self, dataset_root: Path, blocks: dict[int, dict[str, Any]]):
        if not torch.xpu.is_available():
            raise RuntimeError("XPU_UNAVAILABLE_NO_CPU_FALLBACK")
        self.device = torch.device("xpu:0")
        self.device_name = torch.xpu.get_device_name(0)
        lexicon = json.loads((dataset_root / "state/dataset_lexicon.json").read_text())
        values = [(int(str(row["symbol"])[2:], 16), str(row["anchor"]), str(row["anchor_kind"])) for row in lexicon["anchors"]]
        self.vocabulary_size = max(value for value, _anchor, _kind in values) + 1
        self.anchor_to_id = {anchor: value for value, anchor, _kind in values}
        self.id_to_anchor = {value: anchor for value, anchor, _kind in values}
        kind_code = {"content": 0, "relation": 1, "glue": 2, "boundary": 3, "object": 4}
        kinds = torch.full((self.vocabulary_size,), 4, dtype=torch.int8, device=self.device)
        for value, _anchor, kind in values:
            kinds[value] = kind_code[kind]
        self.kinds = kinds

        raw = (dataset_root / "counts/block_anchor_postings.awbin").read_bytes()
        count = len(raw) // POSTING.size
        dtype = np.dtype({"names": ["symbol", "block", "position"], "formats": [("u1", 6), ">u4", ">u2"], "offsets": [0, 6, 10], "itemsize": 12})
        rows = np.frombuffer(raw, dtype=dtype)
        powers = np.array([256**5, 256**4, 256**3, 256**2, 256, 1], dtype=np.int64)
        symbols = torch.from_numpy((rows["symbol"].astype(np.int64) @ powers).copy())
        posting_blocks = torch.from_numpy(rows["block"].astype(np.int64).copy())
        positions = torch.from_numpy(rows["position"].astype(np.int64).copy())
        self.symbols = symbols.to(self.device)
        self.posting_blocks = posting_blocks.to(self.device)
        self.positions = positions.to(self.device)
        counts = torch.bincount(self.symbols, minlength=self.vocabulary_size)
        self.symbol_starts = torch.cat((torch.zeros(1, dtype=torch.long, device=self.device), counts.cumsum(0)))
        self.document_frequency = torch.zeros(self.vocabulary_size, dtype=torch.long, device=self.device)
        encoded = self.symbols * len(blocks) + self.posting_blocks
        unique_symbol_block = torch.unique(encoded, sorted=True)
        self.document_frequency.scatter_add_(0, unique_symbol_block // len(blocks), torch.ones_like(unique_symbol_block))

        # Reusable block-to-unique-anchor representation is built once on XPU.
        block_symbol = torch.unique(self.posting_blocks * self.vocabulary_size + self.symbols, sorted=True)
        self.block_symbol_ids = block_symbol % self.vocabulary_size
        block_ids = block_symbol // self.vocabulary_size
        block_counts = torch.bincount(block_ids, minlength=len(blocks))
        self.block_starts = torch.cat((torch.zeros(1, dtype=torch.long, device=self.device), block_counts.cumsum(0)))
        self.block_count = len(blocks)

        # Title boundaries are derived once during permitted CPU file loading,
        # then remain resident on XPU for every query.
        from truemem.engine.anchors import anchorize
        title_lengths = torch.zeros(len(blocks), dtype=torch.long)
        for block_id, block in blocks.items():
            title = str(block["text"]).splitlines()[0] if str(block["text"]) else ""
            title_lengths[int(block_id)] = len(anchorize(title))
        self.title_lengths = title_lengths.to(self.device)
        _assert_xpu(self.symbols, self.posting_blocks, self.positions, self.symbol_starts, self.block_symbol_ids, self.block_starts, self.title_lengths, self.document_frequency, self.kinds)
        torch.xpu.synchronize()
        self.load_receipt = {
            "stage": "candidate_representation",
            "device": self.device_name,
            "device_type": "xpu",
            "posting_count": int(count),
            "unique_block_anchor_count": int(block_symbol.numel()),
            "vocabulary_size": int(self.vocabulary_size),
            "block_count": int(self.block_count),
            "cpu_role": "binary_file_loading_coordinate_metadata_only",
            "ranking_on_cpu": False,
            "relationship_walk_on_cpu": False,
            "xpu_tensors_verified": True,
            "silent_device_fallback": False,
        }

    def _slice(self, symbol_id: int) -> tuple[torch.Tensor, torch.Tensor]:
        begin = int(self.symbol_starts[symbol_id].item())
        end = int(self.symbol_starts[symbol_id + 1].item())
        blocks = self.posting_blocks[begin:end]
        positions = self.positions[begin:end]
        _assert_xpu(blocks, positions)
        return blocks, positions

    def block_verdict(self, question: str, block_id: int) -> dict[str, Any]:
        """Audit one block with the same XPU qualification law used by ranking."""
        from truemem.engine.anchors import anchor_kind, anchorize
        relationship_matches = torch.zeros((), dtype=torch.long, device=self.device)
        matched_lanes: list[dict[str, Any]] = []
        for demand in relationship_demands(question):
            center = self.anchor_to_id.get(demand["center"])
            neighbor = self.anchor_to_id.get(demand["neighbor"])
            if center is None or neighbor is None:
                continue
            left_blocks, left_positions = self._slice(center)
            right_blocks, right_positions = self._slice(neighbor)
            left_mask = left_blocks == block_id
            wanted = left_blocks[left_mask] * 65536 + left_positions[left_mask] + int(demand["signed_distance"])
            right_keys = right_blocks * 65536 + right_positions
            count = torch.isin(wanted, right_keys).sum()
            relationship_matches += count
            if bool((count > 0).item()):
                matched_lanes.append({
                    "center": demand["center"],
                    "neighbor": demand["neighbor"],
                    "signed_distance": int(demand["signed_distance"]),
                    "witness_count": int(count.item()),
                })
        parent_hits: list[str] = []
        for anchor in anchorize(question):
            if anchor_kind(anchor) != "content":
                continue
            symbol = self.anchor_to_id.get(anchor)
            if symbol is None:
                continue
            blocks, positions = self._slice(symbol)
            mask = (blocks == block_id) & (positions < self.title_lengths[blocks])
            if bool(mask.any().item()) and anchor not in parent_hits:
                parent_hits.append(anchor)
        qualified = (relationship_matches > 0) | torch.tensor(bool(parent_hits), device=self.device)
        _assert_xpu(relationship_matches, qualified)
        torch.xpu.synchronize()
        return {
            "block_id": int(block_id),
            "qualified": bool(qualified.item()),
            "relationship_witness_count": int(relationship_matches.item()),
            "relationship_witness_lanes": matched_lanes,
            "parent_anchor_hits": parent_hits,
            "stage_receipt": {
                "stage": "single_block_relationship_qualification",
                "device": self.device_name,
                "device_type": "xpu",
                "cpu_relationship_math": False,
                "cpu_ranking": False,
                "xpu_tensors_verified": True,
                "silent_device_fallback": False,
            },
        }

    def _ruling_group_masks(
        self,
        question: str,
        anchor_structure_sheet: dict[str, Any] | None,
    ) -> tuple[torch.Tensor, torch.Tensor, list[dict[str, Any]]]:
        """Resolve already-validated question groups against exact XPU postings."""
        empty = torch.zeros((self.block_count, 0), dtype=torch.bool, device=self.device)
        # An empty mapping is the transport-level representation of "no sheet"
        # in multi-turn callers. It must take the exact baseline route. A
        # non-empty malformed mapping is verified below and fails closed.
        if not anchor_structure_sheet:
            return empty, empty, []
        from truemem.engine.query_ruling import build_anchor_structure_sheet

        if str(anchor_structure_sheet.get("question")) != question:
            raise ValueError("anchor structure sheet question does not match query")
        rebuilt = build_anchor_structure_sheet(
            question,
            ruling_groups=list(anchor_structure_sheet.get("ruling_anchor_groups") or []),
            operation=dict(anchor_structure_sheet.get("operation") or {}),
            required_evidence=list(anchor_structure_sheet.get("required_evidence") or []),
        )
        if rebuilt["sheet_id"] != anchor_structure_sheet.get("sheet_id"):
            raise ValueError("anchor structure sheet identity failed verification")
        groups = rebuilt["ruling_anchor_groups"]
        exact = torch.zeros((self.block_count, len(groups)), dtype=torch.bool, device=self.device)
        title = torch.zeros_like(exact)
        for group_index, group in enumerate(groups):
            symbol_ids = [self.anchor_to_id.get(anchor) for anchor in group["anchors"]]
            if any(symbol is None for symbol in symbol_ids):
                continue
            first_blocks, first_positions = self._slice(int(symbol_ids[0]))
            candidate_keys = first_blocks * 65536 + first_positions
            matched = torch.ones(candidate_keys.shape, dtype=torch.bool, device=self.device)
            for offset, symbol_id in enumerate(symbol_ids[1:], start=1):
                blocks, positions = self._slice(int(symbol_id))
                matched &= torch.isin(candidate_keys + offset, blocks * 65536 + positions)
            matched_blocks = first_blocks[matched]
            if matched_blocks.numel():
                exact[matched_blocks, group_index] = True
                first_matched_positions = first_positions[matched]
                in_title = first_matched_positions + len(symbol_ids) <= self.title_lengths[matched_blocks]
                title[matched_blocks[in_title], group_index] = True
            if group["match_scope"] == "parent_title":
                exact[:, group_index] = title[:, group_index]
        _assert_xpu(exact, title)
        return exact, title, groups

    def qualify_and_select(
        self,
        question: str,
        *,
        maximum_pool: int = 160,
        anchor_structure_sheet: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from truemem.engine.anchors import anchor_kind, anchorize
        demands = relationship_demands(question)
        relation_counts = torch.zeros(self.block_count, dtype=torch.long, device=self.device)
        coverage = torch.zeros((self.block_count, len(anchorize(question))), dtype=torch.bool, device=self.device)
        witnesses = []
        for demand in demands:
            center = self.anchor_to_id.get(demand["center"])
            neighbor = self.anchor_to_id.get(demand["neighbor"])
            if center is None or neighbor is None:
                continue
            left_blocks, left_positions = self._slice(center)
            right_blocks, right_positions = self._slice(neighbor)
            right_keys = right_blocks * 65536 + right_positions
            wanted = left_blocks * 65536 + left_positions + int(demand["signed_distance"])
            mask = torch.isin(wanted, right_keys)
            matched_blocks = left_blocks[mask]
            if matched_blocks.numel():
                relation_counts.scatter_add_(0, matched_blocks, torch.ones_like(matched_blocks))
                coverage[matched_blocks, int(demand["query_positions"][0])] = True
                coverage[matched_blocks, int(demand["query_positions"][1])] = True
                witnesses.append({"center": demand["center"], "neighbor": demand["neighbor"], "signed_distance": int(demand["signed_distance"]), "block_count": int(torch.unique(matched_blocks).numel())})

        parent_counts = torch.zeros(self.block_count, dtype=torch.long, device=self.device)
        parent_anchor_ids = []
        for query_position, anchor in enumerate(anchorize(question)):
            if anchor_kind(anchor) != "content":
                continue
            symbol = self.anchor_to_id.get(anchor)
            if symbol is None:
                continue
            blocks, positions = self._slice(symbol)
            mask = positions < self.title_lengths[blocks]
            parent_blocks = blocks[mask]
            if parent_blocks.numel():
                parent_counts.scatter_add_(0, parent_blocks, torch.ones_like(parent_blocks))
                coverage[parent_blocks, query_position] = True
                parent_anchor_ids.append(symbol)

        ruling_matches, ruling_title_matches, ruling_groups = self._ruling_group_masks(
            question, anchor_structure_sheet
        )
        ruling_blocks = ruling_matches.any(1) if ruling_groups else torch.zeros(
            self.block_count, dtype=torch.bool, device=self.device
        )
        qualified = (relation_counts > 0) | (parent_counts > 0) | ruling_blocks
        qualified_ids = torch.nonzero(qualified, as_tuple=False).flatten()
        coverage_count = coverage.sum(1)
        # Candidate reduction is ranked on XPU and retains both relationship
        # and parent lanes. Direct-hit count is absent.
        relation_order = _lexicographic_order([-
            coverage_count[qualified_ids], -relation_counts[qualified_ids], qualified_ids
        ])
        relation_pool = qualified_ids[relation_order[:maximum_pool]]
        parent_ids = torch.nonzero(parent_counts > 0, as_tuple=False).flatten()
        parent_order = _lexicographic_order([-coverage_count[parent_ids], -parent_counts[parent_ids], parent_ids]) if parent_ids.numel() else parent_ids
        parent_pool = parent_ids[parent_order[:maximum_pool]] if parent_ids.numel() else parent_ids
        explicit_ruling_pool = torch.nonzero(ruling_blocks, as_tuple=False).flatten()
        pool = torch.unique(torch.cat((relation_pool, parent_pool, explicit_ruling_pool)), sorted=True)

        # Dense pool-by-vocabulary presence is bounded after qualification and
        # permits bridge comparison on XPU without rebuilding Python sets.
        presence = torch.zeros((pool.numel(), self.vocabulary_size), dtype=torch.float16, device=self.device)
        for row_index in range(pool.numel()):
            block_id = int(pool[row_index].item())
            begin = int(self.block_starts[block_id].item())
            end = int(self.block_starts[block_id + 1].item())
            anchor_ids = self.block_symbol_ids[begin:end]
            content_ids = anchor_ids[self.kinds[anchor_ids] == 0]
            presence[row_index, content_ids] = 1
        if ruling_groups:
            single_ruling_count = ruling_matches[pool].sum(1)
            complete_single = torch.nonzero(
                single_ruling_count == len(ruling_groups), as_tuple=False
            ).flatten()
            if complete_single.numel():
                single_title_count = ruling_title_matches[pool].sum(1)
                single_order = _lexicographic_order([
                    -single_title_count[complete_single],
                    -coverage_count[pool[complete_single]],
                    -relation_counts[pool[complete_single]],
                    -parent_counts[pool[complete_single]],
                    pool[complete_single],
                ])
                winner_pool_index = int(complete_single[single_order[0]].item())
                selected_block = int(pool[winner_pool_index].item())
                _assert_xpu(
                    ruling_matches, ruling_title_matches, single_ruling_count,
                    complete_single, single_order, pool, presence,
                )
                torch.xpu.synchronize()
                return {
                    "selected_block_ids": [selected_block],
                    "bridge_anchor_ids": [],
                    "bridge_anchors": [],
                    "vector": {
                        "ruling_group_coverage": int(single_ruling_count[winner_pool_index].item()),
                        "ruling_parent_title_coverage": int(single_title_count[winner_pool_index].item()),
                        "query_anchor_coverage": int(coverage_count[selected_block].item()),
                        "bridge_frequency_corrected_support": 0.0,
                        "relationship_match_count": int(relation_counts[selected_block].item()),
                        "parent_anchor_hit_count": int(parent_counts[selected_block].item()),
                        "shared_bridge_anchor_count": 0,
                    },
                    "qualified_block_count": int(qualified_ids.numel()),
                    "candidate_pool_count": int(pool.numel()),
                    "relationship_witness_lanes": witnesses,
                    "anchor_structure_sheet_id": anchor_structure_sheet["sheet_id"],
                    "ruling_group_matches": [
                        {
                            "group_id": group["group_id"],
                            "anchors": group["anchors"],
                            "match_scope": group["match_scope"],
                            "matching_block_count": int(ruling_matches[:, index].sum().item()),
                            "title_matching_block_count": int(ruling_title_matches[:, index].sum().item()),
                        }
                        for index, group in enumerate(ruling_groups)
                    ],
                    "stage_receipt": {
                        "stage": "relationship_qualification_and_chain_ranking",
                        "device": self.device_name,
                        "device_type": "xpu",
                        "cpu_ranking": False,
                        "cpu_relationship_math": False,
                        "xpu_tensors_verified": True,
                        "silent_device_fallback": False,
                        "direct_hit_primary_sort": False,
                        "positions_preserved": True,
                        "signed_distances_preserved": True,
                        "temporary_query_overlay": True,
                        "stored_counts_modified": False,
                        "stored_relationships_modified": False,
                        "proper_nouns_inferred": False,
                        "ruling_groups_supplied_externally": True,
                        "selection_cardinality": 1,
                        "cardinality_law": "one block covering all ruling groups precedes multi-block pairing",
                        "cpu_role": "file loading, coordinate metadata, and receipt serialization only",
                    },
                }
        bridge_count = presence @ presence.T
        rarity = torch.zeros(self.vocabulary_size, dtype=torch.float16, device=self.device)
        nonzero = self.document_frequency > 0
        rarity[nonzero] = self.document_frequency[nonzero].to(torch.float32).rsqrt().to(torch.float16)
        bridge_frequency_corrected = (presence * rarity) @ presence.T
        diagonal = torch.arange(pool.numel(), device=self.device)
        bridge_count[diagonal, diagonal] = -1
        bridge_frequency_corrected[diagonal, diagonal] = -1
        pair_left, pair_right = torch.triu_indices(pool.numel(), pool.numel(), offset=1, device=self.device)
        pair_coverage = (coverage[pool[pair_left]] | coverage[pool[pair_right]]).sum(1)
        pair_bridge_weight = bridge_frequency_corrected[pair_left, pair_right]
        pair_bridge_count = bridge_count[pair_left, pair_right]
        pair_relations = relation_counts[pool[pair_left]] + relation_counts[pool[pair_right]]
        pair_parents = parent_counts[pool[pair_left]] + parent_counts[pool[pair_right]]
        if ruling_groups:
            pair_ruling = ruling_matches[pool[pair_left]] | ruling_matches[pool[pair_right]]
            pair_ruling_count = pair_ruling.sum(1)
            pair_title_count = (
                ruling_title_matches[pool[pair_left]] | ruling_title_matches[pool[pair_right]]
            ).sum(1)
            eligible = pair_ruling_count == len(ruling_groups)
            eligible_pair_ids = torch.nonzero(eligible, as_tuple=False).flatten()
            if not eligible_pair_ids.numel():
                torch.xpu.synchronize()
                return {
                    "status": "REQUIRED_RULING_PATH_NOT_FOUND",
                    "selected_block_ids": [],
                    "anchor_structure_sheet_id": anchor_structure_sheet["sheet_id"],
                    "ruling_group_matches": [
                        {
                            "group_id": group["group_id"],
                            "matching_block_count": int(ruling_matches[:, index].sum().item()),
                            "title_matching_block_count": int(ruling_title_matches[:, index].sum().item()),
                        }
                        for index, group in enumerate(ruling_groups)
                    ],
                    "stage_receipt": {
                        "stage": "relationship_qualification_and_chain_ranking",
                        "device": self.device_name,
                        "device_type": "xpu",
                        "temporary_query_overlay": True,
                        "stored_counts_modified": False,
                        "stored_relationships_modified": False,
                        "cpu_ranking": False,
                    },
                }
        else:
            pair_ruling_count = torch.zeros_like(pair_coverage)
            pair_title_count = torch.zeros_like(pair_coverage)
            eligible_pair_ids = torch.arange(pair_left.numel(), device=self.device)
        relative_order = _lexicographic_order([
            -pair_ruling_count[eligible_pair_ids],
            -pair_title_count[eligible_pair_ids],
            -pair_coverage[eligible_pair_ids],
            -pair_bridge_weight[eligible_pair_ids],
            -pair_relations[eligible_pair_ids],
            -pair_parents[eligible_pair_ids],
            -pair_bridge_count[eligible_pair_ids],
            pool[pair_left[eligible_pair_ids]],
            pool[pair_right[eligible_pair_ids]],
        ])
        pair_order = eligible_pair_ids[relative_order]
        native_pair_order = _lexicographic_order([
            -pair_coverage,
            -pair_bridge_weight,
            -pair_relations,
            -pair_parents,
            -pair_bridge_count,
            pool[pair_left],
            pool[pair_right],
        ])
        best = int(pair_order[0].item())
        selected = pool[torch.stack((pair_left[best], pair_right[best]))]
        bridge_ids = torch.nonzero((presence[pair_left[best]] > 0) & (presence[pair_right[best]] > 0), as_tuple=False).flatten()
        _assert_xpu(relation_counts, parent_counts, coverage, qualified_ids, pool, presence, bridge_count, bridge_frequency_corrected, pair_order, native_pair_order, selected, bridge_ids, ruling_matches, ruling_title_matches)
        torch.xpu.synchronize()
        return {
            "selected_block_ids": [int(value) for value in selected.cpu().tolist()],
            "bridge_anchor_ids": [int(value) for value in bridge_ids.cpu().tolist()],
            "bridge_anchors": [self.id_to_anchor[int(value)] for value in bridge_ids.cpu().tolist()],
            "vector": {
                "ruling_group_coverage": int(pair_ruling_count[best].item()),
                "ruling_parent_title_coverage": int(pair_title_count[best].item()),
                "query_anchor_coverage": int(pair_coverage[best].item()),
                "bridge_frequency_corrected_support": float(pair_bridge_weight[best].item()),
                "relationship_match_count": int(pair_relations[best].item()),
                "parent_anchor_hit_count": int(pair_parents[best].item()),
                "shared_bridge_anchor_count": int(pair_bridge_count[best].item()),
            },
            "qualified_block_count": int(qualified_ids.numel()),
            "candidate_pool_count": int(pool.numel()),
            "relationship_witness_lanes": witnesses,
            "anchor_structure_sheet_id": anchor_structure_sheet["sheet_id"] if anchor_structure_sheet else None,
            "ruling_group_matches": [
                {
                    "group_id": group["group_id"],
                    "anchors": group["anchors"],
                    "match_scope": group["match_scope"],
                    "matching_block_count": int(ruling_matches[:, index].sum().item()),
                    "title_matching_block_count": int(ruling_title_matches[:, index].sum().item()),
                }
                for index, group in enumerate(ruling_groups)
            ],
            "stage_receipt": {
                "stage": "relationship_qualification_and_chain_ranking",
                "device": self.device_name,
                "device_type": "xpu",
                "cpu_ranking": False,
                "direct_hit_primary_sort": False,
                "positions_preserved": True,
                "signed_distances_preserved": True,
                "temporary_query_overlay": bool(anchor_structure_sheet),
                "stored_counts_modified": False,
                "stored_relationships_modified": False,
                "proper_nouns_inferred": False,
                "ruling_groups_supplied_externally": bool(anchor_structure_sheet),
                "selection_cardinality": 2,
                "cardinality_law": "multi-block pair used because no single block covered all ruling groups" if anchor_structure_sheet else "native baseline pair",
                "cpu_relationship_math": False,
                "xpu_tensors_verified": True,
                "silent_device_fallback": False,
                "cpu_role": "file loading, coordinate metadata, and receipt serialization only",
            },
        }


class XpuAnswerWalker:
    """XPU-only branch selection over a prepared signed 6-1-6 answer map."""
    OFFSETS = (-6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6)

    def __init__(self, prepared: Path):
        if not torch.xpu.is_available():
            raise RuntimeError("XPU_UNAVAILABLE_NO_CPU_FALLBACK")
        self.device = torch.device("xpu:0")
        self.device_name = torch.xpu.get_device_name(0)
        mapping = json.loads((prepared / "symbol-index-mapping.json").read_text())
        self.surface_to_id = {str(row["surface"]): int(row["dense_model_index"]) for row in mapping["entries"]}
        self.id_to_surface = {int(row["dense_model_index"]): str(row["surface"]) for row in mapping["entries"]}
        permanent_to_dense = {str(row["permanent_symbol"]): int(row["dense_model_index"]) for row in mapping["entries"]}
        self.vocabulary_size = len(mapping["entries"])
        from truemem.engine.anchors import anchor_kind
        kind_code = {"content": 0, "relation": 1, "glue": 2, "boundary": 3, "object": 4}
        self.kinds = torch.tensor([kind_code.get(anchor_kind(self.id_to_surface[index]), 4) for index in range(self.vocabulary_size)], dtype=torch.int8, device=self.device)
        frequencies = torch.zeros(self.vocabulary_size, dtype=torch.float32)
        with gzip.open(prepared / "M001.jsonl.gz", "rt", encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                dense = permanent_to_dense.get(str(row["symbol"]))
                if dense is not None:
                    frequencies[dense] = int(row["count"])
        centers=[];lanes=[];neighbors=[];counts=[]
        with gzip.open(prepared / "M002.jsonl.gz", "rt", encoding="utf-8") as stream:
            for line in stream:
                row=json.loads(line);center=permanent_to_dense.get(str(row["center"]));neighbor=permanent_to_dense.get(str(row["neighbor"]));offset=int(row["offset"])
                if center is not None and neighbor is not None:
                    centers.append(center);lanes.append(self.OFFSETS.index(offset));neighbors.append(neighbor);counts.append(int(row["count"]))
        center=torch.tensor(centers,dtype=torch.long,device=self.device);lane=torch.tensor(lanes,dtype=torch.long,device=self.device);neighbor=torch.tensor(neighbors,dtype=torch.long,device=self.device);count=torch.tensor(counts,dtype=torch.float32,device=self.device)
        key=(center*12+lane)*self.vocabulary_size+neighbor;order=torch.argsort(key,stable=True);self.keys=key[order];self.counts=count[order]
        plus_lane=self.OFFSETS.index(1);mask=lane==plus_lane;plus_center=center[mask];plus_neighbor=neighbor[mask];plus_count=count[mask];plus_order=torch.argsort(plus_center,stable=True);self.plus_neighbors=plus_neighbor[plus_order];self.plus_counts=plus_count[plus_order];plus_center=plus_center[plus_order];center_counts=torch.bincount(plus_center,minlength=self.vocabulary_size);self.plus_starts=torch.cat((torch.zeros(1,dtype=torch.long,device=self.device),center_counts.cumsum(0)))
        pair_key=center*self.vocabulary_size+neighbor;pair_order=torch.argsort(pair_key,stable=True);pair_key=pair_key[pair_order];unique_pair=torch.unique_consecutive(pair_key);pair_center=unique_pair//self.vocabulary_size;pair_neighbor=unique_pair%self.vocabulary_size
        self.graph_centers=pair_center
        self.graph_neighbors=pair_neighbor
        self.plus_centers=plus_center
        reverse_key=pair_neighbor*self.vocabulary_size+pair_center;reverse_order=torch.argsort(reverse_key,stable=True);reverse_key=reverse_key[reverse_order];self.reverse_predecessor=reverse_key%self.vocabulary_size;reverse_target=reverse_key//self.vocabulary_size;reverse_counts=torch.bincount(reverse_target,minlength=self.vocabulary_size);self.reverse_starts=torch.cat((torch.zeros(1,dtype=torch.long,device=self.device),reverse_counts.cumsum(0)))
        self.frequencies=frequencies.to(self.device);self.total_frequency=self.frequencies.sum()
        _assert_xpu(self.keys,self.counts,self.plus_neighbors,self.plus_counts,self.plus_starts,self.plus_centers,self.graph_centers,self.graph_neighbors,self.reverse_predecessor,self.reverse_starts,self.frequencies,self.kinds)
        torch.xpu.synchronize()
        self.load_receipt={"stage":"answer_map_representation","device":self.device_name,"device_type":"xpu","vocabulary_size":self.vocabulary_size,"signed_relation_tuple_count":len(centers),"cpu_role":"gzip_and_mapping_decode_only","relationship_walk_on_cpu":False,"ranking_on_cpu":False}

    def _lookup(self, centers: torch.Tensor, offsets: torch.Tensor, neighbors: torch.Tensor) -> torch.Tensor:
        lanes=torch.empty_like(offsets)
        for lane,offset in enumerate(self.OFFSETS):lanes[offsets==offset]=lane
        wanted=(centers*12+lanes)*self.vocabulary_size+neighbors;position=torch.searchsorted(self.keys,wanted);valid=position<self.keys.numel();safe=position.clamp(max=max(0,self.keys.numel()-1));valid &= self.keys[safe]==wanted;out=torch.zeros(wanted.shape,dtype=torch.float32,device=self.device);out[valid]=self.counts[safe[valid]];_assert_xpu(out);return out

    def _cloud_scores(self, query_mask: torch.Tensor, depth: int=3) -> torch.Tensor:
        """Propagate query support over the frozen graph in three batched XPU steps."""
        frontier=query_mask.to(torch.long)
        scores=torch.zeros(self.vocabulary_size,dtype=torch.long,device=self.device)
        for _ in range(depth):
            edge_support=frontier[self.graph_centers]
            next_frontier=torch.zeros_like(frontier)
            next_frontier.scatter_add_(0,self.graph_neighbors,edge_support)
            scores += next_frontier
            frontier=(next_frontier>0).to(torch.long)
        _assert_xpu(scores)
        return scores

    def _field(self,current:int,history:list[int],allowed:torch.Tensor,cloud_scores:torch.Tensor,forward_counts:torch.Tensor,top_k:int)->dict[str,torch.Tensor]:
        begin=int(self.plus_starts[current].item());end=int(self.plus_starts[current+1].item());neighbors=self.plus_neighbors[begin:end];native=self.plus_counts[begin:end];mask=allowed[neighbors];neighbors=neighbors[mask];native=native[mask]
        if not neighbors.numel():return {}
        native_order=torch.argsort(native,descending=True,stable=True)[:top_k];candidates=neighbors[native_order];native=native[native_order];n=candidates.numel();centers=torch.full((n,),current,dtype=torch.long,device=self.device);offsets=torch.ones(n,dtype=torch.long,device=self.device);local=self._lookup(centers,offsets,candidates)
        lane_total=local.sum().clamp(min=1);conditional=local/lane_total;background=self.frequencies[candidates]/self.total_frequency.clamp(min=1);lift=torch.where(background>0,conditional/background,torch.zeros_like(background));support=torch.log1p(local)
        all_counts=[]
        for offset in self.OFFSETS:all_counts.append(self._lookup(centers,torch.full((n,),offset,dtype=torch.long,device=self.device),candidates))
        lanes=torch.stack(all_counts,1);pair_total=lanes.sum(1).clamp(min=1);distribution=lanes/pair_total[:,None];stability=(distribution*distribution).sum(1);positive=lanes[:,6:].sum(1);negative=lanes[:,:6].sum(1);direction=(positive-negative)/pair_total
        backside=torch.zeros(n,device=self.device)
        for distance,previous in enumerate(reversed(history[-6:]),start=1):backside += self._lookup(torch.full((n,),previous,dtype=torch.long,device=self.device),torch.full((n,),distance,dtype=torch.long,device=self.device),candidates)
        forward=forward_counts[candidates]
        cloud=cloud_scores[candidates]
        native_rank=torch.arange(1,n+1,dtype=torch.long,device=self.device)
        order=_lexicographic_order([-(cloud>0).long(),-(forward>0).long(),-backside,-local,-conditional,-lift,-stability,-direction,native_rank,candidates])
        result={"candidates":candidates[order],"native_count":native[order],"local":local[order],"conditional":conditional[order],"lift":lift[order],"support":support[order],"stability":stability[order],"direction":direction[order],"backside":backside[order],"cloud":cloud[order],"forward":forward[order],"native_rank":native_rank[order]};_assert_xpu(*result.values());return result

    def walk(self,question:str,evidence_texts:list[str],*,top_k:int,max_new_anchors:int=24)->dict[str,Any]:
        if top_k not in {3,6}:raise ValueError("top_k must be 3 or 6")
        from truemem.engine.anchors import anchor_kind,anchorize,anchors_to_text
        factual=set(anchorize(question));[factual.update(anchorize(text)) for text in evidence_texts]
        allowed=torch.zeros(self.vocabulary_size,dtype=torch.bool,device=self.device);query_mask=torch.zeros_like(allowed)
        for surface,index in self.surface_to_id.items():
            if surface in factual or surface.startswith("<") or anchor_kind(surface) in {"glue","relation","boundary"}:allowed[index]=True
        for anchor in factual:
            if anchor in self.surface_to_id:query_mask[self.surface_to_id[anchor]]=True
        cloud_scores=self._cloud_scores(query_mask)
        forward_counts=torch.zeros(self.vocabulary_size,dtype=torch.long,device=self.device)
        forward_counts.scatter_add_(0,self.plus_centers,allowed[self.plus_neighbors].to(torch.long))
        _assert_xpu(cloud_scores,forward_counts)
        history=[self.surface_to_id[x] for x in ("<END_MESSAGE>","<ASSISTANT>","<BEGIN_MESSAGE>")];beam=[{"path":history,"new":[],"steps":[]}];pruned=[]
        for output_position in range(max_new_anchors):
            branches=[]
            branch_vectors=[]
            for branch in beam:
                field=self._field(branch["path"][-1],branch["path"],allowed,cloud_scores,forward_counts,top_k)
                if not field:continue
                for index in range(field["candidates"].numel()):
                    candidate=int(field["candidates"][index].item());vector={name:(int(values[index].item()) if values.dtype in {torch.long,torch.int64} else float(values[index].item())) for name,values in field.items() if name!="candidates"}
                    branches.append({"path":[*branch["path"],candidate],"new":[*branch["new"],candidate],"steps":[*branch["steps"],{"output_position":output_position,"selected_anchor":self.id_to_surface[candidate],"candidate_vector":vector,"candidate_field":[self.id_to_surface[int(value)] for value in field["candidates"].cpu().tolist()]}]})
                    branch_vectors.append(torch.stack((
                        (field["cloud"][index] > 0).to(torch.float32),
                        (field["forward"][index] > 0).to(torch.float32),
                        field["backside"][index].to(torch.float32),
                        field["local"][index].to(torch.float32),
                        field["support"][index].to(torch.float32),
                        field["lift"][index].to(torch.float32),
                        field["stability"][index].to(torch.float32),
                        field["direction"][index].to(torch.float32),
                        -field["native_rank"][index].to(torch.float32),
                        -field["candidates"][index].to(torch.float32),
                    )))
            if not branches:break
            # Preserve the complete eight-measurement relationship vector when
            # pruning sibling branches.  This ordering is computed on XPU;
            # Python only carries the already-ranked branch receipts.
            branch_matrix=torch.stack(branch_vectors)
            order=_lexicographic_order([-branch_matrix[:,column] for column in range(branch_matrix.shape[1])])
            _assert_xpu(branch_matrix,order)
            ordered=[branches[int(index)] for index in order.cpu().tolist()];pruned.extend(ordered[top_k:]);beam=ordered[:top_k]
            if all(self.id_to_surface[row["path"][-1]] in {"<END_MESSAGE>","<END_SESSION>"} for row in beam):break
        chosen=beam[0] if beam else {"path":history,"new":[],"steps":[]};surfaces=[self.id_to_surface[value] for value in chosen["new"]];spoken=[value for value in surfaces if not value.startswith("<")];torch.xpu.synchronize()
        return {"schema":"truesystems_xpu_evidence_answer_walk@1","top_k":top_k,"speech_anchors":spoken,"speech_text":anchors_to_text(spoken),"steps":chosen["steps"],"generated_surfaces":surfaces,"pruned_branch_count":len(pruned),"content_anchor_workspace_enforced":True,"reference_answer_copied":False,"stage_receipt":{"stage":"signed_relationship_answer_walk","device":self.device_name,"device_type":"xpu","cpu_relationship_math":False,"cpu_candidate_ranking":False,"signed_lanes_preserved":True,"backside_used":True,"cloud_used":True,"forward_used":True,"top_k":top_k}}
