from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

import fastjsonschema

from .core import ChatChain, ChatChainError, now


ATTACHMENT_SCHEMA = "clearbox.chain-attachment/1.0.0"
ATTACHMENT_VERSION = "1.0.0"
PLACEMENT_EXTENSION = "org.clearbox.chat-chain"
DEFAULT_CONTRACT_ROOT = Path("/home/lamercey/ClearboxAI-V2.5/contracts/v1")

MIGRATION = """
CREATE TABLE IF NOT EXISTS external_attachments (
 sequence INTEGER PRIMARY KEY AUTOINCREMENT,
 attachment_id TEXT NOT NULL UNIQUE,
 conversation_id TEXT NOT NULL,
 branch_id TEXT NOT NULL,
 placement_kind TEXT NOT NULL,
 target_id TEXT,
 document_json TEXT NOT NULL,
 artifact_owner_system TEXT NOT NULL,
 artifact_id TEXT NOT NULL,
 hash_algorithm TEXT NOT NULL,
 hash_digest TEXT NOT NULL,
 artifact_ref TEXT NOT NULL,
 created_at TEXT NOT NULL,
 event_cursor INTEGER,
 FOREIGN KEY(conversation_id) REFERENCES conversations(id),
 FOREIGN KEY(branch_id) REFERENCES branches(id));
CREATE INDEX IF NOT EXISTS idx_external_attachments_conversation
 ON external_attachments(conversation_id,sequence);
CREATE INDEX IF NOT EXISTS idx_external_attachments_branch
 ON external_attachments(branch_id,sequence);
CREATE TABLE IF NOT EXISTS attachment_commands (
 idempotency_key TEXT PRIMARY KEY,
 request_hash TEXT NOT NULL,
 attachment_id TEXT NOT NULL,
 result_json TEXT NOT NULL,
 created_at TEXT NOT NULL,
 FOREIGN KEY(attachment_id) REFERENCES external_attachments(attachment_id));
CREATE TABLE IF NOT EXISTS branch_attachment_snapshots (
 branch_id TEXT PRIMARY KEY,
 max_parent_attachment_sequence INTEGER NOT NULL,
 FOREIGN KEY(branch_id) REFERENCES branches(id));
INSERT OR IGNORE INTO branch_attachment_snapshots(branch_id,max_parent_attachment_sequence)
 SELECT id,COALESCE((SELECT MAX(sequence) FROM external_attachments),0)
 FROM branches WHERE parent_branch_id IS NOT NULL;
CREATE TRIGGER IF NOT EXISTS snapshot_attachments_after_branch_insert
 AFTER INSERT ON branches WHEN NEW.parent_branch_id IS NOT NULL
 BEGIN
  INSERT INTO branch_attachment_snapshots(branch_id,max_parent_attachment_sequence)
  VALUES(NEW.id,COALESCE((SELECT MAX(sequence) FROM external_attachments),0));
 END;
"""


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class AttachmentContractValidator:
    """Validate the canonical Clearbox schema without copying it into Chat/Chain."""

    def __init__(self, contract_root: str | Path | None = None):
        configured = contract_root or os.getenv("CLEARBOX_CONTRACT_ROOT") or DEFAULT_CONTRACT_ROOT
        self.root = Path(configured).resolve()
        self.schemas = self.root / "schemas"
        schema_path = self.schemas / "chain-attachment.schema.json"
        if not schema_path.is_file():
            raise RuntimeError(f"Clearbox contract schema not found: {schema_path}")
        self.validate_document = fastjsonschema.compile(
            self._load(schema_path),
            handlers={"": self._offline_schema},
            use_default=False,
            use_formats=False,
        )

    @staticmethod
    def _load(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _offline_schema(self, uri: str) -> dict[str, Any]:
        name = uri.split("#", 1)[0]
        if not name.endswith(".schema.json") or Path(name).name != name:
            raise ValueError(f"non-local schema reference rejected: {uri}")
        path = (self.schemas / name).resolve()
        if path.parent != self.schemas or not path.is_file():
            raise ValueError(f"unresolved schema reference: {uri}")
        return self._load(path)

    def validate(self, document: Any) -> dict[str, Any]:
        if not isinstance(document, dict):
            raise ChatChainError(400, "invalid_attachment_contract", "attachment must be an object")
        if document.get("contract_schema") != ATTACHMENT_SCHEMA or document.get("contract_version") != ATTACHMENT_VERSION:
            raise ChatChainError(422, "unsupported_attachment_contract", "only clearbox.chain-attachment/1.0.0 is supported")
        try:
            self.validate_document(document)
        except fastjsonschema.JsonSchemaException as exc:
            raise ChatChainError(400, "invalid_attachment_contract", str(exc)) from exc
        return document


class AttachmentChatChain(ChatChain):
    """Chat/Chain with immutable external-reference custody and no artifact I/O."""

    def __init__(
        self,
        database: str | Path,
        auto_execute: bool = True,
        contract_root: str | Path | None = None,
    ):
        super().__init__(database, auto_execute=False)
        self.attachment_contract = AttachmentContractValidator(contract_root)
        with self.repo.lock, self.repo.connect() as db:
            db.executescript(MIGRATION)
        self.auto_execute = auto_execute
        if auto_execute:
            self.resume()

    @staticmethod
    def _placement(document: dict[str, Any]) -> dict[str, str]:
        extension = document.get("extensions", {}).get(PLACEMENT_EXTENSION)
        if not isinstance(extension, dict) or set(extension) != {"placement"}:
            raise ChatChainError(400, "invalid_attachment_placement", f"extensions.{PLACEMENT_EXTENSION}.placement is required")
        placement = extension["placement"]
        if not isinstance(placement, dict):
            raise ChatChainError(400, "invalid_attachment_placement", "placement must be an object")
        kind = placement.get("kind")
        expected = {"kind", "branch_id"} if kind == "conversation" else {"kind", "branch_id", "target_id"}
        if kind not in {"conversation", "message", "model_output"} or set(placement) != expected:
            raise ChatChainError(400, "invalid_attachment_placement", "placement requires kind, branch_id, and target_id except at conversation level")
        if any(not isinstance(value, str) or not value for value in placement.values()):
            raise ChatChainError(400, "invalid_attachment_placement", "placement values must be non-empty strings")
        return placement

    @staticmethod
    def _artifact_identity(document: dict[str, Any]) -> tuple[str, str, str, str, str]:
        artifact = document["artifact"]
        return (
            artifact["owner_system"],
            artifact["artifact_id"],
            artifact["content_hash"]["algorithm"],
            artifact["content_hash"]["digest"],
            artifact["ref"],
        )

    @staticmethod
    def _projection(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        value = dict(row)
        return {
            "sequence": value["sequence"],
            "created_at": value["created_at"],
            "placement": {key: item for key, item in {
                "kind": value["placement_kind"],
                "branch_id": value["branch_id"],
                "target_id": value["target_id"],
            }.items() if item is not None},
            "attachment": json.loads(value["document_json"]),
        }

    def _validate_placement(
        self,
        db: sqlite3.Connection,
        conversation_id: str,
        placement: dict[str, str],
        expected_revision: Any,
    ) -> sqlite3.Row:
        branch = db.execute("SELECT * FROM branches WHERE id=?", (placement["branch_id"],)).fetchone()
        if not branch or branch["conversation_id"] != conversation_id:
            raise ChatChainError(404, "branch_not_found", "placement branch not found in conversation")
        if branch["revision"] != expected_revision:
            raise ChatChainError(409, "revision_conflict", "branch revision changed")
        if placement["kind"] == "message":
            visible_ids = {item["id"] for item in self._branch_context(db, branch["id"])}
            if placement["target_id"] not in visible_ids:
                raise ChatChainError(404, "message_not_found", "placement message is not visible on the branch")
        elif placement["kind"] == "model_output":
            output = db.execute(
                "SELECT o.id,t.user_message_id FROM model_outputs o JOIN turns t ON t.id=o.turn_id "
                "WHERE o.id=? AND t.conversation_id=? AND o.status='completed'",
                (placement["target_id"], conversation_id),
            ).fetchone()
            visible_ids = {item["id"] for item in self._branch_context(db, branch["id"])}
            if not output or output["user_message_id"] not in visible_ids:
                raise ChatChainError(404, "output_not_found", "placement output is not visible on the branch")
        return branch

    def create_attachment(self, conversation_id: str, command: dict[str, Any]) -> dict[str, Any]:
        if set(command) != {"idempotency_key", "expected_branch_revision", "attachment"}:
            raise ChatChainError(400, "invalid_attachment_command", "command requires only idempotency_key, expected_branch_revision, and attachment")
        key = command.get("idempotency_key")
        if not isinstance(key, str) or not key:
            raise ChatChainError(400, "missing_idempotency_key", "idempotency_key is required")
        expected_revision = command.get("expected_branch_revision")
        if isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 0:
            raise ChatChainError(400, "invalid_expected_revision", "expected_branch_revision must be a non-negative integer")
        document = self.attachment_contract.validate(command.get("attachment"))
        if document["chain_id"] != conversation_id:
            raise ChatChainError(409, "conversation_mismatch", "attachment chain_id does not match target conversation")
        placement = self._placement(document)
        request_hash = hashlib.sha256(_canonical({"conversation_id": conversation_id, **command}).encode()).hexdigest()
        stamp = now()
        with self.repo.lock, self.repo.connect() as db:
            prior = db.execute("SELECT * FROM attachment_commands WHERE idempotency_key=?", (key,)).fetchone()
            if prior:
                if prior["request_hash"] != request_hash:
                    raise ChatChainError(409, "idempotency_conflict", "key was reused for different attachment content")
                return json.loads(prior["result_json"])
            if db.execute("SELECT 1 FROM idempotency_keys WHERE key=?", (key,)).fetchone():
                raise ChatChainError(409, "idempotency_conflict", "key was used for another command")
            conversation = db.execute("SELECT id FROM conversations WHERE id=?", (conversation_id,)).fetchone()
            if not conversation:
                raise ChatChainError(404, "conversation_not_found", "conversation not found")
            self._validate_placement(db, conversation_id, placement, expected_revision)
            existing = db.execute("SELECT * FROM external_attachments WHERE attachment_id=?", (document["attachment_id"],)).fetchone()
            if existing:
                existing_identity = (
                    existing["artifact_owner_system"], existing["artifact_id"], existing["hash_algorithm"],
                    existing["hash_digest"], existing["artifact_ref"],
                )
                code = "attachment_identity_conflict" if existing_identity != self._artifact_identity(document) else "attachment_id_conflict"
                raise ChatChainError(409, code, "attachment_id is already persisted")
            owner, artifact_id, algorithm, digest, artifact_ref = self._artifact_identity(document)
            db.execute(
                "INSERT INTO external_attachments(attachment_id,conversation_id,branch_id,placement_kind,target_id,document_json,artifact_owner_system,artifact_id,hash_algorithm,hash_digest,artifact_ref,created_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (document["attachment_id"], conversation_id, placement["branch_id"], placement["kind"], placement.get("target_id"), _canonical(document), owner, artifact_id, algorithm, digest, artifact_ref, stamp),
            )
            row = db.execute("SELECT * FROM external_attachments WHERE attachment_id=?", (document["attachment_id"],)).fetchone()
            result = self._projection(row)
            event_payload = {
                "conversation_id": conversation_id,
                "branch_id": placement["branch_id"],
                "attachment_id": document["attachment_id"],
                "artifact": {
                    "owner_system": owner,
                    "artifact_id": artifact_id,
                    "content_hash": {"algorithm": algorithm, "digest": digest},
                    "ref": artifact_ref,
                },
            }
            self._event(db, "AttachmentCreated", event_payload)
            cursor = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            db.execute("UPDATE external_attachments SET event_cursor=? WHERE attachment_id=?", (cursor, document["attachment_id"]))
            db.execute("INSERT INTO attachment_commands VALUES(?,?,?,?,?)", (key, request_hash, document["attachment_id"], _canonical(result), stamp))
            db.execute("INSERT INTO idempotency_keys VALUES(?,?,?,?)", (key, "create_attachment", _canonical(result), stamp))
        return result

    def get_attachment(self, attachment_id: str) -> dict[str, Any]:
        with self.repo.connect() as db:
            row = db.execute("SELECT * FROM external_attachments WHERE attachment_id=?", (attachment_id,)).fetchone()
        if not row:
            raise ChatChainError(404, "attachment_not_found", "attachment not found")
        return self._projection(row)

    def _placement_before_fork(self, db: sqlite3.Connection, row: sqlite3.Row, child: sqlite3.Row) -> bool:
        if row["placement_kind"] == "conversation":
            return True
        parent_context = self._branch_context(db, child["parent_branch_id"])
        positions = {item["id"]: index for index, item in enumerate(parent_context)}
        if child["forked_from_message_id"]:
            cutoff = positions.get(child["forked_from_message_id"], -1)
            if row["placement_kind"] == "message":
                return positions.get(row["target_id"], cutoff + 1) <= cutoff
            output = db.execute(
                "SELECT t.user_message_id,t.final_assistant_message_id FROM model_outputs o JOIN turns t ON t.id=o.turn_id WHERE o.id=?",
                (row["target_id"],),
            ).fetchone()
            marker = output["final_assistant_message_id"] or output["user_message_id"] if output else None
            return marker in positions and positions[marker] <= cutoff
        if child["forked_from_output_id"]:
            source = db.execute(
                "SELECT o.turn_id,o.ordinal,t.user_message_id FROM model_outputs o JOIN turns t ON t.id=o.turn_id WHERE o.id=?",
                (child["forked_from_output_id"],),
            ).fetchone()
            if not source:
                return False
            source_position = positions.get(source["user_message_id"], -1)
            if row["placement_kind"] == "message":
                return positions.get(row["target_id"], source_position + 1) <= source_position
            output = db.execute(
                "SELECT o.turn_id,o.ordinal,t.user_message_id FROM model_outputs o JOIN turns t ON t.id=o.turn_id WHERE o.id=?",
                (row["target_id"],),
            ).fetchone()
            if not output:
                return False
            if output["turn_id"] == source["turn_id"]:
                return output["ordinal"] <= source["ordinal"]
            return positions.get(output["user_message_id"], source_position) < source_position
        return False

    def _visible_rows(self, db: sqlite3.Connection, branch_id: str) -> list[sqlite3.Row]:
        branch = db.execute("SELECT * FROM branches WHERE id=?", (branch_id,)).fetchone()
        if not branch:
            raise ChatChainError(404, "branch_not_found", "branch not found")
        inherited: list[sqlite3.Row] = []
        if branch["parent_branch_id"]:
            snapshot = db.execute("SELECT max_parent_attachment_sequence FROM branch_attachment_snapshots WHERE branch_id=?", (branch_id,)).fetchone()
            cutoff = snapshot[0] if snapshot else 0
            inherited = [row for row in self._visible_rows(db, branch["parent_branch_id"])
                         if row["sequence"] <= cutoff and self._placement_before_fork(db, row, branch)]
        own = list(db.execute("SELECT * FROM external_attachments WHERE branch_id=? ORDER BY sequence", (branch_id,)))
        return sorted(inherited + own, key=lambda row: row["sequence"])

    def list_attachments(self, conversation_id: str, branch_id: str | None = None) -> list[dict[str, Any]]:
        with self.repo.connect() as db:
            if not db.execute("SELECT 1 FROM conversations WHERE id=?", (conversation_id,)).fetchone():
                raise ChatChainError(404, "conversation_not_found", "conversation not found")
            if branch_id:
                branch = db.execute("SELECT conversation_id FROM branches WHERE id=?", (branch_id,)).fetchone()
                if not branch or branch["conversation_id"] != conversation_id:
                    raise ChatChainError(404, "branch_not_found", "branch not found in conversation")
                rows = self._visible_rows(db, branch_id)
            else:
                rows = list(db.execute("SELECT * FROM external_attachments WHERE conversation_id=? ORDER BY sequence", (conversation_id,)))
        return [self._projection(row) for row in rows]

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        result = super().get_conversation(conversation_id)
        result["attachments"] = self.list_attachments(conversation_id)
        return result

    def get_branch(self, branch_id: str) -> dict[str, Any]:
        result = super().get_branch(branch_id)
        attachments = self.list_attachments(result["branch"]["conversation_id"], branch_id)
        by_message: dict[str, list[dict[str, Any]]] = {}
        for attachment in attachments:
            placement = attachment["placement"]
            if placement["kind"] == "message":
                by_message.setdefault(placement["target_id"], []).append(attachment)
        for message in result["messages"]:
            message["attachments"] = by_message.get(message["id"], [])
        result["attachments"] = attachments
        return result

    def get_turn(self, turn_id: str) -> dict[str, Any]:
        result = super().get_turn(turn_id)
        turn = result["turn"]
        attachments = self.list_attachments(turn["conversation_id"], turn["branch_id"])
        output_ids = {output["id"] for output in result["outputs"]}
        relevant = []
        for attachment in attachments:
            placement = attachment["placement"]
            if placement["kind"] == "message" and placement["target_id"] in {turn["user_message_id"], turn["final_assistant_message_id"]}:
                relevant.append(attachment)
            elif placement["kind"] == "model_output" and placement["target_id"] in output_ids:
                relevant.append(attachment)
        by_output = {output_id: [] for output_id in output_ids}
        for attachment in relevant:
            placement = attachment["placement"]
            if placement["kind"] == "model_output":
                by_output[placement["target_id"]].append(attachment)
        for output in result["outputs"]:
            output["attachments"] = by_output[output["id"]]
        result["attachments"] = relevant
        return result
