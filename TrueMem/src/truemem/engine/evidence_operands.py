"""Bind deterministic operator operands to exact admitted evidence spans."""

from __future__ import annotations

import hashlib
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from .base import sha1_text
from .operator_skills import execute_operator_skill

MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4,
    "May": 5, "June": 6, "July": 7, "August": 8,
    "September": 9, "October": 10, "November": 11, "December": 12,
}
DECIMAL_RE = re.compile(r"[+-]?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?")
DATE_DMY_RE = re.compile(
    r"(0?[1-9]|[12][0-9]|3[01]) (" + "|".join(MONTHS) + r") ([0-9]{4})"
)
DATE_ISO_RE = re.compile(r"([0-9]{4})-(0[1-9]|1[0-2])-(0[1-9]|[12][0-9]|3[01])")


def bind_operator_operands(
    evidence_records: list[dict[str, Any]],
    operand_requests: list[dict[str, Any]],
) -> dict[str, Any]:
    """Derive typed operands only from verified UTF-8 spans in admitted blocks."""
    evidence_by_citation: dict[str, dict[str, Any]] = {}
    for ordinal, raw in enumerate(evidence_records):
        record = _verify_evidence_record(raw, ordinal)
        citation_id = record["citation_id"]
        if citation_id in evidence_by_citation:
            raise ValueError(f"duplicate evidence citation: {citation_id}")
        evidence_by_citation[citation_id] = record

    operands = []
    for ordinal, request in enumerate(operand_requests):
        citation_id = str(request.get("citation_id") or "")
        evidence = evidence_by_citation.get(citation_id)
        if evidence is None:
            raise ValueError(f"operand {ordinal} citation is not in the supplied evidence packet")
        identity_span = _verify_span(evidence["text"], request.get("identity_span"), f"operand {ordinal} identity")
        value_kind = str(request.get("value_kind") or "")
        if value_kind == "lifespan":
            start_span = _verify_span(evidence["text"], request.get("start_span"), f"operand {ordinal} lifespan start")
            end_span = _verify_span(evidence["text"], request.get("end_span"), f"operand {ordinal} lifespan end")
            value = {"start": _parse_date(start_span["text"]), "end": _parse_date(end_span["text"])}
            value_spans = [start_span, end_span]
        elif value_kind == "exact_string_list":
            raw_spans = request.get("value_spans")
            if not isinstance(raw_spans, list) or not raw_spans:
                raise ValueError(f"operand {ordinal} exact string list has no spans")
            value_spans = [
                _verify_span(evidence["text"], raw, f"operand {ordinal} list value {index}")
                for index, raw in enumerate(raw_spans)
            ]
            value = [row["text"] for row in value_spans]
        else:
            value_span = _verify_span(evidence["text"], request.get("value_span"), f"operand {ordinal} value")
            value = _parse_value(value_kind, value_span["text"])
            value_spans = [value_span]
        binding = {
            "schema": "truemem_evidence_operand_binding@1",
            "citation_id": citation_id,
            "block_ordinal": evidence["block_ordinal"],
            "file_path": evidence["file_path"],
            "line_start": evidence["line_start"],
            "line_end": evidence["line_end"],
            "text_sha1": evidence["text_sha1"],
            "text_sha256": evidence["text_sha256"],
            "identity_span": identity_span,
            "value_spans": value_spans,
            "value_kind": value_kind,
            "source_bytes_unchanged": True,
        }
        operands.append({
            "identity": identity_span["text"],
            "value": value,
            "citations": [citation_id],
            "binding_receipt": binding,
        })
    return {
        "schema": "truemem_bound_operator_operands@1",
        "status": "EXACT_EVIDENCE_SPANS_VERIFIED",
        "operands": operands,
        "evidence_citations": sorted(evidence_by_citation),
        "source_text_normalization": "none",
        "model_authority_created": False,
        "device_boundary": {
            "execution_device": "cpu",
            "allowed_work": "exact UTF-8 byte slicing, cryptographic hashing, and typed scalar parsing",
            "relationship_math": False,
            "candidate_ranking": False,
            "model_execution": False,
            "silent_device_fallback": False,
        },
    }


def execute_bound_operator_skill(
    operation: str,
    binding_packet: dict[str, Any],
) -> dict[str, Any]:
    """Execute only a packet produced by exact evidence binding."""
    if binding_packet.get("schema") != "truemem_bound_operator_operands@1":
        raise ValueError("operator input is not a bound evidence packet")
    if binding_packet.get("status") != "EXACT_EVIDENCE_SPANS_VERIFIED":
        raise ValueError("operator evidence binding is not verified")
    operands = list(binding_packet.get("operands") or [])
    if not operands or any(row.get("binding_receipt", {}).get("schema") != "truemem_evidence_operand_binding@1" for row in operands):
        raise ValueError("operator evidence binding receipts are missing")
    result = execute_operator_skill(operation, operands)
    result["binding_packet_schema"] = binding_packet["schema"]
    result["exact_evidence_spans_verified"] = True
    result["device_boundary"] = {
        "execution_device": "cpu",
        "allowed_work": "bounded deterministic scalar, date, count, equality, and set operation",
        "relationship_math": False,
        "candidate_ranking": False,
        "model_execution": False,
        "silent_device_fallback": False,
    }
    return result


