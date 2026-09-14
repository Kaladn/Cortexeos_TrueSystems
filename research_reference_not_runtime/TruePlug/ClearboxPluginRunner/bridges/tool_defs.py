"""Forest AI — Tool Registry & Mediated Execution.

Architecture:  User → UI → Bridge → LLM Pass 1 → Tool Call → Bridge Executes → LLM Pass 2 → Response

Each tool is ONE dict in TOOL_REGISTRY. The system prompt, Ollama schemas,
and dispatch table all auto-generate from that single source of truth.

To add a tool:
  1. Write the async handler:  async def _my_tool(args, session_id) -> str
  2. Append a ToolDef dict to TOOL_REGISTRY
  3. Done. System prompt, schemas, dispatch — all auto-built.

Safety invariants:
  - AI caller can only write to WriteZone.ARTIFACTS (gateway-enforced)
  - No shell/OS commands — system visibility is read-only via observe module
  - Extension allowlist + 500KB size cap on artifacts
  - Max 1 tool call per round, 1 round (no recursion)
  - Path traversal blocked before gateway even sees the request
  - Missing telemetry fields → explicit null (model must not guess)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, TypedDict
from urllib.parse import urlparse

LOGGER = logging.getLogger("forest.tools")

from security.runtime_log import debug_enter, debug_exit, log_error as _rt_error  # DEBUGWIRE:TOOLCALL


# ── Tool Contract ─────────────────────────────────────────────

class ToolParam(TypedDict, total=False):
    """Single parameter definition for a tool."""
    type: str
    description: str
    enum: list[str]


class ToolDef(TypedDict, total=False):
    """Everything needed to define, describe, and execute a tool.

    One dict = one tool. The registry auto-generates:
      - System prompt listing
      - Ollama-format schema
      - Dispatch entry
    """
    name: str                                     # unique identifier
    description: str                              # shown to model
    hint: str                                     # when to call (for system prompt)
    safety: str                                   # "read" | "write"
    params: dict[str, ToolParam]                  # parameter schemas
    required: list[str]                           # required param names
    handler: Any                                  # async (args, session_id) -> str


# ── Artifact safety constants ─────────────────────────────────

_SAFE_EXT = frozenset({
    ".txt", ".md", ".json", ".csv", ".py", ".html",
    ".xml", ".yaml", ".yml", ".toml",
})
_MAX_ARTIFACT_SIZE = 512_000  # 500 KB


# ── Tool Handlers ─────────────────────────────────────────────
# Each handler: async (args: dict, session_id: str|None) -> str
# Returns deterministic JSON or plain text. Never omit fields — use null.

async def _write_artifact(args: dict, session_id: str | None) -> str:
    from security.gateway import gateway, WriteZone

    filename = args.get("filename", "").strip()
    content = args.get("content", "")

    if not filename or "/" in filename or "\\" in filename or ".." in filename:
        return "Rejected: filename must be a simple name with extension, no path separators."
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _SAFE_EXT:
        return f"Rejected: extension '{ext}' not in allowed list: {sorted(_SAFE_EXT)}"
    if len(content) > _MAX_ARTIFACT_SIZE:
        return f"Rejected: content exceeds {_MAX_ARTIFACT_SIZE // 1024}KB limit."

    result = gateway.write("ai", WriteZone.ARTIFACTS, filename, content)
    if result.success:
        return (
            f"Artifact saved: {filename} ({len(content)} bytes, "
            f"audit_id: {result.audit_id or 'n/a'})"
        )
    return f"Write failed: {result.error or 'unknown error'}"


def _read_cpu_name() -> str | None:
    """CPU model name from Windows registry (authoritative)."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            r"HARDWARE\DESCRIPTION\System\CentralProcessor\0",
        )
        name = winreg.QueryValueEx(key, "ProcessorNameString")[0].strip()
        winreg.CloseKey(key)
        return name or None
    except Exception:
        return None


def _read_gpu_name_fallback() -> str | None:
    """GPU name via Win32_VideoController (works for AMD + Intel iGPU)."""
    try:
        import subprocess
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_VideoController | "
             "Select-Object -ExpandProperty Name"],
            text=True, timeout=5, stderr=subprocess.DEVNULL,
        ).strip()
        lines = [l.strip() for l in out.splitlines() if l.strip()]
        return lines[0] if lines else None
    except Exception:
        return None


