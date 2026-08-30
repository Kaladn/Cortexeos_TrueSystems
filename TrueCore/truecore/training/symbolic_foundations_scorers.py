"""Untrained supplied-candidate scorers and deterministic readiness checks."""
from __future__ import annotations

import hashlib
import json
import random
import subprocess
from pathlib import Path
from typing import Any

import torch
from torch import nn
import torch.nn.functional as F

SCHEMA = "truesystems_symbolic_foundations_scorers@1"
SEED = 61613
UNSEEN_EXTERNAL_CALL = "UNSEEN_EXTERNAL_CALL"


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def digest(value: bytes | dict | list) -> str:
    return hashlib.sha256(value if isinstance(value, bytes) else canonical(value)).hexdigest()


def rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_bytes().splitlines() if line]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical(value) + b"\n")


def _seed() -> None:
    random.seed(SEED)
    torch.manual_seed(SEED)
    if hasattr(torch, "xpu") and torch.xpu.is_available():
        torch.xpu.manual_seed_all(SEED)
    torch.use_deterministic_algorithms(True)


class Local616SuppliedCandidateScorer(nn.Module):
    """Score only candidate symbols supplied with a local 6-1-6 record."""

    def __init__(self, identity_count: int) -> None:
        super().__init__()
        self.embedding = nn.Embedding(identity_count, 32)
        self.history = nn.GRU(32, 64, batch_first=True)
        self.head = nn.Sequential(nn.Linear(96, 64), nn.ReLU(), nn.Linear(64, 1))

    def forward(self, history_ids: torch.Tensor, candidate_ids: torch.Tensor) -> torch.Tensor:
        encoded = self.embedding(history_ids)
        _, state = self.history(encoded)
        context = state[-1].expand(candidate_ids.shape[0], -1)
        return self.head(torch.cat((context, self.embedding(candidate_ids)), dim=-1)).squeeze(-1)


class ExternalAstSuppliedCandidateScorer(nn.Module):
    """Score only candidate call identities supplied with one isolated AST record."""

    def __init__(self, identity_count: int, argument_kind_count: int) -> None:
        super().__init__()
        self.embedding = nn.Embedding(identity_count, 32)
        self.history = nn.GRU(32, 64, batch_first=True)
        self.argument_embedding = nn.Embedding(argument_kind_count, 32)
        self.head = nn.Sequential(nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, 1))

    def forward(self, call_ids: torch.Tensor, argument_kind_ids: torch.Tensor, candidate_ids: torch.Tensor) -> torch.Tensor:
        _, state = self.history(self.embedding(call_ids))
        context = state[-1].expand(candidate_ids.shape[0], -1)
        argument_summary = self.argument_embedding(argument_kind_ids).mean(dim=0).expand(candidate_ids.shape[0], -1)
        return self.head(torch.cat((context, argument_summary, self.embedding(candidate_ids)), dim=-1)).squeeze(-1)


def _load_retained_decoder(clean_source: Path) -> dict:
    commit = subprocess.run(["git", "-C", str(clean_source), "rev-parse", "HEAD"], capture_output=True, text=True, check=False).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(clean_source), "status", "--porcelain"], capture_output=True, text=True, check=False).stdout
    if commit != "170ad86c44a87cbbaa273719ac6231b2872d6f68" or dirty:
        raise ValueError("retained model checkout is not clean at frozen commit")
    root = clean_source / "src"
    module = root / "awrag_location_model/modeling/decoder.py"
    if not module.exists():
        raise ValueError("isolated retained model source is incomplete")
    import sys
    sys.path.insert(0, str(root))
    try:
        from awrag_location_model.modeling.decoder import ControlledDecoder, count_parameters
        model = ControlledDecoder(seed=SEED, device="cpu")
        with torch.no_grad():
            logits = model(torch.tensor([[1, 2, 3]], dtype=torch.long))
        return {"module": str(module.resolve()), "commit": commit, "clean_status_sha256": digest(dirty.encode()), "parameter_count": count_parameters(model), "forward_shape": list(logits.shape), "loaded": True}
    finally:
        sys.path.remove(str(root))


def _artifact(path: Path) -> dict:
    raw = path.read_bytes()
    return {"path": str(path.resolve()), "bytes": len(raw), "sha256": digest(raw)}


def _verify_representation(root: Path) -> dict:
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    if manifest.get("schema") not in ("truesystems_symbolic_foundations_representation@1", "truesystems_symbolic_foundations_replacement@1"):
        raise ValueError("unsupported representation")
    for item in manifest["artifacts"].values():
        path = root / item["path"]
        if digest(path.read_bytes()) != item["sha256"]:
            raise ValueError(f"representation artifact mismatch: {path}")
    return manifest


