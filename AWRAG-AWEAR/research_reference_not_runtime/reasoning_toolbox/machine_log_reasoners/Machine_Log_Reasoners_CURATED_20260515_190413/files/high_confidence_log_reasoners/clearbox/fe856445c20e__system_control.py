"""System health probing and process control services."""
from __future__ import annotations

import asyncio
import os
import subprocess as _sp
import textwrap
from pathlib import Path
from typing import Any

import httpx

from bridges.helpers import _safe_error
from bridges.state import LOGGER
from security.data_paths import STATE_DIR


class SystemControlService:
    """Owns service health probes and host control operations."""

    def __init__(
        self,
        *,
        state: Any,
        background_tasks: set,
        task_done_cb: Any,
        base_dir: Path,
    ) -> None:
        self.state = state
        self.background_tasks = background_tasks
        self.task_done_cb = task_done_cb
        self.base_dir = base_dir
        self._sentinel_dir = STATE_DIR
        self._sentinel_dir.mkdir(parents=True, exist_ok=True)
        self._stop_sentinel = self._sentinel_dir / "clearbox_stop"

    async def _probe(self, url: str) -> bool:
        try:
            verify: bool | str = False
            try:
                from security.tls import CERT_PATH as _PROBE_CERT
                if url.startswith("https") and _PROBE_CERT.exists():
                    verify = str(_PROBE_CERT)
            except ImportError:
                pass
            async with httpx.AsyncClient(timeout=2.0, verify=verify) as client:
                r = await client.get(url)
                return r.status_code < 500
        except Exception:
            return False

    async def services_health(self) -> dict[str, bool]:
        _tls = self.state.config.get("server", {}).get("tls", False)
        _proto = "https" if _tls else "http"
        llm_ok, ui_ok = await asyncio.gather(
            self._probe("http://127.0.0.1:11434/api/tags"),
            self._probe(f"{_proto}://127.0.0.1:8080/"),
        )
        return {
            "bridge": True,
            "llm": llm_ok,
            "reasoning": self.state.reasoning_service.is_available(),
            "ui": ui_ok,
        }

    def _ps(self, cmd: str, timeout_s: int = 12) -> tuple[int, str]:
        cmd = textwrap.dedent(cmd).strip()
        try:
            p = _sp.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", cmd],
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            return p.returncode, (p.stdout or "") + (p.stderr or "")
        except _sp.TimeoutExpired:
            return 1, "PowerShell timed out"
        except Exception as e:
            return 1, _safe_error(e)

    def kill_all_clearbox_processes(self) -> list[dict[str, int | str]]:
        my_pid = os.getpid()
        killed: list[dict[str, int | str]] = []
        _, out = self._ps(
            f"""
            $ports = @(5050, 11435, 8080)
            $pids = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
                Where-Object {{ $ports -contains $_.LocalPort }} |
                Select-Object -ExpandProperty OwningProcess -Unique
            foreach ($pid in $pids) {{
                if ($pid -eq {my_pid}) {{ continue }}
                try {{
                    Stop-Process -Id $pid -Force -ErrorAction Stop
                    Write-Output "$pid"
                }} catch {{}}
            }}
            """
        )
        for line in out.strip().splitlines():
            line = line.strip()
            if line.isdigit():
                killed.append({"name": "port_listener", "pid": int(line)})
                LOGGER.info("Killed pid %s (port listener)", line)

        self._ps(
            """
            Get-Process powershell -ErrorAction SilentlyContinue |
                Where-Object {
                    $_.MainWindowTitle -like '*Bridge Server*' -or
                    $_.MainWindowTitle -like '*LLM Server*' -or
                    $_.MainWindowTitle -like '*UI Server*'
                } | Stop-Process -Force -ErrorAction SilentlyContinue
            """
        )
        self._ps(f"Remove-Item '{self.base_dir}\\temp_*.ps1' -Force -ErrorAction SilentlyContinue")
        return killed

    async def system_shutdown(self) -> dict[str, Any]:
        LOGGER.warning("System shutdown requested via UI")
        try:
            self._stop_sentinel.write_text("stop", encoding="utf-8")
            LOGGER.info("Shutdown sentinel created: %s", self._stop_sentinel)
        except Exception as e:
            LOGGER.warning("Failed to create sentinel: %s", e)

        killed = self.kill_all_clearbox_processes()

        async def _self_terminate() -> None:
            await asyncio.sleep(0.5)
            LOGGER.warning("Bridge server shutting down")
            os._exit(0)

        task = asyncio.get_running_loop().create_task(_self_terminate())
        self.background_tasks.add(task)
        task.add_done_callback(self.task_done_cb)
        return {"status": "shutting_down", "killed": killed}

    async def system_restart(self) -> dict[str, str]:
        LOGGER.warning("System restart requested via UI")
        if self._stop_sentinel.exists():
            self._stop_sentinel.unlink()

        self.kill_all_clearbox_processes()

        async def _self_terminate() -> None:
            await asyncio.sleep(0.5)
            LOGGER.warning("Bridge server restarting via loop")
            os._exit(0)

        task = asyncio.get_running_loop().create_task(_self_terminate())
        self.background_tasks.add(task)
        task.add_done_callback(self.task_done_cb)
        return {"status": "restarting"}

    async def system_lock(self) -> dict[str, str]:
        LOGGER.info("System lock requested via UI")
        try:
            _sp.Popen(
                ["rundll32.exe", "user32.dll,LockWorkStation"],
                creationflags=_sp.CREATE_NO_WINDOW,
            )
            return {"status": "locked"}
        except Exception as e:
            LOGGER.warning("Failed to lock workstation: %s", e)
            return {"status": "lock_failed", "error": _safe_error(e)}