async def _get_system_metrics(args: dict, session_id: str | None) -> str:
    """Strict telemetry: every field present, null if unknown."""
    from observe.reader import _read_cpu, _read_ram, _read_gpu
    import psutil

    # Parallel sensor reads — each has its own timeout, gather avoids serial wait
    cpu_result, ram_result, gpu_result = await asyncio.gather(
        asyncio.to_thread(_read_cpu),
        asyncio.to_thread(_read_ram),
        asyncio.to_thread(_read_gpu),
        return_exceptions=True,
    )
    cpu = cpu_result if isinstance(cpu_result, dict) else {}
    ram = ram_result if isinstance(ram_result, dict) else {}
    gpu = gpu_result if isinstance(gpu_result, dict) else {}

    gpu_name = gpu.get("gpu.name") or await asyncio.to_thread(_read_gpu_name_fallback)

    return json.dumps({
        "cpu_name": await asyncio.to_thread(_read_cpu_name),
        "cpu_cores_physical": psutil.cpu_count(logical=False),
        "cpu_threads_logical": psutil.cpu_count(logical=True),
        "cpu_percent": cpu.get("cpu.percent"),
        "cpu_freq_mhz": cpu.get("cpu.freq_mhz"),
        "ram_total_gb": ram.get("ram.total_gb"),
        "ram_used_gb": ram.get("ram.used_gb"),
        "ram_available_gb": ram.get("ram.available_gb"),
        "ram_percent": ram.get("ram.percent"),
        "gpu_name": gpu_name,
        "gpu_util_percent": gpu.get("gpu.util_percent"),
        "gpu_temp_c": gpu.get("gpu.temp_c"),
        "gpu_mem_used_mb": gpu.get("gpu.mem_used_mb"),
        "gpu_mem_total_mb": gpu.get("gpu.mem_total_mb"),
        "gpu_power_w": gpu.get("gpu.power_w"),
        "source": "windows_observe_v1",
    }, indent=2)


async def _get_service_health(args: dict, session_id: str | None) -> str:
    import httpx

    services = {
        "bridge": "http://localhost:5050/api/stats",
        "llm_server": "http://localhost:11435/health",
        "reasoning": "http://localhost:5051/health",
        "ui": "http://localhost:8080",
    }
    results = {}
    async with httpx.AsyncClient(timeout=2.0) as client:
        for name, url in services.items():
            try:
                r = await client.get(url)
                results[name] = "up" if r.is_success else f"error ({r.status_code})"
            except Exception:
                results[name] = "down"
    results["source"] = "health_probe_v1"
    return json.dumps(results, indent=2)


async def _search_archive(args: dict, session_id: str | None) -> str:
    query = args.get("query", "")
    if not query:
        return "No query provided."
    try:
        from lakespeak.api.router import get_engine
        engine = get_engine()
        result = await asyncio.to_thread(
            engine.query, query=query, mode="grounded", topk=5,
            session_id=session_id,
        )
        citations = result.citations or []
        lines = []
        for i, c in enumerate(citations[:5]):
            snippet = c.get("snippet", c.get("text", ""))[:400]
            score = c.get("score", 0)
            lines.append(f"[{i+1}] (score: {score:.3f}) {snippet}")
        return "\n\n".join(lines) if lines else "No results found in archive."
    except Exception as e:
        return f"Archive search failed: {e}"


async def _analyze_text(args: dict, session_id: str | None) -> str:
    text = args.get("text", "")
    if not text:
        return "No text provided."
    try:
        from wolf_engine.api.router import get_engine as get_wolf_engine
        engine = get_wolf_engine()
        result = await asyncio.to_thread(
            engine.analyze, session_id=session_id or "tool_call", text=text,
        )
        return json.dumps({
            "verdict": result.get("verdict"),
            "patterns": result.get("patterns"),
            "session_id": result.get("session_id"),
            "source": "wolf_engine_v1",
        }, indent=2, default=str)
    except Exception as e:
        return f"Analysis failed: {e}"


