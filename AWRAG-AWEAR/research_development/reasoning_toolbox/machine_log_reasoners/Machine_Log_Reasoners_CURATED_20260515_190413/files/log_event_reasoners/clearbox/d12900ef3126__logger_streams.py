"""Logger stream inspection/toggle service."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException


class LoggerStreamService:
    """Owns logger stream metadata, tail reads, and toggle behavior."""

    def __init__(
        self,
        *,
        runtime_log_path: Path | None,
        tool_telemetry_path: Path | None,
        diagnostic_dir: Path | None,
    ) -> None:
        self._streams = [
            {
                "name": "runtime_log",
                "path": str(runtime_log_path) if runtime_log_path else "",
                "toggleable": False,
                "description": "Runtime errors and events (always on)",
            },
            {
                "name": "debugwire",
                "path": str(runtime_log_path) if runtime_log_path else "",
                "toggleable": True,
                "description": "DEBUGWIRE entry/exit tracing",
            },
            {
                "name": "tool_telemetry",
                "path": str(tool_telemetry_path) if tool_telemetry_path else "",
                "toggleable": True,
                "description": "Tool execution telemetry (per-model)",
            },
            {
                "name": "p5_diagnostic",
                "path": str(diagnostic_dir) if diagnostic_dir else "",
                "toggleable": False,
                "description": "P5 diagnostic suite output (on demand)",
            },
            {
                "name": "gateway_denials",
                "path": str(runtime_log_path) if runtime_log_path else "",
                "toggleable": False,
                "description": "Gateway write denials (always on)",
            },
        ]

    def _get_stream(self, name: str) -> dict[str, Any]:
        stream = next((s for s in self._streams if s["name"] == name), None)
        if not stream:
            raise HTTPException(404, "Logger stream not found")
        return stream

    def list_streams(self) -> dict[str, Any]:
        from security.runtime_log import debugwire_status

        debugwire = debugwire_status()
        streams: list[dict[str, Any]] = []
        for stream in self._streams:
            active = True
            if stream["name"] == "debugwire":
                active = debugwire.get("enabled", False)
            elif stream["name"] == "tool_telemetry":
                path = Path(stream["path"]) if stream["path"] else None
                active = bool(path and path.exists())
            elif stream["name"] == "p5_diagnostic":
                active = False

            last_event = None
            try:
                path = Path(stream["path"]) if stream["path"] else None
                if path and path.is_file():
                    lines = path.read_text(encoding="utf-8").splitlines()
                    for line in reversed(lines[-20:]):
                        try:
                            obj = json.loads(line.strip())
                            ts = obj.get("ts_utc") or obj.get("timestamp")
                            if ts:
                                last_event = ts
                                break
                        except (json.JSONDecodeError, AttributeError):
                            continue
            except Exception:
                pass

            streams.append(
                {
                    "name": stream["name"],
                    "path": stream["path"],
                    "toggleable": stream["toggleable"],
                    "active": active,
                    "last_event": last_event,
                    "description": stream["description"],
                }
            )
        return {"streams": streams}

    def tail(self, name: str, lines: int = 200) -> dict[str, Any]:
        stream = self._get_stream(name)
        path = Path(stream["path"]) if stream["path"] else None
        if not path or not path.is_file():
            return {"lines": [], "stream": name}

        try:
            all_lines = path.read_text(encoding="utf-8").splitlines()
            tail = all_lines[-min(lines, len(all_lines)) :]
            parsed = []
            for line in tail:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed.append(json.loads(line))
                except json.JSONDecodeError:
                    parsed.append(line)
            return {"lines": parsed, "stream": name, "total": len(all_lines)}
        except Exception as exc:
            raise HTTPException(500, f"Failed to read log: {exc}")

    def toggle(self, name: str, enabled: bool = True) -> dict[str, Any]:
        stream = self._get_stream(name)
        if not stream["toggleable"]:
            raise HTTPException(403, f"Stream '{name}' cannot be toggled")

        if name == "debugwire":
            from security.runtime_log import debugwire_set, debugwire_status

            debugwire_set(enabled)
            return debugwire_status()
        return {"name": name, "enabled": enabled}

