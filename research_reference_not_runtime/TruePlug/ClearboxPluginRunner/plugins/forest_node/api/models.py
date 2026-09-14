"""Forest Node API -- Pydantic request/response models.

All response fields have defaults -- serialization never crashes.
Error shape is consistent: Optional[Dict[str, Any]].
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# -- Discovery & Node Info ------------------------------------------------

class NodeInfo(BaseModel):
    """A single discovered or paired node."""
    node_id: str = ""
    hostname: str = ""
    ip: str = ""
    port: int = 5052
    caps_summary: Dict[str, Any] = {}
    pairing_state: str = "unpaired"  # unpaired | pending | paired | rejected
    pubkey_fingerprint: str = ""
    last_seen: float = 0.0


class NodeListResponse(BaseModel):
    nodes: List[NodeInfo] = []
    error: Optional[Dict[str, Any]] = None


class NodeStatusResponse(BaseModel):
    version: str = ""
    enabled: bool = False
    node_count: int = 0
    paired_count: int = 0
    local_node_id: str = ""
    caps: Dict[str, Any] = {}
    error: Optional[Dict[str, Any]] = None


# -- Registration (Phase 2 — manual add by IP:port) -----------------------

class RegisterRequest(BaseModel):
    """Register a remote node by IP:port."""
    ip: str
    port: int = 5052
    nickname: str = ""


class RegisterResponse(BaseModel):
    ok: bool = False
    node: Optional[NodeInfo] = None
    error: Optional[Dict[str, Any]] = None


class RemoveNodeRequest(BaseModel):
    node_id: str


# -- File Access (Phase 3A) -----------------------------------------------

class FileListRequest(BaseModel):
    """Request to list files on a remote node."""
    node_id: str
    path: str = ""


class FileEntry(BaseModel):
    """A single file or directory entry."""
    name: str = ""
    is_dir: bool = False
    size: int = 0
    modified: float = 0.0
    is_junction: bool = False
    traversable: bool = True


class FileListResponse(BaseModel):
    entries: List[FileEntry] = []
    path: str = ""
    node_id: str = ""
    error: Optional[Dict[str, Any]] = None


class FileReadRequest(BaseModel):
    """Request to read a file from a remote node."""
    node_id: str
    path: str


class FileWriteRequest(BaseModel):
    """Request to write a file on a remote node."""
    node_id: str
    path: str
    content_b64: str  # base64-encoded file content


class FileMkdirRequest(BaseModel):
    """Request to create a directory on a remote node."""
    node_id: str
    path: str


class FileDeleteRequest(BaseModel):
    """Request to delete a file or empty directory on a remote node."""
    node_id: str
    path: str


class FileWriteResponse(BaseModel):
    ok: bool = False
    path: str = ""
    size: int = 0
    node_id: str = ""
    error: Optional[Dict[str, Any]] = None


class FileAccessModeRequest(BaseModel):
    """Request to change file access mode on a remote node."""
    node_id: str
    mode: str = "locked"      # locked | allowlist | full
    ttl_s: int = 300
    share_write: bool = False


class FileAccessModeResponse(BaseModel):
    mode: str = "locked"
    share_write: bool = False
    expires_at: float = 0.0
    allowlist_roots: List[str] = []
    full_requires_auth: bool = True
    node_id: str = ""
    error: Optional[Dict[str, Any]] = None


# -- Pairing (Phase 3B) ---------------------------------------------------

class PairRequest(BaseModel):
    node_id: str
    secret_hex: str = ""  # 64-char hex string (32 bytes)


class UnpairRequest(BaseModel):
    node_id: str


class PairResponse(BaseModel):
    pairing_state: str = ""
    node_id: str = ""
    error: Optional[Dict[str, Any]] = None


