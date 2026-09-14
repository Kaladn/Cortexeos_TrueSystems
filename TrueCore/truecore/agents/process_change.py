"""Deterministic process-change agent for TrueMachine Fusion Packs."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Callable


STATE_SCHEMA = "truecore.process_change_agent_state@1"
DECISION_SCHEMA = "truecore.process_change_decision@1"
PROCESS_SCHEMA = "truemachine.linux.processes@2"


class ProcessChangeAgent:
    """Observe process snapshots, decide changes, and emit structured decisions."""

    agent_id = "process_change"

    def __init__(
        self,
        state_path: str | Path,
        emit_capability: Callable[[dict[str, Any]], Any] | None = None,
    ) -> None:
        self.state_path = Path(state_path)
        self.emit_capability = emit_capability
        self._state = self._load_state()

    def observe(self, fusion_pack: dict[str, Any]) -> list[dict[str, Any]]:
        """Consume one Fusion Pack and return decisions in deterministic order."""
        snapshot = self._extract_process_snapshot(fusion_pack)
        run_id = str(fusion_pack["run_id"])
        sequence = int(fusion_pack["sequence"])
        previous_run = self._state.get("run_id")
        previous_sequence = int(self._state.get("sequence", 0))
        if previous_run == run_id and sequence <= previous_sequence:
            return []

        current = {str(row["pid"]): self._identity(row) for row in snapshot}
        previous = self._state.get("processes", {}) if previous_run == run_id else {}
        decisions = self.decide(fusion_pack, previous, current, baseline=previous_run != run_id)
        self._state = {
            "schema": STATE_SCHEMA,
            "run_id": run_id,
            "sequence": sequence,
            "timeline_ns": int(fusion_pack["timeline_ns"]),
            "processes": current,
        }
        self._save_state()
        return self.emit(decisions)

    def decide(
        self,
        fusion_pack: dict[str, Any],
        previous: dict[str, dict[str, Any]],
        current: dict[str, dict[str, Any]],
        *,
        baseline: bool,
    ) -> list[dict[str, Any]]:
        """Compare bounded snapshots without consulting wall time or host state."""
        if baseline:
            return []
        decisions: list[dict[str, Any]] = []
        for pid in sorted(set(current) - set(previous), key=int):
            decisions.append(self._decision(fusion_pack, "process_started", pid, None, current[pid]))
        for pid in sorted(set(previous) - set(current), key=int):
            decisions.append(self._decision(fusion_pack, "process_stopped", pid, previous[pid], None))
        for pid in sorted(set(previous) & set(current), key=int):
            if previous[pid] != current[pid]:
                decisions.append(
                    self._decision(fusion_pack, "process_identity_changed", pid, previous[pid], current[pid])
                )
        return decisions

    def emit(self, decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Emit through the injected capability and return the exact decisions."""
        if self.emit_capability is not None:
            for decision in decisions:
                self.emit_capability(decision)
        return decisions

    @staticmethod
    def _identity(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "pid": int(row["pid"]),
            "ppid": int(row.get("ppid", 0)),
            "name": str(row.get("name", "")),
            "uid": int(row.get("uid", 0)),
        }

    @staticmethod
    def _extract_process_snapshot(fusion_pack: dict[str, Any]) -> list[dict[str, Any]]:
        if fusion_pack.get("schema") != "truemachine.fusion@2":
            raise ValueError("unsupported Fusion Pack schema")
        for observation in fusion_pack.get("observations", []):
            if observation.get("schema") == PROCESS_SCHEMA:
                if observation.get("status") != "ok":
                    raise ValueError("process observation is not usable")
                processes = observation.get("data", {}).get("processes")
                if not isinstance(processes, list):
                    raise ValueError("process observation has no process list")
                return processes
        raise ValueError("Fusion Pack contains no Linux process observation")

    @staticmethod
    def _decision(
        fusion_pack: dict[str, Any],
        decision_type: str,
        pid: str,
        previous: dict[str, Any] | None,
        current: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return {
            "schema": DECISION_SCHEMA,
            "agent_id": ProcessChangeAgent.agent_id,
            "decision_type": decision_type,
            "confidence": 1.0,
            "recommended_action": "observe",
            "source": {
                "fusion_run_id": str(fusion_pack["run_id"]),
                "fusion_sequence": int(fusion_pack["sequence"]),
                "timeline_ns": int(fusion_pack["timeline_ns"]),
                "utc": str(fusion_pack["time"]["utc"]),
            },
            "subject": {"pid": int(pid)},
            "previous": previous,
            "current": current,
        }

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {"schema": STATE_SCHEMA, "run_id": None, "sequence": 0, "processes": {}}
        state = json.loads(self.state_path.read_text(encoding="utf-8"))
        if state.get("schema") != STATE_SCHEMA:
            raise ValueError("unsupported process agent state schema")
        return state

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        content = (json.dumps(self._state, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        fd, temporary = tempfile.mkstemp(prefix=f".{self.state_path.name}.", dir=self.state_path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.state_path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run ProcessChangeAgent on one TrueMachine Fusion Pack.")
    parser.add_argument("--fusion-pack", type=Path, required=True)
    parser.add_argument("--state-path", type=Path, required=True)
    args = parser.parse_args(argv)
    pack = json.loads(args.fusion_pack.read_text(encoding="utf-8"))
    decisions = ProcessChangeAgent(args.state_path).observe(pack)
    print(json.dumps(decisions, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
