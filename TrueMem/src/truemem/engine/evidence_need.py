from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


EVIDENCE_NEED_SCHEMA = "truemem_evidence_need@1"
PROOF_FORMS = {"single_source_block"}


@dataclass(frozen=True)
class AnchorGroup:
    """One required evidence field; anchors within the group are alternatives."""

    field: str
    anchors: tuple[str, ...]
    required: bool = True

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any], *, expected_field: str | None = None) -> "AnchorGroup":
        if not isinstance(value, Mapping):
            raise TypeError("EVIDENCE_NEED_FIELD_MUST_BE_OBJECT")
        field = str(value.get("field") or "").strip()
        if expected_field is not None and field != expected_field:
            raise ValueError(f"EVIDENCE_NEED_FIELD_NAME_MISMATCH: expected={expected_field}; actual={field}")
        required = value.get("required", True)
        if not isinstance(required, bool):
            raise TypeError(f"EVIDENCE_NEED_REQUIRED_FLAG_MUST_BE_BOOLEAN: field={field or '<missing>'}")
        raw_anchors = value.get("anchors")
        if not isinstance(raw_anchors, list) or (required and not raw_anchors):
            raise ValueError(f"EVIDENCE_NEED_ANCHORS_REQUIRED: field={field or '<missing>'}")
        anchors = tuple(dict.fromkeys(str(anchor).strip() for anchor in raw_anchors if str(anchor).strip()))
        if not field or (required and not anchors):
            raise ValueError("EVIDENCE_NEED_FIELD_AND_ANCHORS_REQUIRED")
        if expected_field in {"subject", "relation"} and not required:
            raise ValueError(f"EVIDENCE_NEED_CORE_FIELD_REQUIRED: {expected_field}")
        return cls(field=field, anchors=anchors, required=required)

    def to_dict(self) -> dict[str, Any]:
        return {"field": self.field, "anchors": list(self.anchors), "required": self.required}


@dataclass(frozen=True)
class EvidenceNeed:
    """Only legal public input to TrueMem evidence retrieval.

    It intentionally has no question, claim, prompt, or expected-answer field.
    """

    need_id: str
    subject: AnchorGroup
    relation: AnchorGroup
    qualifiers: tuple[AnchorGroup, ...]
    quantity: AnchorGroup
    requested_proof_form: str
    schema: str = EVIDENCE_NEED_SCHEMA

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "EvidenceNeed":
        if not isinstance(value, Mapping):
            raise TypeError("EVIDENCE_NEED_OBJECT_REQUIRED")
        forbidden = sorted({"question", "claim", "prompt", "answer", "expected_answer"} & set(value))
        if forbidden:
            raise ValueError(f"ANSWER_SHAPED_INPUT_FORBIDDEN: {', '.join(forbidden)}")
        if value.get("schema") != EVIDENCE_NEED_SCHEMA:
            raise ValueError(f"EVIDENCE_NEED_SCHEMA_REQUIRED: {EVIDENCE_NEED_SCHEMA}")
        need_id = str(value.get("need_id") or "").strip()
        if not need_id:
            raise ValueError("EVIDENCE_NEED_ID_REQUIRED")
        qualifiers_raw = value.get("qualifiers")
        if not isinstance(qualifiers_raw, list) or not qualifiers_raw:
            raise ValueError("EVIDENCE_NEED_QUALIFIERS_REQUIRED")
        qualifiers = tuple(AnchorGroup.from_mapping(item) for item in qualifiers_raw)
        if len({group.field for group in qualifiers}) != len(qualifiers):
            raise ValueError("EVIDENCE_NEED_DUPLICATE_QUALIFIER_FIELD")
        proof_form = str(value.get("requested_proof_form") or "").strip()
        if proof_form not in PROOF_FORMS:
            raise ValueError(f"UNSUPPORTED_PROOF_FORM: {proof_form or '<missing>'}")
        return cls(
            need_id=need_id,
            subject=AnchorGroup.from_mapping(value.get("subject"), expected_field="subject"),
            relation=AnchorGroup.from_mapping(value.get("relation"), expected_field="relation"),
            qualifiers=qualifiers,
            quantity=AnchorGroup.from_mapping(value.get("quantity"), expected_field="quantity"),
            requested_proof_form=proof_form,
        )

    def groups(self) -> tuple[AnchorGroup, ...]:
        return (self.subject, self.relation, *self.qualifiers, self.quantity)

    def required_groups(self) -> tuple[AnchorGroup, ...]:
        return tuple(group for group in self.groups() if group.required)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "need_id": self.need_id,
            "subject": self.subject.to_dict(),
            "relation": self.relation.to_dict(),
            "qualifiers": [group.to_dict() for group in self.qualifiers],
            "quantity": self.quantity.to_dict(),
            "requested_proof_form": self.requested_proof_form,
        }