# ── Custom Tool Runner Infrastructure ─────────────────────────
# Human-created tools use declarative JSON configs with a "runner" field.
# The runner factory creates async handlers from those configs.

_WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
_VENV_PYTHON_PATH = _WORKSPACE_ROOT / ".venv" / "Scripts" / "python.exe"
_VENV_PYTHON = str(_VENV_PYTHON_PATH) if _VENV_PYTHON_PATH.exists() else sys.executable

_VALID_RUNNER_TYPES = frozenset({"powershell", "python", "executable", "http"})
_MAX_RUNNER_TIMEOUT = 60


async def _run_subprocess(cmd: list[str], timeout: int = 15) -> str:
    """Run a subprocess and capture stdout+stderr. Never interactive."""
    try:
        proc = await asyncio.to_thread(
            subprocess.run, cmd,
            capture_output=True, text=True,
            timeout=timeout, stdin=subprocess.DEVNULL,
        )
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        if proc.returncode != 0 and err:
            return f"{out}\n[stderr] {err}".strip() if out else f"[stderr] {err}"
        return out or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Tool timed out after {timeout}s"
    except FileNotFoundError as e:
        return f"Command not found: {e}"
    except Exception as e:
        return f"Subprocess error: {e}"


_BLOCKED_HTTP_NETS = (
    "127.", "10.", "192.168.", "169.254.", "0.",
    "172.16.", "172.17.", "172.18.", "172.19.",
    "172.20.", "172.21.", "172.22.", "172.23.",
    "172.24.", "172.25.", "172.26.", "172.27.",
    "172.28.", "172.29.", "172.30.", "172.31.",
)


