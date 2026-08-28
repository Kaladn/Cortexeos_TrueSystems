"""USB + Windows Hello pairing endpoints for mobile nodes.

Pairing doctrine:
  - ALL pairing endpoints are loopback-only (127.0.0.1)
  - ALL pairing endpoints require a valid Windows Hello session
  - USB device must be physically connected during pairing
  - Enrollment bundle delivered via USB (ADB push or manual transfer)
  - No mDNS, no QR, no network-discoverable pairing paths

Mounted on the bridge at /api/nodes/pair/...
"""

from __future__ import annotations

import json
import logging
import os
import secrets
import tempfile
import time
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from forest_node.core.session_gate import require_hello_session
from forest_node.core.usb_detect import detect_usb_devices, adb_push_file
from forest_node.core.ed25519_auth import generate_keypair, MobileKeyStore

LOGGER = logging.getLogger("forest.node.pairing")

router = APIRouter(prefix="/api/nodes/pair", tags=["mobile-pairing"])


# -- Loopback-only guard -------------------------------------------------------

def _is_loopback(request: Request) -> bool:
    """Check if request comes from loopback (127.0.0.1 or ::1)."""
    client = request.client
    if not client:
        return False
    host = client.host
    return host in ("127.0.0.1", "::1", "localhost")


def _require_loopback(request: Request):
    """FastAPI dependency: reject non-loopback requests."""
    if not _is_loopback(request):
        return JSONResponse(
            status_code=403,
            content={"error": "Pairing endpoints are loopback-only"}
        )
    return None


# -- Enrollment token store (in-memory, 10min TTL) -----------------------------

_enrollment_tokens: dict = {}  # token -> {"node_id", "public_key", "expires"}
_ENROLLMENT_TTL = 600  # 10 minutes

# Rate limit: max 5 enrollment attempts per minute
_enrollment_attempts: list = []
_RATE_LIMIT_WINDOW = 60
_RATE_LIMIT_MAX = 5


# -- Pending bundles (in-memory, short-lived) -----------------------------------

_pending_bundles: dict = {}  # node_id -> bundle_dict


# -- Key store singleton --------------------------------------------------------

_key_store: Optional[MobileKeyStore] = None


def _get_key_store() -> MobileKeyStore:
    global _key_store
    if _key_store is None:
        from security.data_paths import FOREST_NODE_MOBILE_KEYS
        _key_store = MobileKeyStore(FOREST_NODE_MOBILE_KEYS)
    return _key_store


# -- Models ---------------------------------------------------------------------

class ApproveRequest(BaseModel):
    serial: str
    hello_assertion: Optional[dict] = None  # WebAuthn assertion (if re-verifying)


class EnrollRequest(BaseModel):
    enrollment_token: str
    public_key: str  # base64-encoded Ed25519 public key


# -- Endpoints (loopback + Hello) -----------------------------------------------

@router.get("/usb/detect")
async def detect_devices(
    request: Request,
    _caller: str = Depends(require_hello_session),
):
    """List USB-connected mobile devices."""
    if not _is_loopback(request):
        return JSONResponse(status_code=403, content={"error": "Loopback only"})

    devices = detect_usb_devices()
    return {
        "devices": [
            {
                "serial": d.serial,
                "vendor": d.vendor,
                "model": d.model,
                "platform": d.platform,
                "transport_id": d.transport_id,
            }
            for d in devices
        ],
        "count": len(devices),
    }


@router.post("/usb/approve")
async def approve_pairing(
    request: Request,
    body: ApproveRequest,
    _caller: str = Depends(require_hello_session),
):
    """Approve USB pairing: Hello verified + USB present -> mint enrollment bundle."""
    if not _is_loopback(request):
        return JSONResponse(status_code=403, content={"error": "Loopback only"})

    # Verify USB device is still connected
    devices = detect_usb_devices()
    device = next((d for d in devices if d.serial == body.serial), None)
    if not device:
        return JSONResponse(
            status_code=400,
            content={"error": f"Device {body.serial} not connected via USB"}
        )

    # Generate Ed25519 keypair
    private_key_b64, public_key_b64 = generate_keypair()

    # Create node ID from device serial
    node_id = f"mobile_{device.serial[:16]}"

    # Create one-time enrollment token
    enrollment_token = secrets.token_urlsafe(32)
    _enrollment_tokens[enrollment_token] = {
        "node_id": node_id,
        "public_key": public_key_b64,
        "expires": time.time() + _ENROLLMENT_TTL,
    }

    # Get server URL and cert fingerprint
    try:
        from security.tls import get_cert_fingerprint
        cert_fp = get_cert_fingerprint() or ""
    except Exception:
        cert_fp = ""

    # Determine server URLs: LAN (primary) + Tailscale (remote)
    try:
        from security.tls import _get_local_ips
        local_ips = _get_local_ips()
        server_ip = local_ips[0] if local_ips else "127.0.0.1"
    except Exception:
        server_ip = "127.0.0.1"

    server_urls = [
        {"type": "lan", "bridge": f"https://{server_ip}:5050", "ui": f"https://{server_ip}:8080"},
    ]
    try:
        from security.network import get_remote_urls
        remote = get_remote_urls(bridge_port=5050, ui_port=8080)
        server_urls.extend(remote)
    except Exception:
        pass

    bundle = {
        "node_id": node_id,
        "server_url": f"https://{server_ip}:5050",
        "ui_url": f"https://{server_ip}:8080",
        "server_urls": server_urls,
        "server_cert_fingerprint": cert_fp,
        "ed25519_private_key": private_key_b64,
        "ed25519_public_key": public_key_b64,
        "enrollment_token": enrollment_token,
        "created": int(time.time()),
        "version": 2,
    }

    _pending_bundles[node_id] = bundle

    LOGGER.info("Pairing approved: node=%s, device=%s (%s)",
                node_id, device.model, device.platform)

    return {
        "ok": True,
        "node_id": node_id,
        "device": {
            "serial": device.serial,
            "model": device.model,
            "platform": device.platform,
        },
        "bundle_ready": True,
    }


