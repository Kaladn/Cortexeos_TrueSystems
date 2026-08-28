"""ps_runner.py — Headless PowerShell executor for WinUtil operations.

All functions return a dict: {ok, stdout, stderr, returncode, admin_required}.
Admin elevation is detected but NOT auto-elevated — callers get a clear message.
"""
from __future__ import annotations

import ctypes
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

# Path to the winutil-main source directory (nested)
_BASE_DIR = Path(__file__).resolve().parent.parent.parent
WINUTIL_DIR = _BASE_DIR / "winutil-main" / "winutil-main"
_PRIVATE_DIR = WINUTIL_DIR / "functions" / "private"

# Preamble that dot-sources core winutil private helpers for tweak/fix scripts
_WINUTIL_PREAMBLE = r"""
$ErrorActionPreference = "Continue"
$VerbosePreference = "SilentlyContinue"

# Dot-source the private helpers that tweak/fix scripts depend on
$_privateFunctions = @(
    "Set-WinUtilRegistry.ps1",
    "Set-WinUtilService.ps1",
    "Set-WinUtilScheduledTask.ps1",
    "Invoke-WinUtilExplorerUpdate.ps1",
    "Invoke-WinUtilScript.ps1",
    "Remove-WinUtilAPPX.ps1",
    "Test-WinUtilInternetConnection.ps1"
)
foreach ($fn in $_privateFunctions) {
    $fp = Join-Path "{PRIVATE_DIR}" $fn
    if (Test-Path $fp) {{ . $fp }}
}
""".strip()


