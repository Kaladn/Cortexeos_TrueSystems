from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from .engine import append_chat_count
from .engine import default_chat_count_root
from .engine import query as aw_query
from .engine import status as aw_status
from .engine import system_metrics
from .operator_contract import COMMAND_REGISTRY, parse_operator_command
from .operator_state import audit_operator_state


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="awear-operator",
        description="Chat-first terminal operator shell for AWEAR command contracts.",
    )
    parser.add_argument("--once", help="Process one live operator input and exit.")
    parser.add_argument("--json", action="store_true", help="Emit JSON for --once.")
    parser.add_argument("--launch-side-windows", action="store_true", help="Allow implemented side-window commands to launch helpers.")
    parser.add_argument("--runtime-root", type=Path, help="Runtime root for live AW question mode.")
    parser.add_argument("--dataset-id", help="Dataset id for live AW question mode.")
    parser.add_argument("--top-k", type=int, default=5, help="Top-K evidence locations for live AW question mode.")
    parser.add_argument("--chat-count-root", type=Path, help="Root for daily operator chat count field.")
    parser.add_argument("--no-chat-counts", action="store_true", help="Disable normal chat daily count append.")
    parser.add_argument("--live", action="store_true", help="Use the optional Rich live cockpit display if Rich is installed.")
    parser.add_argument("--live-refresh-seconds", type=float, default=10.0, help="Seconds between Rich cockpit refreshes.")
    args = parser.parse_args()

    shell = OperatorShell(
        launch_side_windows=args.launch_side_windows,
        runtime_root=args.runtime_root,
        dataset_id=args.dataset_id,
        top_k=args.top_k,
        chat_count_root=args.chat_count_root,
        chat_counts_enabled=not args.no_chat_counts,
    )
    if args.once is not None:
        result = shell.handle_input(args.once)
        if args.json:
            print(json.dumps(result, ensure_ascii=True))
        else:
            print(result["message"])
        return

    if args.live:
        from .operator_live import run_live_shell

        run_live_shell(shell, refresh_seconds=args.live_refresh_seconds)
        return

    shell.run()


