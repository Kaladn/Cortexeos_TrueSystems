"""Read-only occurrence-addressed B70 structural projection."""

from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import Any

import numpy as np
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
        symbol_rows = [
            (int(str(row["symbol"])[2:], 16), str(row["anchor"]))
            for row in lexicon["anchors"]
        ]
        self.symbol_to_anchor = dict(symbol_rows)
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

        # The native posting spine is the complete local context authority.  It
        # is indexed once by physical block/position so bounded 6-1-6 clouds do
        # not depend on whether an anchor also belongs to a compiled structure.
        posting_raw = (self.root / "counts/block_anchor_postings.awbin").read_bytes()
        posting_record = struct.Struct(">6sIH")
        posting_dtype = np.dtype({
            "names": ["symbol", "block", "position"],
            "formats": [("u1", 6), ">u4", ">u2"],
            "offsets": [0, 6, 10], "itemsize": posting_record.size,
        })
        posting_rows = np.frombuffer(posting_raw, dtype=posting_dtype)
        powers = np.array([256**5, 256**4, 256**3, 256**2, 256, 1], dtype=np.int64)
        posting_symbols_cpu = posting_rows["symbol"].astype(np.int64) @ powers
        posting_blocks_cpu = posting_rows["block"].astype(np.int64)
        posting_positions_cpu = posting_rows["position"].astype(np.int64)
        posting_keys = torch.from_numpy(
            (posting_blocks_cpu * 65536 + posting_positions_cpu).copy()
        ).to(self.device)
        posting_order = torch.argsort(posting_keys, stable=True)
        self.position_posting_keys = posting_keys[posting_order]
        self.position_posting_symbols = torch.from_numpy(posting_symbols_cpu.copy()).to(self.device)[posting_order]
        self.position_posting_positions = torch.from_numpy(posting_positions_cpu.copy()).to(self.device)[posting_order]
        ordered_blocks = torch.from_numpy(posting_blocks_cpu.copy()).to(self.device)[posting_order]
        block_count = len(self.parent_objects)
        block_counts = torch.bincount(ordered_blocks, minlength=block_count)
        self.block_posting_offsets = torch.cat((
            torch.zeros(1, dtype=torch.long, device=self.device), block_counts.cumsum(0),
        ))
        self.parent_block_ids = torch.tensor(
            [int(row["block_ordinal"]) for row in self.parent_objects],
            dtype=torch.long, device=self.device,
        )

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
        self.edge_explicit_alias = torch.tensor(
            [bool(row.get("explicit_alias")) for row in self.relations],
            dtype=torch.bool, device=self.device,
        )
        self.alias_cue_symbols = {
            anchor: torch.tensor(
                sorted(symbol for symbol, text in self.symbol_to_anchor.items() if text.casefold() == anchor),
                dtype=torch.long, device=self.device,
            )
            for anchor in ("alias", "also", "as", "called", "formerly", "known")
        }
        occurrence_order = torch.argsort(self.occurrence_symbols, stable=True)
        self.form_symbols, form_counts = torch.unique_consecutive(
            self.occurrence_symbols[occurrence_order], return_counts=True,
        )
        self.form_occurrence_offsets = torch.cat((
            torch.zeros(1, dtype=torch.long, device=self.device), form_counts.cumsum(0),
        ))
        self.form_occurrences = occurrence_order
        self.parent_child_offsets, self.parent_child_occurrences = self._make_csr(
            len(self.parent_objects),
            [(self.parent_to_index[row["parent_object_id"]], index) for index, row in enumerate(self.structures)],
        )
        self.parent_relation_offsets, self.parent_relation_edges = self._make_csr(
            len(self.parent_objects),
            [(self.parent_to_index[row["parent_object_id"]], index) for index, row in enumerate(self.relations)],
        )
        self.parent_native_offsets, self.parent_native_occurrences = self._make_csr(
            len(self.parent_objects),
            [
                (self.parent_to_index[row["parent_object_id"]], index)
                for index, row in enumerate(self.structures)
                if row["inside_native_identity_region"]
            ],
        )
        sentence_keys = sorted({
            (self.parent_to_index[row["parent_object_id"]], int(row["sentence_ordinal"]))
            for row in self.structures
        })
        sentence_to_index = {key: index for index, key in enumerate(sentence_keys)}
        occurrence_sentences = []
        sentence_anchor_pairs: set[tuple[int, int]] = set()
        for row in self.structures:
            sentence_index = sentence_to_index[(self.parent_to_index[row["parent_object_id"]], int(row["sentence_ordinal"]))]
            occurrence_sentences.append(sentence_index)
            sentence_anchor_pairs.add((sentence_index, int(row["symbol"][2:], 16)))
            sentence_anchor_pairs.update((sentence_index, int(symbol[2:], 16)) for symbol in row["child_symbols"])
        self.occurrence_sentence_context = torch.tensor(occurrence_sentences, dtype=torch.long, device=self.device)
        self.sentence_anchor_offsets, self.sentence_anchor_symbols = self._make_csr(len(sentence_keys), list(sentence_anchor_pairs))
        self.sentence_occurrence_offsets, self.sentence_occurrences = self._make_csr(
            len(sentence_keys),
            [(sentence_index, occurrence_index) for occurrence_index, sentence_index in enumerate(occurrence_sentences)],
        )
        child_pairs = []
        for occurrence_index, row in enumerate(self.structures):
            child_pairs.extend((occurrence_index, int(symbol[2:], 16)) for symbol in row["child_symbols"])
        self.occurrence_child_offsets, self.occurrence_child_symbols = self._make_csr(len(self.structures), child_pairs)
        traversable_binding_rows = []
        for binding_index, row in enumerate(self.reference_bindings):
            if row["binding_status"] not in {"VERIFIED_EXACT_PARENT_IDENTITY", "VERIFIED_EXPLICIT_ALIAS", "AMBIGUOUS_PARENT_IDENTITY"}:
                continue
            for parent_id in row["candidate_parent_object_ids"]:
                traversable_binding_rows.append((
                    self.occurrence_to_index[row["mention_occurrence_id"]],
                    (binding_index, self.parent_to_index[parent_id]),
                ))
        binding_pairs = [(source, ordinal) for ordinal, (source, _) in enumerate(traversable_binding_rows)]
        self.mention_binding_offsets, binding_ordinals = self._make_csr(len(self.structures), binding_pairs)
        binding_targets = [target for _, (_, target) in traversable_binding_rows]
        binding_record_ids = [binding_index for _, (binding_index, _) in traversable_binding_rows]
        if binding_ordinals.numel():
            order = binding_ordinals.cpu().tolist()
            binding_targets = [binding_targets[index] for index in order]
            binding_record_ids = [binding_record_ids[index] for index in order]
        self.binding_target_parents = torch.tensor(binding_targets, dtype=torch.long, device=self.device)
        self.binding_record_indices = torch.tensor(binding_record_ids, dtype=torch.long, device=self.device)
        _assert_xpu(*(getattr(self, name) for name in tensors))
        _assert_xpu(
            self.parent_child_offsets, self.parent_child_occurrences,
            self.parent_relation_offsets, self.parent_relation_edges,
            self.parent_native_offsets, self.parent_native_occurrences,
            self.occurrence_sentence_context, self.sentence_anchor_offsets,
            self.sentence_anchor_symbols,
            self.sentence_occurrence_offsets, self.sentence_occurrences,
            self.occurrence_child_offsets, self.occurrence_child_symbols,
            self.mention_binding_offsets, self.binding_target_parents,
            self.binding_record_indices,
            self.position_posting_keys, self.position_posting_symbols,
            self.position_posting_positions, self.block_posting_offsets,
            self.parent_block_ids,
            self.form_symbols, self.form_occurrence_offsets, self.form_occurrences,
        )
        torch.xpu.synchronize()
        self.load_receipt = {
            "schema": "truemem_xpu_occurrence_graph_projection@2",
            "device": self.device_name, "device_type": "xpu",
            "structure_occurrences": len(self.structures),
            "relation_occurrence_edges": len(self.relations),
            "verified_reference_bindings": len(verified_bindings),
            "parent_objects": len(self.parent_objects),
            "adjacency": "CSR",
            "local_context_authority": "block_anchor_postings.awbin signed 6-1-6",
            "frontier_identity": "occurrence_id",
            "global_form_posting_broadcast": False,
            "cpu_role": "verified artifact loading and receipt serialization only",
            "frontier_math_on_cpu": False, "silent_device_fallback": False,
        }

    def _occurrence_anchor_cloud(
        self, occurrences: torch.Tensor, *, maximum_local_hops: int = 1,
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """Resolve exact signed 6-1-6 posting records for occurrences on XPU."""
        if not occurrences.numel():
            empty = torch.empty(0, dtype=torch.long, device=self.device)
            return empty, empty, empty, empty
        reach = 6 * int(maximum_local_hops)
        offsets = torch.cat((
            torch.arange(-reach, 0, dtype=torch.long, device=self.device),
            torch.arange(1, reach + 1, dtype=torch.long, device=self.device),
        ))
        blocks = self.occurrence_blocks[occurrences]
        starts = torch.tensor(
            [int(self.structures[index]["anchor_start"]) for index in occurrences.cpu().tolist()],
            dtype=torch.long, device=self.device,
        )
        wanted_positions = starts.unsqueeze(1) + offsets.unsqueeze(0)
        wanted_keys = blocks.unsqueeze(1) * 65536 + wanted_positions
        flat_keys = wanted_keys.flatten()
        indices = torch.searchsorted(self.position_posting_keys, flat_keys)
        in_range = indices < self.position_posting_keys.numel()
        safe = indices.clamp(max=max(0, self.position_posting_keys.numel() - 1))
        found = in_range & (self.position_posting_keys[safe] == flat_keys) & (wanted_positions.flatten() >= 0)
        owners = torch.arange(occurrences.numel(), device=self.device).repeat_interleave(offsets.numel())[found]
        symbols = self.position_posting_symbols[safe[found]]
        positions = wanted_positions.flatten()[found]
        signed_offsets = offsets.repeat(occurrences.numel())[found]
        _assert_xpu(owners, symbols, positions, signed_offsets)
        return owners, symbols, positions, signed_offsets

    def _bounded_context_qualification(
        self,
        occurrences: torch.Tensor,
        required_symbols: list[int],
        *,
        maximum_local_hops: int = 6,
    ) -> torch.Tensor:
        """Prove required anchors reachable through repeated native 6-1-6 steps."""
        owners, cloud_symbols, _, _ = self._occurrence_anchor_cloud(
            occurrences, maximum_local_hops=maximum_local_hops,
        )
        qualified = torch.ones(occurrences.numel(), dtype=torch.bool, device=self.device)
        for required in required_symbols:
            found = torch.zeros(occurrences.numel(), dtype=torch.long, device=self.device)
            match = cloud_symbols == required
            if bool(match.any().item()):
                found.scatter_add_(
                    0, owners[match],
                    torch.ones(int(match.sum().item()), dtype=torch.long, device=self.device),
                )
            qualified &= found > 0
        _assert_xpu(qualified)
        return qualified

    def _bounded_context_any_qualification(
        self,
        occurrences: torch.Tensor,
        required_symbols: list[int],
        *,
        maximum_local_hops: int = 6,
    ) -> torch.Tensor:
        """Prove at least one question-derived anchor in a bounded local cloud."""
        owners, cloud_symbols, _, _ = self._occurrence_anchor_cloud(
            occurrences, maximum_local_hops=maximum_local_hops,
        )
        if not required_symbols:
            return torch.zeros(occurrences.numel(), dtype=torch.bool, device=self.device)
        matched = torch.isin(cloud_symbols, torch.tensor(
            sorted(set(required_symbols)), dtype=torch.long, device=self.device,
        ))
        found = torch.zeros(occurrences.numel(), dtype=torch.long, device=self.device)
        if bool(matched.any().item()):
            found.scatter_add_(
                0, owners[matched],
                torch.ones(int(matched.sum().item()), dtype=torch.long, device=self.device),
            )
        qualified = found > 0
        _assert_xpu(qualified)
        return qualified

    def _context_witness_records(
        self,
        occurrence_index: int,
        required_symbols: list[int],
        *,
        maximum_local_hops: int = 6,
    ) -> list[dict[str, Any]]:
        """Serialize the closest exact posting witness for each proved anchor."""
        occurrence = torch.tensor([occurrence_index], dtype=torch.long, device=self.device)
        _, symbols, positions, offsets = self._occurrence_anchor_cloud(
            occurrence, maximum_local_hops=maximum_local_hops,
        )
        block = int(self.occurrence_blocks[occurrence_index].item())
        records = []
        for required in required_symbols:
            distances = offsets.abs()
            valid = symbols == required
            choices = torch.nonzero(valid, as_tuple=False).flatten()
            if not choices.numel():
                continue
            chosen = choices[torch.argmin(distances[choices])]
            witness_position = int(positions[chosen].item())
            signed_distance = int(offsets[chosen].item())
            distance = abs(signed_distance)
            records.append({
                "block_ordinal": block,
                "anchor_position": witness_position,
                "signed_distance": signed_distance,
                "minimum_local_hops": (distance + 5) // 6,
                "symbol": f"0x{required:012x}",
                "anchor": self.symbol_to_anchor[required],
            })
        return records

    def _explicit_alias_relation_mask(self, relation_edges: torch.Tensor) -> torch.Tensor:
        """Recognize exact admitted alias cues inside relation occurrences."""
        if not relation_edges.numel():
            return torch.empty(0, dtype=torch.bool, device=self.device)
        stored = self.edge_explicit_alias[relation_edges]
        relation_occurrences = self.edge_relation_occurrences[relation_edges]
        owners, symbols = self._expand_csr(
            self.occurrence_child_offsets, self.occurrence_child_symbols, relation_occurrences,
        )

        def has(anchor: str) -> torch.Tensor:
            values = self.alias_cue_symbols[anchor]
            result = torch.zeros(relation_edges.numel(), dtype=torch.long, device=self.device)
            if not values.numel():
                return result > 0
            matched = torch.isin(symbols, values)
            if bool(matched.any().item()):
                result.scatter_add_(0, owners[matched], torch.ones(int(matched.sum().item()), dtype=torch.long, device=self.device))
            return result > 0

        derived = (has("known") & has("as")) | (has("called") & (has("also") | has("formerly"))) | has("alias")
        result = stored | derived
        _assert_xpu(result)
        return result

    def _make_csr(self, row_count: int, pairs: list[tuple[int, int]]) -> tuple[torch.Tensor, torch.Tensor]:
        ordered = sorted(pairs, key=lambda row: (row[0], row[1]))
        counts = [0] * row_count
        for source, _ in ordered:
            counts[source] += 1
        offsets = [0]
        for count in counts:
            offsets.append(offsets[-1] + count)
        return (
            torch.tensor(offsets, dtype=torch.long, device=self.device),
            torch.tensor([target for _, target in ordered], dtype=torch.long, device=self.device),
        )

    def _expand_csr(
        self,
        offsets: torch.Tensor,
        values: torch.Tensor,
        rows: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """Return owner positions and CSR values without scanning unrelated rows."""
        if not rows.numel():
            empty = torch.empty(0, dtype=torch.long, device=self.device)
            return empty, empty
        starts = offsets[rows]
        lengths = offsets[rows + 1] - starts
        owners = torch.repeat_interleave(torch.arange(rows.numel(), device=self.device), lengths)
        total = int(lengths.sum().item())
        if not total:
            empty = torch.empty(0, dtype=torch.long, device=self.device)
            return empty, empty
        bases = torch.repeat_interleave(starts, lengths)
        prefix = torch.repeat_interleave(torch.cumsum(lengths, dim=0) - lengths, lengths)
        positions = bases + torch.arange(total, device=self.device) - prefix
        expanded = values[positions]
        _assert_xpu(owners, expanded)
        return owners, expanded

    def exact_postings(self, structure_keys: list[str]) -> dict[str, Any]:
        requested = [self.key_to_symbol[key] for key in structure_keys if key in self.key_to_symbol]
        if not requested:
            return {"occurrence_ids": [], "block_ids": [], "status": "NO_EXACT_STRUCTURE", "device": self.device_name}
        query = torch.tensor(sorted(set(requested)), dtype=torch.long, device=self.device)
        rows = torch.searchsorted(self.form_symbols, query)
        valid = (rows < self.form_symbols.numel()) & (self.form_symbols[rows.clamp(max=self.form_symbols.numel() - 1)] == query)
        _, indices = self._expand_csr(self.form_occurrence_offsets, self.form_occurrences, rows[valid])
        blocks = torch.unique(self.occurrence_blocks[indices], sorted=True)
        _assert_xpu(query, indices, blocks)
        torch.xpu.synchronize()
        return {
            "occurrence_ids": [self.structures[index]["occurrence_id"] for index in indices.cpu().tolist()],
            "block_ids": [int(value) for value in blocks.cpu().tolist()],
            "status": "EXACT_STRUCTURE_POSTINGS", "device": self.device_name,
            "silent_device_fallback": False,
        }

    def walk_pressure(
        self,
        structure_keys: list[str],
        pressure_specs: list[dict[str, Any]],
        *,
        start_block_ids: list[int],
        maximum_rounds: int = 6,
        maximum_branches: int = 4096,
    ) -> dict[str, Any]:
        """Traverse parent clouds with exact pressure masks on XPU CSR arrays."""
        import copy

        start_symbols = sorted({self.key_to_symbol[key] for key in structure_keys if key in self.key_to_symbol})
        if not start_symbols or not start_block_ids:
            return {"status": "NO_ADMITTED_START_EVIDENCE", "branches": [], "device": self.device_name}
        symbols = torch.tensor(start_symbols, dtype=torch.long, device=self.device)
        blocks = torch.tensor(sorted(set(start_block_ids)), dtype=torch.long, device=self.device)
        form_rows = torch.searchsorted(self.form_symbols, symbols)
        valid_forms = (form_rows < self.form_symbols.numel()) & (
            self.form_symbols[form_rows.clamp(max=self.form_symbols.numel() - 1)] == symbols
        )
        _, supplied_occurrences = self._expand_csr(
            self.form_occurrence_offsets, self.form_occurrences, form_rows[valid_forms],
        )
        start_occurrences = supplied_occurrences[
            torch.isin(self.occurrence_blocks[supplied_occurrences], blocks)
        ]
        if not start_occurrences.numel():
            return {"status": "NO_VALID_FRONTIER", "branches": [], "device": self.device_name}
        parents = torch.unique(self.occurrence_parents[start_occurrences], sorted=True)
        pressure_count = len(pressure_specs)
        masks = torch.zeros((parents.numel(), pressure_count), dtype=torch.bool, device=self.device)
        ruling_seen = torch.zeros_like(masks)
        histories = torch.full((parents.numel(), maximum_rounds + 1), -1, dtype=torch.long, device=self.device)
        histories[:, 0] = parents
        branch_meta = [
            {
                "branch_id": index,
                "predecessor_branch_id": None,
                "current_parent_object_id": self.parent_objects[parent]["parent_object_id"],
                "incoming_binding_id": None,
                "pressure_evidence": {spec["pressure_id"]: [] for spec in pressure_specs},
                "transition_evidence": [],
                "parent_path": [self.parent_objects[parent]["parent_object_id"]],
            }
            for index, parent in enumerate(parents.cpu().tolist())
        ]
        next_branch_id = len(branch_meta)
        terminal: list[dict[str, Any]] = []
        rounds = []
        global_status = "TRAVERSAL_BUDGET_EXHAUSTED"

        def tensor(values: list[int]) -> torch.Tensor:
            return torch.tensor(sorted(set(values)), dtype=torch.long, device=self.device)

        def branch_any(owner: torch.Tensor, match: torch.Tensor, count: int) -> torch.Tensor:
            result = torch.zeros(count, dtype=torch.long, device=self.device)
            if owner.numel() and bool(match.any().item()):
                result.scatter_add_(0, owner[match], torch.ones(int(match.sum().item()), dtype=torch.long, device=self.device))
            return result > 0

        for round_index in range(maximum_rounds):
            branch_count = int(parents.numel())
            cloud_owner, cloud_occurrences = self._expand_csr(self.parent_child_offsets, self.parent_child_occurrences, parents)
            relation_owner, relation_edges = self._expand_csr(self.parent_relation_offsets, self.parent_relation_edges, parents)
            cloud_symbols = self.occurrence_symbols[cloud_occurrences]
            previous_masks = masks.clone()
            evidence_by_pressure: list[dict[int, list[dict[str, Any]]]] = []

            for pressure_index, spec in enumerate(pressure_specs):
                ruling_symbols = tensor(spec["ruling_symbols"])
                ruling_match = torch.isin(cloud_symbols, ruling_symbols)
                ruling_seen[:, pressure_index] |= branch_any(cloud_owner, ruling_match, branch_count)
                evidence_match = torch.zeros(branch_count, dtype=torch.bool, device=self.device)
                evidence: dict[int, list[dict[str, Any]]] = {}
                if spec["kind"] == "EXACT_STRUCTURE":
                    matched = torch.isin(cloud_symbols, tensor(spec["exact_symbols"]))
                    evidence_match = branch_any(cloud_owner, matched, branch_count)
                    for position in torch.nonzero(matched, as_tuple=False).flatten().cpu().tolist():
                        branch = int(cloud_owner[position].item())
                        evidence.setdefault(branch, []).append({
                            "record_kind": "STRUCTURE_OCCURRENCE",
                            "occurrence": self.structures[int(cloud_occurrences[position].item())],
                        })
                elif spec["kind"] == "EXACT_CONTEXT_ANCHORS":
                    parent_blocks = self.parent_block_ids[parents]
                    context_owner, context_symbols = self._expand_csr(
                        self.block_posting_offsets, self.position_posting_symbols, parent_blocks,
                    )
                    _, context_positions = self._expand_csr(
                        self.block_posting_offsets, self.position_posting_positions, parent_blocks,
                    )
                    evidence_match = torch.ones(branch_count, dtype=torch.bool, device=self.device)
                    matched_context = torch.zeros(context_symbols.numel(), dtype=torch.bool, device=self.device)
                    for required in spec["context_symbols"]:
                        match = context_symbols == required
                        evidence_match &= branch_any(context_owner, match, branch_count)
                        matched_context |= match
                    for position in torch.nonzero(matched_context, as_tuple=False).flatten().cpu().tolist():
                        branch = int(context_owner[position].item())
                        evidence.setdefault(branch, []).append({
                            "record_kind": "CONTEXT_CLOUD_ANCHOR",
                            "block_ordinal": int(parent_blocks[branch].item()),
                            "anchor_position": int(context_positions[position].item()),
                            "anchor": self.symbol_to_anchor[int(context_symbols[position].item())],
                            "symbol": f"0x{int(context_symbols[position].item()):012x}",
                        })
                elif spec["kind"] == "EXACT_RELATION_FIELD":
                    rel_occurrences = self.edge_relation_occurrences[relation_edges] if relation_edges.numel() else relation_edges
                    child_owner, child_symbols = self._expand_csr(self.occurrence_child_offsets, self.occurrence_child_symbols, rel_occurrences)
                    relation_qualifies = torch.ones(relation_edges.numel(), dtype=torch.bool, device=self.device)
                    for required in spec["relation_field_symbols"]:
                        present = torch.zeros(relation_edges.numel(), dtype=torch.long, device=self.device)
                        match = child_symbols == required
                        if bool(match.any().item()):
                            present.scatter_add_(0, child_owner[match], torch.ones(int(match.sum().item()), dtype=torch.long, device=self.device))
                        relation_qualifies &= present > 0
                    evidence_match = branch_any(relation_owner, relation_qualifies, branch_count)
                    for position in torch.nonzero(relation_qualifies, as_tuple=False).flatten().cpu().tolist():
                        branch = int(relation_owner[position].item())
                        edge_index = int(relation_edges[position].item())
                        edge = self.relations[edge_index]
                        evidence.setdefault(branch, []).append({
                            "record_kind": "RELATION_CONTEXT",
                            "relation": edge,
                            "subject_occurrence": self.structures[self.occurrence_to_index[edge["subject_occurrence_id"]]],
                            "relation_occurrence": self.structures[self.occurrence_to_index[edge["relation_occurrence_id"]]],
                            "object_occurrence": self.structures[self.occurrence_to_index[edge["object_occurrence_id"]]],
                        })
                elif spec["kind"] == "EXPLICIT_ALIAS":
                    alias_match = self._explicit_alias_relation_mask(relation_edges)
                    evidence_match = branch_any(relation_owner, alias_match, branch_count)
                    for position in torch.nonzero(alias_match, as_tuple=False).flatten().cpu().tolist():
                        branch = int(relation_owner[position].item())
                        edge_index = int(relation_edges[position].item())
                        edge = self.relations[edge_index]
                        evidence.setdefault(branch, []).append({
                            "record_kind": "EXPLICIT_ALIAS_RELATION",
                            "relation": edge,
                            "subject_occurrence": self.structures[self.occurrence_to_index[edge["subject_occurrence_id"]]],
                            "relation_occurrence": self.structures[self.occurrence_to_index[edge["relation_occurrence_id"]]],
                            "object_occurrence": self.structures[self.occurrence_to_index[edge["object_occurrence_id"]]],
                        })
                evidence_by_pressure.append(evidence)
                if spec["kind"] != "EXACT_PARENT_TRANSITION":
                    masks[:, pressure_index] |= ruling_seen[:, pressure_index] & evidence_match

            newly_resolved = masks & ~previous_masks
            for pressure_index, evidence in enumerate(evidence_by_pressure):
                for branch, records in evidence.items():
                    if bool(masks[branch, pressure_index].item()):
                        branch_meta[branch]["pressure_evidence"][pressure_specs[pressure_index]["pressure_id"]].extend(records)

            complete = masks.all(dim=1) if pressure_count else torch.zeros(branch_count, dtype=torch.bool, device=self.device)
            for branch in torch.nonzero(complete, as_tuple=False).flatten().cpu().tolist():
                row = copy.deepcopy(branch_meta[branch])
                row["termination"] = "ALL_PRESSURE_POINTS_RESOLVED"
                row["satisfied_pressure_ids"] = [spec["pressure_id"] for spec in pressure_specs]
                terminal.append(row)

            incomplete = ~complete
            if bool(complete.any().item()):
                rounds.append({
                    "round": round_index + 1,
                    "branches_inspected": branch_count,
                    "context_occurrences_inspected": int(cloud_occurrences.numel()),
                    "relation_occurrences_inspected": int(relation_edges.numel()),
                    "verified_or_ambiguous_bindings": 0,
                    "parent_transitions": 0,
                    "pressure_resolutions": int(newly_resolved.sum().item()),
                    "completed_branches": int(complete.sum().item()),
                })
                for branch in torch.nonzero(incomplete, as_tuple=False).flatten().cpu().tolist():
                    row = copy.deepcopy(branch_meta[branch])
                    row["termination"] = "EVIDENCE_WORKSPACE_COMPLETE"
                    row["satisfied_pressure_ids"] = [
                        pressure_specs[index]["pressure_id"]
                        for index in torch.nonzero(masks[branch], as_tuple=False).flatten().cpu().tolist()
                    ]
                    terminal.append(row)
                global_status = "ALL_PRESSURE_POINTS_RESOLVED"
                break
            mention_owner, binding_targets = self._expand_csr(self.mention_binding_offsets, self.binding_target_parents, cloud_occurrences)
            _, binding_records = self._expand_csr(self.mention_binding_offsets, self.binding_record_indices, cloud_occurrences)
            source_branches = cloud_owner[mention_owner] if mention_owner.numel() else mention_owner
            mentions = cloud_occurrences[mention_owner] if mention_owner.numel() else mention_owner
            valid = incomplete[source_branches] if source_branches.numel() else torch.empty(0, dtype=torch.bool, device=self.device)
            transition_eligible = torch.zeros_like(valid)
            if mentions.numel():
                # A caller may provide exact context witnesses, but production
                # query planning does not.  In that path, a mention may cross
                # parents only when it is an endpoint of an exact relation in
                # the bounded current-parent cloud.
                occurrence_base = max(1, len(self.structures))
                mention_keys = source_branches * occurrence_base + mentions
                for pressure_index, spec in enumerate(pressure_specs):
                    required_context = spec["transition_context_symbols"]
                    if not required_context:
                        if relation_edges.numel():
                            sources = self.edge_sources[relation_edges]
                            targets = self.edge_targets[relation_edges]
                            source_symbols = self.occurrence_symbols[sources]
                            target_symbols = self.occurrence_symbols[targets]
                            ruling_symbols = tensor(spec["ruling_symbols"])
                            source_is_ruling = torch.isin(source_symbols, ruling_symbols)
                            target_is_ruling = torch.isin(target_symbols, ruling_symbols)
                            linked_endpoints = torch.cat((targets[source_is_ruling], sources[target_is_ruling]))
                            linked_owners = torch.cat((relation_owner[source_is_ruling], relation_owner[target_is_ruling]))
                            linked_keys = linked_owners * occurrence_base + linked_endpoints
                            context_match = torch.isin(mention_keys, linked_keys)
                        else:
                            context_match = torch.zeros_like(transition_eligible)
                    else:
                        if round_index == 0 and spec.get("transition_context_mode") == "ANY":
                            # The admitted starting parent is already selected
                            # by an exact ruling occurrence.  Its verified
                            # reference bindings are the first bounded context
                            # cloud and remain independent candidate paths.
                            # Later rounds require renewed question pressure.
                            context_match = torch.ones_like(transition_eligible)
                        elif spec.get("transition_context_mode") == "ANY":
                            context_match = self._bounded_context_any_qualification(
                                mentions, required_context, maximum_local_hops=6,
                            )
                        else:
                            context_match = self._bounded_context_qualification(
                                mentions, required_context, maximum_local_hops=6,
                            )
                    transition_eligible |= (
                        ruling_seen[source_branches, pressure_index]
                        & ~masks[source_branches, pressure_index]
                        & context_match
                    )
            valid &= transition_eligible
            if valid.numel():
                valid &= binding_targets != parents[source_branches]
                valid &= ~(histories[source_branches] == binding_targets.unsqueeze(1)).any(dim=1)
            source_branches = source_branches[valid]
            mentions = mentions[valid]
            binding_targets = binding_targets[valid]
            binding_records = binding_records[valid]

            pressure_resolutions = int(newly_resolved.sum().item())
            transition_count = int(binding_targets.numel())
            rounds.append({
                "round": round_index + 1,
                "branches_inspected": branch_count,
                "context_occurrences_inspected": int(cloud_occurrences.numel()),
                "relation_occurrences_inspected": int(relation_edges.numel()),
                "verified_or_ambiguous_bindings": int(binding_records.numel()),
                "parent_transitions": transition_count,
                "pressure_resolutions": pressure_resolutions,
                "completed_branches": int(complete.sum().item()),
            })
            if not transition_count:
                global_status = "ALL_PRESSURE_POINTS_RESOLVED" if bool(complete.all().item()) else "NO_NEW_VERIFIED_STATE"
                for branch in torch.nonzero(incomplete, as_tuple=False).flatten().cpu().tolist():
                    row = copy.deepcopy(branch_meta[branch])
                    row["termination"] = "NO_NEW_VERIFIED_STATE"
                    row["satisfied_pressure_ids"] = [pressure_specs[index]["pressure_id"] for index in torch.nonzero(masks[branch], as_tuple=False).flatten().cpu().tolist()]
                    terminal.append(row)
                break
            if transition_count > maximum_branches:
                global_status = "TRAVERSAL_BUDGET_EXHAUSTED"
                for branch in range(branch_count):
                    row = copy.deepcopy(branch_meta[branch])
                    row["termination"] = "TRAVERSAL_BUDGET_EXHAUSTED"
                    terminal.append(row)
                break

            new_parents = binding_targets
            new_histories = histories[source_branches].clone()
            new_histories[:, round_index + 1] = new_parents
            new_masks = masks[source_branches].clone()
            new_ruling = ruling_seen[source_branches].clone()
            new_meta = []
            native_owner, native_occurrences = self._expand_csr(self.parent_native_offsets, self.parent_native_occurrences, new_parents)
            native_symbols = self.occurrence_symbols[native_occurrences]
            for output_index in range(transition_count):
                source_branch = int(source_branches[output_index].item())
                mention_index = int(mentions[output_index].item())
                binding_index = int(binding_records[output_index].item())
                target_parent_index = int(new_parents[output_index].item())
                binding = self.reference_bindings[binding_index]
                raw_owner, raw_symbols, raw_positions, raw_offsets = self._occurrence_anchor_cloud(
                    mentions[output_index].reshape(1)
                )
                del raw_owner
                row = copy.deepcopy(branch_meta[source_branch])
                row["predecessor_branch_id"] = row["branch_id"]
                row["branch_id"] = next_branch_id
                next_branch_id += 1
                row["current_parent_object_id"] = self.parent_objects[target_parent_index]["parent_object_id"]
                row["incoming_binding_id"] = binding["binding_id"]
                row["parent_path"].append(row["current_parent_object_id"])
                transition_record = {
                    "record_kind": "PARENT_TRANSITION_CONTEXT",
                    "mention_occurrence": self.structures[mention_index],
                    "binding": binding,
                    "source_parent": self.parent_objects[int(parents[source_branch].item())],
                    "target_parent": self.parent_objects[target_parent_index],
                    "transition_context_occurrences": [
                        self.structures[index]
                        for index in self._expand_csr(
                            self.sentence_occurrence_offsets,
                            self.sentence_occurrences,
                            self.occurrence_sentence_context[mentions[output_index]].reshape(1),
                        )[1].cpu().tolist()
                    ],
                    "transition_context_records": [
                        {
                            "block_ordinal": int(self.occurrence_blocks[mention_index].item()),
                            "anchor_position": int(position),
                            "signed_offset": int(offset),
                            "symbol": f"0x{int(symbol):012x}",
                            "anchor": self.symbol_to_anchor[int(symbol)],
                        }
                        for symbol, position, offset in zip(
                            raw_symbols.cpu().tolist(),
                            raw_positions.cpu().tolist(),
                            raw_offsets.cpu().tolist(),
                        )
                    ],
                    "transition_path_witnesses": [
                        {
                            "pressure_id": spec["pressure_id"],
                            "required_anchor_records": self._context_witness_records(
                                mention_index, spec["transition_context_symbols"], maximum_local_hops=6,
                            ),
                            "maximum_local_hops": 6,
                            "native_lane_width": 6,
                        }
                        for spec in pressure_specs
                        if spec["transition_context_symbols"]
                        and bool(new_ruling[output_index, pressure_specs.index(spec)].item())
                        and not bool(new_masks[output_index, pressure_specs.index(spec)].item())
                        and bool(self._bounded_context_qualification(
                            mentions[output_index].reshape(1),
                            spec["transition_context_symbols"], maximum_local_hops=6,
                        )[0].item())
                    ],
                }
                row["transition_evidence"].append(transition_record)
                new_meta.append(row)
                mention_symbol = int(self.occurrence_symbols[mention_index].item())
                target_symbols = native_symbols[native_owner == output_index]
                for pressure_index, spec in enumerate(pressure_specs):
                    if spec["kind"] != "EXACT_PARENT_TRANSITION" or not bool(new_ruling[output_index, pressure_index].item()):
                        continue
                    mention_ok = mention_symbol in spec["mention_symbols"]
                    target_ok = bool(torch.isin(target_symbols, tensor(spec["target_symbols"])).any().item())
                    if mention_ok and target_ok:
                        new_masks[output_index, pressure_index] = True
                        row["pressure_evidence"][spec["pressure_id"]].append(transition_record)
            parents, histories, masks, ruling_seen, branch_meta = new_parents, new_histories, new_masks, new_ruling, new_meta
        else:
            for branch in range(len(branch_meta)):
                row = copy.deepcopy(branch_meta[branch])
                row["termination"] = "TRAVERSAL_BUDGET_EXHAUSTED"
                terminal.append(row)

        _assert_xpu(parents, histories, masks, ruling_seen)
        torch.xpu.synchronize()
        return {
            "schema": "truemem_xpu_pressure_traversal@2",
            "status": global_status,
            "branches": terminal,
            "rounds": rounds,
            "pressure_point_count": pressure_count,
            "device": self.device_name, "device_type": "xpu",
            "adjacency": "CSR", "whole_array_hot_path_scans": False,
            "local_cloud_before_cross_parent": True,
            "ambiguous_bindings_preserved": True,
            "independent_paths_preserved": True,
            "global_fixed_point": "NO_NEW_VERIFIED_STATE",
            "cpu_relationship_math": False, "cpu_frontier_ranking": False,
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