def execute_anchor_sheet_capability(
    anchor_structure_sheet: dict[str, Any],
    evidence_records: list[dict[str, Any]],
    operand_requests: list[dict[str, Any]],
) -> dict[str, Any]:
    """Verify a sheet's complete evidence burden, bind spans, then execute."""
    from .query_ruling import build_anchor_structure_sheet

    if not anchor_structure_sheet:
        raise ValueError("capability execution requires a non-empty anchor structure sheet")
    rebuilt = build_anchor_structure_sheet(
        str(anchor_structure_sheet.get("question") or ""),
        ruling_groups=list(anchor_structure_sheet.get("ruling_anchor_groups") or []),
        operation=dict(anchor_structure_sheet.get("operation") or {}),
        required_evidence=list(anchor_structure_sheet.get("required_evidence") or []),
    )
    if rebuilt["sheet_id"] != anchor_structure_sheet.get("sheet_id"):
        raise ValueError("anchor structure sheet identity failed verification")
    groups = {row["group_id"]: row for row in rebuilt["ruling_anchor_groups"]}
    required = {
        (row["group_id"], row["field"])
        for row in rebuilt["required_evidence"]
        if row["required"]
    }
    supplied: dict[tuple[str, str], int] = {}
    expected_identities: dict[int, str] = {}
    for index, request in enumerate(operand_requests):
        group_id = str(request.get("group_id") or "")
        group = groups.get(group_id)
        if group is None:
            raise ValueError(f"operand request {index} references an unknown ruling group")
        fields = [str(field) for field in request.get("evidence_fields") or []]
        if not fields:
            raise ValueError(f"operand request {index} has no evidence fields")
        for field in fields:
            key = (group_id, field)
            if key in supplied:
                raise ValueError(f"required evidence supplied more than once: {key}")
            supplied[key] = index
        expected_identities[index] = " ".join(group["anchors"])
    missing = sorted(required - set(supplied))
    unexpected = sorted(set(supplied) - {
        (row["group_id"], row["field"]) for row in rebuilt["required_evidence"]
    })
    if missing:
        raise ValueError(f"required sheet evidence is missing: {missing}")
    if unexpected:
        raise ValueError(f"operand evidence is not declared by the sheet: {unexpected}")
    binding = bind_operator_operands(evidence_records, operand_requests)
    for index, operand in enumerate(binding["operands"]):
        if operand["identity"] != expected_identities[index]:
            raise ValueError(f"operand {index} identity span does not match its ruling anchor group")
    result = execute_bound_operator_skill(rebuilt["operation"]["name"], binding)
    result["anchor_structure_sheet_id"] = rebuilt["sheet_id"]
    result["required_evidence_satisfied"] = [
        {"group_id": group_id, "field": field, "operand_index": supplied[(group_id, field)]}
        for group_id, field in sorted(required)
    ]
    result["undeclared_evidence_used"] = False
    return result


def run_anchor_sheet_capability(
    anchor_structure_sheet: dict[str, Any],
    evidence_records: list[dict[str, Any]],
    operand_requests: list[dict[str, Any]],
) -> dict[str, Any]:
    """Return an auditable receipt for both execution and refusal."""
    sheet_id = anchor_structure_sheet.get("sheet_id") if isinstance(anchor_structure_sheet, dict) else None
    operation = None
    if isinstance(anchor_structure_sheet, dict) and isinstance(anchor_structure_sheet.get("operation"), dict):
        operation = anchor_structure_sheet["operation"].get("name")
    receipt: dict[str, Any] = {
        "schema": "truemem_capability_authority_receipt@1",
        "anchor_structure_sheet_id": sheet_id,
        "operation": operation,
        "authority": "EXACT_ADMITTED_EVIDENCE_ONLY",
        "model_authority_created": False,
        "evidence_modified": False,
        "operation_executed": False,
        "device_boundary": {
            "evidence_binding": "cpu_exact_bytes_and_hashes",
            "operator_execution": "cpu_bounded_deterministic_operation",
            "relationship_qualification": "not_performed_by_capability_runner",
            "candidate_ranking": "not_performed_by_capability_runner",
            "model_execution": False,
            "silent_device_fallback": False,
        },
    }
    try:
        result = execute_anchor_sheet_capability(
            anchor_structure_sheet, evidence_records, operand_requests
        )
    except (ValueError, KeyError, TypeError) as error:
        receipt.update({
            "status": "REJECTED",
            "failure_code": _failure_code(str(error)),
            "failure_detail": str(error),
            "result": None,
        })
        return receipt
    receipt.update({
        "status": "EXECUTED",
        "failure_code": None,
        "failure_detail": None,
        "operation_executed": True,
        "result": result,
    })
    return receipt