class OperatorShell:
    def __init__(
        self,
        *,
        launch_side_windows: bool = False,
        runtime_root: str | Path | None = None,
        dataset_id: str | None = None,
        top_k: int = 5,
        chat_count_root: str | Path | None = None,
        chat_counts_enabled: bool = True,
    ) -> None:
        self.launch_side_windows = launch_side_windows
        self.runtime_root = Path(runtime_root).expanduser().resolve() if runtime_root is not None else None
        self.dataset_id = dataset_id
        self.top_k = top_k
        self.mode = "chat"
        self.chat_counts_enabled = bool(chat_counts_enabled)
        self.chat_count_root = (
            Path(chat_count_root).expanduser().resolve()
            if chat_count_root is not None
            else default_chat_count_root(runtime_root=self.runtime_root, repo_root=Path(__file__).resolve().parents[2])
        )

    def run(self) -> None:
        print("AWEAR Operator Shell")
        print("Chat stays central. Type menu or help for the numbered cockpit.")
        if self.is_connected:
            print(self._connection_card())
            print("Default mode is CHAT. Switch to RAG/Dataset mode before dataset questions.")
        else:
            print("No dataset connected. Start with --runtime-root and --dataset-id for AW question mode.")
        print(render_menu())
        print("Slash commands must start at character 0. Type /quit to exit.")
        while True:
            try:
                live_input = input("\naw> ")
            except (EOFError, KeyboardInterrupt):
                print("\noperator shell closed")
                return
            result = self.handle_input(live_input)
            print(result["message"])
            if result.get("exit"):
                return

    def handle_input(self, live_input: str) -> dict[str, object]:
        osrl_audit = audit_operator_state(live_input)
        menu_choice = parse_menu_choice(live_input)
        if menu_choice is not None:
            return self._handle_menu_choice(menu_choice, osrl_audit=osrl_audit)
        command = parse_operator_command(live_input)
        if command is None:
            if self.is_connected and self.mode == "dataset" and live_input.strip():
                return self._handle_aw_question(live_input, osrl_audit=osrl_audit)
            chat_count = self._append_chat_count(live_input) if self.mode == "chat" and live_input.strip() else None
            return {
                "kind": "conversation_osrl",
                "mode": self.mode,
                "chat_count_record": chat_count,
                "message": _chat_mode_message(osrl_audit, chat_count),
                "accepted": False,
                "osrl_audit": osrl_audit,
            }
        if command.name == "help":
            return {"kind": "help", "accepted": True, "message": render_menu(), "osrl_audit": osrl_audit}
        if command.name == "quit":
            return {"kind": "quit", "accepted": True, "exit": True, "message": "operator shell closed", "osrl_audit": osrl_audit}
        if command.name == "settings":
            return {
                "kind": "settings",
                "accepted": True,
                "message": f"side_window_launch={'enabled' if self.launch_side_windows else 'disabled'}",
                "osrl_audit": osrl_audit,
            }
        if not command.implemented:
            return {
                "kind": "locked",
                "accepted": True,
                "command": command.name,
                "message": f"{command.prefix} is locked: action bridge not enabled.",
                "osrl_audit": osrl_audit,
            }
        if command.name == "laptop" and self.launch_side_windows:
            result = self._launch_laptop_helper()
            result["osrl_audit"] = osrl_audit
            return result
        return {
            "kind": "command_contract",
            "accepted": True,
            "command": command.name,
            "mutating": command.mutating,
            "side_window": command.side_window,
            "message": _command_card(command.name),
            "osrl_audit": osrl_audit,
        }

    @property
    def is_connected(self) -> bool:
        return self.runtime_root is not None and bool(self.dataset_id)

    def _connection_card(self) -> str:
        assert self.runtime_root is not None
        assert self.dataset_id is not None
        try:
            state = aw_status(self.runtime_root, self.dataset_id)
            return "\n".join(
                [
                    "Connected dataset:",
                    f"- runtime_root: {self.runtime_root}",
                    f"- dataset_id: {self.dataset_id}",
                    f"- index_status: {state.get('index_status')}",
                    f"- query_allowed: {str(state.get('query_allowed')).lower()}",
                    f"- count_backend: {state.get('count_backend')}",
                    f"- anchors: {state.get('anchor_count')}",
                    f"- relations: {state.get('relation_count')}",
                    f"- blocks: {state.get('block_count')}",
                ]
            )
        except Exception as exc:  # noqa: BLE001 - connection card should explain why chat cannot query.
            return "\n".join(
                [
                    "Dataset connection failed:",
                    f"- runtime_root: {self.runtime_root}",
                    f"- dataset_id: {self.dataset_id}",
                    f"- error: {exc}",
                ]
            )

    def read_system_metrics(self) -> dict[str, object]:
        return system_metrics(
            runtime_root=self.runtime_root,
            dataset_id=self.dataset_id,
            repo_path=Path(__file__).resolve().parents[2],
        )

    def _handle_aw_question(self, question: str, *, osrl_audit: dict[str, object]) -> dict[str, object]:
        assert self.runtime_root is not None
        assert self.dataset_id is not None
        result = aw_query(self.runtime_root, self.dataset_id, question, top_k=self.top_k)
        message = _render_aw_chat_answer(result)
        return {
            "kind": "aw_question",
            "accepted": True,
            "dataset_id": self.dataset_id,
            "runtime_root": str(self.runtime_root),
            "output_path": result.get("output_path"),
            "qa_record": result.get("qa_record"),
            "model_used": result.get("model_used", "none"),
            "model_may_search": result.get("model_may_search", False),
            "mode": self.mode,
            "message": message,
            "osrl_audit": osrl_audit,
        }

    def _handle_menu_choice(self, choice: str, *, osrl_audit: dict[str, object]) -> dict[str, object]:
        if choice in {"menu", "help"}:
            return {"kind": "menu", "accepted": True, "mode": self.mode, "message": render_menu(), "osrl_audit": osrl_audit}
        if choice in {"1", "chat", "chat mode"}:
            self.mode = "chat"
            return {
                "kind": "mode_change",
                "accepted": True,
                "mode": self.mode,
                "message": (
                    "CHAT mode active. Normal text will not query datasets or write dataset Q/A ledger records. "
                    f"Daily chat counts append under: {self.chat_count_root}"
                ),
                "osrl_audit": osrl_audit,
            }
        if choice in {"2", "rag", "rag/dataset", "dataset", "dataset mode", "rag/dataset mode", "5", "ask active dataset"}:
            self.mode = "dataset"
            if not self.is_connected:
                return {
                    "kind": "mode_change",
                    "accepted": False,
                    "mode": self.mode,
                    "message": "RAG/Dataset mode selected, but no dataset is connected. Relaunch with --runtime-root and --dataset-id.",
                    "osrl_audit": osrl_audit,
                }
            return {
                "kind": "mode_change",
                "accepted": True,
                "mode": self.mode,
                "message": "RAG/Dataset mode active. The next normal input will run against the active dataset and write a dataset-local Q/A ledger row.",
                "osrl_audit": osrl_audit,
            }
        if choice in {"3", "ingest", "ingest new dataset"}:
            return {"kind": "menu_card", "accepted": True, "mode": self.mode, "message": _command_card("intake"), "osrl_audit": osrl_audit}
        if choice in {"4", "open", "open existing dataset"}:
            return {
                "kind": "menu_card",
                "accepted": True,
                "mode": self.mode,
                "message": _open_dataset_card(self),
                "osrl_audit": osrl_audit,
            }
        if choice in {"6", "overview", "dataset overview"}:
            return {"kind": "menu_card", "accepted": True, "mode": self.mode, "message": _overview_card(), "osrl_audit": osrl_audit}
        if choice in {"7", "count-walk", "count walk", "count-walk speech", "count walk speech"}:
            return {"kind": "menu_card", "accepted": True, "mode": self.mode, "message": _command_card("speech"), "osrl_audit": osrl_audit}
        if choice in {"8", "metrics", "system metrics"}:
            metrics = system_metrics(
                runtime_root=self.runtime_root,
                dataset_id=self.dataset_id,
                repo_path=Path(__file__).resolve().parents[2],
            )
            return {
                "kind": "system_metrics",
                "accepted": True,
                "mode": self.mode,
                "metrics": metrics,
                "message": _render_system_metrics(metrics),
                "osrl_audit": osrl_audit,
            }
        if choice in {"9", "export", "export dataset receipts/q&a", "export dataset receipts", "export q/a"}:
            return {"kind": "menu_card", "accepted": True, "mode": self.mode, "message": _export_card(), "osrl_audit": osrl_audit}
        if choice in {"10", "quit", "exit"}:
            return {"kind": "quit", "accepted": True, "exit": True, "mode": self.mode, "message": "operator shell closed", "osrl_audit": osrl_audit}
        return {"kind": "menu", "accepted": False, "mode": self.mode, "message": render_menu(), "osrl_audit": osrl_audit}

    def _launch_laptop_helper(self) -> dict[str, object]:
        script = Path(__file__).resolve().parents[2] / "Start_Laptop_Temp_Intake.ps1"
        if not script.exists():
            return {
                "kind": "side_window_missing",
                "accepted": True,
                "command": "laptop",
                "message": f"laptop side-window helper missing: {script}",
            }
        subprocess.Popen(["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", str(script)])
        return {
            "kind": "side_window_launched",
            "accepted": True,
            "command": "laptop",
            "message": "Started laptop temp intake side-window helper.",
        }

    def _append_chat_count(self, live_input: str) -> dict[str, object] | None:
        if not self.chat_counts_enabled:
            return None
        return append_chat_count(self.chat_count_root, live_input, source="operator_chat")


