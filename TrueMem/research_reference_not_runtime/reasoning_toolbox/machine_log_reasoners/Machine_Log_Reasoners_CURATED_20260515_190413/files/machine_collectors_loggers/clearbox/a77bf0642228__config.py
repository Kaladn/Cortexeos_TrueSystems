"""
OpenRefine Plugin — Configuration
Locates the OpenRefine installation, controls port/memory/host.
Override any value via environment variables or forest.config.json.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Default OpenRefine install candidates (Windows) ───────────────────────────
_OR_DEFAULT_CANDIDATES = [
    Path(r"C:\Users\Lee\Downloads\openrefine-win-with-java-3.10.0\openrefine-3.10.0"),
    Path.home() / "Downloads" / "openrefine-win-with-java-3.10.0" / "openrefine-3.10.0",
    Path(r"C:\Program Files\OpenRefine"),
    Path(r"C:\OpenRefine"),
]


def _find_default_install() -> Path:
    for p in _OR_DEFAULT_CANDIDATES:
        if (p / "openrefine.exe").exists() or (p / "refine.bat").exists():
            return p
    return _OR_DEFAULT_CANDIDATES[0]  # fallback even if not found


@dataclass(frozen=True)
class OpenRefineConfig:
    plugin_id: str = "openrefine"
    api_prefix: str = "/api/openrefine"
    display_name: str = "OpenRefine"
    version: str = "0.1.0"

    # ── OpenRefine process settings ──────────────────────────────────────────
    or_port: int = 3333
    or_host: str = "127.0.0.1"
    or_memory_mb: int = 1400
    or_startup_timeout_s: int = 30   # seconds to wait for OR to be ready
    or_poll_interval_s: float = 0.5  # poll interval during startup

    # ── Install path (resolved at import time) ───────────────────────────────
    or_install_dir_env: str = "OPENREFINE_INSTALL_DIR"

    @property
    def or_install_dir(self) -> Path:
        override = os.environ.get(self.or_install_dir_env)
        if override:
            return Path(override).expanduser().resolve()
        return _find_default_install()

    @property
    def or_exe(self) -> Path:
        """Preferred launcher — .exe on Windows, refine.bat as fallback."""
        exe = self.or_install_dir / "openrefine.exe"
        if exe.exists():
            return exe
        return self.or_install_dir / "refine.bat"

    @property
    def or_base_url(self) -> str:
        return f"http://{self.or_host}:{self.or_port}"

    @property
    def or_version_url(self) -> str:
        return f"{self.or_base_url}/command/core/get-version"

    @property
    def or_csrf_url(self) -> str:
        return f"{self.or_base_url}/command/core/get-csrf-token"

    @property
    def or_projects_url(self) -> str:
        return f"{self.or_base_url}/command/core/get-all-project-metadata"

    @property
    def workspace_dir(self) -> Path:
        """Where OpenRefine stores project data."""
        override = os.environ.get("OPENREFINE_WORKSPACE_DIR")
        if override:
            return Path(override).expanduser().resolve()
        return Path.home() / "OpenRefine"


# ── Load overrides from forest.config.json ────────────────────────────────────
def load_config() -> OpenRefineConfig:
    """
    Returns a frozen config dataclass.
    Reads the [openrefine] section of forest.config.json if available,
    but the dataclass is frozen — overrides are handled at construction time.
    """
    overrides: dict = {}

    try:
        from security.data_paths import FOREST_CONFIG_PATH
        from security.secure_storage import secure_json_load
        path = FOREST_CONFIG_PATH
        loader = secure_json_load
    except ImportError:
        path = Path("forest.config.json")
        loader = None

    try:
        if path.exists():
            raw = loader(path) if loader else json.loads(path.read_text(encoding="utf-8"))
            overrides = raw.get("openrefine", {})
    except Exception as exc:
        logger.warning("OpenRefine config load failed: %s", exc)

    # Map config keys → constructor kwargs
    kwargs = {}
    if "port" in overrides:
        object.__setattr__(kwargs, "or_port", int(overrides["port"]))
    if "memory_mb" in overrides:
        object.__setattr__(kwargs, "or_memory_mb", int(overrides["memory_mb"]))
    if "startup_timeout_s" in overrides:
        object.__setattr__(kwargs, "or_startup_timeout_s", int(overrides["startup_timeout_s"]))

    # frozen dataclass — rebuild with overrides
    if not kwargs:
        return OpenRefineConfig()

    return OpenRefineConfig(
        or_port=overrides.get("port", OpenRefineConfig.or_port),
        or_memory_mb=overrides.get("memory_mb", OpenRefineConfig.or_memory_mb),
        or_startup_timeout_s=overrides.get("startup_timeout_s", OpenRefineConfig.or_startup_timeout_s),
    )


CONFIG = OpenRefineConfig()
