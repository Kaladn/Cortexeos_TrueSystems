"""Fixed-argv read-only observations for systemd services and Git repositories."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any

from .navigation import NavigationError, _integer


OPERATIONS = frozenset({"service.status", "repo.status"})
UNIT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@:-]{0,254}$")


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _identity(path: Path) -> dict[str, int]:
    info = path.stat()
    return {"device": info.st_dev, "inode": info.st_ino}


def _run(command: list[str], *, cwd: Path | None, timeout_seconds: int, output_budget: int) -> tuple[int, str, str]:
    environment = dict(os.environ)
    environment.update({
        "LC_ALL": "C", "LANG": "C", "GIT_OPTIONAL_LOCKS": "0",
        "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
    })
    try:
        completed = subprocess.run(
            command, cwd=cwd, env=environment, capture_output=True,
            timeout=timeout_seconds, check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise NavigationError("READ_ONLY_COMMAND_TIMEOUT") from error
    if len(completed.stdout) + len(completed.stderr) > output_budget:
        raise NavigationError("COMMAND_OUTPUT_BUDGET_EXCEEDED")
    return (
        completed.returncode,
        completed.stdout.decode("utf-8", errors="strict"),
        completed.stderr.decode("utf-8", errors="strict"),
    )


def _packet(operation: str, identity: dict[str, int], locations: list[dict[str, Any]], measurements: dict[str, Any], unresolved=None) -> dict[str, Any]:
    packet = {
        "schema": "truemachine.command_observation@1",
        "operation": operation,
        "root_identity": identity,
        "locations": locations,
        "measurements": measurements,
        "unresolved": unresolved or [],
        "truncated": False,
        "answer": None,
    }
    packet["receipt_sha256"] = "sha256:" + hashlib.sha256(_canonical(packet)).hexdigest()
    return packet


def run(
    operation: str,
    resource_path: str | Path,
    parameters: dict[str, Any],
    *,
    executable_path: str | None = None,
    max_entries: int = 10_000,
    max_file_bytes: int = 256 * 1024 * 1024,
    max_total_bytes: int = 1024 * 1024 * 1024,
    timeout_seconds: int = 10,
) -> dict[str, Any]:
    if operation not in OPERATIONS or not isinstance(parameters, dict):
        raise NavigationError("INVALID_COMMAND_OBSERVATION")
    _integer(max_entries, "host_entry_budget", 1, 1_000_000)
    timeout = _integer(timeout_seconds, "timeout_seconds", 1, 60)
    output_budget = min(
        _integer(max_total_bytes, "host_total_budget", 1, 1 << 60),
        _integer(max_file_bytes, "host_file_budget", 1, 1 << 50),
    )

    if operation == "service.status":
        if set(parameters) != {"unit"}:
            raise NavigationError("INVALID_PARAMETERS")
        unit = parameters["unit"]
        if not isinstance(unit, str) or not UNIT_RE.fullmatch(unit):
            raise NavigationError("INVALID_SERVICE_UNIT")
        executable = Path(resource_path)
        if not executable.is_absolute() or executable.is_symlink() or not executable.is_file():
            raise NavigationError("INVALID_SYSTEMCTL_EXECUTABLE")
        returncode, stdout, stderr = _run([
            str(executable), "show", "--no-pager",
            "--property=Id,LoadState,ActiveState,SubState,UnitFileState,FragmentPath",
            "--", unit,
        ], cwd=None, timeout_seconds=timeout, output_budget=output_budget)
        fields = {}
        for line in stdout.splitlines():
            key, separator, value = line.partition("=")
            if separator:
                fields[key] = value
        unresolved = []
        if returncode != 0:
            unresolved.append({"unit": unit, "state": "SYSTEMCTL_NONZERO", "returncode": returncode, "stderr": stderr})
        return _packet(
            operation, _identity(executable),
            [{"relative_path": unit, "kind": "systemd_unit", **fields}],
            {"returncode": returncode}, unresolved,
        )

    if set(parameters) != {"include_remotes"} or type(parameters["include_remotes"]) is not bool:
        raise NavigationError("INVALID_PARAMETERS")
    repository = Path(resource_path)
    executable = Path(executable_path or "")
    if (
        not repository.is_absolute() or repository.is_symlink() or not repository.is_dir() or
        not (repository / ".git").exists()
    ):
        raise NavigationError("INVALID_GIT_REPOSITORY")
    if not executable.is_absolute() or executable.is_symlink() or not executable.is_file():
        raise NavigationError("INVALID_GIT_EXECUTABLE")
    base = [
        str(executable), "--no-optional-locks", "-c", "core.fsmonitor=false",
        "-C", str(repository),
    ]
    returncode, stdout, stderr = _run(
        [*base, "status", "--porcelain=v2", "--branch"],
        cwd=None, timeout_seconds=timeout, output_budget=output_budget,
    )
    if returncode != 0:
        return _packet(
            operation, _identity(repository), [], {"returncode": returncode},
            [{"state": "GIT_STATUS_NONZERO", "returncode": returncode, "stderr": stderr}],
        )
    lines = stdout.splitlines()
    locations = [
        {"relative_path": ".", "kind": "git_status_line", "ordinal": index, "text": line}
        for index, line in enumerate(lines, 1)
    ]
    remote_returncode = None
    if parameters["include_remotes"]:
        remote_returncode, remote_stdout, remote_stderr = _run(
            [*base, "remote", "-v"], cwd=None, timeout_seconds=timeout, output_budget=output_budget,
        )
        if remote_returncode == 0:
            locations.extend({
                "relative_path": ".git/config", "kind": "git_remote", "ordinal": index, "text": line,
            } for index, line in enumerate(remote_stdout.splitlines(), 1))
        else:
            stderr = remote_stderr
    unresolved = []
    if remote_returncode not in (None, 0):
        unresolved.append({"state": "GIT_REMOTE_NONZERO", "returncode": remote_returncode, "stderr": stderr})
    return _packet(
        operation, _identity(repository), locations,
        {"status_returncode": returncode, "remote_returncode": remote_returncode, "status_lines": len(lines)},
        unresolved,
    )
