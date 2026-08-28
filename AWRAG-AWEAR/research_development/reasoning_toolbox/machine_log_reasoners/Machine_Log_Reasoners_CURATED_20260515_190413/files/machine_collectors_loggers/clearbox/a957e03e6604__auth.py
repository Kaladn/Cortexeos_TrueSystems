"""WebAuthn / Windows Hello authentication + session management.

Flow:
  1. First visit → no credential exists → /api/auth/register/begin → Windows Hello enrollment
  2. Every session → /api/auth/login/begin → Windows Hello → session cookie (8h TTL)
  3. Middleware checks session on every protected request

Credential storage:
  %LOCALAPPDATA%\\ClearboxAI\\auth\\credentials.json  (DPAPI-encrypted)

Session storage:
  DPAPI-encrypted on disk (survives restarts) + in-memory dict for fast lookups.
  File: CLEARBOX_ROOT/runtime/cache/sessions.json (DPAPI V1 whole-file encryption).
  Bound to the Windows user account — another user or another machine cannot decrypt.

Requirements:
  pip install webauthn
"""

import json
import logging
import secrets
import time
from pathlib import Path
from threading import RLock
from typing import Optional

from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    ResidentKeyRequirement,
    PublicKeyCredentialDescriptor,
    AuthenticatorAttachment,
    RegistrationCredential,
    AuthenticationCredential,
    AuthenticatorAttestationResponse,
    AuthenticatorAssertionResponse,
)
from webauthn.helpers import bytes_to_base64url, base64url_to_bytes

from .data_paths import AUTH_DIR, SESSIONS_DIR, CLEARBOX_CONFIG_PATH
from .secure_storage import secure_json_load, secure_json_dump

_log = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────
RP_ID = "localhost"
RP_NAME = "Clearbox AI Studio"
try:
    _auth_tls = secure_json_load(CLEARBOX_CONFIG_PATH).get("server", {}).get("tls", False)
except Exception:
    _auth_tls = False
ORIGIN = f"{'https' if _auth_tls else 'http'}://localhost:8080"
SESSION_TTL = 8 * 60 * 60  # 8 hours in seconds

CREDENTIALS_PATH = AUTH_DIR / "credentials.json"
SESSIONS_FILE = SESSIONS_DIR / "sessions.json"

# ── In-memory state ────────────────────────────────────────────
# Active sessions:  {token: {"created": timestamp, "user_id": str}}
_sessions: dict[str, dict] = {}
_sessions_lock = RLock()

# Pending challenges (short-lived):  {challenge_b64: {"type": "register"|"login", "created": timestamp}}
_pending_challenges: dict[str, dict] = {}


# ── Session persistence (DPAPI-encrypted on disk) ─────────────

def _persist_sessions() -> None:
    """Write current sessions to DPAPI-encrypted file (atomic write)."""
    try:
        tmp = SESSIONS_FILE.with_suffix(".tmp")
        secure_json_dump(tmp, _sessions)
        tmp.replace(SESSIONS_FILE)
    except Exception as exc:
        _log.warning("Failed to persist sessions to disk: %s", exc)


def _load_sessions() -> None:
    """Restore sessions from DPAPI-encrypted file, filtering expired entries."""
    if not SESSIONS_FILE.exists():
        return
    try:
        data = secure_json_load(SESSIONS_FILE)
        if not isinstance(data, dict):
            _log.warning("Session file has unexpected format — starting empty")
            return
        now = time.time()
        for token, session in list(data.items()):
            if not isinstance(session, dict):
                continue
            if not isinstance(session.get("user_id"), str):
                continue
            if now - session.get("created", 0) > SESSION_TTL:
                continue
            _sessions[token] = session
        _log.info("Restored %d session(s) from disk", len(_sessions))
    except Exception as exc:
        _log.warning("Failed to load sessions from disk — starting empty: %s", exc)


# ── Credential persistence ────────────────────────────────────

def _load_credentials() -> list[dict]:
    """Load stored WebAuthn credentials from DPAPI-encrypted file."""
    if not CREDENTIALS_PATH.exists():
        return []
    try:
        data = secure_json_load(CREDENTIALS_PATH)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_credentials(creds: list[dict]) -> None:
    """Save WebAuthn credentials to DPAPI-encrypted file."""
    secure_json_dump(CREDENTIALS_PATH, creds)


def has_registered_credential() -> bool:
    """Check if at least one credential is registered."""
    return len(_load_credentials()) > 0


# ── Registration (first-time setup) ───────────────────────────

def begin_registration() -> dict:
    """Generate WebAuthn registration options for Windows Hello.

    Returns JSON-serializable options for navigator.credentials.create().
    """
    user_id = secrets.token_bytes(32)

    options = generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=user_id,
        user_name="clearbox-operator",
        user_display_name="Clearbox Operator",
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
    )

    # Store challenge for verification
    challenge_b64 = bytes_to_base64url(options.challenge)
    _pending_challenges[challenge_b64] = {
        "type": "register",
        "created": time.time(),
        "user_id": bytes_to_base64url(user_id),
    }

    return json.loads(options_to_json(options))


