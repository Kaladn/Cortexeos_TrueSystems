from __future__ import annotations

import json
import os
import sqlite3
import threading
import urllib.request
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def uid() -> str:
    return str(uuid.uuid4())


class ChatChainError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


SCHEMA = """
PRAGMA foreign_keys=ON;
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS conversations (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, root_branch_id TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, revision INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS branches (
 id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, parent_branch_id TEXT,
 forked_from_output_id TEXT, forked_from_message_id TEXT, kind TEXT NOT NULL,
 created_at TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0,
 FOREIGN KEY(conversation_id) REFERENCES conversations(id));
CREATE TABLE IF NOT EXISTS messages (
 id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, branch_id TEXT NOT NULL,
 parent_message_id TEXT, role TEXT NOT NULL, content TEXT NOT NULL,
 created_at TEXT NOT NULL, FOREIGN KEY(branch_id) REFERENCES branches(id));
CREATE TABLE IF NOT EXISTS turns (
 id TEXT PRIMARY KEY, conversation_id TEXT NOT NULL, branch_id TEXT NOT NULL,
 user_message_id TEXT NOT NULL, plan_json TEXT NOT NULL, status TEXT NOT NULL,
 current_step INTEGER NOT NULL DEFAULT 0, final_assistant_message_id TEXT,
 error TEXT, cancel_requested INTEGER NOT NULL DEFAULT 0,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS model_outputs (
 id TEXT PRIMARY KEY, turn_id TEXT NOT NULL, ordinal INTEGER NOT NULL,
 provider TEXT NOT NULL, model TEXT NOT NULL, content TEXT NOT NULL,
 status TEXT NOT NULL, error TEXT, created_at TEXT NOT NULL,
 UNIQUE(turn_id, ordinal));
CREATE TABLE IF NOT EXISTS idempotency_keys (
 key TEXT PRIMARY KEY, command_type TEXT NOT NULL, result_json TEXT NOT NULL,
 created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS events (
 cursor INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL,
 payload_json TEXT NOT NULL, created_at TEXT NOT NULL);
"""


class Repository:
    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        with self.connect() as db:
            db.executescript(SCHEMA)
            db.execute("UPDATE turns SET status='accepted', revision=revision+1, updated_at=? WHERE status='running'", (now(),))

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()