def _command_card(command_name: str) -> str:
    command = COMMAND_REGISTRY[command_name]
    lines = [
        f"{command.prefix} command",
        f"shortcut: {command.shortcut}",
        f"summary: {command.summary}",
        f"mutating: {str(command.mutating).lower()}",
        f"side_window: {str(command.side_window).lower()}",
        "touches:",
        *[f"- {value}" for value in command.touches],
        "receipts:",
        *[f"- {value}" for value in command.receipts],
        "review:",
        *[f"- {value}" for value in command.next_review],
        "run:",
        command.cli_template,
    ]
    if command.mutating:
        lines.append("receipt required before trust.")
    return "\n".join(lines)


MENU_ITEMS: tuple[tuple[str, str], ...] = (
    ("1", "Chat mode"),
    ("2", "RAG/Dataset mode"),
    ("3", "Ingest new dataset"),
    ("4", "Open existing dataset"),
    ("5", "Ask active dataset"),
    ("6", "Dataset overview"),
    ("7", "Count-walk speech"),
    ("8", "System metrics"),
    ("9", "Export dataset receipts/Q&A"),
    ("10", "Quit"),
)


def parse_menu_choice(live_input: str) -> str | None:
    value = " ".join(str(live_input or "").strip().casefold().split())
    if not value:
        return None
    names = {"menu", "help"}
    for number, label in MENU_ITEMS:
        names.add(number)
        names.add(label.casefold())
    return value if value in names else None


