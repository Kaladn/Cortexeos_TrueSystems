"""Invoke a materialized agent's exact local Python symbol."""

from __future__ import annotations

import argparse
import asyncio
import importlib
import inspect
import json
from typing import Any


def resolve_callable(module_name: str, symbol: str, payload: dict[str, Any]):
    module = importlib.import_module(module_name)
    parts = symbol.split(".")
    if len(parts) == 1:
        return getattr(module, parts[0])
    owner = getattr(module, parts[0])
    instance = owner(
        *payload.get("constructor_args", []),
        **payload.get("constructor_kwargs", {}),
    )
    target = instance
    for part in parts[1:]:
        target = getattr(target, part)
    return target


def invoke(module_name: str, symbol: str, payload: dict[str, Any]) -> Any:
    target = resolve_callable(module_name, symbol, payload)
    result = target(*payload.get("args", []), **payload.get("kwargs", {}))
    if inspect.isawaitable(result):
        return asyncio.run(result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Invoke one materialized SecureCore agent.")
    parser.add_argument("--module", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--input-json", default="{}")
    args = parser.parse_args(argv)
    payload = json.loads(args.input_json)
    if not isinstance(payload, dict):
        raise ValueError("input JSON must be an object")
    print(json.dumps(invoke(args.module, args.symbol, payload), sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
