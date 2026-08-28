#!/usr/bin/env python3
"""Clearbox AI Studio — Uninstaller

Removes every artifact created by clearbox_install.py:
  * .venv/                        — virtual environment
  * <selected data root>/         — all user data, config, sessions
  * <selected data root>/runtime/install_state.json — installer state file
  * Registry resume hook          — HKCU\...\Run\ClearboxAI_Install_Resume
  * .install_tmp_req.txt           — temp file left by a failed install
  * __pycache__ trees              — compiled bytecode

Source code is untouched.

Usage:
    python scripts/clearbox_uninstall.py                  # interactive (prompts)
    python scripts/clearbox_uninstall.py --yes            # non-interactive
    python scripts/clearbox_uninstall.py --backup         # backup user data first
    python scripts/clearbox_uninstall.py --backup --yes   # backup + skip prompt
    python scripts/clearbox_uninstall.py --data-root X:\ClearboxData
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
VENV_DIR       = WORKSPACE_ROOT / ".venv"

_C_OK   = "\033[92m"
_C_WARN = "\033[93m"
_C_ERR  = "\033[91m"
_C_DIM  = "\033[90m"
_C_END  = "\033[0m"

def _ok(msg: str)   -> None: print(f"   {_C_OK}OK{_C_END}  {msg}")
def _warn(msg: str) -> None: print(f"   {_C_WARN}!!{_C_END}  {msg}")
def _err(msg: str)  -> None: print(f"   {_C_ERR}XX{_C_END}  {msg}")
def _info(msg: str) -> None: print(f"   {_C_DIM}--{_C_END}  {msg}")


def _data_root() -> Path:
    env_root = os.environ.get("CLEARBOX_DATA_ROOT")
    if env_root:
        return Path(env_root.strip().strip('"')).expanduser()
    saved = _read_bootstrap_data_root()
    if saved is not None:
        return saved
    return Path("D:/CLEARBOX")


def _legacy_data_root() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    return Path(local) / "ClearboxAI" if local else Path.home() / ".clearbox_ai"


def _bootstrap_storage_file() -> Path:
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA")
        if local:
            return Path(local) / "ClearboxAI" / "storage_paths.json"
    return Path.home() / ".clearbox_ai" / "storage_paths.json"


def _read_bootstrap_data_root() -> Path | None:
    cfg = _bootstrap_storage_file()
    if not cfg.exists():
        return None
    try:
        data = json.loads(cfg.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    root = data.get("data_root")
    if not root or not isinstance(root, str):
        return None
    return Path(root).expanduser()


def _state_file_path(root: Path | None = None) -> Path:
    base = root if root is not None else _data_root()
    return base / "runtime" / "install_state.json"


def _legacy_state_file_path() -> Path:
    return _legacy_data_root() / "install_state.json"


def _desktop() -> Path:
    """Return the user's Desktop path."""
    # Windows: check known folder via env var first
    desktop = os.environ.get("USERPROFILE")
    if desktop:
        d = Path(desktop) / "Desktop"
        if d.exists():
            return d
    # OneDrive Desktop fallback
    onedrive = os.environ.get("OneDrive")
    if onedrive:
        d = Path(onedrive) / "Desktop"
        if d.exists():
            return d
    return Path.home() / "Desktop"


def _backup_user_data(data_root: Path) -> Path | None:
    """Copy user data to a timestamped folder on the Desktop.

    Returns the backup path on success, None on failure.
    """
    if not data_root.exists():
        _info("No user data to back up")
        return None

    stamp = time.strftime("%Y%m%d_%H%M%S")
    backup_name = f"ClearboxAI_backup_{stamp}"
    backup_path = _desktop() / backup_name

    print(f"  Backing up user data to:")
    print(f"    {backup_path}")
    print()

    try:
        shutil.copytree(data_root, backup_path)
        _ok(f"Backup complete: {backup_path}")
        return backup_path
    except OSError as e:
        _err(f"Backup failed: {e}")
        return None


