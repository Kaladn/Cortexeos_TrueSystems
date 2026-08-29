"""FastAPI router for the machine observability system.

7 endpoints for sensor catalog, privacy policy, reading, and resolution.
All read-only — no system configuration or sensor writes.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from observe.catalog import get_catalog, get_categories
from observe.policy import load_policy, save_policy, is_allowed, filter_catalog
from observe.reader import read_sensors, read_with_window
from observe.resolver import resolve
from observe.audit import log_read

router = APIRouter(prefix="/api/observe", tags=["observe"])


# ── Request / Response models ──────────────────────────────────

class ReadRequest(BaseModel):
    ids: List[str]
    window_sec: int = 0   # 0 = single snapshot, >0 = aggregated window
    samples: int = 3


class ResolveRequest(BaseModel):
    question: str
    context: Optional[Dict[str, Any]] = None


class PolicyPatch(BaseModel):
    disabled_sensor_ids: Optional[List[str]] = None
    disabled_categories: Optional[List[str]] = None
    disabled_sources: Optional[List[str]] = None
    notes: Optional[str] = None


# ── Endpoints ──────────────────────────────────────────────────

@router.get("/sensors")
async def sensors_list():
    """Return the full sensor catalog with metadata."""
    catalog = get_catalog()
    return {"sensors": catalog, "count": len(catalog)}


@router.get("/sensors/categories")
async def sensors_categories():
    """Return sensor counts grouped by category."""
    return {"categories": get_categories()}


@router.post("/sensors/refresh")
async def sensors_refresh():
    """Rebuild the sensor catalog from scratch."""
    catalog = get_catalog(force_refresh=True)
    return {"sensors": catalog, "count": len(catalog)}


@router.get("/policy")
async def policy_get():
    """Return the current privacy deny-list policy."""
    return load_policy()


@router.patch("/policy")
async def policy_update(patch: PolicyPatch):
    """Update the privacy policy. Merges provided fields."""
    current = load_policy()
    if patch.disabled_sensor_ids is not None:
        current["disabled_sensor_ids"] = patch.disabled_sensor_ids
    if patch.disabled_categories is not None:
        current["disabled_categories"] = patch.disabled_categories
    if patch.disabled_sources is not None:
        current["disabled_sources"] = patch.disabled_sources
    if patch.notes is not None:
        current["notes"] = patch.notes
    saved = save_policy(current)
    return saved


@router.post("/resolve")
async def observe_resolve(req: ResolveRequest):
    """Resolve a natural language question to sensor IDs.

    Returns requested, allowed, and blocked sensor IDs.
    """
    catalog = get_catalog()
    policy = load_policy()
    result = resolve(req.question, catalog, policy)
    return result


@router.post("/read")
async def observe_read(req: ReadRequest):
    """Read live sensor values for the given IDs.

    Respects the privacy policy — blocked sensors are listed separately.
    Optionally aggregates over a time window.
    """
    catalog = get_catalog()
    policy = load_policy()
    catalog_map = {s["id"]: s for s in catalog}

    # Split requested IDs into allowed and blocked
    allowed_ids = []
    blocked_ids = []
    for sid in req.ids:
        sensor = catalog_map.get(sid)
        if sensor is None:
            blocked_ids.append(sid)
        elif not is_allowed(sensor, policy):
            blocked_ids.append(sid)
        else:
            allowed_ids.append(sid)

    # Read only allowed sensors
    if req.window_sec > 0:
        readings = read_with_window(
            allowed_ids, catalog,
            window_sec=req.window_sec, samples=req.samples,
        )
    else:
        readings = read_sensors(allowed_ids, catalog)

    # Audit
    log_read(
        requester="api",
        sensor_ids=allowed_ids,
        window_sec=req.window_sec,
        readings_count=len(readings),
    )

    return {
        "readings": readings,
        "allowed": allowed_ids,
        "blocked": blocked_ids,
        "count": len(readings),
    }
