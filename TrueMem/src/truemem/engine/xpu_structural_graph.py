"""Read-only B70 projection of TrueVision structural bindings."""

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
        self.symbol_to_key = {value: key for key, value in self.key_to_symbol.items()}
        graph = read_structural_graph(self.root / "state/structure_graph.awbin")
        self.structures = graph["structures"]
        self.relations = graph["relations"]
        structure_symbols = [int(row["symbol"][2:], 16) for row in self.structures]
        structure_blocks = [int(row["block_ordinal"]) for row in self.structures]
        edge_sources = [int(row["subject_symbol"][2:], 16) for row in self.relations]
        edge_relations = [int(row["relation_symbol"][2:], 16) for row in self.relations]
        edge_targets = [int(row["object_symbol"][2:], 16) for row in self.relations]
        self.structure_symbols = torch.tensor(structure_symbols, dtype=torch.long, device=self.device)
        self.structure_blocks = torch.tensor(structure_blocks, dtype=torch.long, device=self.device)
        self.edge_sources = torch.tensor(edge_sources, dtype=torch.long, device=self.device)
        self.edge_relations = torch.tensor(edge_relations, dtype=torch.long, device=self.device)
        self.edge_targets = torch.tensor(edge_targets, dtype=torch.long, device=self.device)
        _assert_xpu(self.structure_symbols, self.structure_blocks, self.edge_sources, self.edge_relations, self.edge_targets)
        torch.xpu.synchronize()
        self.load_receipt = {
            "schema": "truemem_xpu_structural_projection@1",
            "device": self.device_name,
            "device_type": "xpu",
            "structure_occurrences": len(structure_symbols),
            "relation_edges": len(edge_sources),
            "cpu_role": "verified artifact loading and receipt serialization only",
            "frontier_math_on_cpu": False,
            "silent_device_fallback": False,
        }

    def exact_postings(self, structure_keys: list[str]) -> dict[str, Any]:
        requested = [self.key_to_symbol[key] for key in structure_keys if key in self.key_to_symbol]
        if not requested:
            return {"symbols": [], "block_ids": [], "status": "NO_EXACT_STRUCTURE", "device": self.device_name}
        query = torch.tensor(sorted(set(requested)), dtype=torch.long, device=self.device)
        mask = torch.isin(self.structure_symbols, query)
        blocks = torch.unique(self.structure_blocks[mask], sorted=True)
        _assert_xpu(query, mask, blocks)
        torch.xpu.synchronize()
        return {
            "symbols": [int(value) for value in query.cpu().tolist()],
            "block_ids": [int(value) for value in blocks.cpu().tolist()],
            "status": "EXACT_STRUCTURE_POSTINGS",
            "device": self.device_name,
            "silent_device_fallback": False,
        }

    def walk(self, structure_keys: list[str], *, maximum_hops: int = 6) -> dict[str, Any]:
        starts = sorted({self.key_to_symbol[key] for key in structure_keys if key in self.key_to_symbol})
        if not starts:
            return {"status": "NO_VALID_FRONTIER", "paths": [], "device": self.device_name}
        frontier = torch.tensor(starts, dtype=torch.long, device=self.device)
        visited = torch.unique(frontier, sorted=True)
        steps = []
        for hop in range(maximum_hops):
            edge_mask = torch.isin(self.edge_sources, frontier)
            edge_ids = torch.nonzero(edge_mask, as_tuple=False).flatten()
            if not edge_ids.numel():
                break
            # Structural symbol and source edge ordinal are deterministic; no
            # retrieval score or model value participates.
            targets = self.edge_targets[edge_ids]
            order = torch.argsort(targets * (len(self.relations) + 1) + edge_ids, stable=True)
            edge_ids = edge_ids[order]
            targets = targets[order]
            new_mask = ~torch.isin(targets, visited)
            chosen = edge_ids[new_mask]
            frontier = torch.unique(targets[new_mask], sorted=True)
            if not frontier.numel():
                break
            visited = torch.unique(torch.cat((visited, frontier)), sorted=True)
            _assert_xpu(edge_mask, edge_ids, targets, chosen, frontier, visited)
            chosen_cpu = [int(value) for value in chosen.cpu().tolist()]
            steps.append({
                "hop": hop + 1,
                "edges": [self.relations[index] for index in chosen_cpu],
                "frontier_symbols": [int(value) for value in frontier.cpu().tolist()],
            })
        block_mask = torch.isin(self.structure_symbols, visited)
        blocks = torch.unique(self.structure_blocks[block_mask], sorted=True)
        _assert_xpu(block_mask, blocks)
        torch.xpu.synchronize()
        return {
            "status": "NO_VALID_FRONTIER" if not steps else "FRONTIER_EXHAUSTED",
            "start_symbols": starts,
            "visited_symbols": [int(value) for value in visited.cpu().tolist()],
            "block_ids": [int(value) for value in blocks.cpu().tolist()],
            "steps": steps,
            "hop_count": len(steps),
            "device": self.device_name,
            "device_type": "xpu",
            "cpu_relationship_math": False,
            "cpu_frontier_ranking": False,
            "silent_device_fallback": False,
        }
