"""TrueCore worker adapter for TrueMachine repository-state mapping."""

from __future__ import annotations

import argparse
from argparse import Namespace
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
from typing import Any

TRUECORE_ROOT = Path(__file__).resolve().parents[2]
if str(TRUECORE_ROOT) not in sys.path:
    sys.path.insert(0, str(TRUECORE_ROOT))

from truecore.live_agents.worker_result import build_result, canonical


WORKER_ID = "truemachine_repository_map"
TRUESYSTEMS_ROOT = Path(__file__).resolve().parents[3]
TRUEMACHINE_SRC = TRUESYSTEMS_ROOT / "TrueMachine" / "src"


def _load_truemachine_mapper():
    if not TRUEMACHINE_SRC.is_dir():
        raise RuntimeError("TrueMachine source boundary is unavailable")
    if str(TRUEMACHINE_SRC) not in sys.path:
        sys.path.insert(0, str(TRUEMACHINE_SRC))
    from truemachine import repository_map
    return repository_map


def _radius(request: dict[str, Any], name: str, default: int) -> int:
    value = request.get(name, default)
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 64:
        raise ValueError(f"{name} must be an integer from 0 through 64")
    return value


def _invoke(callable_, arguments: Namespace) -> tuple[int, dict[str, Any]]:
    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        code = callable_(arguments)
    rendered = stream.getvalue().strip()
    if not rendered:
        raise RuntimeError("TrueMachine operation returned no structured result")
    result = json.loads(rendered)
    if not isinstance(result, dict):
        raise RuntimeError("TrueMachine operation result must be an object")
    return code, result


