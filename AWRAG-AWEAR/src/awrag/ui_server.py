from __future__ import annotations

import argparse
import json
import mimetypes
import os
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from . import ui_read_bridge


ACTION_ENDPOINTS = {
    "/api/ui/batch/run",
}

READ_ENDPOINTS = {
    "/api/ui/status",
    "/api/ui/manifest",
    "/api/ui/lexicon/search",
    "/api/ui/anchor/detail",
    "/api/ui/anchor/locations",
    "/api/ui/count-backend",
    "/api/ui/symbol-system",
    "/api/ui/protected-notice",
}


def create_server(
    address: tuple[str, int],
    *,
    runtime_root: str | Path,
    dataset_id: str,
    static_root: str | Path | None = None,
) -> ThreadingHTTPServer:
    handler = create_handler(runtime_root=runtime_root, dataset_id=dataset_id, static_root=static_root)
    return ThreadingHTTPServer(address, handler)


def create_handler(
    *,
    runtime_root: str | Path,
    dataset_id: str,
    static_root: str | Path | None = None,
) -> type[BaseHTTPRequestHandler]:
    runtime = Path(runtime_root).expanduser()
    dataset = str(dataset_id)
    static = _resolve_static_root(static_root)

    class AWEARReadOnlyHandler(BaseHTTPRequestHandler):
        server_version = "AWEARReadOnlyUI/0.05"

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)
            try:
                if path.startswith("/api/"):
                    self._handle_api(path, query)
                    return
                self._handle_static(path)
            except FileNotFoundError as exc:
                self._send_json(HTTPStatus.NOT_FOUND, _error_payload("not_found", str(exc)))
            except KeyError as exc:
                self._send_json(HTTPStatus.NOT_FOUND, _error_payload("not_found", str(exc)))
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, _error_payload("bad_request", str(exc)))
            except Exception as exc:  # pragma: no cover - defensive safety net
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, _error_payload("internal_error", str(exc)))

        def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            parsed = urlparse(self.path)
            try:
                if parsed.path == "/api/ui/batch/run":
                    self._handle_batch_run()
                    return
                self._send_json(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    _error_payload("read_only", "Locked: action bridge not enabled."),
                    extra_headers={"Allow": "GET"},
                )
            except FileNotFoundError as exc:
                self._send_json(HTTPStatus.NOT_FOUND, _error_payload("not_found", str(exc)))
            except ValueError as exc:
                self._send_json(HTTPStatus.BAD_REQUEST, _error_payload("bad_request", str(exc)))
            except RuntimeError as exc:
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, _error_payload("batch_failed", str(exc)))

        def do_PUT(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            self.do_POST()

        def do_DELETE(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
            self.do_POST()

        def log_message(self, _format: str, *args: Any) -> None:
            return

        def _handle_api(self, path: str, query: dict[str, list[str]]) -> None:
            if path not in READ_ENDPOINTS:
                self._send_json(HTTPStatus.NOT_FOUND, _error_payload("not_found", "Read endpoint not found."))
                return

            if path == "/api/ui/status":
                payload = ui_read_bridge.get_status(runtime, dataset)
            elif path == "/api/ui/manifest":
                payload = ui_read_bridge.get_manifest(runtime, dataset)
            elif path == "/api/ui/lexicon/search":
                payload = ui_read_bridge.search_lexicon(
                    runtime,
                    dataset,
                    query=_first(query, "q"),
                    prefix=_first(query, "prefix"),
                    limit=_int_query(query, "limit", 100),
                )
            elif path == "/api/ui/anchor/detail":
                payload = ui_read_bridge.get_anchor_detail(
                    runtime,
                    dataset,
                    anchor=_first(query, "anchor"),
                    symbol=_first(query, "symbol"),
                )
            elif path == "/api/ui/anchor/locations":
                payload = ui_read_bridge.search_anchor_locations(
                    runtime,
                    dataset,
                    query=_first(query, "q"),
                    limit=_int_query(query, "limit", 25),
                )
            elif path == "/api/ui/count-backend":
                payload = ui_read_bridge.get_count_backend_status(runtime, dataset)
            elif path == "/api/ui/symbol-system":
                payload = ui_read_bridge.get_symbol_system_status(runtime, dataset)
            elif path == "/api/ui/protected-notice":
                payload = ui_read_bridge.get_protected_notice()
            else:  # pragma: no cover - guarded by READ_ENDPOINTS
                payload = _error_payload("not_found", "Read endpoint not found.")

            self._send_json(HTTPStatus.OK, payload)


        def _handle_batch_run(self) -> None:
            payload = self._read_json_body()
            questions_path = Path(str(payload.get("questions_path", "")).strip()).expanduser()
            if not str(questions_path):
                raise ValueError("questions_path is required")
            questions_path = questions_path.resolve()
            if not questions_path.exists() or not questions_path.is_file():
                raise FileNotFoundError(str(questions_path))
            top_k = int(payload.get("top_k") or 5)
            if top_k < 1:
                raise ValueError("top_k must be at least 1")

            command = [
                sys.executable,
                "-m",
                "awear.cli",
                "batch",
                "--runtime-root",
                str(runtime),
                "--dataset-id",
                dataset,
                "--questions",
                str(questions_path),
                "--top-k",
                str(top_k),
            ]
            completed = subprocess.run(
                command,
                cwd=str(Path(__file__).resolve().parents[2]),
                capture_output=True,
                text=True,
                timeout=None,
                check=False,
            )
            if completed.returncode != 0:
                raise RuntimeError((completed.stderr or completed.stdout or "awear batch failed").strip())
            stdout_lines = [line for line in completed.stdout.splitlines() if line.strip()]
            if not stdout_lines:
                raise RuntimeError("awear batch produced no JSON summary")
            summary = json.loads(stdout_lines[-1])
            summary["schema"] = summary.get("schema", "awrag_batch_run_summary@1")
            summary["ui_action"] = "batch_run"
            summary["cli_command"] = " ".join(command)
            summary["progress_log"] = completed.stderr.strip()
            self._send_json(HTTPStatus.OK, summary)

        def _read_json_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length <= 0:
                return {}
            body = self.rfile.read(length).decode("utf-8")
            value = json.loads(body)
            if not isinstance(value, dict):
                raise ValueError("JSON body must be an object")
            return value
        def _handle_static(self, path: str) -> None:
            if static is None:
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    _error_payload(
                        "static_ui_not_installed",
                        "Static UI is not installed. Use API endpoints or provide --static-root.",
                    ),
                )
                return
            target = _static_target(static, path)
            if not target.exists() or not target.is_file():
                raise FileNotFoundError(path)
            content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            body = target.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_json(
            self,
            status: HTTPStatus,
            payload: dict[str, Any],
            *,
            extra_headers: dict[str, str] | None = None,
        ) -> None:
            body = json.dumps(payload, ensure_ascii=True, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for key, value in (extra_headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

    return AWEARReadOnlyHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the optional read-only AWEAR UI.")
    parser.add_argument("--runtime-root", default=os.environ.get("AWEAR_RUNTIME_ROOT"), required=False)
    parser.add_argument("--dataset-id", default=os.environ.get("AWEAR_DATASET_ID"), required=False)
    parser.add_argument("--host", default=os.environ.get("AWEAR_UI_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("AWEAR_UI_PORT", "8765")))
    parser.add_argument("--static-root", default=os.environ.get("AWEAR_UI_STATIC_ROOT"))
    args = parser.parse_args()

    if not args.runtime_root:
        parser.error("--runtime-root or AWEAR_RUNTIME_ROOT is required")
    if not args.dataset_id:
        parser.error("--dataset-id or AWEAR_DATASET_ID is required")

    server = create_server(
        (args.host, args.port),
        runtime_root=args.runtime_root,
        dataset_id=args.dataset_id,
        static_root=args.static_root,
    )
    url = f"http://{args.host}:{server.server_address[1]}/"
    print(f"AWEAR read-only UI serving {url}")
    print("Locked: action bridge not enabled.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def _resolve_static_root(static_root: str | Path | None) -> Path | None:
    candidates = []
    if static_root:
        candidates.append(Path(static_root).expanduser())
    candidates.append(Path.cwd() / "HTML UI")
    candidates.append(Path(__file__).resolve().parents[2] / "HTML UI")
    for index, candidate in enumerate(candidates):
        if not candidate.exists() or not candidate.is_dir():
            continue
        if static_root and index == 0:
            return candidate.resolve()
        if (candidate / "index.html").is_file():
            return candidate.resolve()
    return None


def _static_target(static_root: Path, request_path: str) -> Path:
    if request_path in {"", "/"}:
        relative = Path("index.html")
    else:
        clean = unquote(request_path).lstrip("/")
        relative = Path(clean)
    target = (static_root / relative).resolve()
    if static_root not in target.parents and target != static_root:
        raise FileNotFoundError(request_path)
    return target


def _first(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    if not values:
        return None
    value = values[0].strip()
    return value or None


def _int_query(query: dict[str, list[str]], key: str, default: int) -> int:
    raw = _first(query, key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{key} must be an integer") from exc


def _error_payload(code: str, message: str) -> dict[str, Any]:
    payload = ui_read_bridge.get_protected_notice()
    payload.update({
        "schema": "awrag_ui_error@1",
        "error": code,
        "message": message,
        "read_only": True,
    })
    return payload


if __name__ == "__main__":
    main()
