"""Freeze operator-authored, data-first parameterized evidence studies.

This module does not interpret a human request, inspect a dataset, choose a
statistical method, execute an analysis, or compose an answer.  The operator
agent performs those tasks.  The coded boundary validates that the operator
recorded the data layers, questions, agent-set parameters, isolation rules, and
output contract before computation, then emits a deterministic freeze receipt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


STUDY_SCHEMA = "truesystems_parameterized_evidence_study@1"
FREEZE_SCHEMA = "truesystems_parameterized_evidence_study_freeze@1"
PHASES = {
    "DATA_REQUESTED",
    "DATA_PROFILED",
    "QUESTION_REQUESTED",
    "PARAMETERS_DRAFTED",
    "PARAMETERS_LOCKED",
}
ANSWER_CLASSES = {"MEASUREMENT", "DESCRIPTIVE", "PROXY", "COUNTERFACTUAL"}
PARAMETER_SETTERS = {"agent", "human_override"}
SOURCE_KINDS = {"file", "directory", "database", "api", "stream", "artifact"}


class ParameterizedStudyContractError(ValueError):
    """Raised when a study plan is incomplete, ambiguous, or internally unsafe."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def stable_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_bytes(value)).hexdigest()


def validate_study_plan(plan: dict[str, Any], *, require_locked: bool = False) -> dict[str, Any]:
    """Return a canonical copy of a valid parameterized-study plan."""
    if not isinstance(plan, dict):
        raise ParameterizedStudyContractError("study plan must be an object")
    required = {
        "schema", "study_id", "original_request", "phase", "data_layers",
        "questions", "parameters", "isolation_rules", "output_contract",
        "operator_identity",
    }
    _require_fields(plan, required, "study plan")
    if plan["schema"] != STUDY_SCHEMA:
        raise ParameterizedStudyContractError("unsupported study schema")
    for field in ("study_id", "original_request", "operator_identity"):
        _nonempty_string(plan, field, "study plan")
    if plan["phase"] not in PHASES:
        raise ParameterizedStudyContractError("invalid study phase")
    if require_locked and plan["phase"] != "PARAMETERS_LOCKED":
        raise ParameterizedStudyContractError("study must be PARAMETERS_LOCKED before freezing or computation")

    phase = plan["phase"]
    layers = _object_list(plan["data_layers"], "data_layers", allow_empty=phase == "DATA_REQUESTED")
    layer_ids: list[str] = []
    layer_by_id: dict[str, dict[str, Any]] = {}
    for layer in layers:
        _require_fields(layer, {
            "layer_id", "source_ref", "source_sha256", "source_kind",
            "observed_fields", "observed_time_range", "authority",
            "allowed_question_ids", "forbidden_join_layer_ids",
        }, "data layer")
        for field in ("layer_id", "source_ref", "authority"):
            _nonempty_string(layer, field, "data layer")
        _sha256(layer["source_sha256"], "data layer source_sha256")
        if layer["source_kind"] not in SOURCE_KINDS:
            raise ParameterizedStudyContractError("data layer source_kind is invalid")
        _string_list(layer["observed_fields"], "observed_fields", allow_empty=False)
        _validate_time_range(layer["observed_time_range"])
        _string_list(layer["allowed_question_ids"], "allowed_question_ids", allow_empty=True)
        _string_list(layer["forbidden_join_layer_ids"], "forbidden_join_layer_ids", allow_empty=True)
        layer_ids.append(layer["layer_id"])
        layer_by_id[layer["layer_id"]] = layer
    _unique(layer_ids, "layer IDs")

    questions = _object_list(
        plan["questions"], "questions",
        allow_empty=phase in {"DATA_REQUESTED", "DATA_PROFILED", "QUESTION_REQUESTED"},
    )
    question_ids: list[str] = []
    question_by_id: dict[str, dict[str, Any]] = {}
    for question in questions:
        _require_fields(question, {
            "question_id", "text", "layer_ids", "answer_class",
            "required_fields", "unavailable_fields", "status",
        }, "question")
        for field in ("question_id", "text", "status"):
            _nonempty_string(question, field, "question")
        _string_list(question["layer_ids"], "question layer_ids", allow_empty=False)
        unknown_layers = sorted(set(question["layer_ids"]) - set(layer_ids))
        if unknown_layers:
            raise ParameterizedStudyContractError(f"question names unknown layers: {unknown_layers}")
        if question["answer_class"] not in ANSWER_CLASSES:
            raise ParameterizedStudyContractError("question answer_class is invalid")
        _string_list(question["required_fields"], "required_fields", allow_empty=False)
        _string_list(question["unavailable_fields"], "unavailable_fields", allow_empty=True)
        question_ids.append(question["question_id"])
        question_by_id[question["question_id"]] = question
    _unique(question_ids, "question IDs")

    for question in questions:
        for layer_id in question["layer_ids"]:
            if question["question_id"] not in layer_by_id[layer_id]["allowed_question_ids"]:
                raise ParameterizedStudyContractError(
                    f"question {question['question_id']} is not allowed by layer {layer_id}"
                )

    for layer in layers:
        unknown_questions = sorted(set(layer["allowed_question_ids"]) - set(question_ids))
        if unknown_questions:
            raise ParameterizedStudyContractError(f"data layer names unknown questions: {unknown_questions}")
        unknown_forbidden = sorted(set(layer["forbidden_join_layer_ids"]) - set(layer_ids))
        if unknown_forbidden:
            raise ParameterizedStudyContractError(f"data layer forbids unknown layers: {unknown_forbidden}")
        if layer["layer_id"] in layer["forbidden_join_layer_ids"]:
            raise ParameterizedStudyContractError("a data layer cannot forbid joining to itself")

    parameters = _object_list(
        plan["parameters"], "parameters",
        allow_empty=phase in {"DATA_REQUESTED", "DATA_PROFILED", "QUESTION_REQUESTED"},
    )
    parameter_ids: list[str] = []
    for parameter in parameters:
        _require_fields(parameter, {
            "parameter_id", "value", "value_type", "set_by", "rationale",
            "evidence_basis", "affects_question_ids", "locked",
        }, "parameter")
        for field in ("parameter_id", "value_type", "rationale", "evidence_basis"):
            _nonempty_string(parameter, field, "parameter")
        if parameter["set_by"] not in PARAMETER_SETTERS:
            raise ParameterizedStudyContractError("parameter set_by must be agent or human_override")
        if not isinstance(parameter["locked"], bool):
            raise ParameterizedStudyContractError("parameter locked must be boolean")
        if require_locked and not parameter["locked"]:
            raise ParameterizedStudyContractError(f"unlocked parameter: {parameter['parameter_id']}")
        _string_list(parameter["affects_question_ids"], "affects_question_ids", allow_empty=False)
        unknown_questions = sorted(set(parameter["affects_question_ids"]) - set(question_ids))
        if unknown_questions:
            raise ParameterizedStudyContractError(f"parameter names unknown questions: {unknown_questions}")
        if parameter["set_by"] == "human_override":
            _require_fields(parameter, {"agent_proposed_value", "override_reason"}, "human override parameter")
            _nonempty_string(parameter, "override_reason", "human override parameter")
        parameter_ids.append(parameter["parameter_id"])
    _unique(parameter_ids, "parameter IDs")

    rules = plan["isolation_rules"]
    if not isinstance(rules, list):
        raise ParameterizedStudyContractError("isolation_rules must be a list")
    rule_ids: list[str] = []
    forbidden_pairs: set[frozenset[str]] = set()
    for rule in rules:
        if not isinstance(rule, dict):
            raise ParameterizedStudyContractError("every isolation rule must be an object")
        _require_fields(rule, {"rule_id", "left_layer_id", "right_layer_id", "rule", "reason"}, "isolation rule")
        for field in ("rule_id", "left_layer_id", "right_layer_id", "rule", "reason"):
            _nonempty_string(rule, field, "isolation rule")
        if rule["left_layer_id"] not in layer_by_id or rule["right_layer_id"] not in layer_by_id:
            raise ParameterizedStudyContractError("isolation rule names an unknown layer")
        if rule["left_layer_id"] == rule["right_layer_id"]:
            raise ParameterizedStudyContractError("isolation rule must name two different layers")
        rule_ids.append(rule["rule_id"])
        if rule["rule"] == "FORBID_JOIN":
            forbidden_pairs.add(frozenset((rule["left_layer_id"], rule["right_layer_id"])))
    _unique(rule_ids, "isolation rule IDs")

    for question in questions:
        selected = question["layer_ids"]
        for left_index, left in enumerate(selected):
            for right in selected[left_index + 1:]:
                if frozenset((left, right)) in forbidden_pairs:
                    raise ParameterizedStudyContractError(
                        f"question {question['question_id']} crosses a forbidden layer join: {left}, {right}"
                    )
                if right in layer_by_id[left]["forbidden_join_layer_ids"] or left in layer_by_id[right]["forbidden_join_layer_ids"]:
                    raise ParameterizedStudyContractError(
                        f"question {question['question_id']} crosses a layer-declared forbidden join: {left}, {right}"
                    )

    output = plan["output_contract"]
    if not isinstance(output, dict):
        raise ParameterizedStudyContractError("output_contract must be an object")
    _require_fields(output, {
        "required_artifacts", "required_receipts", "timing_required",
        "failed_attempt_timing_required", "chart_label_rules", "claim_audit_required",
    }, "output contract")
    _string_list(output["required_artifacts"], "required_artifacts", allow_empty=False)
    _string_list(output["required_receipts"], "required_receipts", allow_empty=False)
    _string_list(output["chart_label_rules"], "chart_label_rules", allow_empty=False)
    for field in ("timing_required", "failed_attempt_timing_required", "claim_audit_required"):
        if not isinstance(output[field], bool):
            raise ParameterizedStudyContractError(f"output_contract {field} must be boolean")

    return json.loads(canonical_bytes(plan))


