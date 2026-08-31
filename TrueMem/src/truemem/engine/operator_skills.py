from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

OPERATOR_SKILLS = {
    "all_equal": {"minimum_operands": 1, "kind": "comparison"},
    "chronological_order": {"minimum_operands": 2, "kind": "date"},
    "count_anchors": {"exact_operands": 1, "kind": "count"},
    "date_difference_days": {"exact_operands": 2, "kind": "date"},
    "earlier_date": {"exact_operands": 2, "kind": "date"},
    "identity_intersection": {"minimum_operands": 2, "kind": "set"},
    "later_date": {"exact_operands": 2, "kind": "date"},
    "lifespan_longer": {"exact_operands": 2, "kind": "date"},
    "numeric_add": {"minimum_operands": 2, "kind": "arithmetic"},
    "numeric_difference": {"exact_operands": 2, "kind": "arithmetic"},
    "numeric_divide": {"exact_operands": 2, "kind": "arithmetic"},
    "numeric_max": {"minimum_operands": 2, "kind": "comparison"},
    "numeric_min": {"minimum_operands": 2, "kind": "comparison"},
    "numeric_multiply": {"minimum_operands": 2, "kind": "arithmetic"},
    "percentage_of": {"exact_operands": 2, "kind": "arithmetic"},
    "set_intersection": {"minimum_operands": 2, "kind": "set"},
    "set_union": {"minimum_operands": 2, "kind": "set"},
}


def available_operator_skills() -> dict[str, dict[str, Any]]:
    """Return the fixed, inspectable capability surface."""
    return {name: dict(OPERATOR_SKILLS[name]) for name in sorted(OPERATOR_SKILLS)}


def execute_operator_skill(operation: str, operands: list[dict[str, Any]]) -> dict[str, Any]:
    """Execute one bounded operation over source-backed, cited operands."""
    operation = str(operation)
    prepared = [_operand(row, index) for index, row in enumerate(operands)]
    if operation in {"earlier_date", "later_date"}:
        _require_count(prepared, 2)
        dated = [(row, _date_value(row["value"])) for row in prepared]
        selected = min(dated, key=lambda item: item[1]) if operation == "earlier_date" else max(dated, key=lambda item: item[1])
        return _result(operation, prepared, selected[0]["identity"], {"ordered_date": selected[1].isoformat()})
    if operation == "lifespan_longer":
        _require_count(prepared, 2)
        durations = [(row, _date_value(row["value"]["end"]) - _date_value(row["value"]["start"])) for row in prepared]
        selected = max(durations, key=lambda item: item[1])
        return _result(operation, prepared, selected[0]["identity"], {"duration_days": selected[1].days})
    if operation == "chronological_order":
        _require_minimum(prepared, 2)
        ordered = sorted(prepared, key=lambda row: (_date_value(row["value"]), row["identity"]))
        return _result(operation, prepared, [row["identity"] for row in ordered], {
            "ordered_dates": [_date_value(row["value"]).isoformat() for row in ordered]
        })
    if operation == "date_difference_days":
        _require_count(prepared, 2)
        difference = _date_value(prepared[1]["value"]) - _date_value(prepared[0]["value"])
        return _result(operation, prepared, difference.days, {"signed_days": difference.days})
    if operation in {"numeric_min", "numeric_max"}:
        _require_minimum(prepared, 2)
        values = [(row, _decimal(row["value"])) for row in prepared]
        selected = min(values, key=lambda item: item[1]) if operation == "numeric_min" else max(values, key=lambda item: item[1])
        return _result(operation, prepared, selected[0]["identity"], {"numeric_value": str(selected[1])})
    if operation in {"numeric_add", "numeric_multiply"}:
        _require_minimum(prepared, 2)
        values = [_decimal(row["value"]) for row in prepared]
        result = sum(values, Decimal(0)) if operation == "numeric_add" else _product(values)
        return _result(operation, prepared, str(result), {"numeric_value": str(result)})
    if operation in {"numeric_difference", "numeric_divide", "percentage_of"}:
        _require_count(prepared, 2)
        left, right = (_decimal(row["value"]) for row in prepared)
        if operation == "numeric_difference":
            result = left - right
        elif operation == "numeric_divide":
            if right == 0:
                raise ValueError("numeric_divide divisor cannot be zero")
            result = left / right
        else:
            if right == 0:
                raise ValueError("percentage_of reference value cannot be zero")
            result = left / right * Decimal(100)
        return _result(operation, prepared, str(result), {"numeric_value": str(result)})
    if operation in {"set_intersection", "identity_intersection"}:
        _require_minimum(prepared, 2)
        sets = [set(map(str, row["value"])) for row in prepared]
        return _result(operation, prepared, sorted(set.intersection(*sets)), {"intersection_count": len(set.intersection(*sets))})
    if operation == "set_union":
        _require_minimum(prepared, 2)
        values = sorted(set().union(*(set(map(str, row["value"])) for row in prepared)))
        return _result(operation, prepared, values, {"union_count": len(values)})
    if operation == "count_anchors":
        _require_count(prepared, 1)
        values = list(prepared[0]["value"])
        return _result(operation, prepared, len(values), {"counted_identity": prepared[0]["identity"]})
    if operation == "all_equal":
        if not prepared:
            raise ValueError("all_equal requires at least one operand")
        return _result(operation, prepared, all(row["value"] == prepared[0]["value"] for row in prepared), {})
    raise ValueError(f"unsupported operator skill: {operation}")


def _operand(row: dict[str, Any], index: int) -> dict[str, Any]:
    if not str(row.get("identity") or ""):
        raise ValueError(f"operand {index} lacks identity")
    if "value" not in row:
        raise ValueError(f"operand {index} lacks value")
    citations = [str(value) for value in row.get("citations") or [] if str(value)]
    if not citations:
        raise ValueError(f"operand {index} lacks citation authority")
    return {"identity": str(row["identity"]), "value": row["value"], "citations": citations}


def _date_value(value: Any) -> date:
    if not isinstance(value, dict) or not {"year", "month", "day"}.issubset(value):
        raise ValueError("date operand requires an exact structured year/month/day value")
    return date(int(value["year"]), int(value["month"]), int(value["day"]))


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError(f"invalid numeric operand: {value}") from error


def _require_count(operands: list[dict[str, Any]], count: int) -> None:
    if len(operands) != count:
        raise ValueError(f"operation requires exactly {count} operands")


def _require_minimum(operands: list[dict[str, Any]], count: int) -> None:
    if len(operands) < count:
        raise ValueError(f"operation requires at least {count} operands")


def _product(values: list[Decimal]) -> Decimal:
    result = Decimal(1)
    for value in values:
        result *= value
    return result


def _result(operation: str, operands: list[dict[str, Any]], value: Any, measurements: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "truemem_deterministic_operator_skill@1",
        "operation": operation,
        "status": "VERIFIED_OPERATION_RESULT",
        "result": value,
        "measurements": measurements,
        "operand_receipt": operands,
        "citations": list(dict.fromkeys(citation for row in operands for citation in row["citations"])),
        "model_authority_created": False,
        "evidence_modified": False,
        "capability_authority": "DETERMINISTIC_CITED_OPERANDS_ONLY",
    }