def _identity_maps(adapter_root: Path, representation_manifest: dict, representation_root: Path) -> tuple[dict[str, int], dict[str, int]]:
    adapter_manifest = adapter_root / "manifest.json"
    if digest(adapter_manifest.read_bytes()) != representation_manifest["adapter_manifest_sha256"]:
        raise ValueError("adapter identity mismatch")
    adapter = json.loads(adapter_manifest.read_bytes())
    lexicon = json.loads((adapter_root / adapter["artifacts"]["lexicon"]["path"]).read_bytes())
    symbol_by_anchor = {entry["anchor"]: int(entry["symbol"], 16) for entry in lexicon["anchors"]}
    external_values = set()
    for split in ("train", "validation"):
        for record in rows(representation_root / f"splits/external-{split}.jsonl"):
            external_values.add(record["center_call"]["name"])
            external_values.update(record["supplied_candidates"])
    external_values.add(UNSEEN_EXTERNAL_CALL)
    return symbol_by_anchor, {value: index for index, value in enumerate(sorted(external_values))}


def _assert_candidate_boundary(record: dict, selected: str) -> None:
    if selected not in record["supplied_candidates"]:
        raise ValueError("candidate identity escaped supplied field")


def _local_case(record: dict, symbols: dict[str, int], device: torch.device) -> tuple[Local616SuppliedCandidateScorer, torch.Tensor, int]:
    model = Local616SuppliedCandidateScorer(max(symbols.values()) + 1).to(device)
    history = record["history"] or [record["center_anchor"]]
    history_ids = torch.tensor([[symbols[value] for value in history]], dtype=torch.long, device=device)
    candidate_ids = torch.tensor([symbols[value] for value in record["supplied_candidates"]], dtype=torch.long, device=device)
    target_value = record["expected_outcome"]["anchor"]
    target = record["supplied_candidates"].index(target_value)
    _assert_candidate_boundary(record, target_value)
    return model, model(history_ids, candidate_ids), target


def _argument_kinds(record: dict) -> list[str]:
    kinds = [x.get("kind", "unavailable") for x in record["center_call"].get("arguments", [])]
    kinds.extend(x.get("argument", {}).get("kind", "unavailable") for x in record["center_call"].get("keywords", []))
    return kinds or ["none"]


def _external_case(record: dict, identities: dict[str, int], device: torch.device) -> tuple[ExternalAstSuppliedCandidateScorer, torch.Tensor, int]:
    kind_ids = {value: index for index, value in enumerate(("attribute", "expression", "literal", "name", "none", "unavailable"))}
    model = ExternalAstSuppliedCandidateScorer(len(identities), len(kind_ids)).to(device)
    center = torch.tensor([[identities[record["center_call"]["name"]]]], dtype=torch.long, device=device)
    arguments = torch.tensor([kind_ids[x] for x in _argument_kinds(record)], dtype=torch.long, device=device)
    candidates = torch.tensor([identities[x] for x in record["supplied_candidates"]], dtype=torch.long, device=device)
    target_value = record["expected_outcome"].get("call_identity", record["expected_outcome"].get("call_name"))
    target = record["supplied_candidates"].index(target_value)
    _assert_candidate_boundary(record, target_value)
    return model, model(center, arguments, candidates), target


def _run_once(local_record: dict, external_record: dict, symbols: dict[str, int], external_ids: dict[str, int], device_name: str) -> dict:
    _seed()
    device = torch.device(device_name)
    with torch.no_grad():
        local_model, local_logits, local_target = _local_case(local_record, symbols, device)
        external_model, external_logits, external_target = _external_case(external_record, external_ids, device)
        local_loss = F.cross_entropy(local_logits.unsqueeze(0), torch.tensor([local_target], device=device))
        external_loss = F.cross_entropy(external_logits.unsqueeze(0), torch.tensor([external_target], device=device))
    return {
        "local_logits": local_logits.cpu().tolist(), "local_loss": local_loss.cpu().item(),
        "external_logits": external_logits.cpu().tolist(), "external_loss": external_loss.cpu().item(),
        "local_parameters": sum(x.numel() for x in local_model.parameters()),
        "external_parameters": sum(x.numel() for x in external_model.parameters()),
    }


