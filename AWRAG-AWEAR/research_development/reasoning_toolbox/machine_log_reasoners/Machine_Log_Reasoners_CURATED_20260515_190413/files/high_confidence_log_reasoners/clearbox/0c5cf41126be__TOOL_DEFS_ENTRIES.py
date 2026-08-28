"""
SENSORYSTACK TOOL DEFINITIONS
==============================
Drop these ToolDef entries into ClearboxPluginRunner/bridges/tool_defs.py
TOOL_REGISTRY dict. Claude A: surgical insert only — find the existing
TOOL_REGISTRY and append these entries.

Four plugins, 8 tools total.
"""

# ── visual_io ─────────────────────────────────────────────────

VISUAL_IO_TOOLS = [
    {
        "name": "visual_io_start",
        "description": "Start the visual I/O capture session. Begins capturing screen frames and building ScreenVectorState.",
        "hint": "Use when user wants to start visual monitoring or screen analysis.",
        "safety": "write",
        "params": {
            "label":          {"type": "string", "description": "Session label"},
            "fps":            {"type": "number", "description": "Frames per second (default 2.0)"},
        },
        "required": [],
        "handler": "visual_io_start_handler",
    },
    {
        "name": "visual_io_latest",
        "description": "Get the most recent ScreenVectorState — entropy, symmetry, directional vectors, anomaly flags.",
        "hint": "Use when user asks what is on screen or wants current visual analysis.",
        "safety": "read",
        "params": {},
        "required": [],
        "handler": "visual_io_latest_handler",
    },
]

# ── audio_io ──────────────────────────────────────────────────

AUDIO_IO_TOOLS = [
    {
        "name": "audio_io_start",
        "description": "Start the audio I/O capture session. Begins capturing mic audio with MFCC fingerprinting and ILD direction analysis.",
        "hint": "Use when user wants to start audio monitoring.",
        "safety": "write",
        "params": {
            "label":        {"type": "string", "description": "Session label"},
            "device_index": {"type": "integer", "description": "Audio device index (default = system default)"},
        },
        "required": [],
        "handler": "audio_io_start_handler",
    },
    {
        "name": "audio_io_latest",
        "description": "Get the most recent audio event — sound type, direction, RMS, MFCC fingerprint.",
        "hint": "Use when user asks what sound was just heard or wants audio analysis.",
        "safety": "read",
        "params": {},
        "required": [],
        "handler": "audio_io_latest_handler",
    },
]

# ── av_security ───────────────────────────────────────────────

AV_SECURITY_TOOLS = [
    {
        "name": "av_correlate",
        "description": "Run audio-visual correlation analysis on completed visual_io and audio_io sessions. Detects phantom audio, silent visuals, delayed correlation (>70ms), and directional mismatch.",
        "hint": "Use after capturing both audio and video sessions to find AV anomalies.",
        "safety": "read",
        "params": {
            "visual_session_dir": {"type": "string", "description": "Path to visual_io session directory"},
            "audio_session_dir":  {"type": "string", "description": "Path to audio_io session directory"},
        },
        "required": ["visual_session_dir", "audio_session_dir"],
        "handler": "av_correlate_handler",
    },
    {
        "name": "av_findings",
        "description": "Get cached AV security findings from the last correlation run. Returns anomaly list with types and confidence scores.",
        "hint": "Use when user asks about AV anomalies or security findings.",
        "safety": "read",
        "params": {
            "limit": {"type": "integer", "description": "Max findings to return (default 100)"},
        },
        "required": [],
        "handler": "av_findings_handler",
    },
]

# ── netlog ────────────────────────────────────────────────────

NETLOG_TOOLS = [
    {
        "name": "netlog_start",
        "description": "Start the network traffic logger. Captures all active TCP/UDP connections with process ownership.",
        "hint": "Use when user wants to monitor network traffic or log connections.",
        "safety": "write",
        "params": {
            "label": {"type": "string", "description": "Session label"},
        },
        "required": [],
        "handler": "netlog_start_handler",
    },
    {
        "name": "netlog_query",
        "description": "Query the live network connection ring buffer. Filter by process name, remote address, or alert type (SUSPICIOUS_PORT, NEW_PROCESS_CONNECTION, HIGH_CONNECTION_COUNT).",
        "hint": "Use when user asks what processes are using the network or wants to find suspicious connections.",
        "safety": "read",
        "params": {
            "proc":           {"type": "string", "description": "Filter by process name substring"},
            "raddr_contains": {"type": "string", "description": "Filter by remote address substring"},
            "alert_type":     {"type": "string", "description": "Filter by alert type"},
            "limit":          {"type": "integer", "description": "Max results (default 100)"},
        },
        "required": [],
        "handler": "netlog_query_handler",
    },
]

# ── Handler stubs (implement in tool_defs.py using httpx to bridge) ───────────
#
# Pattern: all handlers call the bridge's own plugin endpoints via HTTP
# since the plugin is already mounted on the same bridge process.
# Use httpx.AsyncClient pointing to http://127.0.0.1:5050/api/<plugin>/...
#
# Example:
#   async def visual_io_latest_handler(args: dict, session_id: str | None) -> str:
#       async with httpx.AsyncClient() as client:
#           r = await client.get("http://127.0.0.1:5050/api/visual_io/frame/latest")
#           return r.text