def render_menu() -> str:
    lines = [
        "AWEAR CLI Cockpit",
        "",
        "Modes:",
        "- CHAT mode: talk only; no dataset query and no dataset Q/A ledger write.",
        "- RAG/Dataset mode: questions run against the active dataset and write dataset-local Q/A records.",
        "- System metrics: read-only runtime/dataset/resource page.",
        "",
        "Menu:",
    ]
    lines.extend(f"{number}. {label}" for number, label in MENU_ITEMS)
    lines.extend(
        [
            "",
            "Type a number, a menu name, menu, or help.",
            "Heavy work is launched through the shown AWEAR CLI command cards.",
        ]
    )
    return "\n".join(lines)


def _chat_mode_message(osrl_audit: dict[str, object], chat_count: dict[str, object] | None = None) -> str:
    payload = osrl_audit.get("system_output", {}) if isinstance(osrl_audit, dict) else {}
    rendered = payload.get("payload") if isinstance(payload, dict) else None
    lines = [
        str(rendered or "CHAT mode received input."),
        "",
        "CHAT mode active: no dataset query ran and no dataset Q/A ledger was written.",
    ]
    if chat_count and chat_count.get("appended"):
        lines.extend(
            [
                f"chat_count_day: {chat_count.get('chat_day')}",
                f"chat_count_events: {chat_count.get('event_count')}",
                f"chat_count_file: {chat_count.get('events_path')}",
            ]
        )
    elif chat_count is None:
        lines.append("chat_count: disabled or not applicable")
    lines.extend(
        [
            "Type 2 or RAG/Dataset mode before asking the active dataset.",
            "Type menu for the cockpit.",
        ]
    )
    return "\n".join(lines)


def _open_dataset_card(shell: OperatorShell) -> str:
    lines = [
        "Open existing dataset",
        "This cockpit does not mutate or switch datasets silently.",
        "Relaunch with:",
        "python -m awear.operator_shell --runtime-root <runtime> --dataset-id <dataset>",
    ]
    if shell.runtime_root is not None:
        datasets_root = shell.runtime_root / "datasets"
        dataset_ids = sorted(item.name for item in datasets_root.iterdir() if item.is_dir()) if datasets_root.exists() else []
        lines.append("")
        lines.append("known datasets:")
        lines.extend(f"- {item}" for item in dataset_ids[:25])
        if len(dataset_ids) > 25:
            lines.append(f"- ... {len(dataset_ids) - 25} more")
    return "\n".join(lines)


def _overview_card() -> str:
    return "\n".join(
        [
            "Dataset overview",
            "run:",
            "python -m awear.cli dataset-overview --runtime-root <runtime> --dataset <dataset> --out <overview-folder>",
            "read-only overview; no intake, query, model, or count mutation.",
        ]
    )


def _export_card() -> str:
    return "\n".join(
        [
            "Export dataset receipts/Q&A",
            "Q/A ledger:",
            "python -m awear.cli qa-export --runtime-root <runtime> --dataset <dataset> --output <qa_export.jsonl>",
            "Receipts:",
            "open <runtime>/datasets/<dataset>/receipts/",
            "read-only export; no global memory.",
        ]
    )


