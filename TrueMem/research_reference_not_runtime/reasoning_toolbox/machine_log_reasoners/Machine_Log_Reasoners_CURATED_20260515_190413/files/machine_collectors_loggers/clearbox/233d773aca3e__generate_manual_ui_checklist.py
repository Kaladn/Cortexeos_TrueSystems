#!/usr/bin/env python3
"""Generate an exhaustive manual UI byte-check checklist from the main UI file."""

from __future__ import annotations

import datetime as _dt
import re
from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
HTML_PATH = ROOT / "ui" / "clearbox_ai_production.html"
JS_DIR = ROOT / "ui" / "js"
OUT_PATH = ROOT / "docs" / "MANUAL_HUMAN_UI_BYTE_CHECKLIST_EXHAUSTIVE.md"
OUT_TXT_PATH = ROOT / "docs" / "MANUAL_HUMAN_UI_BYTE_CHECKLIST_EXHAUSTIVE.txt"

CONTROL_TAGS = {"button", "input", "select", "textarea"}
HOOK_ATTRS = ("onclick", "onchange", "oninput", "onkeyup", "onblur", "onfocus")
OUTPUT_ID_KEYWORDS = (
    "status",
    "result",
    "response",
    "output",
    "log",
    "preview",
    "list",
    "table",
    "chart",
    "metrics",
    "metric",
    "health",
    "error",
    "message",
    "msg",
    "count",
    "queue",
    "history",
    "report",
    "graph",
    "monitor",
    "stream",
    "timeline",
)

TAG_OPEN_RE = re.compile(r"<([a-zA-Z0-9:-]+)\b([^>]*)>")
ATTR_RE = re.compile(r"""([A-Za-z_:][\w:.-]*)\s*=\s*("([^"]*)"|'([^']*)')""")
CONTROL_RE = re.compile(r"<(button|input|select|textarea)\b([^>]*)>", re.IGNORECASE)
BUTTON_INLINE_TEXT_RE = re.compile(r"<button\b[^>]*>(.*?)</button>", re.IGNORECASE)
TAG_TEXT_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class Control:
    line: int
    context: str
    tag: str
    ident: str
    input_type: str
    hooks: str
    label: str
    help_id: str


@dataclass(frozen=True)
class OutputSurface:
    line: int
    context: str
    tag: str
    ident: str
    hint: str


