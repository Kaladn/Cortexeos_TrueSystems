"""Config, snapshot, routing, providers, and inference profile routes."""
from __future__ import annotations
import copy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from fastapi import APIRouter, HTTPException

from bridges.state import BridgeState, LOGGER, VERSION
from bridges.models import SnapshotRequest, RollbackRequest, ConfigUpdateRequest
from bridges.helpers import _validate_path_within
from bridges.ws_manager import WebSocketManager
from security.data_paths import STATE_DIR


def make_router(state: BridgeState, ws_manager: WebSocketManager) -> APIRouter:
    router = APIRouter()

    # ── Dev Routing imports ─────────────────────────────────────
    from routing.config import (
        load_routing_profile,
        validate_profile as _rt_validate,
        list_named_profiles as _rt_list,
        load_named_profile as _rt_load_named,
        save_named_profile as _rt_save_named,
        DEFAULTS as _RT_DEFAULTS,
    )

    # ── Provider Key Management imports ────────────────────────
    from security.provider_keys import (
        list_providers as _prov_list,
        get_provider_status as _prov_status,
        save_provider_key as _prov_save,
        delete_provider_key as _prov_delete,
        get_provider_key as _prov_get_key,
        _load_all as _prov_load_all,
        _save_all as _prov_save_all,
        VALID_PROVIDERS as _prov_valid,
    )
    from security.provider_test import TESTERS as _prov_testers
    from security.inference_profiles import (
        load_all_profiles as _inf_load_all,
        load_profile as _inf_load,
        save_profile as _inf_save,
    )
    from security.identity_profiles import (
        load_all_profiles as _ident_load_all,
        load_profile as _ident_load,
        save_profile as _ident_save,
    )

    # ── LakeSpeak config defaults ───────────────────────────────
    _LAKESPEAK_CFG_DEFAULTS: Dict[str, Any] = {
        "enabled": True,
        "chunk_size": 512,
        "chunk_overlap": 64,
        "bm25_topk": 20,
        "dense_topk": 20,
        "final_topk": 5,
        "bm25_weight": 0.4,
        "dense_weight": 0.6,
        "anchor_weight": 0.3,
        "min_score": 0.01,
        "dense_model": "all-MiniLM-L6-v2",
        "dense_enabled": True,
        "ollama_timeout": 120.0,
    }
    _LAKESPEAK_EDITABLE = {
        "chunk_size": int, "chunk_overlap": int,
        "bm25_topk": int, "dense_topk": int, "final_topk": int,
        "bm25_weight": float, "dense_weight": float, "anchor_weight": float,
        "min_score": float, "dense_enabled": bool, "ollama_timeout": float,
    }

    # ── Extra system config fields ──────────────────────────────
    _SYSEXTRA_FIELDS = {
        "log_level": (str, ["debug", "info", "warning", "error"]),
        "clearbox_node_require_hello": (bool, None),
        "network_require_auth": (bool, None),
    }

    # ── /api/config GET / PATCH ─────────────────────────────────

    @router.get("/api/config")
    async def get_config():
        return {"config": state.bridge.get_config(), "version": VERSION}

    @router.patch("/api/config")
    async def patch_config(body: ConfigUpdateRequest):
        payload = cast(Dict[str, Any], body.dict(exclude_none=True))
        if not payload:
            raise HTTPException(status_code=400, detail="No config fields provided")
        result = await state.update_config(payload)
        await ws_manager.broadcast({
            "evt": "config-update",
            "config": result["config"],
            "version": VERSION,
        })
        return result

    # ── /api/snapshot, /api/rollback, /api/snapshots ────────────

    @router.post("/api/snapshot")
    async def post_snapshot(body: SnapshotRequest):
        await state.ensure_bridge_loaded("snapshot")
        path = state.bridge.create_snapshot(body.tag)
        await ws_manager.broadcast({
            "evt": "snapshot",
            "path": str(path),
            "version": VERSION,
        })
        return {"path": str(path), "version": VERSION}

    @router.post("/api/rollback")
    async def post_rollback(body: RollbackRequest):
        await state.ensure_bridge_loaded("rollback")
        snapshot_path = Path(body.path)
        # Snapshots must live within STATE_DIR
        _validate_path_within(snapshot_path, STATE_DIR, "snapshot path")
        stats = await state.rollback_snapshot(snapshot_path)
        await ws_manager.broadcast({
            "evt": "rollback",
            "path": str(snapshot_path),
            "stats": stats,
            "version": VERSION,
        })
        return stats

    @router.get("/api/snapshots")
    async def list_snapshots():
        """List available lexicon snapshots, newest first."""
        snapshots = []
        # Check both governed (state/snapshots) and legacy (reports/snapshots) paths
        search_dirs = [state.bridge._snapshot_folder()]
        try:
            from security.storage_layout import STATE_DIR
            governed_snap = STATE_DIR / "snapshots"
            if governed_snap != search_dirs[0]:
                search_dirs.append(governed_snap)
        except ImportError:
            pass
        seen = set()
        for snap_dir in search_dirs:
            if not snap_dir.exists():
                continue
            for d in snap_dir.iterdir():
                if d.is_dir() and (d / "lexicon.json").exists() and d.name not in seen:
                    seen.add(d.name)
                    snapshots.append({
                        "name": d.name,
                        "path": str(d),
                        "created": d.stat().st_mtime,
                    })
        snapshots.sort(key=lambda s: s["created"], reverse=True)
        return {"snapshots": snapshots[:20]}

    # ── /api/routing/* ──────────────────────────────────────────

    @router.get("/api/routing/profile")
    async def routing_get_profile():
        """Return the active routing profile."""
        return load_routing_profile(state.config.get("routing"))

    @router.post("/api/routing/profile")
    async def routing_update_profile(profile: dict):
        """Update the active routing profile. Validates first."""
        ok, err = _rt_validate(profile)
        if not ok:
            raise HTTPException(status_code=400, detail=err)
        await state.write_config({"routing": profile})
        return {"ok": True, "profile": profile.get("name")}

    @router.get("/api/routing/profiles")
    async def routing_list_profiles():
        """List all saved named profiles."""
        return {"profiles": _rt_list()}

    @router.post("/api/routing/profiles/{name}")
    async def routing_save_named(name: str):
        """Save the current active profile as a named profile."""
        active = load_routing_profile(state.config.get("routing"))
        ok, err = _rt_save_named(name, active)
        if not ok:
            raise HTTPException(status_code=400, detail=err)
        return {"ok": True, "name": name}

    @router.post("/api/routing/profiles/{name}/activate")
    async def routing_activate_named(name: str):
        """Load a named profile as the active profile."""
        profile = _rt_load_named(name)
        if profile is None:
            raise HTTPException(status_code=404, detail=f"Profile '{name}' not found")
        ok, err = _rt_validate(profile)
        if not ok:
            raise HTTPException(status_code=400, detail=f"Saved profile invalid: {err}")
        await state.write_config({"routing": profile})
        return {"ok": True, "name": name, "profile": profile}

    @router.post("/api/routing/reset")
    async def routing_reset():
        """Restore the default routing profile."""
        defaults = copy.deepcopy(_RT_DEFAULTS)
        await state.write_config({"routing": defaults})
        return {"ok": True, "profile": "default"}

    @router.get("/api/routing/dev-mode")
    async def routing_get_dev_mode():
        """Check if dev routing panel is enabled."""
        routing = state.config.get("routing", {})
        return {"enabled": routing.get("dev_mode", False)}

    @router.post("/api/routing/dev-mode")
    async def routing_toggle_dev_mode():
        """Toggle the dev_mode flag."""
        routing = dict(state.config.get("routing", {}))
        routing["dev_mode"] = not routing.get("dev_mode", False)
        await state.write_config({"routing": routing})
        return {"ok": True, "dev_mode": routing["dev_mode"]}

    # ── /api/providers/* ────────────────────────────────────────

    @router.get("/api/providers")
    async def providers_list():
        """List all configured providers with status. Keys never returned."""
        return {"providers": _prov_list()}

    @router.get("/api/providers/{name}")
    async def provider_status(name: str):
        """Get status of a single provider."""
        if name not in _prov_valid:
            raise HTTPException(status_code=404, detail=f"Unknown provider: {name}")
        return _prov_status(name)

    @router.post("/api/providers/{name}/key")
    async def provider_save_key(name: str, body: dict):
        """Save an API key for a provider. Body: {"key": "sk-..."}"""
        if name not in _prov_valid:
            raise HTTPException(status_code=404, detail=f"Unknown provider: {name}")
        key = body.get("key", "").strip()
        if not key:
            raise HTTPException(status_code=400, detail="Key is required")
        if name == "openai" and not key.startswith("sk-"):
            raise HTTPException(status_code=400, detail="OpenAI keys start with 'sk-'")
        if name == "claude" and not key.startswith("sk-ant-"):
            raise HTTPException(status_code=400, detail="Claude keys start with 'sk-ant-'")
        if name == "gemini" and not key.startswith("AIza"):
            raise HTTPException(status_code=400, detail="Gemini keys typically start with 'AIza'")
        result = _prov_save(name, key)
        LOGGER.info(f"Provider key saved: {name}")
        return result

    @router.delete("/api/providers/{name}/key")
    async def provider_delete_key(name: str):
        """Remove a provider's API key."""
        if name not in _prov_valid:
            raise HTTPException(status_code=404, detail=f"Unknown provider: {name}")
        result = _prov_delete(name)
        LOGGER.info(f"Provider key removed: {name}")
        return result

    @router.post("/api/providers/{name}/test")
    async def provider_test(name: str):
        """Test connection to a provider using the stored key."""
        if name not in _prov_valid:
            raise HTTPException(status_code=404, detail=f"Unknown provider: {name}")
        key = _prov_get_key(name)
        if not key:
            raise HTTPException(status_code=400, detail=f"No key configured for {name}")
        tester = _prov_testers.get(name)
        if not tester:
            raise HTTPException(status_code=500, detail=f"No tester for {name}")
        ok, message = await tester(key)
        # Update test timestamp in storage
        data = _prov_load_all()
        if name in data:
            data[name]["last_tested"] = datetime.now(timezone.utc).isoformat()
            data[name]["test_ok"] = ok
            _prov_save_all(data)
        return {"ok": ok, "message": message, "provider": name}

    # ── /api/inference/profiles ─────────────────────────────────

    @router.get("/api/inference/profiles")
    async def inference_profiles_list():
        """Get all per-model inference profiles."""
        return {"profiles": _inf_load_all()}

    @router.get("/api/inference/profiles/{model:path}")
    async def inference_profile_get(model: str):
        """Get inference profile for a specific model."""
        profile = _inf_load(model)
        if profile is None:
            return {"model": model, "profile": None, "using_defaults": True}
        return {"model": model, "profile": profile, "using_defaults": False}

    @router.post("/api/inference/profiles/{model:path}")
    async def inference_profile_save(model: str, body: dict):
        """Save inference profile for a specific model."""
        result = _inf_save(model, body)
        LOGGER.info(f"Inference profile saved: {model}")
        return {"ok": True, "model": model, "profile": result}

    # ── /api/identity/profiles ───────────────────────────────

    @router.get("/api/identity/profiles")
    async def identity_profiles_list():
        """Get all per-model identity profiles."""
        return {"profiles": _ident_load_all()}

    @router.get("/api/identity/profiles/{model:path}")
    async def identity_profile_get(model: str):
        """Get identity profile for a specific model."""
        profile = _ident_load(model)
        if profile is None:
            return {"model": model, "profile": None, "using_defaults": True}
        return {"model": model, "profile": profile, "using_defaults": False}

    @router.post("/api/identity/profiles/{model:path}")
    async def identity_profile_save(model: str, body: dict):
        """Save identity profile for a specific model."""
        result = _ident_save(model, body)
        LOGGER.info(f"Identity profile saved: {model}")
        return {"ok": True, "model": model, "profile": result}

    # ── /api/plugins/lakespeak/config ──────────────────────────

    @router.get("/api/plugins/lakespeak/config")
    async def lakespeak_get_config():
        """Return current LakeSpeak config (defaults merged with overrides)."""
        section = dict(state.config).get("lakespeak", {})
        return {**_LAKESPEAK_CFG_DEFAULTS, **section}

    @router.patch("/api/plugins/lakespeak/config")
    async def lakespeak_patch_config(body: dict):
        """Update LakeSpeak config in clearbox.config.json['lakespeak']."""
        errors = []
        validated: Dict[str, Any] = {}
        for key, cast_fn in _LAKESPEAK_EDITABLE.items():
            if key not in body:
                continue
            val = body[key]
            try:
                validated[key] = cast_fn(val)
            except (TypeError, ValueError):
                errors.append(f"{key}: expected {cast_fn.__name__}, got {val!r}")
        if errors:
            raise HTTPException(status_code=422, detail={"errors": errors})
        if not validated:
            raise HTTPException(status_code=400, detail="No editable fields provided")
        current_ls = dict(state.config.get("lakespeak", {}))
        current_ls.update(validated)
        await state.write_config({"lakespeak": current_ls})
        return {"ok": True, "lakespeak": {**_LAKESPEAK_CFG_DEFAULTS, **current_ls}}

    # ── /api/config/extra ───────────────────────────────────────

    @router.get("/api/config/extra")
    async def sysextra_get():
        """Return the extra system config fields not covered by /api/config."""
        cfg = dict(state.config)
        return {
            "log_level": cfg.get("log_level", "info"),
            "clearbox_node_require_hello": cfg.get("clearbox_node", {}).get("require_hello", True),
            "network_require_auth": cfg.get("network", {}).get("require_auth", True),
        }

    @router.patch("/api/config/extra")
    async def sysextra_patch(body: dict):
        """Update extra system config fields in clearbox.config.json."""
        errors = []
        config_data = copy.deepcopy(dict(state.config))
        changed = False

        if "log_level" in body:
            val = body["log_level"]
            if val not in ["debug", "info", "warning", "error"]:
                errors.append(f"log_level: must be one of debug/info/warning/error, got {val!r}")
            else:
                config_data["log_level"] = val
                changed = True

        if "clearbox_node_require_hello" in body:
            val = body["clearbox_node_require_hello"]
            if not isinstance(val, bool):
                errors.append(f"clearbox_node_require_hello: expected bool")
            else:
                config_data.setdefault("clearbox_node", {})["require_hello"] = val
                changed = True

        if "network_require_auth" in body:
            val = body["network_require_auth"]
            if not isinstance(val, bool):
                errors.append(f"network_require_auth: expected bool")
            else:
                config_data.setdefault("network", {})["require_auth"] = val
                changed = True

        if errors:
            raise HTTPException(status_code=422, detail={"errors": errors})
        if not changed:
            raise HTTPException(status_code=400, detail="No recognized fields provided")

        await state.write_config(config_data)
        return {"ok": True}

    return router
