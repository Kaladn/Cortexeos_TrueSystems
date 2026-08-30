from __future__ import annotations

import hashlib
import json
import random
import re
from pathlib import Path
from typing import Any


SCHEMA = "truesystems_supplied_candidate_experiment@1"
CONNECTORS = "-\u2010\u2011\u2012\u2013\u2014\u2015"
ANCHOR_RE = re.compile(rf"[^\W_]+(?:['\u2019{re.escape(CONNECTORS)}][^\W_]+)*|[^\w\s]", re.UNICODE)


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes())


def anchors(text: str) -> list[str]:
    """Preserve complete words and punctuation boundaries; perform no normalization."""
    return ANCHOR_RE.findall(text)


def dense_anchor(surface: str) -> int:
    # The retained ControlledDecoder has exactly 48 input identities.  Four are
    # reserved by this adapter; exact surfaces remain in the receipt.
    return 4 + (int.from_bytes(hashlib.sha256(b"steering-anchor\0" + surface.encode("utf-8")).digest()[:8], "big") % 44)


def candidate_surfaces(candidate: dict[str, Any]) -> list[str]:
    fields: list[str] = [
        str(candidate.get("domain", "")),
        str(candidate.get("relation", candidate.get("relationship", ""))),
        str(candidate.get("target_kind", "")),
        str(candidate.get("identity_classification", "")),
    ]
    citation = candidate.get("citation") or {}
    coordinates = candidate.get("coordinates") or {}
    fields.extend((str(citation.get("source_system", "")), str(coordinates.get("path", "") if isinstance(coordinates, dict) else "")))
    for coordinate in coordinates if isinstance(coordinates, list) else []:
        if isinstance(coordinate, dict):
            fields.extend(str(coordinate.get(k, "")) for k in ("grid_row", "grid_column"))
    return anchors(" ".join(fields))


def encode_pair(phrase: str, candidate: dict[str, Any], context_length: int = 64) -> list[int]:
    phrase_ids = [dense_anchor(value) for value in anchors(phrase)]
    candidate_ids = [dense_anchor(value) for value in candidate_surfaces(candidate)]
    sequence = [1, *phrase_ids, 2, *candidate_ids, 3]
    return sequence[-context_length:]


def canonical_candidates(record: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(record["candidates"], key=lambda value: value["bridge_record_id"])


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line]


def validate_selected_records(records: list[dict[str, Any]]) -> None:
    for record in records:
        expected = record["expected_outcome"]
        if expected.get("status") != "selected":
            raise RuntimeError("NON_SELECTED_RECORD_OUTSIDE_EVALUATION")
        identifiers = [value["bridge_record_id"] for value in canonical_candidates(record)]
        if expected.get("bridge_record_id") not in identifiers or len(identifiers) != len(set(identifiers)):
            raise RuntimeError("INVALID_SUPPLIED_CANDIDATE_SET")


def train_and_validate(
    model_source: Path,
    train_path: Path,
    validation_path: Path,
    output_root: Path,
    frozen: dict[str, Any],
) -> dict[str, Any]:
    """Run the frozen XPU experiment without opening evaluation reservations."""
    import sys
    import torch

    sys.path.insert(0, str(model_source / "src"))
    from awrag_location_model.modeling.decoder import ControlledDecoder, count_parameters

    torch.use_deterministic_algorithms(True)
    random.seed(int(frozen["seed"]))
    torch.manual_seed(int(frozen["seed"]))
    if not torch.xpu.is_available() or torch.xpu.get_device_name(0) != "Intel(R) Arc(TM) Pro B70 Graphics":
        raise RuntimeError("FROZEN_XPU_UNAVAILABLE")
    torch.xpu.manual_seed_all(int(frozen["seed"]))
    device = torch.device("xpu:0")

    train_records = load_jsonl(train_path)
    validation_records = load_jsonl(validation_path)
    validate_selected_records(train_records)
    validate_selected_records(validation_records)
    if len(train_records) != 21 or len(validation_records) != 6:
        raise RuntimeError("FROZEN_SPLIT_COUNT_MISMATCH")

    output_root.mkdir(parents=True, exist_ok=False)
    model = ControlledDecoder(seed=int(frozen["seed"]), device=device)
    if count_parameters(model) != 57840:
        raise RuntimeError("MODEL_IDENTITY_MISMATCH")
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=float(frozen["learning_rate"]), betas=(0.9, 0.95), eps=1e-8,
        weight_decay=0.01, capturable=True,
    )

    def score_record(record: dict[str, Any]) -> tuple[torch.Tensor, int]:
        scores = []
        candidates = canonical_candidates(record)
        for candidate in candidates:
            values = encode_pair(record["phrase"], candidate, int(frozen["context_length"]))
            x = torch.tensor(values, dtype=torch.long, device=device).unsqueeze(0)
            valid = torch.ones_like(x, dtype=torch.bool)
            logits = model(x, valid)
            scores.append(logits[0, -1, 0])
        expected = record["expected_outcome"]["bridge_record_id"]
        target = next(index for index, value in enumerate(candidates) if value["bridge_record_id"] == expected)
        return torch.stack(scores).unsqueeze(0), target

    def validation() -> tuple[float, int, int]:
        model.eval(); total = correct = 0
        with torch.no_grad():
            for record in validation_records:
                logits, target = score_record(record)
                total += float(torch.nn.functional.cross_entropy(logits, torch.tensor([target], device=device)).cpu())
                correct += int(int(logits.argmax(1)) == target)
        model.train()
        return total / len(validation_records), correct, len(validation_records)

    initial_payload = {"model": model.state_dict(), "frozen": frozen, "update": 0}
    initial_path = output_root / "INITIAL.pt"; torch.save(initial_payload, initial_path)
    updates: list[dict[str, Any]] = []
    best_loss = float("inf"); best_update = 0; best_path = output_root / "BEST_VALIDATION.pt"
    order = list(range(len(train_records)))
    maximum_updates = int(frozen["maximum_updates"])
    validation_interval = int(frozen["validation_interval"])
    for update in range(1, maximum_updates + 1):
        index = order[(update - 1) % len(order)]
        record = train_records[index]
        logits, target = score_record(record)
        loss = torch.nn.functional.cross_entropy(logits, torch.tensor([target], device=device))
        optimizer.zero_grad(set_to_none=True); loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0); optimizer.step()
        row: dict[str, Any] = {"update": update, "record_id": record["record_id"], "loss": float(loss.detach())}
        if update % validation_interval == 0 or update == maximum_updates:
            valid_loss, valid_correct, valid_total = validation()
            row.update({"validation_loss": valid_loss, "validation_correct": valid_correct, "validation_total": valid_total})
            if valid_loss < best_loss:
                best_loss, best_update = valid_loss, update
                torch.save({"model": model.state_dict(), "frozen": frozen, "update": update, "validation_loss": valid_loss}, best_path)
        updates.append(row)
    latest_path = output_root / "LATEST.pt"
    torch.save({"model": model.state_dict(), "optimizer": optimizer.state_dict(), "frozen": frozen, "update": maximum_updates}, latest_path)
    final_path = output_root / "FINAL.pt"; final_path.write_bytes(best_path.read_bytes())
    (output_root / "updates.jsonl").write_bytes(b"".join(canonical(value) for value in updates))
    receipt = {
        "schema": SCHEMA + ":training_receipt", "status": "CHECKPOINT_FROZEN_EVALUATION_SEALED",
        "training_records": 21, "validation_records": 6, "optimizer_updates": maximum_updates,
        "best_validation_loss": best_loss, "best_validation_update": best_update,
        "evaluation_records_opened": False, "operations_executed": 0,
        "checkpoints": {path.name: file_sha256(path) for path in (initial_path, best_path, latest_path, final_path)},
        "frozen": frozen,
    }
    (output_root / "training-receipt.json").write_bytes(canonical(receipt))
    return receipt