def freeze_study_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Validate a locked plan and return a deterministic computation gate receipt."""
    frozen = validate_study_plan(plan, require_locked=True)
    return {
        "schema": FREEZE_SCHEMA,
        "study_id": frozen["study_id"],
        "phase": "PARAMETERS_LOCKED",
        "frozen_plan": frozen,
        "frozen_plan_sha256": stable_hash(frozen),
        "computation_permitted": True,
        "evidence_authority_created": False,
        "relationship_authority_created": False,
        "answer_composed": False,
    }


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}")
    temporary.write_bytes(canonical_bytes(value) + b"\n")
    os.replace(temporary, path)


def _require_fields(value: dict[str, Any], required: set[str], label: str) -> None:
    missing = sorted(required.difference(value))
    if missing:
        raise ParameterizedStudyContractError(f"{label} missing fields: {missing}")


def _nonempty_string(value: dict[str, Any], field: str, label: str) -> None:
    if not isinstance(value.get(field), str) or not value[field].strip():
        raise ParameterizedStudyContractError(f"{label} {field} must be a non-empty string")


def _object_list(value: Any, label: str, *, allow_empty: bool) -> list[dict[str, Any]]:
    if not isinstance(value, list) or (not allow_empty and not value) or not all(isinstance(row, dict) for row in value):
        qualifier = "" if allow_empty else "non-empty "
        raise ParameterizedStudyContractError(f"{label} must be a {qualifier}list of objects")
    return value


def _string_list(value: Any, label: str, *, allow_empty: bool) -> None:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ParameterizedStudyContractError(f"{label} must be a {'non-empty ' if not allow_empty else ''}list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ParameterizedStudyContractError(f"{label} must contain only non-empty strings")
    _unique(value, label)


def _unique(values: list[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise ParameterizedStudyContractError(f"{label} must be unique")


def _sha256(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.startswith("sha256:") or len(value) != 71:
        raise ParameterizedStudyContractError(f"{label} must be sha256:<64 lowercase hex characters>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ParameterizedStudyContractError(f"{label} must be hexadecimal") from exc
    if value[7:] != value[7:].lower():
        raise ParameterizedStudyContractError(f"{label} must use lowercase hex")


def _validate_time_range(value: Any) -> None:
    if not isinstance(value, dict):
        raise ParameterizedStudyContractError("observed_time_range must be an object")
    _require_fields(value, {"start_utc", "end_utc", "resolution", "timezone_assumption"}, "observed_time_range")
    for field in ("start_utc", "end_utc", "resolution", "timezone_assumption"):
        if value[field] is not None and (not isinstance(value[field], str) or not value[field].strip()):
            raise ParameterizedStudyContractError(f"observed_time_range {field} must be null or a non-empty string")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate or freeze a parameterized TrueSystems study plan.")
    parser.add_argument("command", choices=("validate", "freeze"))
    parser.add_argument("plan", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    result = validate_study_plan(plan) if args.command == "validate" else freeze_study_plan(plan)
    if args.output:
        atomic_write_json(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