def is_admin() -> bool:
    """Return True if the current process has admin privileges."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _run(script: str, timeout: int = 120) -> dict[str, Any]:
    """Execute a PowerShell script string headlessly. Returns result dict."""
    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-WindowStyle", "Hidden",
                "-ExecutionPolicy", "Bypass",
                "-Command", script,
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
            "admin_required": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"PowerShell timed out after {timeout}s",
            "returncode": -1,
            "admin_required": False,
        }
    except FileNotFoundError:
        return {
            "ok": False,
            "stdout": "",
            "stderr": "powershell.exe not found",
            "returncode": -1,
            "admin_required": False,
        }


def _admin_check(op: str) -> dict[str, Any] | None:
    """Return an error dict if admin is needed but missing, else None."""
    if not is_admin():
        return {
            "ok": False,
            "stdout": "",
            "stderr": f"{op} requires administrator privileges. Restart the Clearbox AI Studio server as administrator.",
            "returncode": -1,
            "admin_required": True,
        }
    return None


def run_ps(script: str, *, require_admin: bool = False, timeout: int = 120) -> dict[str, Any]:
    """Public entrypoint: run arbitrary PS with optional admin check."""
    if require_admin:
        err = _admin_check("This operation")
        if err:
            return err
    return _run(script, timeout=timeout)


# ── App management ─────────────────────────────────────────────────────────

def winget_install(winget_id: str, *, silent: bool = True) -> dict[str, Any]:
    """Install an application via winget."""
    flags = "--silent --accept-source-agreements --accept-package-agreements"
    if not silent:
        flags = "--accept-source-agreements --accept-package-agreements"
    script = f'winget install --id "{winget_id}" {flags}; exit $LASTEXITCODE'
    return _run(script, timeout=300)


def winget_uninstall(winget_id: str) -> dict[str, Any]:
    """Uninstall an application via winget."""
    script = f'winget uninstall --id "{winget_id}" --silent; exit $LASTEXITCODE'
    return _run(script, timeout=180)


def winget_list_installed() -> dict[str, Any]:
    """Return installed packages as parsed JSON list."""
    script = "winget list --output json 2>$null | ConvertFrom-Json | ConvertTo-Json -Compress"
    result = _run(script, timeout=60)
    if result["ok"] and result["stdout"]:
        try:
            result["data"] = json.loads(result["stdout"])
        except json.JSONDecodeError:
            result["data"] = []
    else:
        result["data"] = []
    return result


def choco_install(choco_id: str) -> dict[str, Any]:
    """Install an application via Chocolatey."""
    script = f'choco install "{choco_id}" -y --no-progress; exit $LASTEXITCODE'
    return _run(script, timeout=300)


# ── Registry tweaks ────────────────────────────────────────────────────────

def apply_registry_entries(entries: list[dict], *, undo: bool = False) -> list[dict]:
    """Apply (or undo) registry entries from a tweak's registry list.

    Each entry dict has: Path, Name, Value, Type, OriginalValue.
    When undo=True, restores OriginalValue (or removes if Value was <RemoveEntry>).
    Returns list of per-entry results.
    """
    import winreg  # only available on Windows

    results = []
    _HIVE_MAP = {
        "HKLM:": winreg.HKEY_LOCAL_MACHINE,
        "HKCU:": winreg.HKEY_CURRENT_USER,
        "HKCR:": winreg.HKEY_CLASSES_ROOT,
        "HKU:":  winreg.HKEY_USERS,
        "HKCC:": winreg.HKEY_CURRENT_CONFIG,
    }
    _TYPE_MAP = {
        "DWord":      winreg.REG_DWORD,
        "QWord":      winreg.REG_QWORD,
        "String":     winreg.REG_SZ,
        "ExpandString": winreg.REG_EXPAND_SZ,
        "MultiString": winreg.REG_MULTI_SZ,
        "Binary":     winreg.REG_BINARY,
    }

    for entry in entries:
        reg_path: str = entry.get("Path", "")
        name: str = entry.get("Name", "")
        value = entry.get("OriginalValue") if undo else entry.get("Value")
        reg_type: str = entry.get("Type", "DWord")
        result = {"path": reg_path, "name": name, "ok": False, "error": ""}

        try:
            # Resolve hive
            hive_prefix = next((p for p in _HIVE_MAP if reg_path.startswith(p)), None)
            if not hive_prefix:
                result["error"] = f"Unknown hive in path: {reg_path}"
                results.append(result)
                continue

            hive = _HIVE_MAP[hive_prefix]
            sub_path = reg_path[len(hive_prefix):].lstrip("\\")

            if str(value) == "<RemoveEntry>":
                # Delete the value
                with winreg.OpenKey(hive, sub_path, 0, winreg.KEY_SET_VALUE) as k:
                    winreg.DeleteValue(k, name)
                result["ok"] = True
                result["action"] = "deleted"
            else:
                # Ensure key exists, then set value
                winreg.CreateKeyEx(hive, sub_path, 0, winreg.KEY_SET_VALUE)
                with winreg.OpenKey(hive, sub_path, 0, winreg.KEY_SET_VALUE) as k:
                    reg_type_code = _TYPE_MAP.get(reg_type, winreg.REG_SZ)
                    typed_value: Any = value
                    if reg_type in ("DWord", "QWord"):
                        typed_value = int(value) if value not in (None, "") else 0
                    winreg.SetValueEx(k, name, 0, reg_type_code, typed_value)
                result["ok"] = True
                result["action"] = "set"

        except PermissionError:
            result["error"] = "Permission denied — run as administrator"
            result["admin_required"] = True
        except FileNotFoundError:
            if str(value) == "<RemoveEntry>":
                result["ok"] = True  # already absent — success
                result["action"] = "already_absent"
            else:
                result["error"] = "Registry key not found"
        except Exception as exc:
            result["error"] = str(exc)

        results.append(result)

    return results


def apply_invoke_scripts(scripts: list[str], *, timeout: int = 60) -> dict[str, Any]:
    """Run a list of InvokeScript PowerShell strings with winutil helpers available."""
    if not scripts:
        return {"ok": True, "stdout": "", "stderr": "", "returncode": 0, "admin_required": False}

    private_dir = str(_PRIVATE_DIR).replace("\\", "/")
    preamble = _WINUTIL_PREAMBLE.replace("{PRIVATE_DIR}", str(_PRIVATE_DIR))
    full_script = preamble + "\n\n" + "\n".join(scripts)
    return _run(full_script, timeout=timeout)


# ── Optional features ───────────────────────────────────────────────────────

def enable_feature(feature_names: list[str], *, invoke_scripts: list[str] | None = None) -> dict[str, Any]:
    """Enable one or more Windows optional features plus run any InvokeScripts."""
    err = _admin_check("Enabling Windows features")
    if err:
        return err
    parts = []
    for f in feature_names:
        parts.append(f'Enable-WindowsOptionalFeature -Online -FeatureName "{f}" -NoRestart -All 2>&1')
    if invoke_scripts:
        parts.extend(invoke_scripts)
    script = "\n".join(parts) if parts else "Write-Host 'No features specified'"
    return _run(script, timeout=300)


# ── DNS ────────────────────────────────────────────────────────────────────

def set_dns(primary: str, secondary: str, primary6: str = "", secondary6: str = "") -> dict[str, Any]:
    """Set DNS servers on all active network adapters."""
    err = _admin_check("Setting DNS")
    if err:
        return err

    servers = f'"{primary}", "{secondary}"'
    servers6 = f'"{primary6}", "{secondary6}"' if primary6 and secondary6 else ""

    script = f"""
