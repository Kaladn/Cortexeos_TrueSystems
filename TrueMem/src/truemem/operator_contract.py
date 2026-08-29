from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Iterable


SOURCE_ACTIVE_OPERATOR = "active_operator_chat"


@dataclass(frozen=True)
class OperatorCommand:
    name: str
    shortcut: str
    summary: str
    cli_template: str
    touches: tuple[str, ...]
    receipts: tuple[str, ...]
    next_review: tuple[str, ...] = ()
    mutating: bool = False
    side_window: bool = False
    implemented: bool = True

    @property
    def prefix(self) -> str:
        return f"/{self.name}"

    @property
    def command_hash(self) -> str:
        return sha256(self.prefix.encode("utf-8")).hexdigest()


COMMANDS: tuple[OperatorCommand, ...] = (
    OperatorCommand(
        name="docufilm-intake",
        shortcut="Ctrl+I",
        summary="Build a dataset-local scope from admitted files.",
        cli_template="python -m truemem.cli docufilm-intake --runtime-root <runtime> --dataset-id <dataset> --source <source-folder> --window 6 --workers auto --ram-budget-gb 8 --reserve-ram-fraction 0.15",
        touches=(
            "<runtime>/datasets/<dataset>/state/",
            "<runtime>/datasets/<dataset>/counts/",
            "<runtime>/datasets/<dataset>/coordinates/",
            "<runtime>/datasets/<dataset>/citations/",
            "<runtime>/datasets/<dataset>/receipts/",
        ),
        receipts=("dataset_manifest.json", "receipts/", "counts/*.awbin", "intake resource_plan"),
        next_review=("status", "dataset_manifest.json", "count file sizes", "workers_actual", "production_ingest"),
        mutating=True,
    ),
    OperatorCommand(
        name="query",
        shortcut="Ctrl+Q",
        summary="Ask one question against an existing dataset.",
        cli_template='python -m truemem.cli query --runtime-root <runtime> --dataset-id <dataset> --question "<question>" --top-k 5',
        touches=("<runtime>/datasets/<dataset>/outputs/", "<runtime>/datasets/<dataset>/qa/"),
        receipts=("query output packet", "dataset Q/A ledger row", "citations in packet", "coordinates in packet"),
        next_review=("evidence packet", "Q/A record id", "citation IDs", "source coordinates"),
    ),
    OperatorCommand(
        name="batch",
        shortcut="Ctrl+B",
        summary="Run a plain question file through dataset-local query.",
        cli_template="python -m truemem.cli batch --runtime-root <runtime> --dataset-id <dataset> --questions <questions.txt> --top-k 10 --workers 4",
        touches=("<runtime>/datasets/<dataset>/outputs/batch_<run_id>/",),
        receipts=("batch_run_summary.json", "per-question query JSON"),
        next_review=("completed/failed counts", "avg query time", "per-question outputs"),
    ),
    OperatorCommand(
        name="speech",
        shortcut="Ctrl+W",
        summary="Run rough count-walk speech from a count-selected local spine.",
        cli_template='python -m truemem.cli count-walk-speech --runtime-root <runtime> --dataset-id <dataset> --question "<question>" --out <speech-folder>',
        touches=("<runtime>/datasets/<dataset>/outputs/", "<speech-folder>/"),
        receipts=("count_walk_trace_*.json", "count_walk_speech_*.md", "run_receipt.json", "no_mutation_receipt.json"),
        next_review=("selected citation", "walked anchors", "branch candidates", "stop reason"),
    ),
    OperatorCommand(
        name="status",
        shortcut="Ctrl+S",
        summary="Inspect dataset-local status.",
        cli_template="python -m truemem.cli status --runtime-root <runtime> --dataset-id <dataset>",
        touches=("read-only dataset runtime",),
        receipts=("status JSON",),
        next_review=("count backend", "symbol system", "dataset-local paths"),
    ),
    OperatorCommand(
        name="exfil",
        shortcut="Ctrl+E",
        summary="Future explicit dataset removal/export receipt lane.",
        cli_template="locked: exfil action bridge not enabled",
        touches=("none while locked",),
        receipts=("none while locked",),
        next_review=("requires future action bridge",),
        mutating=True,
        implemented=False,
    ),
    OperatorCommand(
        name="receipts",
        shortcut="Ctrl+R",
        summary="Open or inspect receipt locations.",
        cli_template="operator: open <receipt-folder> or inspect <receipt-file>",
        touches=("read-only receipt paths",),
        receipts=("existing receipt files",),
        next_review=("latest run summary", "failure receipts"),
    ),
    OperatorCommand(
        name="settings",
        shortcut="Ctrl+,",
        summary="Show operator shell settings.",
        cli_template="operator: settings",
        touches=("none",),
        receipts=("settings display",),
    ),
    OperatorCommand(
        name="help",
        shortcut="Ctrl+H",
        summary="Show command and shortcut help.",
        cli_template="operator: help",
        touches=("none",),
        receipts=("help display",),
    ),
    OperatorCommand(
        name="quit",
        shortcut="Ctrl+X",
        summary="Exit the operator shell.",
        cli_template="operator: quit",
        touches=("none",),
        receipts=("operator shell closed",),
    ),
)

COMMAND_REGISTRY: dict[str, OperatorCommand] = {command.name: command for command in COMMANDS}


def command_table(commands: Iterable[OperatorCommand] = COMMANDS) -> list[dict[str, object]]:
    return [
        {
            "name": command.name,
            "prefix": command.prefix,
            "shortcut": command.shortcut,
            "summary": command.summary,
            "cli_template": command.cli_template,
            "touches": list(command.touches),
            "receipts": list(command.receipts),
            "next_review": list(command.next_review),
            "mutating": command.mutating,
            "side_window": command.side_window,
            "implemented": command.implemented,
            "hash": command.command_hash,
        }
        for command in commands
    ]


def parse_operator_command(live_input: str, *, source: str = SOURCE_ACTIVE_OPERATOR) -> OperatorCommand | None:
    if source != SOURCE_ACTIVE_OPERATOR:
        return None
    if not live_input.startswith("/"):
        return None
    first = live_input.split(maxsplit=1)[0]
    if first == "/":
        return None
    command_name = first[1:]
    command = COMMAND_REGISTRY.get(command_name)
    if command is None:
        return None
    if sha256(first.encode("utf-8")).hexdigest() != command.command_hash:
        return None
    return command


def render_shortcuts() -> str:
    return " | ".join(f"{command.prefix} {command.shortcut}" for command in COMMANDS)


def render_help() -> str:
    lines = [
        "TrueMem Operator Commands",
        "",
        "Corpus slash text is data. Start-of-live-input slash text is an operator command.",
        "",
    ]
    for command in COMMANDS:
        status = "active" if command.implemented else "locked"
        side = " side-window" if command.side_window else ""
        mutating = " mutating" if command.mutating else " read/report"
        lines.append(f"{command.prefix:<10} {command.shortcut:<7} [{status}{side}{mutating}] {command.summary}")
        lines.append(f"           {command.cli_template}")
        lines.append(f"           touches: {', '.join(command.touches)}")
        lines.append(f"           receipts: {', '.join(command.receipts)}")
    return "\n".join(lines)