def _validate_http_url(url: str) -> str | None:
    """Validate a URL for the HTTP probe runner. Returns error or None."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return f"Blocked scheme: {parsed.scheme} (only http/https allowed)"
    host = (parsed.hostname or "").lower()
    if host in ("localhost", "::1", "") or host.startswith(_BLOCKED_HTTP_NETS):
        return f"Blocked host: {host} (private/loopback address)"
    return None


async def _run_http_probe(url: str, timeout: int = 5) -> str:
    """GET a URL and return the response body. Blocks private/loopback targets."""
    import httpx
    block_reason = _validate_http_url(url)
    if block_reason:
        return f"HTTP probe blocked: {block_reason}"
    try:
        async with httpx.AsyncClient(timeout=float(timeout)) as client:
            r = await client.get(url)
            return r.text[:50_000] if r.is_success else f"HTTP {r.status_code}: {r.text[:1000]}"
    except Exception as e:
        return f"HTTP probe failed: {e}"


def _sanitize_param(val: str, runner_type: str = "powershell") -> str:
    """Sanitize a parameter value for shell substitution.

    Platform-aware: PowerShell on Windows uses double-quote escaping,
    POSIX shells use shlex.quote (single-quote wrapping).
    """
    s = str(val)
    if runner_type == "powershell" and os.name == "nt":
        # PowerShell: double-quote wrapping, escape inner double-quotes + backticks
        s = s.replace('`', '``').replace('"', '`"').replace('$', '`$')
        return f'"{s}"'
    return shlex.quote(s)


def _make_runner_handler(runner_config: dict):
    """Create an async handler from a runner config dict."""
    async def _handler(args: dict, session_id: str | None) -> str:
        rtype = runner_config["type"]
        cmd_template = runner_config["command"]
        timeout = min(int(runner_config.get("timeout_sec", 15)), _MAX_RUNNER_TIMEOUT)

        # Substitute {param} placeholders (shell-escaped for subprocess types)
        cmd = cmd_template
        for key, val in args.items():
            safe_val = str(val) if rtype == "http" else _sanitize_param(val, rtype)
            cmd = cmd.replace(f"{{{key}}}", safe_val)

        if rtype == "powershell":
            return await _run_subprocess(
                ["powershell", "-NoProfile", "-NonInteractive",
                 "-ExecutionPolicy", "Bypass", "-Command", cmd],
                timeout=timeout)
        elif rtype == "python":
            parts = shlex.split(cmd)
            return await _run_subprocess(
                [_VENV_PYTHON] + parts, timeout=timeout)
        elif rtype == "executable":
            return await _run_subprocess(
                shlex.split(cmd), timeout=timeout)
        elif rtype == "http":
            return await _run_http_probe(cmd, timeout=timeout)
        else:
            return f"Unknown runner type: {rtype}"
    return _handler


def _validate_tool_json(data: dict) -> str | None:
    """Validate a custom tool JSON dict. Returns error string or None."""
    name = data.get("name", "")
    if not name or not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", name):
        return f"Invalid tool name: '{name}' (must be alphanumeric + underscore, start with letter)"
    if not data.get("description"):
        return "Missing 'description'"
    runner = data.get("runner")
    if not runner or not isinstance(runner, dict):
        return "Missing or invalid 'runner' config"
    rtype = runner.get("type", "")
    if rtype not in _VALID_RUNNER_TYPES:
        return f"Invalid runner type: '{rtype}' (must be one of {sorted(_VALID_RUNNER_TYPES)})"
    if not runner.get("command"):
        return "Missing 'runner.command'"
    return None


def load_custom_tools() -> list[ToolDef]:
    """Load user-created tools from config/tools/*.json."""
    from security.data_paths import TOOLS_DIR
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    tools: list[ToolDef] = []
    for path in sorted(TOOLS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            err = _validate_tool_json(data)
            if err:
                LOGGER.warning("Skipping %s: %s", path.name, err)
                continue
            handler = _make_runner_handler(data["runner"])
            tools.append({
                "name": data["name"],
                "description": data["description"],
                "hint": data.get("hint", ""),
                "safety": data.get("safety", "read"),
                "params": data.get("params", {}),
                "required": data.get("required", []),
                "handler": handler,
            })
            LOGGER.info("Loaded custom tool: %s", data["name"])
        except Exception as e:
            LOGGER.warning("Failed to load custom tool %s: %s", path.name, e)
    return tools


async def _run_diagnostic(args: dict, session_id: str | None) -> str:
    """Run the ForestAI diagnostic suite."""
    debug_enter("diagnostic", "run_diagnostic")  # DEBUGWIRE:TOOLCALL
    try:
        import io
        import json as _json

        # Build argv for the diagnostic runner
        probe_filter = args.get("probes", "")
        argv = ["--json", "--skip-llm", "--skip-ollama"]
        if probe_filter:
            argv.extend(["--probes", probe_filter])

        # Import and run in a thread to avoid blocking the event loop
        def _run():
            import sys
            from tools.diagnostic.runner import main as diag_main
            old_argv = sys.argv
            old_stdout = sys.stdout
            try:
                sys.argv = ["tools.diagnostic"] + argv
                buf = io.StringIO()
                sys.stdout = buf
                try:
                    diag_main()
                except SystemExit:
                    pass
                return buf.getvalue()
            finally:
                sys.argv = old_argv
                sys.stdout = old_stdout

        output = await asyncio.to_thread(_run)

        # Extract the JSON manifest from stdout (skip any non-JSON prefix like data_paths print)
        lines = output.strip().split("\n")
        json_start = None
        for i, line in enumerate(lines):
            if line.strip().startswith("{"):
                json_start = i
                break
        if json_start is not None:
            json_text = "\n".join(lines[json_start:])
            manifest = _json.loads(json_text)
            # Return compact summary for the LLM
            counts = manifest.get("counts", {})
            summary = (
                f"Diagnostic run {manifest.get('run_id', '?')}: "
                f"{counts.get('confirmed', 0)} confirmed, "
                f"{counts.get('denied', 0)} denied, "
                f"{counts.get('skipped', 0)} skipped, "
                f"{counts.get('error', 0)} error"
            )
            if manifest.get("denied_details"):
                summary += "\nDenied: " + ", ".join(
                    d.get("check_id", "?") for d in manifest["denied_details"]
                )
            debug_exit("diagnostic", "run_diagnostic", ok=True)  # DEBUGWIRE:TOOLCALL
            return summary
        else:
            debug_exit("diagnostic", "run_diagnostic", ok=False, detail="no JSON output")
            return f"Diagnostic completed but no JSON manifest found.\nOutput: {output[:500]}"
    except Exception as e:
        debug_exit("diagnostic", "run_diagnostic", ok=False, detail=str(e))
        return f"Diagnostic error: {e}"


# ══════════════════════════════════════════════════════════════
#  TOOL REGISTRY — single source of truth
#
#  To add a tool:
#    1. Write the handler above
#    2. Append a ToolDef dict here
#    3. Done.
# ══════════════════════════════════════════════════════════════

_BUILTIN_TOOLS: list[ToolDef] = [
    {
        "name": "get_system_metrics",
        "description": "Get real-time system metrics: CPU name/usage, RAM, GPU name/usage/temp/VRAM. Read-only.",
        "hint": "When asked about CPU, RAM, GPU, system status, or hardware.",
        "safety": "read",
        "params": {},
        "required": [],
        "handler": _get_system_metrics,
    },
    {
        "name": "get_service_health",
        "description": "Check health of all Clearbox AI Studio services (bridge, LLM server, reasoning engine, UI). Returns up/down status. Read-only.",
        "hint": "When asked if services are running or about service health.",
        "safety": "read",
        "params": {},
        "required": [],
        "handler": _get_service_health,
    },
    {
        "name": "search_archive",
        "description": "Search the Clearbox AI Studio knowledge archive (LakeSpeak) for grounded evidence. Returns scored citations from ingested documents.",
        "hint": "When asked to search, find, or look up information in the archive.",
        "safety": "read",
        "params": {
            "query": {"type": "string", "description": "Search query for the archive"},
        },
        "required": ["query"],
        "handler": _search_archive,
    },
    {
        "name": "analyze_text",
        "description": "Run Wolf Engine analysis on text. Returns verdict, patterns, and symbolic analysis.",
        "hint": "When asked to analyze text, detect patterns, or reason about content structure.",
        "safety": "read",
        "params": {
            "text": {"type": "string", "description": "Text to analyze"},
        },
        "required": ["text"],
        "handler": _analyze_text,
    },
    {
        "name": "write_artifact",
        "description": "Save a file to the artifact folder. All writes audited and encrypted. Create only — no edit, delete, move, or rename.",
        "hint": "ONLY when the user explicitly asks to create, save, or write a file.",
        "safety": "write",
        "params": {
            "filename": {
                "type": "string",
                "description": "Filename with extension (e.g. 'analysis.md'). No path separators.",
            },
            "content": {
                "type": "string",
                "description": "The full content to write to the file.",
            },
            "artifact_type": {
                "type": "string",
                "description": "Category of artifact.",
                "enum": ["notes", "report", "data", "config", "code"],
            },
        },
        "required": ["filename", "content"],
        "handler": _write_artifact,
    },
    {
        "name": "run_diagnostic",
        "description": "Run Clearbox AI Studio diagnostic suite. Checks environment, service health, sensors, logs, and API endpoints. Returns summary of confirmed/denied/error checks.",
        "hint": "When asked to run diagnostics, health check, or system self-test.",
        "safety": "read",
        "params": {
            "probes": {
                "type": "string",
                "description": "Comma-separated probe IDs to run (empty = all). Available: environment, service_liveness, observe_sensors, log_integrity, api_smoke, temporal_audit",
            },
        },
        "required": [],
        "handler": _run_diagnostic,
    },
]

_BUILTIN_NAMES = frozenset(t["name"] for t in _BUILTIN_TOOLS)

# Merge built-in + custom tools
TOOL_REGISTRY: list[ToolDef] = list(_BUILTIN_TOOLS) + load_custom_tools()


# ── Auto-generated from registry ──────────────────────────────

def _build_dispatch() -> dict[str, Any]:
    """Build name → handler map from the registry."""
    return {t["name"]: t["handler"] for t in TOOL_REGISTRY}


def _build_system_prompt_from(registry: list) -> str:
    """Build the tool system prompt from a given registry list."""
    lines = [
        "You are Clearbox AI Studio, a local assistant with tool access.",
        "",
        "Available tools:",
    ]
    for i, t in enumerate(registry, 1):
        params_str = ""
        if t.get("params"):
            params_str = "(" + ", ".join(
                f'{k}="..."' for k in t["params"]
            ) + ")"
        else:
            params_str = "()"
        safety_tag = " [WRITE]" if t.get("safety") == "write" else ""
        lines.append(f"  {i}. {t['name']}{params_str} — {t['description']}{safety_tag}")
        if t.get("hint"):
            lines.append(f"     Use: {t['hint']}")

    lines.extend([
        "",
        "FORMAT — output EXACTLY on its own line:",
        '<tool_call>{"name": "tool_name", "arguments": {"key": "value"}}</tool_call>',
        "",
        "RULES:",
        "- Call ONE tool at a time. Do NOT combine multiple tool calls.",
        "- After calling a tool, STOP. Write nothing else. The system provides the result.",
        "- When you receive a tool result, summarize it for the user. Do NOT call another tool.",
        "- NEVER invent or assume data. If a field is null or missing, say \"unknown\".",
        "- ONLY call [WRITE] tools when the user explicitly asks to create or save a file.",
    ])
    return "\n".join(lines)


def _build_system_prompt() -> str:
    """Build the tool system prompt from the global registry."""
    return _build_system_prompt_from(TOOL_REGISTRY)


def _build_ollama_schemas_from(registry: list) -> list[dict[str, Any]]:
    """Build Ollama-format tool definitions from a given registry list."""
    schemas = []
    for t in registry:
        props = {}
        for pname, pdef in (t.get("params") or {}).items():
            prop: dict[str, Any] = {"type": pdef.get("type", "string")}
            if "description" in pdef:
                prop["description"] = pdef["description"]
            if "enum" in pdef:
                prop["enum"] = pdef["enum"]
            props[pname] = prop

        schemas.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": {
                    "type": "object",
                    "properties": props,
                    **({"required": t["required"]} if t.get("required") else {}),
                },
            },
        })
    return schemas


def _build_ollama_schemas() -> list[dict[str, Any]]:
    """Build Ollama-format tool definitions from the global registry."""
    return _build_ollama_schemas_from(TOOL_REGISTRY)


def _rebuild_public_api() -> None:
    """Rebuild all public API objects from current TOOL_REGISTRY."""
    global _DISPATCH, TOOL_SYSTEM_PROMPT, TOOL_DEFINITIONS
    _DISPATCH = _build_dispatch()
    TOOL_SYSTEM_PROMPT = _build_system_prompt()
    TOOL_DEFINITIONS = _build_ollama_schemas()


# Public API — consumed by forest_bridge_server.py
_DISPATCH: dict[str, Any] = {}
TOOL_SYSTEM_PROMPT: str = ""
TOOL_DEFINITIONS: list[dict[str, Any]] = []
_rebuild_public_api()


def reload_custom_tools() -> int:
    """Hot-reload: re-scan custom tools from disk, rebuild everything.

    Atomic swap: build all structures into locals, then assign globals in one
    batch so concurrent readers never see a half-rebuilt state.

    Returns count of custom tools loaded.
    """
    global TOOL_REGISTRY, _DISPATCH, TOOL_SYSTEM_PROMPT, TOOL_DEFINITIONS
    custom = load_custom_tools()
    new_registry = list(_BUILTIN_TOOLS) + custom
    # Build everything from the new registry before touching any globals
    new_dispatch = {t["name"]: t["handler"] for t in new_registry}
    new_prompt = _build_system_prompt_from(new_registry)
    new_schemas = _build_ollama_schemas_from(new_registry)
    # Atomic swap — all four globals updated together
    TOOL_REGISTRY = new_registry
    _DISPATCH = new_dispatch
    TOOL_SYSTEM_PROMPT = new_prompt
    TOOL_DEFINITIONS = new_schemas
    LOGGER.info("Reloaded tools: %d built-in + %d custom", len(_BUILTIN_TOOLS), len(custom))
    return len(custom)


# ── Execution ─────────────────────────────────────────────────

async def execute_tool(
    name: str, arguments: dict, session_id: str | None = None,
    model_name: str | None = None,
) -> str:
    """Execute a tool call and return the result as a string for the LLM."""
    import time as _t  # DEBUGWIRE:TOOLCALL
    _t0 = _t.perf_counter()  # DEBUGWIRE:TOOLCALL
    debug_enter("toolcall", f"execute/{name}", extra={"args_keys": list(arguments.keys()), "model": model_name or "unknown"})  # DEBUGWIRE:TOOLCALL

    # Per-model tool policy gate
    if model_name:
        try:
            from security.tool_profiles import get_allowed_tools
            allowed = get_allowed_tools(model_name)
            if allowed is not None and name not in allowed:
                LOGGER.info("Tool '%s' denied by policy for model '%s'", name, model_name)
                _ms = (_t.perf_counter() - _t0) * 1000
                debug_exit("toolcall", f"execute/{name}", ok=False, detail="denied_by_policy", ms=_ms)
                try:
                    from security.tool_telemetry import record_tool_call
                    record_tool_call(model_name, name, "denied", int(_ms))
                except Exception:
                    pass
                return f"Tool '{name}' is not allowed for model '{model_name}'"
        except ImportError:
            pass

    handler = _DISPATCH.get(name)
    if not handler:
        LOGGER.warning("Tool call rejected — '%s' not in dispatch table", name)
        debug_exit("toolcall", f"execute/{name}", ok=False, detail="unknown_tool", ms=(_t.perf_counter() - _t0) * 1000)  # DEBUGWIRE:TOOLCALL
        return f"Unknown tool: {name}"
    try:
        result = await handler(arguments, session_id)
        _ms = (_t.perf_counter() - _t0) * 1000
        LOGGER.info("Tool %s executed (%d chars)", name, len(result))
        debug_exit("toolcall", f"execute/{name}", ok=True, ms=_ms)  # DEBUGWIRE:TOOLCALL
        # Record telemetry: success
        try:
            from security.tool_telemetry import record_tool_call
            record_tool_call(model_name or "unknown", name, "success", int(_ms))
        except Exception:
            pass
        return result
    except Exception as e:
        _ms = (_t.perf_counter() - _t0) * 1000
        LOGGER.exception("Tool execution failed: %s", name)
        _rt_error("toolcall", f"execute/{name}", str(e), level=3)  # DEBUGWIRE:TOOLCALL
        debug_exit("toolcall", f"execute/{name}", ok=False, detail=str(e), ms=_ms)  # DEBUGWIRE:TOOLCALL
        # Record telemetry: fail
        try:
            from security.tool_telemetry import record_tool_call
            record_tool_call(model_name or "unknown", name, "fail", int(_ms))
        except Exception:
            pass
        return f"Tool error ({name}): {e}"


# ── Parsing ───────────────────────────────────────────────────
# Canonical format:  <tool_call>{"name":"...","arguments":{...}}</tool_call>
# Known drifts from local models:
#   - Gemma fenced: ```tool_call={"name":"...","arguments":{...}}```
#   - Qwen/gpt_oss:  ```tool_call>{"name":"...","arguments":{...}}```
#   - Gemma bare:   tool_call={"name":"...","arguments":{...}}
#   - Backtick-wrapped: ```{"name":"...","arguments":{...}}```

_TOOL_CALL_RE = re.compile(
    r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL
)
_TOOL_CALL_FENCE_RE = re.compile(
    r"```\s*tool_call\s*[=>:]\s*(\{.*?\})\s*```", re.DOTALL
)
_TOOL_CALL_BACKTICK_RE = re.compile(
    r"```\s*(\{[^`]*?\"name\"\s*:\s*\"[^\"]+\"[^`]*?\})\s*```", re.DOTALL
)
# Path 4: bare  tool_call={...}  (no backtick fence — gemma3 common drift)
_TOOL_CALL_BARE_RE = re.compile(
    r"tool_call\s*[=>:]\s*(\{.*?\})\s*$", re.MULTILINE
)

# All patterns for stripping (display cleanup)
_ALL_TOOL_PATTERNS = [_TOOL_CALL_RE, _TOOL_CALL_FENCE_RE, _TOOL_CALL_BACKTICK_RE, _TOOL_CALL_BARE_RE]


def _try_extract_call(json_str: str, source: str) -> dict | None:
    """Try to parse a JSON string as a tool call. Returns dict or None."""
    try:
        obj = json.loads(json_str)
        name = obj.get("name", "")
        args = obj.get("arguments", {})
        if name and name in _DISPATCH:
            if source != "canonical":
                LOGGER.info("Tool call parsed via %s fallback: %s", source, name)
            return {"name": name, "arguments": args}
    except (json.JSONDecodeError, AttributeError):
        pass
    return None


def parse_tool_calls(text: str) -> list[dict]:
    """Parse tool calls from model output, tolerating known format drifts.

    Priority order:
      1. <tool_call>{...}</tool_call>  (canonical)
      2. ```tool_call={...}```         (Gemma markdown style)
      3. ```{...with "name":...}```    (backtick-wrapped JSON)
      4. tool_call={...}              (bare assignment — gemma3 common drift)

    Returns list of {"name": str, "arguments": dict} or empty list.
    Max 1 per round — no chaining.
    """
    # Path 1: canonical <tool_call> tags
    for m in _TOOL_CALL_RE.finditer(text):
        call = _try_extract_call(m.group(1), "canonical")
        if call:
            return [call]

    # Path 2: ```tool_call={...}``` (Gemma drift)
    for m in _TOOL_CALL_FENCE_RE.finditer(text):
        call = _try_extract_call(m.group(1), "fence_eq")
        if call:
            return [call]

    # Path 3: ```{..."name":"tool_name"...}``` (generic backtick JSON)
    for m in _TOOL_CALL_BACKTICK_RE.finditer(text):
        call = _try_extract_call(m.group(1), "backtick_json")
        if call:
            return [call]

    # Path 4: bare  tool_call={...}  (no fence — gemma3 common drift)
    for m in _TOOL_CALL_BARE_RE.finditer(text):
        call = _try_extract_call(m.group(1), "bare_eq")
        if call:
            return [call]

    return []


def strip_tool_calls(text: str) -> str:
    """Remove all tool call blocks (canonical + known drifts) from text."""
    cleaned = text
    for pattern in _ALL_TOOL_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


# ── Introspection (for API / debugging) ───────────────────────

def tool_directory() -> list[dict]:
    """Return a clean summary of all registered tools (no handlers)."""
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "hint": t.get("hint", ""),
            "safety": t.get("safety", "read"),
            "params": list((t.get("params") or {}).keys()),
            "required": t.get("required", []),
            "is_builtin": t["name"] in _BUILTIN_NAMES,
        }
        for t in TOOL_REGISTRY
    ]


def get_custom_tool_json(name: str) -> dict | None:
    """Read the raw JSON definition for a custom tool from disk."""
    from security.data_paths import TOOLS_DIR
    path = TOOLS_DIR / f"{name}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_custom_tool(data: dict) -> str | None:
    """Save a custom tool JSON to disk. Returns error string or None."""
    err = _validate_tool_json(data)
    if err:
        return err
    name = data["name"]
    if name in _BUILTIN_NAMES:
        return f"Cannot overwrite built-in tool: {name}"
    from security.data_paths import TOOLS_DIR
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    path = TOOLS_DIR / f"{name}.json"
    # Save only the definition (no handler)
    save_data = {
        "name": data["name"],
        "description": data["description"],
        "hint": data.get("hint", ""),
        "safety": data.get("safety", "read"),
        "runner": data["runner"],
        "params": data.get("params", {}),
        "required": data.get("required", []),
    }
    path.write_text(json.dumps(save_data, indent=2, ensure_ascii=False), encoding="utf-8")
    reload_custom_tools()
    return None


def delete_custom_tool(name: str) -> str | None:
    """Delete a custom tool from disk. Returns error string or None."""
    if name in _BUILTIN_NAMES:
        return f"Cannot delete built-in tool: {name}"
    from security.data_paths import TOOLS_DIR
    path = TOOLS_DIR / f"{name}.json"
    if not path.exists():
        return f"Tool not found: {name}"
    path.unlink()
    reload_custom_tools()
    return None
