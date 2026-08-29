from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable
from urllib.parse import urlparse

from .runtime import truemem_deeper_wider, truemem_query, chat_chain, memory_ask, system_status, truemachine_pulse
from .help import answer_help, list_topics


OPERATIONS: dict[str, Callable[[dict[str, Any]], Any]] = {
    "/api/v1/truemachine/pulse": truemachine_pulse,
    "/api/v1/truemem/query": truemem_query,
    "/api/v1/truemem/deeper-wider": truemem_deeper_wider,
    "/api/v1/memory/ask": memory_ask,
    "/api/v1/chat/conversations": lambda body: chat_chain(body, "create"),
    "/api/v1/chat/turns": lambda body: chat_chain(body, "turn"),
    "/api/v1/chat/continue": lambda body: chat_chain(body, "continue"),
    "/api/v1/help/query": lambda body: answer_help(str(body.get("question", "")), int(body.get("layer", 1))),
}


class Handler(BaseHTTPRequestHandler):
    server_version = "TrueSystemsControl/0.1"

    def do_GET(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        try:
            if path in {"/health", "/api/v1/systems"}:
                self._json(200, system_status())
            elif path == "/api/v1/help/topics":
                self._json(200, list_topics())
            elif path == "/api/v1/chat/conversations":
                self._json(200, chat_chain({}, "list"))
            else:
                self._json(404, {"error": "not_found", "path": path})
        except Exception as error:
            self._error(error)

    def do_POST(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        operation = OPERATIONS.get(path)
        if operation is None:
            self._json(404, {"error": "not_found", "path": path})
            return
        try:
            self._json(200, operation(self._body()))
        except Exception as error:
            self._error(error)

    def _body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        value = json.loads(self.rfile.read(length) or b"{}")
        if not isinstance(value, dict):
            raise ValueError("request body must be a JSON object")
        return value

    def _json(self, status: int, value: Any) -> None:
        body = json.dumps(value, ensure_ascii=True, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, error: Exception) -> None:
        status = 400 if isinstance(error, (ValueError, FileNotFoundError)) else 500
        self._json(status, {"error": type(error).__name__, "message": str(error)})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"{self.address_string()} {fmt % args}")


def serve(host: str = "127.0.0.1", port: int = 3220) -> None:
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("TrueSystems control API is local-only")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


def main() -> None:
    parser = argparse.ArgumentParser(prog="truesystems-api")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3220)
    args = parser.parse_args()
    serve(args.host, args.port)


if __name__ == "__main__":
    main()
