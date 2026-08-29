from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parents[3]
STATE_ROOT = Path(os.environ.get("TRUESYSTEMS_STATE_ROOT", Path.home() / ".local/state/truesystems")).expanduser()


def install_component_paths() -> None:
    for relative in (
        "TrueMem/src",
        "TrueMachine/src",
        "TrueAudio",
        "TrueSpeech",
        "TrueVisionIntake",
        "TrueVision",
        "LocalMemoryChat/src",
        "clearbox-chat-chain/src",
    ):
        value = str(REPO_ROOT / relative)
        if value not in sys.path:
            sys.path.insert(0, value)


def system_status() -> dict[str, Any]:
    return {
        "schema": "truesystems_status@1",
        "scope": "local",
        "systems": {
            "control_api": {"ok": True, "mode": "local_python"},
            "truecore": _http_status(os.environ.get("TRUECORE_URL", "http://127.0.0.1:5000/api/health")),
            "chat_chain": _http_status(os.environ.get("CHAT_CHAIN_URL", "http://127.0.0.1:3219/health")),
            "truemachine": truemachine_verify(),
        },
    }


def truemachine_verify() -> dict[str, Any]:
    install_component_paths()
    from truemachine import FusionStore

    state_dir = STATE_ROOT / "truemachine"
    state_dir.mkdir(parents=True, exist_ok=True)
    store = FusionStore(state_dir)
    if not store.wal_path.exists():
        return {"ok": True, "initialized": False, "state_dir": str(state_dir), "verification": None}
    return {"ok": True, "initialized": True, "state_dir": str(state_dir), "verification": store.verify()}


def truemachine_pulse(body: dict[str, Any]) -> dict[str, Any]:
    install_component_paths()
    from truemachine import FusionStore, TemporalEngine
    from truemachine.collectors import IdentityCollector, MemoryCollector, NetworkCollector, ProcessCollector

    state_dir = Path(str(body.get("state_dir") or STATE_ROOT / "truemachine")).expanduser()
    engine = TemporalEngine(
        FusionStore(state_dir),
        [IdentityCollector(), MemoryCollector(), ProcessCollector(), NetworkCollector()],
        cadence_ns=1_000_000_000,
    )
    pack = engine.pulse()
    return {"schema": "truesystems_truemachine_pulse@1", "state_dir": str(state_dir.resolve()), "pack": pack.to_dict()}


def truemem_query(body: dict[str, Any]) -> dict[str, Any]:
    install_component_paths()
    from truemem.engine import query

    return query(
        _required(body, "runtime_root"),
        _required(body, "dataset_id"),
        _required(body, "question"),
        top_k=int(body.get("top_k", 5)),
    )


def truemem_deeper_wider(body: dict[str, Any]) -> dict[str, Any]:
    install_component_paths()
    from truemem.engine import deeper_wider_after_answer

    first = body.get("first_answer")
    if not isinstance(first, dict):
        raise ValueError("first_answer must be an object")
    prediction = first.get("prediction", first)
    return deeper_wider_after_answer(
        _required(body, "runtime_root"),
        _required(body, "dataset_id"),
        prediction,
        depth=int(body.get("depth", 3)),
        width=int(body.get("width", 12)),
    )


def memory_ask(body: dict[str, Any]) -> dict[str, Any]:
    install_component_paths()
    from local_memory_chat.memory import ask

    return ask(
        _required(body, "question"),
        runtime_root=body.get("runtime_root") or str(STATE_ROOT / "local-memory-chat"),
        memory_profile_id=str(body.get("profile", "default")),
        limit=int(body.get("limit", 5)),
    )


def chat_chain(body: dict[str, Any], operation: str) -> Any:
    install_component_paths()
    from clearbox_chat_chain.core import ChatChain

    database = Path(str(body.get("database") or Path.home() / ".local/state/clearbox-chat-chain/chat-chain.sqlite3")).expanduser()
    app = ChatChain(database)
    from .help import chat_help
    app.register_adapter("truesystems-help", chat_help)
    if operation == "list":
        return app.list_conversations()
    if operation == "create":
        return app.create_conversation(body.get("title"))
    if operation == "turn":
        return app.send_turn(_required(body, "conversation_id"), body)
    if operation == "continue":
        return app.continue_output(_required(body, "output_id"), body)
    raise ValueError(f"unknown chat operation: {operation}")


def _required(body: dict[str, Any], key: str) -> str:
    value = body.get(key)
    if value is None or str(value).strip() == "":
        raise ValueError(f"{key} is required")
    return str(value)


def _http_status(url: str) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=0.5) as response:
            raw = response.read()
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"text": raw.decode("utf-8", errors="replace")[:500]}
        return {"ok": True, "url": url, "response": payload}
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        return {"ok": False, "url": url, "error": f"{type(error).__name__}: {error}"}