def _rmtree(path: Path, label: str) -> bool:
    """Remove a directory tree.  Returns True on full success."""
    if not path.exists():
        _info(f"Already gone: {label}")
        return True

    def _on_error(func, fpath, *_):
        # Try clearing read-only flag then retry
        try:
            os.chmod(fpath, 0o777)
            func(fpath)
        except OSError:
            pass  # still locked — will be reported below

    try:
        shutil.rmtree(path, onerror=_on_error)
        if path.exists():
            raise OSError("directory still present after rmtree")
        _ok(f"Removed: {path}")
        return True
    except OSError as e:
        _err(f"Could not fully remove {path}")
        _warn(f"  {e}")
        _warn("  A Python process is holding a file open (e.g. VSCode extension).")
        _warn("  Close all Python/VSCode processes, then re-run this uninstaller.")
        return False


def _rm(path: Path) -> None:
    if path.exists():
        try:
            path.unlink()
            _ok(f"Removed: {path}")
        except OSError as e:
            _err(f"Could not remove {path}: {e}")


def _remove_pycache(root: Path) -> int:
    removed = 0
    for d in root.rglob("__pycache__"):
        if d.is_dir():
            try:
                shutil.rmtree(d)
                removed += 1
            except OSError:
                pass
    return removed


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ap = argparse.ArgumentParser(description="Clearbox AI Studio Uninstaller")
    ap.add_argument("--yes", "-y", action="store_true",
                    help="Skip confirmation prompt")
    ap.add_argument("--backup", "-b", action="store_true",
                    help="Back up user data to Desktop before deleting")
    ap.add_argument("--data-root",
                    help="Explicit data root folder to uninstall")
    args = ap.parse_args()

    dr = Path(args.data_root).expanduser() if args.data_root else _data_root()
    legacy_dr = _legacy_data_root()

    print()
    print("=" * 55)
    print("  CLEARBOX AI STUDIO — UNINSTALLER")
    print("=" * 55)
    print()
    if args.backup:
        print(f"  Will BACK UP user data to Desktop, then delete:")
    else:
        print("  Will permanently delete:")
    print(f"    {VENV_DIR}")
    print(f"    {dr}")
    if legacy_dr != dr:
        print(f"    {legacy_dr} (legacy path, if present)")
    print(f"    __pycache__ trees under {WORKSPACE_ROOT}")
    print()

    if not args.yes:
        ans = input("  Type YES to continue, anything else to abort: ").strip()
        if ans.upper() != "YES":
            print("  Aborted.")
            return 0

    print()

    # 0. Backup (if requested)
    if args.backup:
        backup_target = dr if dr.exists() else legacy_dr
        backup_path = _backup_user_data(backup_target)
        if backup_path is None and (dr.exists() or legacy_dr.exists()):
            _err("Backup failed — aborting uninstall to protect your data.")
            return 1
        print()

    # 1. Virtual environment
    _rmtree(VENV_DIR, ".venv")

    # 2. User data roots
    _rmtree(dr, "Clearbox data root")
    if legacy_dr != dr:
        _rmtree(legacy_dr, "legacy ClearboxAI data root")

    # 3. Temp install artifact
    _rm(WORKSPACE_ROOT / ".install_tmp_req.txt")

    # 4. Bytecode caches
    n = _remove_pycache(WORKSPACE_ROOT)
    if n:
        _ok(f"Removed {n} __pycache__ directories")
    else:
        _info("No __pycache__ directories found")

    # 5. Installer resume hook (Registry Run key)
    if os.name == "nt":
        try:
            import winreg
            _hook_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _hook_key,
                                0, winreg.KEY_SET_VALUE) as key:
                try:
                    winreg.DeleteValue(key, "ClearboxAI_Install_Resume")
                    _ok("Removed installer resume hook")
                except FileNotFoundError:
                    _info("No installer resume hook found")
        except Exception:
            pass

    # 6. Installer state file(s)
    _rm(_state_file_path(dr))
    _rm(_legacy_state_file_path())
    _rm(_bootstrap_storage_file())

    print()
    print("=" * 55)
    print("  UNINSTALL COMPLETE — source code untouched")
    if args.backup:
        print(f"  Backup saved to Desktop")
    print("  To reinstall: python scripts/clearbox_install.py")
    print("=" * 55)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
