from __future__ import annotations

AUDIT_SCHEMA = "awrag_osrl_operator_state_audit@1"
ANCHOR_GROUP_SCHEMA = "awrag_osrl_anchor_groups@1"
SCORE_SCHEMA = "awrag_osrl_anchor_scores@1"

ANCHOR_GROUP_NAMES = (
    "affect_anchors",
    "command_anchors",
    "target_anchors",
    "risk_anchors",
    "care_priority_anchors",
    "ambiguity_anchors",
    "evidence_anchors",
    "mutation_anchors",
)

SCORE_NAMES = (
    "anger",
    "urgency",
    "confusion",
    "care_priority",
    "threat_language",
    "destructive_intent",
    "target_specificity",
    "proof_burden",
    "mutation_risk",
)