@router.get("/usb/bundle/{node_id}")
async def download_bundle(
    request: Request,
    node_id: str,
    _caller: str = Depends(require_hello_session),
):
    """Download enrollment bundle JSON for manual USB transfer."""
    if not _is_loopback(request):
        return JSONResponse(status_code=403, content={"error": "Loopback only"})

    bundle = _pending_bundles.get(node_id)
    if not bundle:
        return JSONResponse(status_code=404, content={"error": "No pending bundle"})

    # Write to temp file for download
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix="forest_enroll_",
        delete=False, dir=tempfile.gettempdir(),
    )
    json.dump(bundle, tmp, indent=2)
    tmp.close()

    return FileResponse(
        tmp.name,
        media_type="application/json",
        filename="forest_enroll.json",
    )


@router.post("/usb/push/{node_id}")
async def adb_push_bundle(
    request: Request,
    node_id: str,
    _caller: str = Depends(require_hello_session),
):
    """Push enrollment bundle to Android device via ADB."""
    if not _is_loopback(request):
        return JSONResponse(status_code=403, content={"error": "Loopback only"})

    bundle = _pending_bundles.get(node_id)
    if not bundle:
        return JSONResponse(status_code=404, content={"error": "No pending bundle"})

    # Extract serial from node_id
    serial = node_id.replace("mobile_", "")

    # Write bundle to temp file
    tmp_path = os.path.join(tempfile.gettempdir(), "forest_enroll.json")
    with open(tmp_path, "w") as f:
        json.dump(bundle, f, indent=2)

    # Push via ADB
    success = adb_push_file(serial, tmp_path, "/sdcard/Download/ForestAI/forest_enroll.json")

    # Clean up temp file
    try:
        os.unlink(tmp_path)
    except Exception:
        pass

    if success:
        return {"ok": True, "message": f"Bundle pushed to {serial}"}
    else:
        return JSONResponse(
            status_code=500,
            content={"error": "ADB push failed -- is the device still connected?"}
        )


# -- Public endpoint: enrollment (remote-accessible, one-time) ------------------

@router.post("/enroll", dependencies=[])
async def enroll_mobile(body: EnrollRequest):
    """Phone submits enrollment token + public key to complete pairing.

    This endpoint is intentionally NOT loopback-only -- the phone calls it
    over the network after importing the bundle.
    Rate-limited: max 5 attempts per minute.
    """
    # Rate limiting
    now = time.time()
    _enrollment_attempts[:] = [t for t in _enrollment_attempts if now - t < _RATE_LIMIT_WINDOW]
    if len(_enrollment_attempts) >= _RATE_LIMIT_MAX:
        return JSONResponse(status_code=429, content={"error": "Rate limited"})
    _enrollment_attempts.append(now)

    # Validate token
    entry = _enrollment_tokens.get(body.enrollment_token)
    if not entry:
        return JSONResponse(status_code=401, content={"error": "Invalid enrollment token"})

    if time.time() > entry["expires"]:
        _enrollment_tokens.pop(body.enrollment_token, None)
        return JSONResponse(status_code=401, content={"error": "Enrollment token expired"})

    node_id = entry["node_id"]
    expected_pubkey = entry["public_key"]

    # Verify the phone sent the correct public key
    if body.public_key != expected_pubkey:
        return JSONResponse(status_code=401, content={"error": "Public key mismatch"})

    # Store public key in DPAPI-encrypted allowlist
    store = _get_key_store()
    store.store(node_id, body.public_key, device_info={"enrolled_at": int(time.time())})

    # Clean up
    _enrollment_tokens.pop(body.enrollment_token, None)
    _pending_bundles.pop(node_id, None)

    LOGGER.info("Mobile node enrolled: %s", node_id)

    return {
        "ok": True,
        "node_id": node_id,
        "message": "Mobile node enrolled successfully",
    }


# -- Management endpoints (loopback + Hello) ------------------------------------

@router.get("/devices")
async def list_paired_devices(
    request: Request,
    _caller: str = Depends(require_hello_session),
):
    """List all paired mobile devices."""
    if not _is_loopback(request):
        return JSONResponse(status_code=403, content={"error": "Loopback only"})

    store = _get_key_store()
    nodes = store.list_nodes()
    return {"devices": nodes, "count": len(nodes)}


@router.delete("/devices/{node_id}")
async def unpair_device(
    request: Request,
    node_id: str,
    _caller: str = Depends(require_hello_session),
):
    """Unpair a mobile device (remove its public key)."""
    if not _is_loopback(request):
        return JSONResponse(status_code=403, content={"error": "Loopback only"})

    store = _get_key_store()
    removed = store.remove(node_id)
    if removed:
        return {"ok": True, "message": f"Unpaired {node_id}"}
    else:
        return JSONResponse(status_code=404, content={"error": "Node not found"})
