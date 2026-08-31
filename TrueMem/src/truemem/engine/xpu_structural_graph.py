"""Read-only occurrence-addressed B70 structural projection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch

from .structural_storage import read_structural_graph


def _assert_xpu(*values: torch.Tensor) -> None:
    if not values or any(value.device.type != "xpu" for value in values):
        raise RuntimeError("XPU_STRUCTURAL_STAGE_FELL_BACK")


class XpuStructuralGraph:
    """Project exact occurrences and verified parent bindings onto XPU."""

    def __init__(self, dataset_root: str | Path):
        if not torch.xpu.is_available():
            raise RuntimeError("XPU_UNAVAILABLE_NO_CPU_FALLBACK")
        self.root = Path(dataset_root)
        self.device = torch.device("xpu:0")
        self.device_name = torch.xpu.get_device_name(0)
        lexicon = json.loads((self.root / "state/dataset_lexicon.json").read_text())
        self.key_to_symbol = {
            str(row["anchor"]): int(str(row["symbol"])[2:], 16)
            for row in lexicon["anchors"] if str(row["anchor"]).startswith("object:structure:")
        }
        graph = read_structural_graph(self.root / "state/structure_graph.awbin")
        self.structures = graph["structures"]
        self.relations = graph["relations"]
        self.parent_objects = graph["parent_objects"]
        self.reference_bindings = graph["reference_bindings"]
        self.occurrence_to_index = {row["occurrence_id"]: index for index, row in enumerate(self.structures)}
        self.parent_to_index = {row["parent_object_id"]: index for index, row in enumerate(self.parent_objects)}

        verified_bindings = [
            row for row in self.reference_bindings
            if row["binding_status"] in {"VERIFIED_EXACT_PARENT_IDENTITY", "VERIFIED_EXPLICIT_ALIAS"}
            and len(row["candidate_parent_object_ids"]) == 1
        ]
        self.verified_bindings = verified_bindings
        tensors = {
            "occurrence_symbols": [int(row["symbol"][2:], 16) for row in self.structures],
            "occurrence_blocks": [int(row["block_ordinal"]) for row in self.structures],
            "occurrence_parents": [self.parent_to_index[row["parent_object_id"]] for row in self.structures],
            "edge_sources": [self.occurrence_to_index[row["subject_occurrence_id"]] for row in self.relations],
            "edge_targets": [self.occurrence_to_index[row["object_occurrence_id"]] for row in self.relations],
            "edge_relation_occurrences": [self.occurrence_to_index[row["relation_occurrence_id"]] for row in self.relations],
            "binding_mentions": [self.occurrence_to_index[row["mention_occurrence_id"]] for row in verified_bindings],
            "binding_parents": [self.parent_to_index[row["candidate_parent_object_ids"][0]] for row in verified_bindings],
        }
        for name, values in tensors.items():
            setattr(self, name, torch.tensor(values, dtype=torch.long, device=self.device))
        _assert_xpu(*(getattr(self, name) for name in tensors))
        torch.xpu.synchronize()
        self.load_receipt = {
            "schema": "truemem_xpu_occurrence_graph_projection@2",
            "device": self.device_name, "device_type": "xpu",
            "structure_occurrences": len(self.structures),
            "relation_occurrence_edges": len(self.relations),
            "verified_reference_bindings": len(verified_bindings),
            "parent_objects": len(self.parent_objects),
            "frontier_identity": "occurrence_id",
            "global_form_posting_broadcast": False,
            "cpu_role": "verified artifact loading and receipt serialization only",
            "frontier_math_on_cpu": False, "silent_device_fallback": False,
        }

    def exact_postings(self, structure_keys: list[str]) -> dict[str, Any]:
        requested = [self.key_to_symbol[key] for key in structure_keys if key in self.key_to_symbol]
        if not requested:
            return {"occurrence_ids": [], "block_ids": [], "status": "NO_EXACT_STRUCTURE", "device": self.device_name}
        query = torch.tensor(sorted(set(requested)), dtype=torch.long, device=self.device)
        indices = torch.nonzero(torch.isin(self.occurrence_symbols, query), as_tuple=False).flatten()
        blocks = torch.unique(self.occurrence_blocks[indices], sorted=True)
        _assert_xpu(query, indices, blocks)
        torch.xpu.synchronize()
        return {
            "occurrence_ids": [self.structures[index]["occurrence_id"] for index in indices.cpu().tolist()],
            "block_ids": [int(value) for value in blocks.cpu().tolist()],
            "status": "EXACT_STRUCTURE_POSTINGS", "device": self.device_name,
            "silent_device_fallback": False,
        }

    def walk(self, structure_keys: list[str], *, maximum_hops: int = 6, start_block_ids: list[int] | None = None) -> dict[str, Any]:
        start_symbols = sorted({self.key_to_symbol[key] for key in structure_keys if key in self.key_to_symbol})
        if not start_symbols:
            return {"status": "NO_VALID_FRONTIER", "paths": [], "device": self.device_name}
        symbols = torch.tensor(start_symbols, dtype=torch.long, device=self.device)
        start_mask = torch.isin(self.occurrence_symbols, symbols)
        if start_block_ids:
            blocks = torch.tensor(sorted(set(start_block_ids)), dtype=torch.long, device=self.device)
            start_mask &= torch.isin(self.occurrence_blocks, blocks)
        start_indices = torch.nonzero(start_mask, as_tuple=False).flatten()
        if not start_indices.numel():
            return {"status": "NO_VALID_FRONTIER", "paths": [], "device": self.device_name}
        # The admitted parent is the first context cloud. Exact question
        # occurrences select the parent; its bounded children become eligible
        # for relationship inspection without any corpus posting broadcast.
        start_parents = torch.unique(self.occurrence_parents[start_indices], sorted=True)
        frontier = torch.nonzero(torch.isin(self.occurrence_parents, start_parents), as_tuple=False).flatten()
        visited = torch.unique(frontier, sorted=True)
        path_rows: list[dict[str, Any]] = []
        parent_path: dict[str, int | None] = {
            self.parent_objects[index]["parent_object_id"]: None for index in start_parents.cpu().tolist()
        }
        steps = []
        for hop in range(maximum_hops):
            edge_ids = torch.nonzero(torch.isin(self.edge_sources, frontier), as_tuple=False).flatten()
            edge_ids = torch.sort(edge_ids, stable=True).values
            targets = self.edge_targets[edge_ids] if edge_ids.numel() else torch.empty(0, dtype=torch.long, device=self.device)
            discovered = torch.unique(torch.cat((frontier, targets)), sorted=True)
            binding_ids = torch.nonzero(torch.isin(self.binding_mentions, discovered), as_tuple=False).flatten()
            if not edge_ids.numel() and not binding_ids.numel():
                break
            bound_parents = torch.unique(self.binding_parents[binding_ids], sorted=True) if binding_ids.numel() else torch.empty(0, dtype=torch.long, device=self.device)
            parent_children = torch.nonzero(torch.isin(self.occurrence_parents, bound_parents), as_tuple=False).flatten() if bound_parents.numel() else torch.empty(0, dtype=torch.long, device=self.device)
            candidates = torch.unique(torch.cat((targets, parent_children)), sorted=True)
            frontier = candidates[~torch.isin(candidates, visited)]
            if not frontier.numel():
                break
            visited = torch.unique(torch.cat((visited, frontier)), sorted=True)
            _assert_xpu(edge_ids, targets, binding_ids, bound_parents, parent_children, candidates, frontier, visited)
            binding_by_mention = {
                self.verified_bindings[index]["mention_occurrence_id"]: self.verified_bindings[index]
                for index in binding_ids.cpu().tolist()
            }
            edge_target_ids = {self.relations[index]["object_occurrence_id"] for index in edge_ids.cpu().tolist()}
            for binding_index in binding_ids.cpu().tolist():
                binding = self.verified_bindings[binding_index]
                if binding["mention_occurrence_id"] in edge_target_ids:
                    continue
                mention = self.structures[self.occurrence_to_index[binding["mention_occurrence_id"]]]
                path_id = len(path_rows)
                source_parent = binding["source_parent_object_id"]
                target_parent = binding["candidate_parent_object_ids"][0]
                path_rows.append({
                    "path_id": path_id, "predecessor_path_id": parent_path.get(source_parent), "hop": hop + 1,
                    "subject_occurrence_id": binding["mention_occurrence_id"],
                    "relation_occurrence_id": None,
                    "object_occurrence_id": binding["mention_occurrence_id"],
                    "relation_edge_id": None,
                    "reference_binding_id": binding["binding_id"],
                    "source_parent_object_id": source_parent,
                    "target_parent_object_id": target_parent,
                    "block_ordinal": mention["block_ordinal"],
                    "transition_kind": "LOCAL_CLOUD_REFERENCE_BINDING",
                })
                parent_path.setdefault(target_parent, path_id)
            for edge_index in edge_ids.cpu().tolist():
                edge = self.relations[edge_index]
                binding = binding_by_mention.get(edge["object_occurrence_id"])
                source_parent = edge["parent_object_id"]
                target_parent = binding["candidate_parent_object_ids"][0] if binding else source_parent
                path_id = len(path_rows)
                path_rows.append({
                    "path_id": path_id, "predecessor_path_id": parent_path.get(source_parent), "hop": hop + 1,
                    "subject_occurrence_id": edge["subject_occurrence_id"],
                    "relation_occurrence_id": edge["relation_occurrence_id"],
                    "object_occurrence_id": edge["object_occurrence_id"],
                    "relation_edge_id": edge["relation_id"],
                    "reference_binding_id": binding["binding_id"] if binding else None,
                    "source_parent_object_id": source_parent,
                    "target_parent_object_id": target_parent,
                    "block_ordinal": edge["block_ordinal"],
                })
                parent_path.setdefault(target_parent, path_id)
            steps.append({
                "hop": hop + 1, "relation_edge_count": int(edge_ids.numel()),
                "verified_binding_count": int(binding_ids.numel()),
                "parent_objects_entered": int(bound_parents.numel()),
                "frontier_occurrence_count": int(frontier.numel()),
            })
        reached_blocks = torch.unique(self.occurrence_blocks[visited], sorted=True)
        _assert_xpu(reached_blocks)
        torch.xpu.synchronize()
        return {
            "status": "NO_VALID_FRONTIER" if not steps else "FRONTIER_EXHAUSTED",
            "start_occurrence_ids": [self.structures[index]["occurrence_id"] for index in start_indices.cpu().tolist()],
            "start_parent_cloud_count": int(frontier.numel()) if not steps else int(torch.nonzero(torch.isin(self.occurrence_parents, start_parents), as_tuple=False).numel()),
            "visited_occurrence_ids": [self.structures[index]["occurrence_id"] for index in visited.cpu().tolist()],
            "block_ids": [int(value) for value in reached_blocks.cpu().tolist()],
            "paths": path_rows, "steps": steps, "hop_count": len(steps),
            "device": self.device_name, "device_type": "xpu",
            "frontier_identity": "occurrence_id", "global_form_posting_broadcast": False,
            "cpu_relationship_math": False, "cpu_frontier_ranking": False,
            "silent_device_fallback": False,
        }
