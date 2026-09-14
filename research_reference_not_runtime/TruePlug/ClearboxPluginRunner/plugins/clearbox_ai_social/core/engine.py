from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List
import base64
import hashlib
import json
import sqlite3
import threading
import time

from plugins.clearbox_ai_social.config import CONFIG


@dataclass
class IdentityState:
    node_id: str = ""
    public_key_pem: str = ""


class ClearboxAISocialEngine:
    """
    Lean MVP engine:
    - persistent identity
    - signed profile
    - signed plugin listings
    - local JSON/JSONL + SQLite index
    - manual peer sync stub

    No recommendations, no global ranking, no public discovery.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized = False
        self._identity = IdentityState()
        self._db_path = CONFIG.marketplace_dir / "index.db"
        self._profile_path = CONFIG.profile_dir / "my_profile.json"
        self._listings_path = CONFIG.marketplace_dir / "my_listings.jsonl"

    # -------------------------
    # lifecycle
    # -------------------------

    def ensure_initialized(self) -> None:
        with self._lock:
            if self._initialized:
                return

            self._ensure_dirs()
            self._load_or_create_identity()
            self._init_db()
            self._initialized = True

    def close(self) -> None:
        # Reserved for future cleanup hooks if needed.
        pass

    # -------------------------
    # status / identity
    # -------------------------

    def status(self) -> Dict[str, Any]:
        self.ensure_initialized()
        return {
            "ok": True,
            "message": "ready",
            "initialized": self._initialized,
            "plugin_id": CONFIG.plugin_id,
            "version": "0.1.0",
            "node_id": self._identity.node_id,
            "features": {
                "profile": CONFIG.enable_profile,
                "listings": CONFIG.enable_listings,
                "manual_sync": CONFIG.enable_manual_sync,
            },
        }

    def get_identity(self) -> Dict[str, Any]:
        self.ensure_initialized()
        return {
            "ok": True,
            "message": "identity loaded",
            "node_id": self._identity.node_id,
            "public_key_pem": self._identity.public_key_pem,
        }

    # -------------------------
    # profile
    # -------------------------

    def save_profile(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.ensure_initialized()
        clean = {
            "display_name": payload.get("display_name", "").strip(),
            "bio": payload.get("bio", "").strip(),
            "interests": list(payload.get("interests", [])),
            "top_3_needs": list(payload.get("top_3_needs", []))[:3],
            "featured_plugins": list(payload.get("featured_plugins", [])),
        }
        envelope = self._sign_object("profile", clean)
        self._profile_path.write_text(
            json.dumps(envelope, indent=2), encoding="utf-8"
        )
        return {"ok": True, "message": "profile saved", "profile": envelope}

    def get_local_profile(self) -> Dict[str, Any]:
        self.ensure_initialized()
        if not self._profile_path.exists():
            return {"ok": True, "message": "no local profile yet", "profile": {}}
        data = json.loads(self._profile_path.read_text(encoding="utf-8"))
        return {"ok": True, "message": "profile loaded", "profile": data}

    # -------------------------
    # listings
    # -------------------------

    def create_listing(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.ensure_initialized()
        clean = {
            "plugin_id": payload.get("plugin_id", "").strip(),
            "name": payload.get("name", "").strip(),
            "description": payload.get("description", "").strip(),
            "plugin_version": payload.get("plugin_version", "").strip(),
            "manifest_url": payload.get("manifest_url", "").strip(),
            "category": payload.get("category", "").strip(),
            "price": int(payload.get("price", 0) or 0),
            "downloads": 0,
        }
        envelope = self._sign_object("plugin_listing", clean)
        self._append_jsonl(self._listings_path, envelope)
        self._upsert_listing(envelope)
        return {"ok": True, "message": "listing created", "listing": envelope}

    def search_listings(
        self,
        category: str = "",
        author_node_id: str = "",
        sort_by: str = "downloads",
    ) -> Dict[str, Any]:
        self.ensure_initialized()

        order_by = {
            "downloads": "downloads DESC",
            "name": "name ASC",
            "first_seen": "first_seen DESC",
        }.get(sort_by, "downloads DESC")

        query = "SELECT * FROM plugins WHERE 1=1"
        params: List[Any] = []

        if category:
            query += " AND category = ?"
            params.append(category)

        if author_node_id:
            query += " AND author_node_id = ?"
            params.append(author_node_id)

        query += f" ORDER BY {order_by}"

        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(query, params).fetchall()
            listings = [dict(row) for row in rows]
        finally:
            conn.close()

        return {"ok": True, "message": "search complete", "listings": listings}

    # -------------------------
    # sync (stubbed but shaped)
    # -------------------------

    def sync_peer(
        self,
        node_id: str,
        host: str,
        port: int,
        scheme: str = "http",
    ) -> Dict[str, Any]:
        self.ensure_initialized()

        # Deliberately a stub for the first Codex pass.
        # This is where paired-node fetch, verify, and import will go.
        return {
            "ok": False,
            "message": "manual peer sync not implemented yet",
            "peer_node_id": node_id,
            "imported_profile": False,
            "imported_listings": 0,
            "error": {
                "code": "not_implemented",
                "host": host,
                "port": port,
                "scheme": scheme,
            },
        }

    # -------------------------
    # internals
    # -------------------------

    def _ensure_dirs(self) -> None:
        CONFIG.data_root.mkdir(parents=True, exist_ok=True)
        CONFIG.identity_dir.mkdir(parents=True, exist_ok=True)
        CONFIG.profile_dir.mkdir(parents=True, exist_ok=True)
        CONFIG.marketplace_dir.mkdir(parents=True, exist_ok=True)
        CONFIG.peers_dir.mkdir(parents=True, exist_ok=True)

    def _load_or_create_identity(self) -> None:
        """
        Replace this placeholder with real Ed25519 + DPAPI/private-key-at-rest
        logic. Left intentionally simple for the skeleton so real crypto can be
        wired cleanly in the first implementation pass.
        """
        pub_path = CONFIG.identity_dir / "node_public.pem"
        meta_path = CONFIG.identity_dir / "identity.json"

        if pub_path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            self._identity = IdentityState(
                node_id=meta.get("node_id", ""),
                public_key_pem=pub_path.read_text(encoding="utf-8"),
            )
            return

        # Placeholder identity bootstrap.
        seed = f"{time.time_ns()}::{CONFIG.plugin_id}".encode("utf-8")
        public_bytes = hashlib.sha256(seed).digest()
        node_id = (
            base64.urlsafe_b64encode(public_bytes).decode("ascii").rstrip("=")
        )

        public_pem = (
            "-----BEGIN PUBLIC KEY-----\n"
            f"{base64.b64encode(public_bytes).decode('ascii')}\n"
            "-----END PUBLIC KEY-----\n"
        )

        pub_path.write_text(public_pem, encoding="utf-8")
        meta_path.write_text(
            json.dumps({"node_id": node_id}, indent=2), encoding="utf-8"
        )

        self._identity = IdentityState(
            node_id=node_id, public_key_pem=public_pem
        )

    def _canonical_json(self, value: Dict[str, Any]) -> bytes:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")

    def _hash_payload(self, payload: Dict[str, Any]) -> str:
        return hashlib.sha256(self._canonical_json(payload)).hexdigest()

    def _fake_sign(self, digest_hex: str) -> str:
        """
        Placeholder signature for skeleton only.
        Swap for real Ed25519 signing in the first real implementation pass.
        """
        raw = hashlib.sha256(
            f"{self._identity.node_id}:{digest_hex}".encode("utf-8")
        ).digest()
        return base64.b64encode(raw).decode("ascii")

    def _sign_object(
        self, obj_type: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        base_payload = dict(payload)
        digest_hex = self._hash_payload(base_payload)
        return {
            "type": obj_type,
            "version": 1,
            "timestamp": int(time.time()),
            "node_id": self._identity.node_id,
            "hash": digest_hex,
            "signature": self._fake_sign(digest_hex),
            "payload": base_payload,
        }

    def _append_jsonl(self, path: Path, obj: Dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS plugins (
                    plugin_id     TEXT PRIMARY KEY,
                    name          TEXT NOT NULL,
                    description   TEXT DEFAULT '',
                    plugin_version TEXT DEFAULT '',
                    category      TEXT DEFAULT '',
                    price         INTEGER DEFAULT 0,
                    author_node_id TEXT NOT NULL,
                    manifest_url  TEXT DEFAULT '',
                    downloads     INTEGER DEFAULT 0,
                    first_seen    INTEGER DEFAULT 0,
                    last_updated  INTEGER DEFAULT 0,
                    signature     TEXT NOT NULL,
                    hash          TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_plugins_category "
                "ON plugins(category)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_plugins_author "
                "ON plugins(author_node_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_plugins_downloads "
                "ON plugins(downloads DESC)"
            )
            conn.commit()
        finally:
            conn.close()

    def _upsert_listing(self, envelope: Dict[str, Any]) -> None:
        payload = envelope["payload"]
        now = int(time.time())

        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute(
                """
                INSERT INTO plugins (
                    plugin_id, name, description, plugin_version, category,
                    price, author_node_id, manifest_url, downloads,
                    first_seen, last_updated, signature, hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(plugin_id) DO UPDATE SET
                    name=excluded.name,
                    description=excluded.description,
                    plugin_version=excluded.plugin_version,
                    category=excluded.category,
                    price=excluded.price,
                    author_node_id=excluded.author_node_id,
                    manifest_url=excluded.manifest_url,
                    downloads=excluded.downloads,
                    last_updated=excluded.last_updated,
                    signature=excluded.signature,
                    hash=excluded.hash
                """,
                (
                    payload.get("plugin_id", ""),
                    payload.get("name", ""),
                    payload.get("description", ""),
                    payload.get("plugin_version", ""),
                    payload.get("category", ""),
                    int(payload.get("price", 0) or 0),
                    envelope.get("node_id", ""),
                    payload.get("manifest_url", ""),
                    int(payload.get("downloads", 0) or 0),
                    now,
                    now,
                    envelope.get("signature", ""),
                    envelope.get("hash", ""),
                ),
            )
            conn.commit()
        finally:
            conn.close()