def build_scorer_readiness(representation_root: Path, adapter_root: Path, clean_model_source: Path, output: Path) -> dict:
    if output.exists():
        raise FileExistsError(output)
    representation_root, adapter_root, clean_model_source = (x.resolve() for x in (representation_root, adapter_root, clean_model_source))
    manifest = _verify_representation(representation_root)
    reserved = manifest["evaluation_records_reserved"]
    if reserved <= 0:
        raise ValueError("evaluation reservation missing")
    symbols, external_ids = _identity_maps(adapter_root, manifest, representation_root)
    local_records = rows(representation_root / "splits/local-train.jsonl") + rows(representation_root / "splits/local-validation.jsonl")
    external_records = rows(representation_root / "splits/external-train.jsonl") + rows(representation_root / "splits/external-validation.jsonl")
    for record in local_records:
        expected = record["expected_outcome"]["anchor"]
        _assert_candidate_boundary(record, expected)
        if any(value not in symbols for value in [record["center_anchor"], *record["history"], *record["supplied_candidates"]]):
            raise ValueError("local identity absent from frozen six-byte lexicon")
        if UNSEEN_EXTERNAL_CALL in record["supplied_candidates"]:
            raise ValueError("external sentinel entered local candidate field")
    for record in external_records:
        expected = record["expected_outcome"].get("call_identity", record["expected_outcome"].get("call_name"))
        _assert_candidate_boundary(record, expected)
        if any(value not in external_ids for value in [record["center_call"]["name"], *record["supplied_candidates"]]):
            raise ValueError("external identity absent from train/validation identity field")
    local_record = min(local_records, key=lambda x: x["record_id"])
    external_record = min((x for x in external_records if len(x["supplied_candidates"]) > 1), key=lambda x: x["record_id"])
    known = next(value for value in sorted(external_ids) if value != UNSEEN_EXTERNAL_CALL)
    synthetic = {
        "center_call": {"name": known, "arguments": [], "keywords": []},
        "supplied_candidates": [known, UNSEEN_EXTERNAL_CALL],
    }
    synthetic_checks = []
    for expected in (known, UNSEEN_EXTERNAL_CALL):
        fixture = {**synthetic, "expected_outcome": {"call_identity": expected}}
        _seed(); _, logits, target = _external_case(fixture, external_ids, torch.device("cpu"))
        loss = F.cross_entropy(logits.unsqueeze(0), torch.tensor([target]))
        synthetic_checks.append({"expected": expected, "target_index": target, "finite_loss": bool(torch.isfinite(loss)), "candidate_ids_distinct": external_ids[known] != external_ids[UNSEEN_EXTERNAL_CALL]})
    if not all(x["finite_loss"] and x["candidate_ids_distinct"] for x in synthetic_checks):
        raise ValueError("sentinel synthetic fixture failed")
    retained = _load_retained_decoder(clean_model_source)
    cpu_a = _run_once(local_record, external_record, symbols, external_ids, "cpu")
    cpu_b = _run_once(local_record, external_record, symbols, external_ids, "cpu")
    cpu_exact = canonical(cpu_a) == canonical(cpu_b)
    xpu = {"available": bool(hasattr(torch, "xpu") and torch.xpu.is_available()), "selected_for_future_training": False}
    if xpu["available"]:
        xpu_a = _run_once(local_record, external_record, symbols, external_ids, "xpu")
        xpu_b = _run_once(local_record, external_record, symbols, external_ids, "xpu")
        repeat_exact = canonical(xpu_a) == canonical(xpu_b)
        max_delta = max(abs(a-b) for key in ("local_logits", "external_logits") for a,b in zip(cpu_a[key], xpu_a[key]))
        losses_delta = max(abs(cpu_a[key]-xpu_a[key]) for key in ("local_loss", "external_loss"))
        xpu.update({"device_name": torch.xpu.get_device_name(), "repeat_exact": repeat_exact, "cpu_max_logit_delta": max_delta, "cpu_max_loss_delta": losses_delta, "equivalence_tolerance": 1e-5, "equivalent": repeat_exact and max(max_delta, losses_delta) <= 1e-5})
        xpu["selected_for_future_training"] = xpu["equivalent"]
    blockers = []
    if not cpu_exact:
        blockers.append("CPU_FORWARD_NOT_REPEATABLE")
    if not xpu.get("equivalent", False):
        blockers.append("XPU_EQUIVALENCE_NOT_PROVEN_CPU_SELECTED")
    result = {
        "schema": SCHEMA, "classification": "UNTRAINED_SCORERS_VERIFIED_NO_OPTIMIZER",
        "representation": _artifact(representation_root / "manifest.json"), "representation_release_id": manifest["release_id"],
        "evaluation": {"reserved_records": reserved, "payloads_opened": False},
        "retained_model": {**retained, "clean_source": str(clean_model_source), "expected_commit": "170ad86c", "weights_transferred": False},
        "candidate_contract": {"source": "record.supplied_candidates only", "generated_identity": False, "checked_records": len(local_records)+len(external_records)},
        "sentinel_contract": {"identity": UNSEEN_EXTERNAL_CALL, "external_only": True, "meaning": "identity unseen by this scorer", "equivalence": False, "operation": False, "authority": False, "generated_resolution": False},
        "sentinel_synthetic_checks": synthetic_checks,
        "smoke_records": {"local": local_record["record_id"], "external": external_record["record_id"], "splits_used": ["train", "validation"]},
        "cpu": {"repeat_exact": cpu_exact, **cpu_a}, "xpu": xpu,
        "future_training_device": "XPU" if xpu["selected_for_future_training"] else "CPU",
        "optimizer_policy": {"status": "FROZEN_NOT_EXECUTED", "name": "AdamW", "learning_rate": 0.001, "betas": [0.9, 0.95], "epsilon": 1e-8, "weight_decay": 0.01},
        "checkpoint_policy": {"status": "FROZEN_NO_CHECKPOINT_CREATED", "selection": "independent lowest validation cross-entropy; earliest epoch wins exact ties"},
        "blockers": blockers, "training_execution_allowed": False, "optimizer_updates": 0, "checkpoints_created": 0,
        "model_training_performed": False, "authority_created": False,
    }
    result["readiness_id"] = digest(result)
    write_json(output / "scorer-readiness.json", result)
    return result
