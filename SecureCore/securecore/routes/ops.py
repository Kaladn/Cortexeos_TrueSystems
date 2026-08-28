"""Admin ops routes for SecureCore runtime inspection.

These routes expose current SecureCore component state and draft-builder
contracts. They do not start agents, enable loggers, write manifests, install a
UI/chat runtime, or mutate runtime state.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import jwt_required

from securecore.core.auth import role_required
from securecore.actions.registry import default_action_registry
from securecore.harness.factories import factory_blueprints
from securecore.harness.knowledge import SecureCoreHarness
from securecore.runtime.manager import SecureCoreRuntimeManager
from securecore.runtime.warmup import run_system_warmup
from securecore.tools.capabilities import build_default_capability_registry
from securecore.tools.recipes import build_default_chain_recipes
from securecore.truevision.config import TrueVisionRuntimeConfig
from securecore.truevision.contracts import CAPTURE_SURFACES, EDITION, FORBIDDEN_KEYS, KIND
from securecore.worker_feeds.registry import default_worker_registry


ops_bp = Blueprint("ops", __name__)


@ops_bp.get("/api/ops/dashboard")
@jwt_required()
@role_required("admin")
def dashboard():
    """Return a compact operator dashboard snapshot."""
    substrates = {}
    for name, substrate in getattr(current_app, "substrates", {}).items():
        substrates[name] = {
            "total_records": _safe_call(substrate, "count", default=0),
            "jsonl_path": str(getattr(substrate, "jsonl_path", "")),
        }

    agents = {}
    for name, agent in getattr(current_app, "agents", {}).items():
        agents[name] = dict(getattr(agent, "stats", {}) or {})

    log_router = getattr(current_app, "log_router", None)
    log_streams = _safe_call(log_router, "stats", default={}) if log_router else {}

    return jsonify(
        {
            "ok": True,
            "mutation_authorized": False,
            "activation_authorized": False,
            "substrates": substrates,
            "agents": agents,
            "log_streams": log_streams,
            "factory_tools": _factory_blueprints(),
            "laws": [
                "Creation tools draft contracts only.",
                "No prompt-only production agents.",
                "Activation requires tests and approval.",
            ],
        }
    )


@ops_bp.get("/api/ops/catalog")
@jwt_required()
@role_required("admin")
def catalog():
    """Return the registries the frontdoor can honestly display."""
    return jsonify(
        {
            "ok": True,
            "agents": _load_agent_manifests(),
            "capabilities": list(build_default_capability_registry().values()),
            "recipes": list(build_default_chain_recipes().values()),
            "factory_tools": _factory_blueprints(),
            "mutation_authorized": False,
            "activation_authorized": False,
        }
    )


@ops_bp.get("/api/ops/toolbox")
@jwt_required()
@role_required("admin")
def toolbox():
    """Return the honest toolbox inventory for workers, loggers, agents, routes, and recipes."""
    return jsonify(
        {
            "ok": True,
            "workers": default_worker_registry(),
            "loggers": _logger_registry(),
            "agents": _load_agent_manifests(),
            "actions": default_action_registry(),
            "capabilities": list(build_default_capability_registry().values()),
            "recipes": list(build_default_chain_recipes().values()),
            "factory_tools": _factory_blueprints(),
            "system_routes": _system_routes(),
            "ui_runtime": "not_installed",
            "chat_runtime": "not_installed",
            "memory_runtime": "not_installed",
            "future_port": True,
            "activation_authorized": False,
            "mutation_authorized": False,
            "laws": [
                "Workers are coded entities, not prompt agents.",
                "Toolbox exposes capability; it does not activate capability.",
                "UI/chat/memory runtime ports are reserved but not installed.",
            ],
        }
    )


@ops_bp.get("/api/ops/truevision")
@jwt_required()
@role_required("admin")
def truevision_tab():
    """Return SecureCore-visible TrueVision boundaries without starting capture."""
    config = TrueVisionRuntimeConfig()
    forbidden_source_truth = sorted(set(FORBIDDEN_KEYS) | {"raw_frames", "generated_media", "screenshots"})
    return jsonify(
        {
            "ok": True,
            "source_system": "TrueVision",
            "edition": EDITION,
            "kind": KIND,
            "status": "sc_edition_available",
            "config": {
                "enabled": config.enabled,
                "source_id": config.source_id,
                "session_id": config.session_id,
                "grid_size": config.grid_size,
                "sample_interval_ms": config.sample_interval_ms,
                "max_payload_bytes": config.max_payload_bytes,
                "allow_camera": config.allow_camera,
                "allow_raw_frames": config.allow_raw_frames,
            },
            "approved_capture_surfaces": sorted(CAPTURE_SURFACES),
            "source_truth": [
                "small visual state-change metadata",
                "grid hashes",
                "glyph summary metadata",
                "Forge sensor events",
                "receipts/manifests",
                "timing pulse metadata",
            ],
            "forbidden_source_truth": forbidden_source_truth,
            "lanes": [
                {
                    "lane_id": "state_change",
                    "sensor_id": "truevision.state_change",
                    "sensor_class": "vision",
                    "writes": "Forge sensor event",
                    "payload_boundary": "small_metadata",
                },
                {
                    "lane_id": "temporal_pulse",
                    "sensor_id": "truevision.temporal_pulse",
                    "sensor_class": "truevision_temporal_pulse",
                    "writes": "fusion metadata",
                    "payload_boundary": "timing metadata only",
                },
                {
                    "lane_id": "glyph_summary",
                    "sensor_id": "truevision.glyph_summary",
                    "sensor_class": "glyph_metadata",
                    "writes": "attached metadata",
                    "payload_boundary": "counts/hashes only",
                },
            ],
            "capture_authorized": False,
            "render_authorized": False,
            "activation_authorized": False,
            "mutation_authorized": False,
            "raw_media_authorized": False,
            "laws": [
                "TrueVision logs state; it does not store raw media in SecureCore.",
                "SecureCore receives metadata, receipts, hashes, and refs only.",
                "Media surfaces are optional outputs, not SecureCore source truth.",
            ],
        }
    )


@ops_bp.get("/api/ops/warmup")
@jwt_required()
@role_required("admin")
def warmup():
    """Run read-only startup checks. Does not launch agents, loggers, or containment."""
    runtime_root = Path(os.environ.get("SECURECORE_RUNTIME_ROOT", r"D:\SecureCore_Runtime\USER1\baseline"))
    return jsonify(
        {
            "ok": True,
            "warmup": run_system_warmup(
                runtime_root=runtime_root,
                repo_root=_repo_root(),
                write_receipt=False,
            ),
        }
    )


@ops_bp.get("/api/ops/runtime/latest")
@jwt_required()
@role_required("admin")
def runtime_latest():
    """Return status, verification, and watcher view for latest runtime proof."""
    runtime_root = Path(os.environ.get("SECURECORE_RUNTIME_ROOT", r"D:\SecureCore_Runtime\USER1\baseline"))
    manager = SecureCoreRuntimeManager(runtime_root)
    status = manager.status()
    verify = manager.verify_latest()
    watch = manager.watch_latest()
    return jsonify(
        {
            "ok": True,
            "runtime_root": str(runtime_root),
            "status": status,
            "verify": verify,
            "watch": watch,
            "mutation_authorized": False,
        }
    )


@ops_bp.get("/api/ops/away-watch/reports")
@jwt_required()
@role_required("admin")
def away_watch_reports():
    """List Away Watch reports for read-only operator review."""
    runtime_root = _away_watch_runtime_root()
    reports_root = runtime_root / "reports"
    rows: list[dict[str, Any]] = []
    if reports_root.exists():
        for path in sorted(
            (item for item in reports_root.rglob("*") if item.is_file()),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        ):
            rows.append(_away_report_row(path, reports_root))
    return jsonify(
        {
            "ok": True,
            "runtime_root": str(runtime_root),
            "reports_root": str(reports_root),
            "reports": rows,
            "mutation_authorized": False,
            "activation_authorized": False,
        }
    )


@ops_bp.get("/api/ops/away-watch/report")
@jwt_required()
@role_required("admin")
def away_watch_report():
    """Read one Away Watch report for read-only operator review."""
    report_id = str(request.args.get("report_id", "")).strip()
    target = _resolve_away_report(report_id)
    if target is None:
        return jsonify({"ok": False, "error": "invalid report_id"}), 400
    if not target.exists() or not target.is_file():
        return jsonify({"ok": False, "error": "report not found"}), 404

    raw = target.read_text(encoding="utf-8", errors="replace")
    parsed: Any = None
    text = raw
    if target.suffix.lower() == ".json":
        try:
            parsed = json.loads(raw)
            text = json.dumps(parsed, indent=2, sort_keys=True)
        except json.JSONDecodeError:
            parsed = None

    reports_root = (_away_watch_runtime_root() / "reports").resolve()
    safe_id = target.relative_to(reports_root).as_posix()
    return jsonify(
        {
            "ok": True,
            "report_id": safe_id,
            "source_ref": str(target),
            "content_type": _away_report_content_type(target),
            "parsed": parsed,
            "text": text,
            "mutation_authorized": False,
            "activation_authorized": False,
        }
    )


@ops_bp.get("/api/ops/harness")
@jwt_required()
@role_required("admin")
def harness_snapshot():
    """Return the deterministic creator/security harness map."""
    return jsonify({"ok": True, "harness": SecureCoreHarness(_repo_root()).snapshot()})


@ops_bp.post("/api/ops/harness/choose")
@jwt_required()
@role_required("admin")
def harness_choose():
    """Classify a request into deterministic capability/agent routing."""
    from flask import request

    payload = request.get_json(silent=True) or {}
    text = str(payload.get("request", "")).strip()
    if not text:
        return jsonify({"ok": False, "error": "request required"}), 400
    return jsonify({"ok": True, "choice": SecureCoreHarness(_repo_root()).choose(text)})


def _safe_call(target: Any, method_name: str, *, default: Any) -> Any:
    try:
        method = getattr(target, method_name)
        return method()
    except Exception:
        return default


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _away_watch_runtime_root() -> Path:
    return Path(os.environ.get("SECURECORE_AWAY_WATCH_ROOT", r"D:\SecureCore_Runtime\USER1\away_watch"))


def _away_report_row(path: Path, reports_root: Path) -> dict[str, Any]:
    stat = path.stat()
    rel = path.relative_to(reports_root).as_posix()
    return {
        "report_id": rel,
        "report_kind": rel.split("/", 1)[0] if "/" in rel else "root",
        "name": path.name,
        "path": str(path),
        "size_bytes": stat.st_size,
        "modified_at_utc": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat().replace("+00:00", "Z"),
        "content_type": _away_report_content_type(path),
        "mutation_authorized": False,
    }


def _away_report_content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return "application/json"
    if suffix == ".jsonl":
        return "application/x-jsonlines"
    if suffix in {".md", ".markdown"}:
        return "text/markdown"
    return "text/plain"


def _resolve_away_report(report_id: str) -> Path | None:
    if not report_id:
        return None
    normalized = report_id.replace("\\", "/")
    rel = Path(normalized)
    if rel.is_absolute() or any(part in {"", ".", ".."} for part in rel.parts):
        return None
    reports_root = (_away_watch_runtime_root() / "reports").resolve()
    target = (reports_root / rel).resolve()
    try:
        target.relative_to(reports_root)
    except ValueError:
        return None
    return target


def _load_agent_manifests() -> list[dict[str, Any]]:
    root = _repo_root() / "securecore" / "live_agents" / "AGENTS" / "agents"
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("*.agent.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            rows.append(
                {
                    "agent_id": data.get("agent_id", path.stem),
                    "name": data.get("name", path.stem),
                    "runtime_language": data.get("runtime_language", "unknown"),
                    "requires_approval": bool(data.get("requires_approval")),
                    "risk_tier": data.get("risk_tier", 0),
                    "dry_run_supported": bool(data.get("dry_run_supported")),
                    "mutation_class": data.get("mutation_class", ""),
                    "manifest_path": str(path),
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "agent_id": path.stem,
                    "name": path.stem,
                    "runtime_language": "unknown",
                    "requires_approval": True,
                    "risk_tier": 5,
                    "dry_run_supported": False,
                    "mutation_class": "unreadable_manifest",
                    "manifest_path": str(path),
                    "error": str(exc),
                }
            )
    return rows


def _factory_blueprints() -> list[dict[str, Any]]:
    return factory_blueprints()


def _logger_registry() -> list[dict[str, Any]]:
    return [
        {
            "logger_id": "process_diff",
            "source_system": "SecureCore",
            "category": "system_security",
            "sensor_class": "process",
            "status": "available",
            "route": "runtime logging window",
            "content_boundary": "metadata only",
            "user_logging_class": "none",
            "user_logging_default": False,
        },
        {
            "logger_id": "network_diff",
            "source_system": "SecureCore",
            "category": "system_security",
            "sensor_class": "network",
            "status": "available",
            "route": "runtime logging window",
            "content_boundary": "endpoint metadata only",
            "user_logging_class": "none",
            "user_logging_default": False,
        },
        {
            "logger_id": "open_window_diff",
            "source_system": "SecureCore",
            "category": "workspace_context",
            "sensor_class": "window",
            "status": "available",
            "route": "runtime logging window",
            "content_boundary": "window metadata only",
            "user_logging_class": "metadata_shape",
            "user_logging_default": False,
        },
        {
            "logger_id": "selected_eventlog",
            "source_system": "SecureCore",
            "category": "system_security",
            "sensor_class": "eventlog",
            "status": "available",
            "route": "runtime logging window",
            "content_boundary": "Windows event metadata only",
            "user_logging_class": "none",
            "user_logging_default": False,
        },
        {
            "logger_id": "user_aura_shape",
            "source_system": "AnchorWorks",
            "category": "cognition_shape",
            "sensor_class": "user_shape",
            "status": "planned_gated",
            "route": "paired encrypted user vault",
            "content_boundary": "non-replayable derived shape only",
            "user_logging_class": "creepy_user_logging",
            "user_logging_default": False,
        },
        {
            "logger_id": "truevision_worker_state",
            "source_system": "TrueVision",
            "category": "worker_diagnostics",
            "sensor_class": "visual_state_worker",
            "status": "planned_gated",
            "route": "worker diagnostic feed",
            "content_boundary": "worker state packets, no desktop surveillance",
            "user_logging_class": "worker_state",
            "user_logging_default": False,
        },
        {
            "logger_id": "trueaudio_timing_state",
            "source_system": "TrueVision",
            "category": "media_timing",
            "sensor_class": "audio_state",
            "status": "parked",
            "route": "TrueAudio side lane",
            "content_boundary": "audio timing/state receipts only",
            "user_logging_class": "media_state",
            "user_logging_default": False,
        },
    ]


def _system_routes() -> list[dict[str, Any]]:
    return [
        {"path": "/api/ops/dashboard", "method": "GET", "purpose": "read runtime dashboard metadata"},
        {"path": "/api/ops/catalog", "method": "GET", "purpose": "read agent/capability/recipe catalog"},
        {"path": "/api/ops/toolbox", "method": "GET", "purpose": "read tool/logger/worker inventory"},
        {"path": "/api/ops/truevision", "method": "GET", "purpose": "read SecureCore-visible TrueVision boundaries"},
        {"path": "/api/ops/warmup", "method": "GET", "purpose": "run read-only startup checks"},
        {"path": "/api/ops/runtime/latest", "method": "GET", "purpose": "read latest runtime proof status"},
        {"path": "/api/ops/away-watch/reports", "method": "GET", "purpose": "list Away Watch reports"},
        {"path": "/api/ops/away-watch/report", "method": "GET", "purpose": "read one Away Watch report"},
        {"path": "/api/ops/harness", "method": "GET", "purpose": "read deterministic harness map"},
        {"path": "/api/ops/harness/choose", "method": "POST", "purpose": "classify a request without executing it"},
    ]
