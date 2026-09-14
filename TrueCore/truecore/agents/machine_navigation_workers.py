"""TrueCore result adapters for fixed TrueMachine read-only navigation."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from truecore.live_agents.worker_result import build_result


TRUESYSTEMS_ROOT = Path(__file__).resolve().parents[3]
TRUEMACHINE_SRC = TRUESYSTEMS_ROOT / "TrueMachine" / "src"
if str(TRUEMACHINE_SRC) not in sys.path:
    sys.path.insert(0, str(TRUEMACHINE_SRC))

from truemachine.navigation import NavigationError, run


def _execute(
    worker_id: str,
    root_path: str,
    parameters: dict[str, Any],
    limits: dict[str, int],
) -> dict[str, Any]:
    try:
        native = run(worker_id, root_path, parameters, **limits)
    except FileNotFoundError:
        return build_result(
            worker_id=worker_id, operation=worker_id, status="UNRESOLVED",
            unresolved=[{"field": "relative_path", "state": "NOT_FOUND"}],
            continuation="STOP_NO_EVIDENCE", reason_code="TARGET_NOT_FOUND",
        )
    except (NavigationError, OSError) as error:
        return build_result(
            worker_id=worker_id, operation=worker_id, status="REFUSED",
            errors=[{"kind": type(error).__name__, "message": str(error)}],
            continuation="STOP_REFUSED", reason_code="NAVIGATION_CONTRACT_REJECTED",
        )
    receipt = native.pop("receipt_sha256")
    status = "PARTIAL" if native["truncated"] or native["unresolved"] else "COMPLETE"
    return build_result(
        worker_id=worker_id,
        operation=worker_id,
        status=status,
        result={
            "measurements": native["measurements"],
            "truncated": native["truncated"],
            "answer": native["answer"],
        },
        locations=native["locations"],
        unresolved=native["unresolved"],
        receipts=[{
            "receipt_type": "truemachine.navigation@1",
            "operation": worker_id,
            "root_identity": native["root_identity"],
            "receipt_sha256": receipt,
        }],
        continuation="STOP_PARTIAL" if status == "PARTIAL" else "STOP_COMPLETE",
        reason_code="BOUNDED_NAVIGATION_PARTIAL" if status == "PARTIAL" else "BOUNDED_NAVIGATION_COMPLETE",
    )


def filesystem_list(root_path: str, parameters: dict[str, Any], limits: dict[str, int]) -> dict[str, Any]:
    return _execute("fs.list", root_path, parameters, limits)


def filesystem_find(root_path: str, parameters: dict[str, Any], limits: dict[str, int]) -> dict[str, Any]:
    return _execute("fs.find", root_path, parameters, limits)


def filesystem_read_metadata(root_path: str, parameters: dict[str, Any], limits: dict[str, int]) -> dict[str, Any]:
    return _execute("fs.read_metadata", root_path, parameters, limits)


def filesystem_hash(root_path: str, parameters: dict[str, Any], limits: dict[str, int]) -> dict[str, Any]:
    return _execute("fs.hash", root_path, parameters, limits)


def filesystem_disk_usage(root_path: str, parameters: dict[str, Any], limits: dict[str, int]) -> dict[str, Any]:
    return _execute("fs.disk_usage", root_path, parameters, limits)


def filesystem_duplicate_scan(root_path: str, parameters: dict[str, Any], limits: dict[str, int]) -> dict[str, Any]:
    return _execute("fs.duplicate_scan", root_path, parameters, limits)