$adapters = Get-NetAdapter | Where-Object {{$_.Status -eq "Up"}}
foreach ($a in $adapters) {{
    Set-DnsClientServerAddress -InterfaceIndex $a.ifIndex -ServerAddresses ({servers})
"""
    if servers6:
        script += f'    Set-DnsClientServerAddress -InterfaceIndex $a.ifIndex -ServerAddresses ({servers6})\n'
    script += "}\nWrite-Host 'DNS updated on all active adapters'"
    return _run(script, timeout=30)


def reset_dns_dhcp() -> dict[str, Any]:
    """Reset DNS to DHCP on all active adapters."""
    err = _admin_check("Resetting DNS")
    if err:
        return err
    script = """
$adapters = Get-NetAdapter | Where-Object {$_.Status -eq "Up"}
foreach ($a in $adapters) {
    Set-DnsClientServerAddress -InterfaceIndex $a.ifIndex -ResetServerAddresses
}
Write-Host 'DNS reset to DHCP on all active adapters'
"""
    return _run(script, timeout=30)


# ── Repair utilities ───────────────────────────────────────────────────────

def fix_windows_update() -> dict[str, Any]:
    """Reset Windows Update components (DISM + SFC + WSReset + service restart)."""
    err = _admin_check("Windows Update fix")
    if err:
        return err
    script = r"""
$services = @("wuauserv","cryptSvc","bits","msiserver")
foreach ($svc in $services) { Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue }

Remove-Item -Path "$env:systemroot\SoftwareDistribution" -Recurse -ErrorAction SilentlyContinue
Remove-Item -Path "$env:systemroot\System32\catroot2" -Recurse -ErrorAction SilentlyContinue

foreach ($svc in $services) { Start-Service -Name $svc -ErrorAction SilentlyContinue }

Write-Host "Running DISM..."
DISM /Online /Cleanup-Image /RestoreHealth
Write-Host "Running SFC..."
sfc /scannow
Write-Host "Windows Update fix complete"
"""
    return _run(script, timeout=600)


def fix_network() -> dict[str, Any]:
    """Reset network stack (Winsock, IP, DNS cache, clear ARP)."""
    err = _admin_check("Network fix")
    if err:
        return err
    script = r"""
netsh int ip reset
netsh int tcp reset
netsh winsock reset
netsh winhttp reset proxy
ipconfig /flushdns
ipconfig /release
ipconfig /renew
arp -d *
Write-Host "Network stack reset complete — reboot recommended"
"""
    return _run(script, timeout=60)


def fix_winget() -> dict[str, Any]:
    """Repair winget (re-register AppInstaller package)."""
    script = r"""
$pkg = Get-AppxPackage *Microsoft.DesktopAppInstaller* -AllUsers | Select-Object -Last 1
if ($pkg) {
    Add-AppxPackage -DisableDevelopmentMode -Register "$($pkg.InstallLocation)\AppxManifest.xml"
    Write-Host "winget re-registered: $($pkg.Version)"
} else {
    Write-Host "AppInstaller package not found — install from Microsoft Store"
}
"""
    return _run(script, timeout=60)


def fix_system_repair() -> dict[str, Any]:
    """Run full system repair: DISM + SFC + disk check scheduling."""
    err = _admin_check("System repair")
    if err:
        return err
    script = r"""
Write-Host "=== DISM RestoreHealth ==="
DISM /Online /Cleanup-Image /RestoreHealth
Write-Host "=== SFC ==="
sfc /scannow
Write-Host "System repair complete"
"""
    return _run(script, timeout=900)


def enable_ultimate_performance() -> dict[str, Any]:
    """Activate Ultimate Performance power plan."""
    err = _admin_check("Power plan change")
    if err:
        return err
    script = r"""
$existing = powercfg /list | Select-String "Ultimate Performance"
if (-not $existing) {
    powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61
}
$guid = (powercfg /list | Select-String "Ultimate Performance") -replace ".*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}).*",'$1'
powercfg /setactive $guid.Trim()
Write-Host "Ultimate Performance plan activated"
"""
    return _run(script, timeout=30)
