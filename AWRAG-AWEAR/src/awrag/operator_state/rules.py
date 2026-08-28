from __future__ import annotations

from typing import Any

from .anchors import CONFUSION_ANCHORS, THREAT_ANCHORS, URGENCY_ANCHORS
from .modes import (
    ACTION_AUDIT_ONLY,
    AMBIGUITY_MODE,
    DESTRUCTIVE_COMMAND_LOCK,
    EVIDENCE_AUDIT_MODE,
    SYSTEM_COMMAND_MODE,
    TASK_MODE,
    VENT_MODE,
)


def compute_anchor_scores(extracted: dict[str, list[str]]) -> dict[str, float]:
    anger = _score(extracted["affect_anchors"], 3)
    urgency = _score(_intersection(extracted["risk_anchors"], URGENCY_ANCHORS), 2)
    confusion = _score(_intersection(extracted["risk_anchors"], CONFUSION_ANCHORS), 2)
    care_priority = _score(extracted["care_priority_anchors"], 2)
    threat_language = _score(_intersection(extracted["risk_anchors"], THREAT_ANCHORS), 1)
    mutation_risk = _score(extracted["mutation_anchors"], 2)
    destructive_intent = max(threat_language, mutation_risk)
    ambiguity_pressure = _score(extracted["ambiguity_anchors"], 2)
    target_specificity = max(0.0, min(1.0, _score(extracted["target_anchors"], 2) - (0.35 * ambiguity_pressure)))
    proof_burden = max(anger, urgency, confusion, threat_language, mutation_risk, _score(extracted["evidence_anchors"], 2))
    return {
        "anger": anger,
        "urgency": urgency,
        "confusion": confusion,
        "care_priority": care_priority,
        "threat_language": threat_language,
        "destructive_intent": destructive_intent,
        "target_specificity": target_specificity,
        "proof_burden": proof_burden,
        "mutation_risk": mutation_risk,
    }


def build_structural_analysis(extracted: dict[str, list[str]], scores: dict[str, float]) -> dict[str, Any]:
    destructive_command = bool(extracted["mutation_anchors"]) or scores["destructive_intent"] >= 0.5
    return {
        "command_anchor_present": bool(extracted["command_anchors"]),
        "destructive_command": destructive_command,
        "target_anchor_present": bool(extracted["target_anchors"]),
        "target_is_ambiguous": bool(extracted["ambiguity_anchors"]) and scores["target_specificity"] < 0.75,
        "proof_burden_anchor_required": scores["proof_burden"] > 0,
        "mutation_allowed": False,
    }


def select_operational_routing(
    extracted: dict[str, list[str]],
    scores: dict[str, float],
    structural: dict[str, Any],
) -> dict[str, str]:
    command_present = bool(structural["command_anchor_present"])
    target_specific = scores["target_specificity"] >= 0.35
    high_affect = max(scores["anger"], scores["threat_language"], scores["confusion"]) > 0

    if structural["destructive_command"] and high_affect:
        return _routing(DESTRUCTIVE_COMMAND_LOCK, "RULE_01_DESTRUCTIVE_HIGH_AFFECT")
    if scores["urgency"] > 0 and command_present and not target_specific:
        return _routing(AMBIGUITY_MODE, "RULE_02_URGENCY_MISSING_TARGET")
    if scores["anger"] > 0 and not command_present:
        return _routing(VENT_MODE, "RULE_03_VENT_NO_COMMAND")
    if scores["care_priority"] > 0 and command_present and target_specific and not structural["destructive_command"]:
        return _routing(SYSTEM_COMMAND_MODE, "RULE_04_CARE_VALID_SYSTEM_COMMAND")
    if extracted["evidence_anchors"]:
        return _routing(EVIDENCE_AUDIT_MODE, "RULE_05_EVIDENCE_REQUEST")
    if command_present and target_specific and scores["mutation_risk"] == 0:
        return _routing(TASK_MODE, "RULE_06_CLEAR_TASK")
    if command_present:
        return _routing(AMBIGUITY_MODE, "RULE_02_URGENCY_MISSING_TARGET")
    return _routing(VENT_MODE, "RULE_03_VENT_NO_COMMAND")


def system_output_for_mode(mode: str) -> dict[str, str]:
    messages = {
        DESTRUCTIVE_COMMAND_LOCK: "Destructive command blocked. Target anchor is ambiguous. Provide explicit file paths and re-verify execution.",
        AMBIGUITY_MODE: "Command not executable. Target anchor missing. Provide dataset id, file path, or operation boundary.",
        VENT_MODE: "Operator vent detected. No executable command found. No state changes made.",
        EVIDENCE_AUDIT_MODE: "Evidence audit mode selected. Provide claim, source, or receipt target.",
        SYSTEM_COMMAND_MODE: "System command shape detected. Audit-only mode active. No execution performed.",
        TASK_MODE: "Task-shaped input detected. Audit-only mode active. No execution performed.",
    }
    return {
        "receipt_type": "osrl_v0_audit",
        "payload": messages.get(mode, "Boundary mode selected. Audit-only mode active. No execution performed."),
    }


def _routing(selected_mode: str, rule: str) -> dict[str, str]:
    return {
        "selected_mode": selected_mode,
        "anchor_rule_triggered": rule,
        "action_state": ACTION_AUDIT_ONLY,
    }


def _score(values: list[str], divisor: int) -> float:
    return round(min(1.0, len(values) / max(1, divisor)), 4)


def _intersection(values: list[str], anchors: tuple[str, ...]) -> list[str]:
    allowed = set(anchors)
    return [value for value in values if value in allowed]