def run_request(request_path: str, out_dir: str) -> dict[str, Any]:
    """Validate one request and delegate it to the fixed TrueMachine mapper API."""
    source = Path(request_path).expanduser().resolve()
    output = Path(out_dir).expanduser().resolve()
    raw = source.read_bytes()
    request = json.loads(raw)
    if not isinstance(request, dict):
        raise ValueError("request must be a JSON object")
    operation = request.get("operation")
    input_receipt = {
        "receipt_type": "truecore.worker_input@1",
        "request_path": str(source),
        "request_sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
    }
    if operation not in {"build", "query", "verify"}:
        return build_result(
            worker_id=WORKER_ID,
            operation=str(operation or "UNRESOLVED"),
            status="NOT_IMPLEMENTED" if operation else "UNRESOLVED",
            unresolved=[{"field": "operation", "state": "MISSING_OR_UNKNOWN"}],
            receipts=[input_receipt],
            continuation="STOP_NOT_IMPLEMENTED" if operation else "ASK_HUMAN",
            reason_code="UNKNOWN_OPERATION" if operation else "OPERATION_REQUIRED",
        )

    mapper = _load_truemachine_mapper()
    try:
        if operation == "build":
            repo_text = request.get("repository")
            if not isinstance(repo_text, str) or not repo_text:
                return build_result(
                    worker_id=WORKER_ID,
                    operation=operation,
                    status="UNRESOLVED",
                    unresolved=[{"field": "repository", "state": "MISSING"}],
                    receipts=[input_receipt],
                    continuation="ASK_HUMAN",
                    reason_code="REPOSITORY_REQUIRED",
                )
            repo = Path(repo_text).expanduser().resolve()
            if not (repo / ".git").exists():
                return build_result(
                    worker_id=WORKER_ID,
                    operation=operation,
                    status="REFUSED",
                    unresolved=[{"field": "repository", "state": "NOT_A_GIT_REPOSITORY", "path": str(repo)}],
                    receipts=[input_receipt],
                    continuation="STOP_REFUSED",
                    reason_code="REPOSITORY_BOUNDARY_INVALID",
                )
            output.mkdir(parents=True, exist_ok=True)
            code, native = _invoke(mapper.build, Namespace(
                repo=repo,
                output_parent=output,
                ownership_n=_radius(request, "ownership_n", 2),
                flow_n=_radius(request, "source_order_n", 6),
                dependency_n=_radius(request, "dependency_n", 3),
                progress=int(request.get("progress", 250)),
            ))
            if code != 0:
                raise RuntimeError(f"TrueMachine build returned {code}")
            return build_result(
                worker_id=WORKER_ID,
                operation=operation,
                status="COMPLETE",
                result={"snapshot_id": native["snapshot_id"], "totals": native["totals"]},
                artifacts=[{"kind": "TRUEMACHINE_REPOSITORY_MAP", "path": native["output"]}],
                receipts=[input_receipt, {"receipt_type": "truemachine.repository_map_build@1", **native}],
            )

        map_text = request.get("map_dir")
        if not isinstance(map_text, str) or not map_text:
            return build_result(
                worker_id=WORKER_ID,
                operation=operation,
                status="UNRESOLVED",
                unresolved=[{"field": "map_dir", "state": "MISSING"}],
                receipts=[input_receipt],
                continuation="ASK_HUMAN",
                reason_code="MAP_DIRECTORY_REQUIRED",
            )
        map_dir = Path(map_text).expanduser().resolve()
        if not (map_dir / "manifest.json").is_file():
            return build_result(
                worker_id=WORKER_ID,
                operation=operation,
                status="REFUSED",
                unresolved=[{"field": "map_dir", "state": "MANIFEST_NOT_FOUND", "path": str(map_dir)}],
                receipts=[input_receipt],
                continuation="STOP_REFUSED",
                reason_code="MAP_BOUNDARY_INVALID",
            )
        if operation == "verify":
            code, native = _invoke(mapper.verify, Namespace(map_dir=map_dir))
            if code != 0:
                raise RuntimeError(f"TrueMachine verification returned {code}")
            return build_result(
                worker_id=WORKER_ID,
                operation=operation,
                status="COMPLETE",
                result={key: native[key] for key in ("status", "snapshot_id", "source_files", "code_objects", "relationship_counts")},
                artifacts=[{"kind": "VERIFIED_TRUEMACHINE_REPOSITORY_MAP", "path": str(map_dir)}],
                receipts=[input_receipt, {"receipt_type": "truemachine.repository_map_verification@1", **native}],
            )

        exact = request.get("exact")
        if not isinstance(exact, str) or not exact:
            return build_result(
                worker_id=WORKER_ID,
                operation=operation,
                status="UNRESOLVED",
                unresolved=[{"field": "exact", "state": "MISSING"}],
                receipts=[input_receipt],
                continuation="ASK_HUMAN",
                reason_code="EXACT_CODE_OBJECT_REQUIRED",
            )
        code, native = _invoke(mapper.query, Namespace(
            map_dir=map_dir,
            exact=exact,
            path=request.get("path"),
            ownership_n=_radius(request, "ownership_n", 2),
            flow_n=_radius(request, "source_order_n", 6),
            dependency_n=_radius(request, "dependency_n", 3),
        ))
        if code == 2:
            return build_result(
                worker_id=WORKER_ID,
                operation=operation,
                status="UNRESOLVED",
                result=native,
                receipts=[input_receipt],
                continuation="STOP_NO_EVIDENCE",
                reason_code="CODE_OBJECT_NOT_FOUND",
            )
        if code == 3:
            return build_result(
                worker_id=WORKER_ID,
                operation=operation,
                status="AMBIGUOUS",
                result={"matches": native.get("matches", [])},
                locations=native.get("matches", []),
                receipts=[input_receipt],
                continuation="STOP_AMBIGUOUS",
                reason_code="CODE_OBJECT_AMBIGUOUS",
            )
        if code != 0:
            raise RuntimeError(f"TrueMachine query returned {code}")
        query_receipt = native.pop("receipt_sha256")
        return build_result(
            worker_id=WORKER_ID,
            operation=operation,
            status="COMPLETE",
            result={"snapshot_id": native["snapshot_id"], "center": native["center"], "radii": native["radii"]},
            locations=native["nodes"],
            relationships=native["relationships"],
            receipts=[input_receipt, {
                "receipt_type": "truemachine.repository_map_query@1",
                "receipt_sha256": query_receipt,
                "snapshot_id": native["snapshot_id"],
            }],
        )
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        return build_result(
            worker_id=WORKER_ID,
            operation=operation,
            status="FAILED",
            errors=[{"kind": type(error).__name__, "message": str(error)}],
            receipts=[input_receipt],
            continuation="STOP_FAILED",
            reason_code="TRUEMACHINE_OPERATION_FAILED",
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args(argv)
    packet = run_request(args.request, args.out_dir)
    sys.stdout.buffer.write(canonical(packet))
    return 0 if packet["status"] not in {"FAILED", "REFUSED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