def _render_system_metrics(metrics: dict[str, object]) -> str:
    resources = metrics.get("resources") if isinstance(metrics.get("resources"), dict) else {}
    totals = metrics.get("totals") if isinstance(metrics.get("totals"), dict) else {}
    symbol_audit = metrics.get("symbol_allocation_audit") if isinstance(metrics.get("symbol_allocation_audit"), dict) else {}
    active = metrics.get("active_dataset") if isinstance(metrics.get("active_dataset"), dict) else {}
    lines = [
        "AWEAR system metrics",
        f"runtime_path: {metrics.get('runtime_path')}",
        f"repo_path: {metrics.get('repo_path')}",
        f"active_dataset_id: {metrics.get('active_dataset_id')}",
        f"dataset_count: {metrics.get('dataset_count')}",
        f"count_backend: {metrics.get('count_backend')}",
        "",
        "resources:",
        f"- cpu_cores: {resources.get('logical_cpu_count')}",
        f"- ram_total_bytes: {resources.get('ram_total_bytes')}",
        f"- ram_used_bytes: {resources.get('ram_used_bytes')}",
        f"- ram_available_bytes: {resources.get('ram_available_bytes')}",
        f"- ram_reserved_15_percent_bytes: {resources.get('ram_reserved_15_percent_bytes')}",
        "",
        "dataset totals:",
        f"- admitted_dataset_artifact_size_bytes: {totals.get('admitted_dataset_artifact_size_bytes')}",
        f"- total_dataset_lexicon_symbols_observed: {totals.get('total_dataset_lexicon_symbols_observed')}",
        f"- relation_count: {totals.get('relation_count')}",
        f"- block_anchor_posting_count: {totals.get('block_anchor_posting_count')}",
        f"- citation_count: {totals.get('citation_count')}",
        f"- coordinate_count: {totals.get('coordinate_count')}",
        "",
        "active dataset:",
        f"- index_status: {active.get('index_status')}",
        f"- query_allowed: {active.get('query_allowed')}",
        f"- last_ingest_receipt_path: {active.get('last_ingest_receipt_path')}",
        f"- last_query_receipt_path: {active.get('last_query_receipt_path')}",
        f"- workers_requested_last_ingest: {active.get('workers_requested_last_ingest')}",
        f"- workers_actual_last_ingest: {active.get('workers_actual_last_ingest')}",
        "",
        "symbol allocation audit:",
        f"- allocator: {symbol_audit.get('current_allocator_kind')}",
        f"- global_monotonic_allocator_active: {str(symbol_audit.get('global_monotonic_allocator_active')).lower()}",
        f"- last_global_symbol_id: {symbol_audit.get('last_global_symbol_id')}",
        f"- audit_result: {symbol_audit.get('audit_result')}",
    ]
    return "\n".join(lines)


def _render_aw_chat_answer(result: dict[str, object]) -> str:
    answer_packet = result.get("answer_packet") if isinstance(result.get("answer_packet"), dict) else {}
    final_answer = result.get("final_answer") if isinstance(result.get("final_answer"), dict) else {}
    qualification = answer_packet.get("qualification") if isinstance(answer_packet, dict) else {}
    locations = answer_packet.get("locations") if isinstance(answer_packet, dict) else []
    qa_record = result.get("qa_record") if isinstance(result.get("qa_record"), dict) else {}
    if not isinstance(locations, list):
        locations = []

    lines = [
        "AW answer",
        f"support: {qualification.get('support_state') if isinstance(qualification, dict) else 'unknown'}",
        f"model_used: {result.get('model_used', 'none')}",
        f"model_may_search: {str(result.get('model_may_search', False)).lower()}",
        "",
        "speech_summary:",
        str(final_answer.get("text", "No answer text returned.") if isinstance(final_answer, dict) else "No answer text returned."),
        "",
        "data links:",
    ]
    if not locations:
        lines.append("- none")
    for index, location in enumerate(locations[:3], start=1):
        if not isinstance(location, dict):
            continue
        file_path = location.get("file_path")
        line_start = location.get("line_start")
        source_link = f"{file_path}:{line_start}" if file_path and line_start else file_path
        lines.append(
            "- "
            f"{index}. {location.get('citation')} "
            f"source={source_link} "
            f"lines={location.get('line_start')}-{location.get('line_end')} "
            f"direct={location.get('direct_hit_count')} "
            f"density={location.get('density_score')} "
            f"score={location.get('score')}"
        )
    lines.extend(
        [
            "",
            f"packet_file: {result.get('output_path')}",
            f"qa_record: {qa_record.get('record_id') if isinstance(qa_record, dict) else None}",
            f"qa_ledger: {qa_record.get('qa_ledger_path') if isinstance(qa_record, dict) else None}",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