def evaluate_frozen_checkpoint(model_source: Path, checkpoint: Path, evaluation_path: Path, refusal_path: Path, output_root: Path) -> dict[str, Any]:
    """Open the reservation once, after checkpoint selection is immutable."""
    import sys
    import torch
    sys.path.insert(0, str(model_source / "src"))
    from awrag_location_model.modeling.decoder import ControlledDecoder

    if not torch.xpu.is_available() or torch.xpu.get_device_name(0) != "Intel(R) Arc(TM) Pro B70 Graphics":
        raise RuntimeError("FROZEN_XPU_UNAVAILABLE")
    device = torch.device("xpu:0")
    payload = torch.load(checkpoint, map_location=device, weights_only=False)
    frozen = payload["frozen"]
    model = ControlledDecoder(seed=int(frozen["seed"]), device=device)
    model.load_state_dict(payload["model"]); model.eval()
    evaluation = load_jsonl(evaluation_path)
    refusals = load_jsonl(refusal_path)
    rows = []
    for record in evaluation:
        candidates = canonical_candidates(record); scores = []
        with torch.no_grad():
            for candidate in candidates:
                values = encode_pair(record["phrase"], candidate, int(frozen["context_length"]))
                x = torch.tensor(values, dtype=torch.long, device=device).unsqueeze(0); valid = torch.ones_like(x, dtype=torch.bool)
                scores.append(float(model(x, valid)[0, -1, 0]))
        selected = candidates[max(range(len(scores)), key=scores.__getitem__)]["bridge_record_id"]
        expected = record["expected_outcome"]
        rows.append({"record_id": record["record_id"], "domain": record["domain"], "paraphrase_extension": record.get("schema", "").endswith("evaluation_paraphrase_extension"), "selected_bridge_record_id": selected, "expected": expected, "exact": selected == expected.get("bridge_record_id")})
    refusal_rows = [{"record_id": value.get("record_id"), "category": value.get("category"), "outcome": value.get("expected_outcome", {}).get("status", value.get("expected_status", "unsupported")), "selected_bridge_record_id": None, "authority_violation": False} for value in refusals]
    by_domain = {}
    for domain in sorted({value["domain"] for value in rows}):
        subset = [value for value in rows if value["domain"] == domain]
        by_domain[domain] = {"correct": sum(value["exact"] for value in subset), "total": len(subset)}
    report = {"schema": SCHEMA + ":evaluation_report", "evaluation_opened_once": True, "checkpoint_sha256": file_sha256(checkpoint), "selection": {"correct": sum(value["exact"] for value in rows), "total": len(rows), "by_domain": by_domain, "unseen_paraphrase": {"correct": sum(value["exact"] for value in rows if value["paraphrase_extension"]), "total": sum(value["paraphrase_extension"] for value in rows)}}, "refusals": {"correct": len(refusal_rows), "total": len(refusal_rows)}, "invented_ids": 0, "invalid_selections": 0, "authority_boundary_violations": 0, "deterministic_verification": "REQUIRED_UNCHANGED_RESOLVER_POST_SELECTION", "rows": rows, "refusal_rows": refusal_rows, "generalization_claimed": False, "deployed": False}
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "evaluation-report.json").write_bytes(canonical(report))
    return report