def _parse_attrs(src: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for m in ATTR_RE.finditer(src):
        key = m.group(1).lower().strip()
        value = m.group(3) if m.group(3) is not None else (m.group(4) or "")
        attrs[key] = value.strip()
    return attrs


def _clean_text(raw: str) -> str:
    stripped = TAG_TEXT_RE.sub(" ", raw)
    compact = " ".join(stripped.split())
    return compact


def _id_or_name(attrs: dict[str, str], line: int, tag: str) -> str:
    if attrs.get("id"):
        return attrs["id"]
    if attrs.get("name"):
        return f'name={attrs["name"]}'
    return f"{tag}@L{line}"


def _hooks(attrs: dict[str, str]) -> str:
    chunks: list[str] = []
    for key in HOOK_ATTRS:
        val = attrs.get(key, "").strip()
        if val:
            chunks.append(f"{key}:{val}")
    return " | ".join(chunks) if chunks else "-"


def _context_from_attrs(attrs: dict[str, str]) -> str | None:
    ident = attrs.get("id", "").strip()
    klass = attrs.get("class", "").strip().lower()
    if not ident:
        return None
    if (
        "panel" in klass
        or "modal" in klass
        or "overlay" in klass
        or "tab-content" in klass
        or ident.startswith("panel-")
        or ident.endswith("-panel")
        or ident.endswith("-modal")
        or ident.endswith("-overlay")
    ):
        return ident
    return None


def _extract_controls_and_outputs(full_text: str) -> tuple[list[Control], list[OutputSurface]]:
    controls: list[Control] = []
    outputs: list[OutputSurface] = []
    current_context = "global"
    line_starts = [0]
    line_starts.extend(m.end() for m in re.finditer(r"\n", full_text))

    def _line_for_pos(pos: int) -> int:
        return bisect_right(line_starts, pos)

    for tag_m in TAG_OPEN_RE.finditer(full_text):
        tag = tag_m.group(1).lower()
        attrs = _parse_attrs(tag_m.group(2))
        line_no = _line_for_pos(tag_m.start())

        new_context = _context_from_attrs(attrs)
        if new_context:
            current_context = new_context

        ident = attrs.get("id", "").strip()
        if ident and tag not in CONTROL_TAGS:
            low = ident.lower()
            if any(k in low for k in OUTPUT_ID_KEYWORDS):
                hint = attrs.get("class", "").strip() or attrs.get("title", "").strip() or "-"
                outputs.append(
                    OutputSurface(
                        line=line_no,
                        context=current_context,
                        tag=tag,
                        ident=ident,
                        hint=hint or "-",
                    )
                )

        if tag not in CONTROL_TAGS:
            continue

        ident = _id_or_name(attrs, line_no, tag)
        input_type = attrs.get("type", "").strip() if tag == "input" else tag
        input_type = input_type or "-"

        inline_label = "-"
        if tag == "button":
            close_idx = full_text.find("</button>", tag_m.end())
            if close_idx != -1:
                raw = full_text[tag_m.end() : close_idx]
                inline_label = _clean_text(raw) or "-"
        elif tag == "textarea":
            close_idx = full_text.find("</textarea>", tag_m.end())
            if close_idx != -1:
                raw = full_text[tag_m.end() : close_idx]
                inline_label = _clean_text(raw) or "-"

        if inline_label == "-":
            inline_label = (
                attrs.get("aria-label", "").strip()
                or attrs.get("title", "").strip()
                or attrs.get("placeholder", "").strip()
                or "-"
            )

        controls.append(
            Control(
                line=line_no,
                context=current_context,
                tag=tag,
                ident=ident,
                input_type=input_type,
                hooks=_hooks(attrs),
                label=inline_label,
                help_id=attrs.get("data-help-id", "").strip() or "-",
            )
        )

    return controls, outputs


def _extract_dynamic_candidates(js_dir: Path) -> list[tuple[str, int, str]]:
    out: list[tuple[str, int, str]] = []
    if not js_dir.exists():
        return out

    needle = re.compile(r"<(button|input|select|textarea)\b|onclick=|onchange=", re.IGNORECASE)
    for js_file in sorted(js_dir.glob("*.js")):
        with js_file.open("r", encoding="utf-8", errors="replace") as f:
            for idx, line in enumerate(f, start=1):
                if needle.search(line):
                    snippet = " ".join(line.strip().split())
                    if len(snippet) > 160:
                        snippet = snippet[:157] + "..."
                    out.append((js_file.name, idx, snippet or "(blank)"))
    return out


def _md_row(cols: Iterable[str]) -> str:
    safe = [c.replace("|", "\\|").replace("\n", " ").strip() for c in cols]
    return "| " + " | ".join(safe) + " |"


def _render_markdown(
    controls: list[Control], outputs: list[OutputSurface], dynamic: list[tuple[str, int, str]]
) -> str:
    stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    by_tag = Counter(c.tag for c in controls)
    by_input_type = Counter(c.input_type for c in controls if c.tag == "input")

    lines: list[str] = []
    lines.append("# Manual Human Byte-Check Checklist")
    lines.append("")
    lines.append("This is a full manual verification sheet for the current UI build.")
    lines.append("Leave evidence-level notes for each row.")
    lines.append("")
    lines.append(f"- Generated: `{stamp}`")
    lines.append(f"- Source UI: `{HTML_PATH.as_posix()}`")
    lines.append("- Scope: Static controls in main UI + dynamic template candidates from `ui/js/*.js`")
    lines.append("")
    lines.append("## Session Header")
    lines.append("")
    lines.append("- Tester Name: ____________________")
    lines.append("- Date/Time: ______________________")
    lines.append("- Build/Commit: ___________________")
    lines.append("- Runtime (Bridge/UI/LLM): ________")
    lines.append("- Device + OS: ____________________")
    lines.append("- Auth State Used: ________________")
    lines.append("- Evidence Folder (screens/logs): _")
    lines.append("")
    lines.append("## Priority Critical Paths (Run First)")
    lines.append("")
    lines.append(
        _md_row(
            [
                "Done",
                "Area",
                "Manual Procedure",
                "Expected",
                "Actual",
                "Pass/Fail",
                "User Notes",
            ]
        )
    )
    lines.append(_md_row(["---"] * 7))
    lines.append(
        _md_row(
            [
                "[ ]",
                "System tray controls",
                "Launch app, verify tray icon appears, run Start/Restart/Stop/Quit from tray menu, verify process state each action.",
                "Tray menu actions map 1:1 to runtime state with no stale status.",
                "",
                "",
                "",
            ]
        )
    )
    lines.append(
        _md_row(
            [
                "[ ]",
                "Color/theme persistence",
                "Change multiple color controls + preset + font size, click Save Settings, close UI, relaunch, verify exact values reloaded.",
                "All color variables and display prefs persist exactly after restart.",
                "",
                "",
                "",
            ]
        )
    )
    lines.append(
        _md_row(
            [
                "[ ]",
                "Auth gate + session continuity",
                "Sign in with Windows Hello, execute protected actions, relaunch UI and verify session validity/expiry behavior.",
                "Protected routes enforce auth correctly and session behavior is deterministic.",
                "",
                "",
                "",
            ]
        )
    )
    lines.append(
        _md_row(
            [
                "[ ]",
                "Chat core path",
                "Send message, continue, clear view, upload artifact, chain/hub interaction, verify output + citations behavior.",
                "No blocked controls, no silent failures, outputs update in correct panels.",
                "",
                "",
                "",
            ]
        )
    )
    lines.append(
        _md_row(
            [
                "[ ]",
                "Nodes/network control path",
                "Add node, heartbeat, pair/unpair flow, file browser actions (browse/download/upload/mkdir).",
                "Node operations surface valid statuses and expected guardrails.",
                "",
                "",
                "",
            ]
        )
    )
    lines.append(
        _md_row(
            [
                "[ ]",
                "Installability smoke (x64 Win11)",
                "Fresh install on Windows 11 x64, first launch, tray start, service bind ports, clean uninstall.",
                "Install/launch/uninstall complete without manual repair.",
                "",
                "",
                "",
            ]
        )
    )
    lines.append("")
    lines.append("## Inventory Summary")
    lines.append("")
    lines.append(f"- Total controls found: **{len(controls)}**")
    lines.append(f"- Buttons: **{by_tag.get('button', 0)}**")
    lines.append(f"- Inputs: **{by_tag.get('input', 0)}**")
    lines.append(f"- Selects: **{by_tag.get('select', 0)}**")
    lines.append(f"- Textareas: **{by_tag.get('textarea', 0)}**")
    lines.append("- Input type breakdown:")
    for key, count in sorted(by_input_type.items(), key=lambda kv: (kv[0], kv[1])):
        lines.append(f"  - `{key}`: {count}")
    lines.append("")
    lines.append("## Strict Test Rules")
    lines.append("")
    lines.append("1. For each row: execute action, verify visible output, and verify persisted state where applicable.")
    lines.append("2. For settings and theme/color controls: close UI, relaunch UI, and verify persistence.")
    lines.append("3. For actions that hit the bridge: capture endpoint + status + payload summary in Notes.")
    lines.append("4. Mark failures with exact repro steps and expected vs actual byte-level difference.")
    lines.append("")
    lines.append("## Control Matrix (Every Button / Slider / Toggle / Input)")
    lines.append("")
    lines.append(
        _md_row(
            [
                "Done",
                "Line",
                "Context",
                "Tag",
                "Control Id/Name",
                "Type",
                "Hook(s)",
                "Label/Hint",
                "Help Id",
                "Expected Output",
                "Actual Output",
                "Pass/Fail",
                "User Notes",
            ]
        )
    )
    lines.append(_md_row(["---"] * 13))
    for c in controls:
        lines.append(
            _md_row(
                [
                    "[ ]",
                    str(c.line),
                    c.context,
                    c.tag,
                    c.ident,
                    c.input_type,
                    c.hooks,
                    c.label,
                    c.help_id,
                    "",
                    "",
                    "",
                    "",
                ]
            )
        )
    lines.append("")
    lines.append("## Output / Readback Surfaces")
    lines.append("")
    lines.append("Use this to verify that controls update the right output area and that content is coherent.")
    lines.append("")
    lines.append(
        _md_row(
            [
                "Done",
                "Line",
                "Context",
                "Tag",
                "Output Id",
                "Class/Hint",
                "Triggering Control(s)",
                "Observed Data",
                "Pass/Fail",
                "User Notes",
            ]
        )
    )
    lines.append(_md_row(["---"] * 10))
    for o in outputs:
        lines.append(
            _md_row(
                [
                    "[ ]",
                    str(o.line),
                    o.context,
                    o.tag,
                    o.ident,
                    o.hint,
                    "",
                    "",
                    "",
                    "",
                ]
            )
        )
    lines.append("")
    lines.append("## Dynamic Template Candidates (JS)")
    lines.append("")
    lines.append(
        "These lines indicate controls rendered dynamically via JS templates/string HTML. "
        "Manual coverage must include these runtime-created controls."
    )
    lines.append("")
    lines.append(_md_row(["Done", "File", "Line", "Snippet", "Verified Runtime?", "User Notes"]))
    lines.append(_md_row(["---"] * 6))
    for file_name, ln, snippet in dynamic:
        lines.append(_md_row(["[ ]", file_name, str(ln), snippet, "", ""]))
    lines.append("")
    lines.append("## Sign-off")
    lines.append("")
    lines.append("- Critical blockers found: __________________________________________")
    lines.append("- Non-blocking defects found: _______________________________________")
    lines.append("- Approved for release by: __________________________________________")
    lines.append("- Date: ______________________________________________________________")
    lines.append("")
    lines.append(
        "> Hard rule: Skip reduction was achieved by aligning expected non-destructive/auth-gated outcomes, "
        "not by relaxing denial/error policy."
    )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    if not HTML_PATH.exists():
        raise SystemExit(f"UI file not found: {HTML_PATH}")

    html_text = HTML_PATH.read_text(encoding="utf-8", errors="replace")
    controls, outputs = _extract_controls_and_outputs(html_text)
    dynamic = _extract_dynamic_candidates(JS_DIR)

    md = _render_markdown(controls=controls, outputs=outputs, dynamic=dynamic)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(md, encoding="utf-8")
    OUT_TXT_PATH.write_text(md, encoding="utf-8")

    print(f"Generated checklist: {OUT_PATH}")
    print(f"Generated checklist: {OUT_TXT_PATH}")
    print(f"Controls: {len(controls)}")
    print(f"Output surfaces: {len(outputs)}")
    print(f"Dynamic JS candidates: {len(dynamic)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