def _verify_evidence_record(raw: dict[str, Any], ordinal: int) -> dict[str, Any]:
    citation_id = str(raw.get("citation_id") or raw.get("citation") or "")
    text = raw.get("text")
    if not citation_id or not isinstance(text, str):
        raise ValueError(f"evidence record {ordinal} lacks citation identity or exact text")
    expected_sha1 = str(raw.get("text_hash") or raw.get("source_text_sha1") or "")
    observed_sha1 = sha1_text(text)
    if not expected_sha1 or expected_sha1 != observed_sha1:
        raise ValueError(f"evidence record {ordinal} text SHA-1 failed verification")
    observed_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
    expected_sha256 = str(raw.get("source_text_sha256") or raw.get("text_sha256") or "")
    if expected_sha256 and expected_sha256 != observed_sha256:
        raise ValueError(f"evidence record {ordinal} text SHA-256 failed verification")
    block_ordinal = raw.get("block_ordinal", raw.get("block_id"))
    if block_ordinal is None or not str(raw.get("file_path") or ""):
        raise ValueError(f"evidence record {ordinal} lacks native coordinates")
    if raw.get("line_start") is None or raw.get("line_end") is None:
        raise ValueError(f"evidence record {ordinal} lacks line coordinates")
    return {
        "citation_id": citation_id,
        "text": text,
        "block_ordinal": int(block_ordinal),
        "file_path": str(raw["file_path"]),
        "line_start": int(raw["line_start"]),
        "line_end": int(raw["line_end"]),
        "text_sha1": observed_sha1,
        "text_sha256": observed_sha256,
    }


def _verify_span(text: str, raw_span: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw_span, dict):
        raise ValueError(f"{label} span is missing")
    start = int(raw_span.get("byte_start", -1))
    end = int(raw_span.get("byte_end", -1))
    exact = raw_span.get("text")
    source = text.encode("utf-8")
    if start < 0 or end <= start or end > len(source) or not isinstance(exact, str):
        raise ValueError(f"{label} span coordinates are invalid")
    observed = source[start:end]
    if observed != exact.encode("utf-8"):
        raise ValueError(f"{label} span does not reconstruct exact source bytes")
    return {
        "byte_start": start,
        "byte_end": end,
        "text": exact,
        "span_sha256": hashlib.sha256(observed).hexdigest(),
    }


def _parse_value(kind: str, source: str) -> Any:
    if kind == "decimal":
        if not DECIMAL_RE.fullmatch(source):
            raise ValueError("decimal evidence span has unsupported exact syntax")
        try:
            return str(Decimal(source))
        except InvalidOperation as error:
            raise ValueError("decimal evidence span is invalid") from error
    if kind == "date":
        return _parse_date(source)
    if kind == "exact_string":
        return source
    raise ValueError(f"unsupported evidence operand value_kind: {kind}")


def _failure_code(message: str) -> str:
    checks = (
        ("non-empty anchor structure sheet", "EMPTY_OR_MISSING_SHEET"),
        ("sheet identity failed", "SHEET_IDENTITY_FAILED"),
        ("unknown ruling group", "UNKNOWN_RULING_GROUP"),
        ("has no evidence fields", "MISSING_EVIDENCE_FIELD_DECLARATION"),
        ("supplied more than once", "DUPLICATE_EVIDENCE_FIELD"),
        ("required sheet evidence is missing", "REQUIRED_EVIDENCE_MISSING"),
        ("not declared by the sheet", "UNDECLARED_EVIDENCE_FIELD"),
        ("identity span does not match", "RULING_IDENTITY_MISMATCH"),
        ("citation is not in", "CITATION_NOT_SUPPLIED"),
        ("duplicate evidence citation", "DUPLICATE_CITATION"),
        ("SHA-1 failed", "SOURCE_HASH_MISMATCH"),
        ("SHA-256 failed", "SOURCE_HASH_MISMATCH"),
        ("native coordinates", "SOURCE_COORDINATES_MISSING"),
        ("line coordinates", "SOURCE_COORDINATES_MISSING"),
        ("span coordinates are invalid", "INVALID_SOURCE_SPAN"),
        ("span does not reconstruct", "SOURCE_SPAN_MISMATCH"),
        ("span is missing", "SOURCE_SPAN_MISSING"),
        ("unsupported exact syntax", "UNSUPPORTED_VALUE_SYNTAX"),
        ("requires exactly", "OPERAND_CARDINALITY_MISMATCH"),
        ("requires at least", "OPERAND_CARDINALITY_MISMATCH"),
        ("cannot be zero", "ZERO_DIVISOR"),
        ("unsupported operator skill", "UNSUPPORTED_CAPABILITY"),
    )
    for fragment, code in checks:
        if fragment in message:
            return code
    return "MALFORMED_CAPABILITY_REQUEST"


def _parse_date(source: str) -> dict[str, int]:
    dmy = DATE_DMY_RE.fullmatch(source)
    if dmy:
        parsed = date(int(dmy.group(3)), MONTHS[dmy.group(2)], int(dmy.group(1)))
    else:
        iso = DATE_ISO_RE.fullmatch(source)
        if not iso:
            raise ValueError("date evidence span has unsupported exact syntax")
        parsed = date(int(iso.group(1)), int(iso.group(2)), int(iso.group(3)))
    return {"year": parsed.year, "month": parsed.month, "day": parsed.day}
