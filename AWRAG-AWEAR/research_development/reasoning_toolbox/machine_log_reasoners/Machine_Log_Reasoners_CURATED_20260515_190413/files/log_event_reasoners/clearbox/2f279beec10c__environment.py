"""Environment probe — workspace health checks.

Graduated from tools/maintenance/environment_health_check.py.
Checks: CWD location, config file, config paths, lexicon.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List, Tuple

from .base import Probe, RunContext, ProbeResult, make_result


def _resolve_config_path(raw_path: str, root: Path) -> Path:
    path = Path(raw_path)
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def _check_cwd() -> Tuple[bool, str, dict]:
    cwd = Path.cwd().resolve()
    in_onedrive = any(part.lower() == "onedrive" for part in cwd.parts)
    detail = {"cwd": str(cwd), "in_onedrive": in_onedrive}
    if in_onedrive:
        return False, f"Workspace inside OneDrive: {cwd}", detail
    return True, str(cwd), detail


def _check_config(config_path: Path) -> Tuple[bool, str, dict, dict]:
    """Returns (ok, message, evidence_detail, parsed_config)."""
    if not config_path.exists():
        return False, f"Missing config file at {config_path}", {"path": str(config_path)}, {}
    try:
        with config_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        return False, f"Invalid JSON: {exc}", {"path": str(config_path), "error": str(exc)}, {}
    if not isinstance(data, dict):
        return False, "Config root is not an object", {"path": str(config_path)}, {}
    return True, f"Loaded {config_path}", {"path": str(config_path), "keys": sorted(data.keys())}, data


def _check_paths(config: dict, config_dir: Path) -> Tuple[bool, str, dict]:
    problems = []
    evidence: dict = {}

    lex_value = config.get("lexicon_root")
    if isinstance(lex_value, str):
        lex_root = _resolve_config_path(lex_value, config_dir)
        evidence["lexicon_root"] = str(lex_root)
        if not lex_root.exists():
            problems.append(f"Lexicon root missing: {lex_root}")
    else:
        problems.append("Config missing 'lexicon_root' string")

    reports_value = config.get("reports_root")
    if isinstance(reports_value, str):
        reports_root = _resolve_config_path(reports_value, config_dir)
        evidence["reports_root"] = str(reports_root)
        if not reports_root.exists():
            problems.append(f"Reports root missing: {reports_root}")
    else:
        problems.append("Config missing 'reports_root' string")

    if problems:
        evidence["problems"] = problems
        return False, "; ".join(problems), evidence
    return True, "paths OK", evidence


def _check_lexicon(config: dict, config_dir: Path) -> Tuple[bool, str, dict]:
    lex_root_value = config.get("lexicon_root")
    if not isinstance(lex_root_value, str):
        return False, "Config missing lexicon_root string", {}

    lex_root = _resolve_config_path(lex_root_value, config_dir)
    lexicon_path = lex_root / "lexicon_v2.json"
    evidence: dict = {"path": str(lexicon_path)}

    if not lexicon_path.exists():
        return None, "Lexicon not yet imported (download/import required)", evidence
    if lexicon_path.stat().st_size == 0:
        return False, f"Lexicon file is empty", evidence

    try:
        with lexicon_path.open("r", encoding="utf-8") as f:
            entries = json.load(f)
    except json.JSONDecodeError as exc:
        return False, f"Lexicon JSON invalid: {exc}", evidence

    if not isinstance(entries, list):
        return False, "Lexicon payload is not a list", evidence

    count = len(entries)
    evidence["entry_count"] = count
    if count == 0:
        return False, "Lexicon contains zero entries", evidence

    sample = entries[0].get("token") if entries else ""
    evidence["first_token"] = sample
    return True, f"{count:,} entries", evidence


class EnvironmentProbe:
    """Workspace health: CWD, config, paths, lexicon."""

    probe_id = "environment"
    description = "Workspace and config health checks"

    def run(self, ctx: RunContext) -> List[ProbeResult]:
        results: List[ProbeResult] = []

        # 1. CWD check
        t0 = time.perf_counter()
        ok, msg, detail = _check_cwd()
        lat = (time.perf_counter() - t0) * 1000
        results.append(make_result(
            ctx, self.probe_id, "env.cwd",
            "CONFIRMED" if ok else "DENIED",
            lat_ms=lat, detail=detail,
        ))

        # 2. Config file check
        config_path = Path("clearbox.config.json").resolve()
        config_dir = config_path.parent
        t0 = time.perf_counter()
        ok_cfg, cfg_msg, cfg_detail, config = _check_config(config_path)
        lat = (time.perf_counter() - t0) * 1000
        results.append(make_result(
            ctx, self.probe_id, "env.config",
            "CONFIRMED" if ok_cfg else "DENIED",
            lat_ms=lat, detail=cfg_detail,
        ))

        if not ok_cfg:
            # Can't check paths/lexicon without config
            results.append(make_result(
                ctx, self.probe_id, "env.paths",
                "SKIPPED", skip_reason="Config missing or invalid — check clearbox_config.yaml",
            ))
            results.append(make_result(
                ctx, self.probe_id, "env.lexicon",
                "SKIPPED", skip_reason="Config missing or invalid — check clearbox_config.yaml",
            ))
            return results

        # 3. Config paths check
        t0 = time.perf_counter()
        ok_paths, paths_msg, paths_detail = _check_paths(config, config_dir)
        lat = (time.perf_counter() - t0) * 1000
        results.append(make_result(
            ctx, self.probe_id, "env.paths",
            "CONFIRMED" if ok_paths else "DENIED",
            lat_ms=lat, detail=paths_detail,
        ))

        # 4. Lexicon check (None = optional asset not present → SKIPPED)
        t0 = time.perf_counter()
        ok_lex, lex_msg, lex_detail = _check_lexicon(config, config_dir)
        lat = (time.perf_counter() - t0) * 1000
        if ok_lex is None:
            results.append(make_result(
                ctx, self.probe_id, "env.lexicon",
                "SKIPPED", lat_ms=lat, skip_reason=lex_msg, detail=lex_detail,
            ))
        else:
            results.append(make_result(
                ctx, self.probe_id, "env.lexicon",
                "CONFIRMED" if ok_lex else "DENIED",
                lat_ms=lat, detail=lex_detail,
            ))

        return results
