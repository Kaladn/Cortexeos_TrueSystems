"""Clearbox AI Security — User-scoped data, DPAPI encryption, Windows Hello auth, governed writes.

Four layers:
1. data_paths     — All user data in %LOCALAPPDATA%\\ClearboxAI (NTFS ACL per-user)
2. secure_storage — DPAPI encryption at rest (tied to Windows user credentials)
3. auth           — WebAuthn / Windows Hello browser authentication + session tokens
4. gateway        — Reader-Writer Gateway: single authority for all filesystem mutations
   directory_law  — Canonical directory structure + boot-time validation
"""