class ChatChain:
    def __init__(self, database: str | Path, auto_execute: bool = True):
        self.repo = Repository(database)
        self.auto_execute = auto_execute
        self.adapters: dict[str, Callable[[str, dict[str, Any]], str]] = {
            "echo": self._echo,
            "openai-compatible": self._openai_compatible,
        }
        if auto_execute:
            self.resume()

    @staticmethod
    def _echo(model: str, context: dict[str, Any]) -> str:
        prior = context["prior_chain_outputs"]
        prefix = (prior[-1]["content"] + "\n\n") if prior else ""
        return f"{prefix}[{model}] {context['current_user_message']['content']}"

    @staticmethod
    def _openai_compatible(model: str, context: dict[str, Any]) -> str:
        endpoint = os.getenv("CLEARBOX_OPENAI_ENDPOINT", "").strip()
        if not endpoint:
            raise RuntimeError("CLEARBOX_OPENAI_ENDPOINT is not configured")
        messages = [{"role": m["role"], "content": m["content"]} for m in context["conversation"]]
        if context["prior_chain_outputs"]:
            joined = "\n\n".join(f"Prior output {o['ordinal']}:\n{o['content']}" for o in context["prior_chain_outputs"])
            messages.insert(0, {"role": "system", "content": "Build on these ordered prior chain outputs:\n" + joined})
        body = json.dumps({"model": model, "messages": messages, "stream": False}).encode()
        headers = {"Content-Type": "application/json"}
        key = os.getenv("CLEARBOX_OPENAI_API_KEY", "")
        if key:
            headers["Authorization"] = f"Bearer {key}"
        request = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=120) as response:
            result = json.load(response)
        return result["choices"][0]["message"]["content"]

    def register_adapter(self, provider: str, adapter: Callable[[str, dict[str, Any]], str]) -> None:
        self.adapters[provider] = adapter

    @staticmethod
    def _row(row: sqlite3.Row | None) -> dict[str, Any] | None:
        return dict(row) if row else None

    @staticmethod
    def _plan(plan: Any) -> dict[str, Any]:
        if not isinstance(plan, dict) or plan.get("mode") not in ("single", "chain"):
            raise ChatChainError(400, "invalid_plan", "plan.mode must be single or chain")
        seats = plan.get("seats")
        if not isinstance(seats, list) or not seats:
            raise ChatChainError(400, "invalid_plan", "plan.seats must be non-empty")
        if plan["mode"] == "single" and len(seats) != 1:
            raise ChatChainError(400, "invalid_plan", "single mode requires exactly one seat")
        if any(not isinstance(s, dict) or not s.get("provider") or not s.get("model") for s in seats):
            raise ChatChainError(400, "invalid_plan", "every seat requires provider and model")
        return {"mode": plan["mode"], "seats": [{"provider": s["provider"], "model": s["model"]} for s in seats]}

    def _event(self, db: sqlite3.Connection, kind: str, payload: dict[str, Any]) -> None:
        db.execute("INSERT INTO events(type,payload_json,created_at) VALUES(?,?,?)", (kind, json.dumps(payload), now()))

    def _idempotent(self, db: sqlite3.Connection, key: str, kind: str) -> dict[str, Any] | None:
        if not key:
            raise ChatChainError(400, "missing_idempotency_key", "idempotency_key is required")
        row = db.execute("SELECT command_type,result_json FROM idempotency_keys WHERE key=?", (key,)).fetchone()
        if row and row["command_type"] != kind:
            raise ChatChainError(409, "idempotency_conflict", "key was used for another command")
        return json.loads(row["result_json"]) if row else None

    def create_conversation(self, title: str | None = None) -> dict[str, Any]:
        cid, bid, stamp = uid(), uid(), now()
        with self.repo.lock, self.repo.connect() as db:
            db.execute("INSERT INTO conversations VALUES(?,?,?,?,?,?)", (cid, title or "New conversation", bid, stamp, stamp, 0))
            db.execute("INSERT INTO branches VALUES(?,?,?,?,?,?,?,?)", (bid, cid, None, None, None, "main", stamp, 0))
            self._event(db, "ConversationCreated", {"conversation_id": cid, "branch_id": bid})
        return self.get_conversation(cid)

    def send_turn(self, conversation_id: str, data: dict[str, Any]) -> dict[str, Any]:
        plan = self._plan(data.get("plan"))
        content = data.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ChatChainError(400, "invalid_content", "content must be non-empty")
        key, stamp = data.get("idempotency_key", ""), now()
        with self.repo.lock, self.repo.connect() as db:
            previous = self._idempotent(db, key, "send_turn")
            if previous: return previous
            branch = db.execute("SELECT * FROM branches WHERE id=?", (data.get("branch_id"),)).fetchone()
            if not branch or branch["conversation_id"] != conversation_id:
                raise ChatChainError(404, "branch_not_found", "branch not found in conversation")
            if branch["revision"] != data.get("expected_branch_revision"):
                raise ChatChainError(409, "revision_conflict", "branch revision changed")
            parent = db.execute("SELECT id FROM messages WHERE branch_id=? ORDER BY created_at DESC,rowid DESC LIMIT 1", (branch["id"],)).fetchone()
            mid, tid = uid(), uid()
            db.execute("INSERT INTO messages VALUES(?,?,?,?,?,?,?)", (mid, conversation_id, branch["id"], parent["id"] if parent else None, "user", content, stamp))
            db.execute("INSERT INTO turns VALUES(?,?,?,?,?,'accepted',0,NULL,NULL,0,?,?,0)", (tid, conversation_id, branch["id"], mid, json.dumps(plan), stamp, stamp))
            revision = branch["revision"] + 1
            db.execute("UPDATE branches SET revision=? WHERE id=?", (revision, branch["id"]))
            result = {"turn_id": tid, "user_message_id": mid, "branch_revision": revision}
            db.execute("INSERT INTO idempotency_keys VALUES(?,?,?,?)", (key, "send_turn", json.dumps(result), stamp))
            self._event(db, "TurnAccepted", {"turn_id": tid})
        self._enqueue(tid)
        return result

    def continue_output(self, output_id: str, data: dict[str, Any]) -> dict[str, Any]:
        plan, key, stamp = self._plan(data.get("plan")), data.get("idempotency_key", ""), now()
        with self.repo.lock, self.repo.connect() as db:
            previous = self._idempotent(db, key, "continue_output")
            if previous: return previous
            source = db.execute("SELECT o.*,t.conversation_id,t.branch_id,t.user_message_id FROM model_outputs o JOIN turns t ON t.id=o.turn_id WHERE o.id=? AND o.status='completed'", (output_id,)).fetchone()
            if not source: raise ChatChainError(404, "output_not_found", "completed output not found")
            bid, seed, mid, tid = uid(), uid(), uid(), uid()
            db.execute("INSERT INTO branches VALUES(?,?,?,?,?,?,?,0)", (bid, source["conversation_id"], source["branch_id"], output_id, None, "continue", stamp))
            db.execute("INSERT INTO messages VALUES(?,?,?,?,?,?,?)", (seed, source["conversation_id"], bid, source["user_message_id"], "assistant", source["content"], stamp))
            instruction = data.get("additional_instruction") or "Continue from this output without repeating completed material."
            db.execute("INSERT INTO messages VALUES(?,?,?,?,?,?,?)", (mid, source["conversation_id"], bid, seed, "user", instruction, stamp))
            db.execute("INSERT INTO turns VALUES(?,?,?,?,?,'accepted',0,NULL,NULL,0,?,?,0)", (tid, source["conversation_id"], bid, mid, json.dumps(plan), stamp, stamp))
            result = {"branch_id": bid, "turn_id": tid}
            db.execute("INSERT INTO idempotency_keys VALUES(?,?,?,?)", (key, "continue_output", json.dumps(result), stamp))
            self._event(db, "TurnAccepted", {"turn_id": tid})
        self._enqueue(tid)
        return result

    def branch_message(self, message_id: str, data: dict[str, Any]) -> dict[str, Any]:
        plan, key, stamp = self._plan(data.get("plan")), data.get("idempotency_key", ""), now()
        content = data.get("new_user_content")
        if not isinstance(content, str) or not content.strip(): raise ChatChainError(400, "invalid_content", "new_user_content must be non-empty")
        with self.repo.lock, self.repo.connect() as db:
            previous = self._idempotent(db, key, "branch_message")
            if previous: return previous
            source = db.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()
            if not source: raise ChatChainError(404, "message_not_found", "message not found")
            bid, mid, tid = uid(), uid(), uid()
            db.execute("INSERT INTO branches VALUES(?,?,?,?,?,?,?,0)", (bid, source["conversation_id"], source["branch_id"], None, message_id, "branch", stamp))
            db.execute("INSERT INTO messages VALUES(?,?,?,?,?,?,?)", (mid, source["conversation_id"], bid, message_id, "user", content, stamp))
            db.execute("INSERT INTO turns VALUES(?,?,?,?,?,'accepted',0,NULL,NULL,0,?,?,0)", (tid, source["conversation_id"], bid, mid, json.dumps(plan), stamp, stamp))
            result = {"branch_id": bid, "turn_id": tid}
            db.execute("INSERT INTO idempotency_keys VALUES(?,?,?,?)", (key, "branch_message", json.dumps(result), stamp))
            self._event(db, "TurnAccepted", {"turn_id": tid})
        self._enqueue(tid)
        return result

    def cancel_turn(self, turn_id: str, data: dict[str, Any]) -> dict[str, Any]:
        with self.repo.lock, self.repo.connect() as db:
            turn = db.execute("SELECT * FROM turns WHERE id=?", (turn_id,)).fetchone()
            if not turn: raise ChatChainError(404, "turn_not_found", "turn not found")
            if turn["revision"] != data.get("expected_turn_revision"): raise ChatChainError(409, "revision_conflict", "turn revision changed")
            if turn["status"] not in ("accepted", "running"): raise ChatChainError(409, "invalid_status", "turn is not cancellable")
            db.execute("UPDATE turns SET cancel_requested=1,revision=revision+1,updated_at=? WHERE id=?", (now(), turn_id))
            self._event(db, "TurnCancellationRequested", {"turn_id": turn_id})
        return self.get_turn(turn_id)

    def _enqueue(self, turn_id: str) -> None:
        if self.auto_execute:
            threading.Thread(target=self.execute_turn, args=(turn_id,), daemon=True).start()

    def resume(self) -> None:
        with self.repo.connect() as db:
            ids = [r["id"] for r in db.execute("SELECT id FROM turns WHERE status='accepted'")]
        for turn_id in ids: self._enqueue(turn_id)

    def _branch_context(self, db: sqlite3.Connection, branch_id: str) -> list[dict[str, Any]]:
        branch = db.execute("SELECT * FROM branches WHERE id=?", (branch_id,)).fetchone()
        if not branch: return []
        if branch["parent_branch_id"]:
            parent = self._branch_context(db, branch["parent_branch_id"])
            fork_id = branch["forked_from_message_id"]
            if branch["forked_from_output_id"]:
                output = db.execute("SELECT t.user_message_id FROM model_outputs o JOIN turns t ON t.id=o.turn_id WHERE o.id=?", (branch["forked_from_output_id"],)).fetchone()
                fork_id = output["user_message_id"] if output else None
            if fork_id:
                clipped = []
                for item in parent:
                    clipped.append(item)
                    if item["id"] == fork_id: break
                parent = clipped
        else: parent = []
        own = [dict(r) for r in db.execute("SELECT * FROM messages WHERE branch_id=? ORDER BY created_at,rowid", (branch_id,))]
        return parent + own

    def execute_turn(self, turn_id: str) -> None:
        try:
            with self.repo.lock, self.repo.connect() as db:
                turn = db.execute("SELECT * FROM turns WHERE id=?", (turn_id,)).fetchone()
                if not turn or turn["status"] not in ("accepted", "running"): return
                db.execute("UPDATE turns SET status='running',revision=revision+1,updated_at=? WHERE id=?", (now(), turn_id))
                self._event(db, "TurnRunning", {"turn_id": turn_id})
            while True:
                with self.repo.lock, self.repo.connect() as db:
                    turn = db.execute("SELECT * FROM turns WHERE id=?", (turn_id,)).fetchone()
                    if turn["cancel_requested"]:
                        db.execute("UPDATE turns SET status='cancelled',revision=revision+1,updated_at=? WHERE id=?", (now(), turn_id))
                        self._event(db, "TurnCancelled", {"turn_id": turn_id}); return
                    plan = json.loads(turn["plan_json"])
                    ordinal = turn["current_step"]
                    if ordinal >= len(plan["seats"]): break
                    seat = plan["seats"][ordinal]
                    user = dict(db.execute("SELECT * FROM messages WHERE id=?", (turn["user_message_id"],)).fetchone())
                    context = {"conversation": self._branch_context(db, turn["branch_id"]), "current_user_message": user,
                               "prior_chain_outputs": [dict(r) for r in db.execute("SELECT * FROM model_outputs WHERE turn_id=? AND status='completed' ORDER BY ordinal", (turn_id,))]}
                adapter = self.adapters.get(seat["provider"])
                if not adapter: raise RuntimeError(f"unknown provider: {seat['provider']}")
                try: content = adapter(seat["model"], context)
                except Exception as exc:
                    with self.repo.lock, self.repo.connect() as db:
                        db.execute("INSERT OR REPLACE INTO model_outputs VALUES(?,?,?,?,?,'','failed',?,?)", (uid(), turn_id, ordinal, seat["provider"], seat["model"], str(exc), now()))
                    raise
                with self.repo.lock, self.repo.connect() as db:
                    oid = uid()
                    db.execute("INSERT INTO model_outputs VALUES(?,?,?,?,?,?, 'completed',NULL,?)", (oid, turn_id, ordinal, seat["provider"], seat["model"], content, now()))
                    db.execute("UPDATE turns SET current_step=?,revision=revision+1,updated_at=? WHERE id=?", (ordinal + 1, now(), turn_id))
                    self._event(db, "ModelOutputCompleted", {"turn_id": turn_id, "output_id": oid, "ordinal": ordinal})
            with self.repo.lock, self.repo.connect() as db:
                turn = db.execute("SELECT * FROM turns WHERE id=?", (turn_id,)).fetchone()
                output = db.execute("SELECT * FROM model_outputs WHERE turn_id=? AND status='completed' ORDER BY ordinal DESC LIMIT 1", (turn_id,)).fetchone()
                mid, stamp = uid(), now()
                db.execute("INSERT INTO messages VALUES(?,?,?,?,?,?,?)", (mid, turn["conversation_id"], turn["branch_id"], turn["user_message_id"], "assistant", output["content"], stamp))
                db.execute("UPDATE turns SET status='completed',final_assistant_message_id=?,revision=revision+1,updated_at=? WHERE id=?", (mid, stamp, turn_id))
                self._event(db, "TurnCompleted", {"turn_id": turn_id, "assistant_message_id": mid})
        except Exception as exc:
            with self.repo.lock, self.repo.connect() as db:
                db.execute("UPDATE turns SET status='failed',error=?,revision=revision+1,updated_at=? WHERE id=?", (str(exc), now(), turn_id))
                self._event(db, "TurnFailed", {"turn_id": turn_id, "error": str(exc)})

    def list_conversations(self) -> list[dict[str, Any]]:
        with self.repo.connect() as db: return [dict(r) for r in db.execute("SELECT * FROM conversations ORDER BY updated_at DESC")]

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        with self.repo.connect() as db:
            conv = self._row(db.execute("SELECT * FROM conversations WHERE id=?", (conversation_id,)).fetchone())
            if not conv: raise ChatChainError(404, "conversation_not_found", "conversation not found")
            branches = [dict(r) for r in db.execute("SELECT * FROM branches WHERE conversation_id=? ORDER BY created_at", (conversation_id,))]
        return {"conversation": conv, "branches": branches, "selected_branch": self.get_branch(conv["root_branch_id"])}

    def get_branch(self, branch_id: str) -> dict[str, Any]:
        with self.repo.connect() as db:
            branch = self._row(db.execute("SELECT * FROM branches WHERE id=?", (branch_id,)).fetchone())
            if not branch: raise ChatChainError(404, "branch_not_found", "branch not found")
            ancestry, cursor = [], branch
            while cursor:
                ancestry.append(cursor)
                cursor = self._row(db.execute("SELECT * FROM branches WHERE id=?", (cursor["parent_branch_id"],)).fetchone()) if cursor["parent_branch_id"] else None
            messages = self._branch_context(db, branch_id)
            active = db.execute("SELECT id FROM turns WHERE branch_id=? AND status IN ('accepted','running') ORDER BY created_at DESC LIMIT 1", (branch_id,)).fetchone()
        return {"branch": branch, "ancestry": list(reversed(ancestry)), "messages": messages, "active_turn": self.get_turn(active["id"]) if active else None, "revision": branch["revision"]}

    def get_turn(self, turn_id: str) -> dict[str, Any]:
        with self.repo.connect() as db:
            turn = self._row(db.execute("SELECT * FROM turns WHERE id=?", (turn_id,)).fetchone())
            if not turn: raise ChatChainError(404, "turn_not_found", "turn not found")
            turn["plan"] = json.loads(turn.pop("plan_json")); turn["cancel_requested"] = bool(turn["cancel_requested"])
            outputs = [dict(r) for r in db.execute("SELECT * FROM model_outputs WHERE turn_id=? ORDER BY ordinal", (turn_id,))]
        return {"turn": turn, "outputs": outputs}

    def models(self) -> list[dict[str, Any]]:
        return [{"provider": "echo", "model": "echo", "description": "Built-in deterministic adapter"},
                {"provider": "openai-compatible", "model": "runtime-defined", "description": "CLEARBOX_OPENAI_ENDPOINT"}]

    def events(self, after: int = 0) -> list[dict[str, Any]]:
        with self.repo.connect() as db:
            return [{**dict(r), "payload": json.loads(r["payload_json"])} for r in db.execute("SELECT * FROM events WHERE cursor>? ORDER BY cursor LIMIT 500", (after,))]
