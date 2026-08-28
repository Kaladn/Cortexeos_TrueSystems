from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .operator_shell import MENU_ITEMS

if TYPE_CHECKING:
    from .operator_shell import OperatorShell


@dataclass
class LiveCockpitState:
    last_input: str = ""
    last_message: str = "Rich cockpit ready. Type a menu number, command name, /help, or /quit."
    last_kind: str = "startup"
    last_receipt: str = "none"
    last_refresh: str = ""
    last_job: str = "no active jobs"
    command_count: int = 0


def run_live_shell(shell: OperatorShell, *, refresh_seconds: float = 10.0) -> None:
    """Run the optional Rich cockpit without changing AW command behavior."""

    try:
        from rich.align import Align
        from rich.console import Console, Group
        from rich.live import Live
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
    except ImportError:
        print("Rich is not installed. Falling back to the plain AWEAR operator shell.")
        print("Install optional cockpit support with: pip install rich")
        shell.run()
        return

    console = Console()
    state = LiveCockpitState()
    refresh_seconds = max(1.0, float(refresh_seconds))

    def render() -> Panel:
        state.last_refresh = datetime.now().strftime("%H:%M:%S")
        return _build_layout(
            shell=shell,
            state=state,
            console_width=max(96, console.size.width),
            Panel=Panel,
            Table=Table,
            Text=Text,
            Group=Group,
            Align=Align,
        )

    console.clear()
    with Live(render(), console=console, screen=False, refresh_per_second=1 / refresh_seconds) as live:
        while True:
            live.update(render(), refresh=True)
            user_input = console.input("[bold cyan]aw> [/]")
            state.last_input = user_input
            result = shell.handle_input(user_input)
            state.command_count += 1
            state.last_kind = str(result.get("kind", "unknown"))
            state.last_message = str(result.get("message", ""))
            state.last_receipt = _receipt_from_result(result)
            state.last_job = _job_from_result(result)
            live.update(render(), refresh=True)
            if result.get("exit"):
                console.print("[cyan]operator cockpit closed[/]")
                return


def _build_layout(
    *,
    shell: "OperatorShell",
    state: LiveCockpitState,
    console_width: int,
    Panel: Any,
    Table: Any,
    Text: Any,
    Group: Any,
    Align: Any,
) -> Any:
    table = Table.grid(expand=True)
    table.add_column(ratio=1, min_width=24)
    table.add_column(ratio=2, min_width=46)
    table.add_column(ratio=1, min_width=32)
    table.add_row(_controls_panel(Panel, Table), _output_panel(shell, state, Panel, Text), _metrics_panel(shell, Panel, Table))

    bottom = Table.grid(expand=True)
    bottom.add_column(ratio=2)
    bottom.add_column(ratio=1)
    bottom.add_row(_jobs_panel(state, Panel, Text), _receipt_panel(state, Panel, Text))

    title = Text(" AWEAR OPERATOR COCKPIT ", style="bold cyan")
    subtitle = Text("Rich optional display | plain CLI fallback | no metrics mutation", style="yellow")
    return Panel(
        Group(Align.left(title), Align.left(subtitle), table, bottom, _footer(Text)),
        border_style="cyan",
        padding=(0, 1),
        width=min(console_width, 128),
    )


def _controls_panel(Panel: Any, Table: Any) -> Any:
    controls = Table.grid(expand=True)
    controls.add_column()
    for number, label in MENU_ITEMS:
        controls.add_row(f"[bold white]{number}[/] [green]{label}[/]")
    controls.add_row("")
    controls.add_row("[dim]Type number/name[/]")
    controls.add_row("[dim]/help and /quit work[/]")
    return Panel(controls, title="[bold yellow]CONTROLS[/]", border_style="blue")


def _output_panel(shell: "OperatorShell", state: LiveCockpitState, Panel: Any, Text: Any) -> Any:
    message = _compact(state.last_message, 18)
    body = Text()
    body.append(f"mode: {shell.mode.upper()}\n", style="bold white")
    body.append(f"active_dataset: {shell.dataset_id or 'none'}\n", style="white")
    body.append(f"last_input: {state.last_input or 'none'}\n", style="dim")
    body.append(f"last_kind: {state.last_kind}\n\n", style="dim")
    body.append(message, style="white")
    return Panel(body, title="[bold yellow]CHAT / DATASET OUTPUT[/]", border_style="blue")