def complete_registration(credential_json: dict) -> dict:
    """Verify registration response and store credential.

    Args:
        credential_json: The credential object from navigator.credentials.create()

    Returns:
        {"ok": True, "message": "..."} on success

    Raises:
        ValueError on verification failure
    """
    credential = RegistrationCredential(
        id=credential_json["id"],
        raw_id=base64url_to_bytes(credential_json["rawId"]),
        response=AuthenticatorAttestationResponse(
            client_data_json=base64url_to_bytes(credential_json["response"]["clientDataJSON"]),
            attestation_object=base64url_to_bytes(credential_json["response"]["attestationObject"]),
        ),
        type=credential_json.get("type", "public-key"),
    )

    # Extract the challenge the browser actually used from clientDataJSON,
    # then look it up directly. Avoids mismatch when the user clicked the
    # button multiple times and several challenges are pending.
    try:
        client_data = json.loads(
            base64url_to_bytes(credential_json["response"]["clientDataJSON"])
        )
        challenge_key = client_data.get("challenge", "")
    except Exception:
        challenge_key = ""

    challenge_entry = _pending_challenges.get(challenge_key)
    if not challenge_entry or challenge_entry.get("type") != "register":
        raise ValueError("No pending registration challenge")

    try:
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(challenge_key),
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
        )
    except Exception as e:
        raise ValueError(f"Registration verification failed: {e}")
    finally:
        _pending_challenges.pop(challenge_key, None)

    # Store credential
    creds = _load_credentials()
    creds.append({
        "credential_id": bytes_to_base64url(verification.credential_id),
        "public_key": bytes_to_base64url(verification.credential_public_key),
        "sign_count": verification.sign_count,
        "user_id": challenge_entry["user_id"],
        "created_at": time.time(),
    })
    _save_credentials(creds)

    return {"ok": True, "message": "Windows Hello credential registered"}


# ── Authentication (every session) ────────────────────────────

def begin_login() -> dict:
    """Generate WebAuthn authentication options.

    Returns JSON-serializable options for navigator.credentials.get().
    """
    creds = _load_credentials()
    if not creds:
        raise ValueError("No credentials registered. Complete setup first.")

    allow_credentials = [
        PublicKeyCredentialDescriptor(
            id=base64url_to_bytes(c["credential_id"]),
        )
        for c in creds
    ]

    options = generate_authentication_options(
        rp_id=RP_ID,
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.REQUIRED,
    )

    challenge_b64 = bytes_to_base64url(options.challenge)
    _pending_challenges[challenge_b64] = {
        "type": "login",
        "created": time.time(),
    }

    return json.loads(options_to_json(options))


def complete_login(credential_json: dict) -> str:
    """Verify authentication response and issue session token.

    Args:
        credential_json: The credential object from navigator.credentials.get()

    Returns:
        Session token string (UUID-style)

    Raises:
        ValueError on verification failure
    """
    resp = credential_json["response"]
    credential = AuthenticationCredential(
        id=credential_json["id"],
        raw_id=base64url_to_bytes(credential_json["rawId"]),
        response=AuthenticatorAssertionResponse(
            client_data_json=base64url_to_bytes(resp["clientDataJSON"]),
            authenticator_data=base64url_to_bytes(resp["authenticatorData"]),
            signature=base64url_to_bytes(resp["signature"]),
            user_handle=base64url_to_bytes(resp["userHandle"]) if resp.get("userHandle") else None,
        ),
        type=credential_json.get("type", "public-key"),
    )

    creds = _load_credentials()
    cred_id_b64 = bytes_to_base64url(credential.raw_id)

    # Find matching stored credential
    stored = None
    stored_idx = None
    for i, c in enumerate(creds):
        if c["credential_id"] == cred_id_b64:
            stored = c
            stored_idx = i
            break

    if not stored:
        raise ValueError("Unknown credential")

    # Extract the challenge the browser actually used from clientDataJSON,
    # then look it up directly to avoid stale-challenge mismatches.
    try:
        login_client_data = json.loads(
            base64url_to_bytes(resp["clientDataJSON"])
        )
        challenge_key = login_client_data.get("challenge", "")
    except Exception:
        challenge_key = ""

    challenge_entry = _pending_challenges.get(challenge_key)
    if not challenge_entry or challenge_entry.get("type") != "login":
        raise ValueError("No pending login challenge")

    try:
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=base64url_to_bytes(challenge_key),
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            credential_public_key=base64url_to_bytes(stored["public_key"]),
            credential_current_sign_count=stored["sign_count"],
        )
    except Exception as e:
        raise ValueError(f"Authentication failed: {e}")
    finally:
        _pending_challenges.pop(challenge_key, None)

    # Update sign count
    creds[stored_idx]["sign_count"] = verification.new_sign_count
    _save_credentials(creds)

    # Issue session token
    token = secrets.token_urlsafe(32)
    with _sessions_lock:
        _sessions[token] = {
            "created": time.time(),
            "user_id": stored.get("user_id", "operator"),
        }
        _cleanup_sessions()
        _persist_sessions()

    return token


# ── Session management ─────────────────────────────────────────

def validate_session(token: Optional[str]) -> bool:
    """Check if a session token is valid and not expired."""
    if not token:
        return False
    session = _sessions.get(token)
    if not session:
        return False
    if time.time() - session["created"] > SESSION_TTL:
        with _sessions_lock:
            _sessions.pop(token, None)
            _persist_sessions()
        return False
    return True


def revoke_session(token: str) -> None:
    """Invalidate a session token."""
    with _sessions_lock:
        _sessions.pop(token, None)
        _persist_sessions()


def _cleanup_sessions() -> None:
    """Remove expired sessions."""
    now = time.time()
    expired = [k for k, v in _sessions.items() if now - v["created"] > SESSION_TTL]
    for k in expired:
        _sessions.pop(k, None)

    # Also clean old challenges (> 5 minutes)
    old_challenges = [k for k, v in _pending_challenges.items() if now - v["created"] > 300]
    for k in old_challenges:
        _pending_challenges.pop(k, None)


# ── Restore sessions on module load ──────────────────────────
_load_sessions()
