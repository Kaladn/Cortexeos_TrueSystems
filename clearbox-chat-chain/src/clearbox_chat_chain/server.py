from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .attachments import AttachmentChatChain
from .core import ChatChainError


class Handler(BaseHTTPRequestHandler):
    server_version = "ClearboxChatChain/0.1"

    def _json(self, status: int, value: object) -> None:
        body = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            value = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(value, dict): raise ValueError
            return value
        except (ValueError, json.JSONDecodeError):
            raise ChatChainError(400, "invalid_json", "request body must be a JSON object")

    @property
    def app(self) -> AttachmentChatChain:
        return self.server.app  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        try:
            parsed = urlparse(self.path); path = parsed.path.rstrip("/") or "/"
            if path == "/health": result = {"status": "ok"}
            elif path == "/api/v1/models": result = self.app.models()
            elif path == "/api/v1/conversations": result = self.app.list_conversations()
            elif path == "/api/v1/events": result = self.app.events(int(parse_qs(parsed.query).get("after", ["0"])[0]))
            elif path.startswith("/api/v1/attachments/"): result = self.app.get_attachment(path.rsplit("/", 1)[1])
            elif path.startswith("/api/v1/conversations/") and path.endswith("/attachments"):
                conversation_id = path.split("/")[-2]
                result = self.app.list_attachments(conversation_id, parse_qs(parsed.query).get("branch_id", [None])[0])
            elif path.startswith("/api/v1/conversations/"): result = self.app.get_conversation(path.rsplit("/", 1)[1])
            elif path.startswith("/api/v1/branches/"): result = self.app.get_branch(path.rsplit("/", 1)[1])
            elif path.startswith("/api/v1/turns/"): result = self.app.get_turn(path.rsplit("/", 1)[1])
            else: raise ChatChainError(404, "not_found", "endpoint not found")
            self._json(200, result)
        except ChatChainError as exc: self._json(exc.status, {"error": exc.code, "message": exc.message})
        except Exception as exc: self._json(500, {"error": "internal_error", "message": str(exc)})

    def do_POST(self) -> None:
        try:
            path, body = urlparse(self.path).path.rstrip("/"), self._body()
            if path == "/api/v1/conversations": result, status = self.app.create_conversation(body.get("title")), 201
            elif path.startswith("/api/v1/conversations/") and path.endswith("/attachments"):
                result, status = self.app.create_attachment(path.split("/")[-2], body), 201
            elif path.startswith("/api/v1/conversations/") and path.endswith("/turns"):
                result, status = self.app.send_turn(path.split("/")[-2], body), 202
            elif path.startswith("/api/v1/outputs/") and path.endswith("/continue"):
                result, status = self.app.continue_output(path.split("/")[-2], body), 202
            elif path.startswith("/api/v1/messages/") and path.endswith("/branch"):
                result, status = self.app.branch_message(path.split("/")[-2], body), 202
            elif path.startswith("/api/v1/turns/") and path.endswith("/cancel"):
                result, status = self.app.cancel_turn(path.split("/")[-2], body), 202
            else: raise ChatChainError(404, "not_found", "endpoint not found")
            self._json(status, result)
        except ChatChainError as exc: self._json(exc.status, {"error": exc.code, "message": exc.message})
        except Exception as exc: self._json(500, {"error": "internal_error", "message": str(exc)})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} {fmt % args}")


def serve(host: str, port: int, database: str) -> None:
    server = ThreadingHTTPServer((host, port), Handler)
    server.app = AttachmentChatChain(database)  # type: ignore[attr-defined]
    print(f"Clearbox Chat-Chain listening on http://{host}:{port}")
    server.serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3219)
    parser.add_argument("--database", default=str(Path.home() / ".local/state/clearbox-chat-chain/chat-chain.sqlite3"))
    args = parser.parse_args()
    serve(args.host, args.port, args.database)


if __name__ == "__main__": main()