def _metrics_panel(shell: "OperatorShell", Panel: Any, Table: Any) -> Any:
    metrics = shell.read_system_metrics()
    resources = metrics.get("resources") if isinstance(metrics.get("resources"), dict) else {}
    totals = metrics.get("totals") if isinstance(metrics.get("totals"), dict) else {}
    active = metrics.get("active_dataset") if isinstance(metrics.get("active_dataset"), dict) else {}
    symbol = metrics.get("symbol_allocation_audit") if isinstance(metrics.get("symbol_allocation_audit"), dict) else {}

    rows = [
        ("CPU cores", resources.get("logical_cpu_count")),
        ("RAM total", _bytes(resources.get("ram_total_bytes"))),
        ("RAM avail", _bytes(resources.get("ram_available_bytes"))),
        ("Reserve 15%", _bytes(resources.get("ram_reserved_15_percent_bytes"))),
        ("Datasets", metrics.get("dataset_count")),
        ("Anchors", totals.get("anchor_count")),
        ("Relations", totals.get("relation_count")),
        ("Postings", totals.get("block_anchor_posting_count")),
        ("Citations", totals.get("citation_count")),
        ("QA rows", totals.get("qa_record_count")),
        ("Symbolizer", symbol.get("current_allocator_kind")),
        ("Last symbol", symbol.get("last_global_symbol_id")),
        ("Query ready", active.get("query_allowed") if active else None),
    ]
    table = Table.grid(expand=True)
    table.add_column(style="bold white", no_wrap=True)
    table.add_column(style="cyan")
    for key, value in rows:
        table.add_row(str(key), str(value if value is not None else "n/a"))
    return Panel(table, title="[bold yellow]LIVE SYSTEM METRICS[/]", border_style="blue")


def _jobs_panel(state: LiveCockpitState, Panel: Any, Text: Any) -> Any:
    body = Text()
    body.append(f"{state.last_job}\n", style="magenta")
    body.append("Heavy operations still run through existing commands.\n", style="white")
    body.append("This cockpit reads receipts/metrics; it does not own backend work.", style="dim")
    return Panel(body, title="[bold yellow]ACTIVE JOBS[/]", border_style="blue")


def _receipt_panel(state: LiveCockpitState, Panel: Any, Text: Any) -> Any:
    body = Text()
    body.append(f"last_receipt: {state.last_receipt}\n", style="white")
    body.append(f"commands_seen: {state.command_count}\n", style="white")
    body.append(f"last_refresh: {state.last_refresh}", style="dim")
    return Panel(body, title="[bold yellow]RECEIPT / STATUS[/]", border_style="blue")


def _footer(Text: Any) -> Any:
    text = Text()
    text.append("Display law: ", style="bold white")
    text.append("metrics are read-only; menu remains numbered; plain CLI remains available.", style="dim")
    return text


def _receipt_from_result(result: dict[str, object]) -> str:
    qa_record = result.get("qa_record") if isinstance(result.get("qa_record"), dict) else {}
    if qa_record:
        record_id = qa_record.get("record_id")
        if record_id:
            return str(record_id)
    for key in ("output_path", "message"):
        value = result.get(key)
        if isinstance(value, (str, Path)) and value:
            return _short_path(str(value))
    return "none"


def _job_from_result(result: dict[str, object]) -> str:
    kind = str(result.get("kind", "unknown"))
    if kind in {"command_contract", "menu_card"}:
        command = result.get("command")
        return f"ready: {command or kind}"
    if kind == "aw_question":
        return "dataset question complete"
    if kind == "system_metrics":
        return "metrics refreshed"
    return kind


def _compact(value: str, max_lines: int) -> str:
    lines = str(value or "").splitlines()
    if len(lines) <= max_lines:
        return "\n".join(lines)
    head = lines[: max_lines - 1]
    head.append(f"... {len(lines) - len(head)} more lines")
    return "\n".join(head)


def _short_path(value: str) -> str:
    path = Path(value)
    parts = path.parts
    if len(parts) <= 4:
        return value
    return str(Path(*parts[-4:]))


def _bytes(value: object) -> str:
    if not isinstance(value, int):
        return "n/a"
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
