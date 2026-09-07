"""Deterministic sparse-grid views for CSV, JSONL, and JSON intake."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path
from typing import Any


SCHEMA = "truevision_tabular_grid@1"
WEIGHT_AUTHORITY = "cell_local_exact_anchor_observation_count_not_confidence"


def _cell_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _anchor_weight(value: str) -> tuple[str, int]:
    from truemem.engine.anchors import anchorize

    anchors = anchorize(value)
    if len(anchors) == 1:
        return anchors[0], 1
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"object:cell:{digest}", 1


def _cells(values: list[tuple[str, Any]], columns: list[str]) -> list[dict[str, Any]]:
    by_name = {name: index for index, name in enumerate(columns)}
    output = []
    for name, raw in values:
        value = _cell_value(raw)
        anchor, weight = _anchor_weight(value)
        output.append({
            "column": by_name[name],
            "column_name": name,
            "value": value,
            "anchor": anchor,
            "weight": weight,
            "weight_authority": WEIGHT_AUTHORITY,
        })
    return output


def _columns(rows: list[list[tuple[str, Any]]]) -> list[str]:
    output = []
    seen = set()
    for row in rows:
        for name, _value in row:
            if name not in seen:
                seen.add(name)
                output.append(name)
    return output


def _summary(source_format: str, rows: list[dict[str, Any]], columns: list[str]) -> dict[str, Any]:
    widths = [int(row["observed_width"]) for row in rows]
    return {
        "schema": SCHEMA,
        "source_format": source_format,
        "row_count": len(rows),
        "cell_count": sum(widths),
        "minimum_row_width": min(widths, default=0),
        "maximum_row_width": max(widths, default=0),
        "columns": columns,
        "column_growth_rule": "first_observed_source_order_to_maximum_observed_width",
        "short_row_policy": "retain_sparse_width_without_synthetic_cells",
        "logical_cell": "value_anchor_weight",
        "weight_authority": WEIGHT_AUTHORITY,
        "source_text_modified": False,
        "semantic_inference": False,
    }


def _json_values(value: Any) -> list[tuple[str, Any]]:
    if isinstance(value, dict):
        return [(str(key), item) for key, item in value.items()]
    if isinstance(value, list):
        return [(f"column_{index}", item) for index, item in enumerate(value)]
    return [("value", value)]


def parse_tabular_source(path: str | Path, text: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Return a file summary and sparse row views without changing source text."""

    suffix = Path(path).suffix.casefold()
    if suffix == ".csv":
        parsed = list(csv.reader(io.StringIO(text)))
        if not parsed:
            return _summary("csv", [], []), []
        maximum = max(len(row) for row in parsed)
        header = [value.strip() or f"column_{index}" for index, value in enumerate(parsed[0])]
        columns = [*header, *(f"column_{index}" for index in range(len(header), maximum))]
        rows = []
        for source_index, values in enumerate(parsed):
            pairs = [(columns[index], value) for index, value in enumerate(values)]
            rows.append({
                "schema": f"{SCHEMA}:row",
                "row_index": source_index,
                "row_kind": "HEADER" if source_index == 0 else "DATA",
                "source_locator": {"line": source_index + 1},
                "observed_width": len(values),
                "maximum_width": maximum,
                "cells": _cells(pairs, columns),
            })
        summary = _summary("csv", rows, columns)
        summary["header_rule"] = "first_csv_record"
        summary["data_row_count"] = max(0, len(rows) - 1)
        return summary, rows

    if suffix == ".jsonl":
        located = [(line_number, json.loads(line)) for line_number, line in enumerate(text.splitlines(), start=1) if line.strip()]
        raw_rows = [_json_values(value) for _line, value in located]
        columns = _columns(raw_rows)
        maximum = max((len(row) for row in raw_rows), default=0)
        rows = [
            {
                "schema": f"{SCHEMA}:row",
                "row_index": index,
                "row_kind": "DATA",
                "source_locator": {"line": line_number},
                "observed_width": len(values),
                "maximum_width": maximum,
                "cells": _cells(values, columns),
            }
            for index, ((line_number, _value), values) in enumerate(zip(located, raw_rows))
        ]
        return _summary("jsonl", rows, columns), rows

    if suffix == ".json":
        value = json.loads(text)
        values = value if isinstance(value, list) else [value]
        raw_rows = [_json_values(row) for row in values]
        columns = _columns(raw_rows)
        maximum = max((len(row) for row in raw_rows), default=0)
        rows = [
            {
                "schema": f"{SCHEMA}:row",
                "row_index": index,
                "row_kind": "DATA",
                "source_locator": {"json_pointer": f"/{index}" if isinstance(value, list) else ""},
                "observed_width": len(row),
                "maximum_width": maximum,
                "cells": _cells(row, columns),
            }
            for index, row in enumerate(raw_rows)
        ]
        return _summary("json", rows, columns), rows

    return None, []
