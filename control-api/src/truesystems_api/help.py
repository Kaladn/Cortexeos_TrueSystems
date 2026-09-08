"""Read-only, code-grounded help for the combined Linux TrueSystems source."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import ast
import hashlib
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
LAYERS = {"1": "quick", "2": "operate", "3": "source"}


@dataclass(frozen=True)
class Reference:
    path: str
    needle: str


@dataclass(frozen=True)
class Topic:
    topic_id: str
    title: str
    keywords: tuple[str, ...]
    quick: str
    operate: str
    references: tuple[Reference, ...]


TOPICS = (
    Topic(
        "whole-system",
        "Whole-system routing",
        ("system", "route", "which", "whole", "operate", "manual"),
        "Select the narrowest real component: TrueMachine for Linux temporal state, TrueVision Intake for DocuFilm document/glyph admission, TrueMem for deterministic cited retrieval, TrueAudio for audio state, TrueSpeech for bounded speech-state candidates, LocalMemoryChat for cited local memory, TrueCore for defensive agents and tools, and Chat-Chain for durable conversation.",
        "Use the unified API only for its declared routes. It delegates to component callables and does not merge their authority. Return component IDs, timestamps, citations, coordinates, and receipts without replacing them.",
        (Reference("OPERATORS_MANUAL.md", "## Selection table"), Reference("control-api/src/truesystems_api/runtime.py", "def install_component_paths")),
    ),
    Topic(
        "truemachine",
        "TrueMachine temporal state",
        ("truemachine", "fusion", "pulse", "wal", "machine", "temporal"),
        "TrueMachine samples Linux state, appends each pulse to its WAL, and atomically publishes a Fusion Pack.",
        "Run `PYTHONPATH=src python -m truemachine run --duration 60 --interval 1 --state-dir state`, then verify with `python -m truemachine verify --state-dir state`. Optional state artifacts require their own schema declaration.",
        (Reference("TrueMachine/src/truemachine/cli.py", "def parser"), Reference("TrueMachine/docs/CONTRACT.md", "#")),
    ),
    Topic(
        "truevision-intake",
        "TrueVision Intake and DocuFilm",
        ("truevision", "intake", "docufilm", "document", "glyph", "page"),
        "TrueVision Intake is the sole DocuFilm document/glyph admission authority and hands parent/contained records to TrueMem.",
        "Use `truevision_intake.document_state` for page/glyph state reads. Preserve its stable state records and pass admitted strings and objects to TrueMem; do not substitute screenshot or raw-media truth.",
        (Reference("TrueVisionIntake/README.md", "# TrueVision Intake"), Reference("TrueVisionIntake/truevision_intake/document_state/state_reader.py", "class DocumentStateReader")),
    ),
    Topic(
        "trueaudio",
        "TrueAudio state",
        ("trueaudio", "audio", "sound", "pipewire", "replay", "monitor"),
        "TrueAudio records deterministic derived audio state and replayable state without saving raw audio as source truth.",
        "File input uses FFmpeg. Machine output uses the Linux PipeWire/Pulse default sink monitor. Run the scripts under `TrueAudio/scripts` and retain their manifests and receipts.",
        (Reference("TrueAudio/README.md", "# TrueAudio"), Reference("TrueAudio/trueaudio_runtime/machine.py", "def capture_linux_pipewire_loopback")),
    ),
    Topic(
        "truespeech",
        "TrueSpeech state",
        ("truespeech", "speech", "voice", "lyrics", "segments", "vad"),
        "TrueSpeech detects bounded speech-like regions from replayable TrueAudio state; it does not transcribe or invent lyrics.",
        "Run `PYTHONPATH=.:../TrueAudio python scripts/truespeech_detect_segments.py --help` from TrueSpeech. Lyric alignment accepts caller-supplied text and returns candidates only.",
        (Reference("TrueSpeech/README.md", "# TrueSpeech"), Reference("TrueSpeech/truespeech_runtime/speech.py", "def detect_speech_segments_from_replayable_state")),
    ),
    Topic(
        "truemem",
        "TrueMem evidence retrieval",
        ("truemem", "truemem", "anchor", "topk", "top-k", "citation", "document", "intake", "deeper", "wider"),
        "TrueMem maps text into deterministic anchors, counts, coordinates, and citations; it does not use an LLM to establish source truth.",
        "Use DocuFilm admission through `docufilm-intake`. Retrieval `query` accepts a structured EvidenceNeed, never a raw question or top_k. Preserve source coordinates and ownership. `deeper-wider` is a separate legacy diagnostic, not the evidence-query continuation contract.",
        (Reference("TrueMem/src/truemem/cli.py", "query_cmd = sub.add_parser"), Reference("TrueMem/src/truemem/engine/prediction_walk.py", "def ")),
    ),
    Topic(
        "local-memory",
        "LocalMemoryChat cited memory",
        ("memory", "localmemory", "remember", "file", "sqlite", "source"),
        "LocalMemoryChat searches local indexed material and returns a cited memory packet and receipt.",
        "Initialize a profile, add or attach sources, index when required, then use `ask`. Counts locate the field; addresses and citations prove the returned source location.",
        (Reference("LocalMemoryChat/src/local_memory_chat/cli.py", "def main"), Reference("LocalMemoryChat/src/local_memory_chat/memory.py", "def ask")),
    ),
    Topic(
        "truecore",
        "TrueCore defensive runtime",
        ("truecore", "security", "agent", "forge", "reaper", "containment", "permission"),
        "TrueCore reads evidence, runs coded defensive agents and bounded capabilities, and keeps action behind policy and receipts.",
        "Inspect with `status`, `tail`, `cells`, `forge`, `help`, and `agents`. Treat a catalog or manifest as description only. Do not claim Linux containment unless the live tool and receipt prove it.",
        (Reference("TrueCore/truecore/cli/main.py", "def _build_parser"), Reference("TrueCore/truecore/agents/process_change.py", "class ProcessChangeAgent")),
    ),
    Topic(
        "chat-chain",
        "Clearbox Chat-Chain",
        ("chat", "conversation", "turn", "continue", "branch", "help"),
        "Chat-Chain persists ordered conversations, branches, turns, and model outputs. The `truesystems-help` provider gives read-only help inside that chat flow.",
        "Choose provider `truesystems-help`. Choose model `quick`, `operate`, or `source` for help layer 1, 2, or 3. Help produces an ordinary completed chat output and never mutates another component.",
        (Reference("clearbox-chat-chain/src/clearbox_chat_chain/core.py", "def register_adapter"), Reference("control-api/src/truesystems_api/runtime.py", "register_adapter(\"truesystems-help\"")),
    ),
    Topic(
        "control-api",
        "Unified localhost API",
        ("api", "endpoint", "localhost", "control", "health", "help"),
        "The control API is a localhost-only delegation surface over existing components.",
        "Start it on `127.0.0.1:3220`. Use `GET /api/v1/help/topics` to list help and `POST /api/v1/help/query` with `question` and optional `layer` from 1 through 3.",
        (Reference("control-api/src/truesystems_api/server.py", "OPERATIONS"), Reference("control-api/src/truesystems_api/help.py", "TOPICS =")),
    ),
)


def list_topics() -> dict[str, Any]:
    return {
        "schema": "truesystems_help_topics@1",
        "layers": LAYERS,
        "topics": [{"topic_id": topic.topic_id, "title": topic.title} for topic in TOPICS],
    }


def answer_help(question: str, layer: int = 1) -> dict[str, Any]:
    question = str(question).strip()
    if not question:
        raise ValueError("question is required")
    if str(layer) not in LAYERS:
        raise ValueError("layer must be 1, 2, or 3")
    topic = _select_topic(question)
    citations = [_resolve(reference) for reference in topic.references
                 if reference.path.endswith('.py') and reference.path != 'control-api/src/truesystems_api/help.py']
    # Topic prose selects no facts. Every returned statement is an exact source
    # excerpt or an explicit unresolved status, not inferred operating advice.
    answer = "\n\n".join(c['location'] + '\n' + c.get('source', c['status']) for c in citations)
    if not answer:
        answer = 'UNRESOLVED: no executable source reference'
    return {
        "schema": "truesystems_help_answer@1",
        "authority": "STATIC_CODE_FACTS_ONLY",
        "read_only": True,
        "question": question,
        "topic_id": topic.topic_id,
        "layer": layer,
        "layer_name": LAYERS[str(layer)],
        "answer": answer,
        "citations": citations,
    }


def chat_help(model: str, context: dict[str, Any]) -> str:
    layer = {"quick": 1, "operate": 2, "source": 3}.get(str(model).lower())
    if layer is None:
        raise ValueError("truesystems-help model must be quick, operate, or source")
    result = answer_help(context["current_user_message"]["content"], layer)
    cites = "\n".join(f"- {item['location']}" for item in result["citations"])
    return f"{result['answer']}\n\nCitations:\n{cites}"


def _select_topic(question: str) -> Topic:
    for topic in TOPICS:
        if question.lower().strip() == topic.topic_id:
            return topic
    words = set(re.findall(r"[a-z0-9-]+", question.lower()))
    scored = []
    for position, topic in enumerate(TOPICS):
        score = sum(3 if keyword in words else 1 for keyword in topic.keywords if keyword in question.lower())
        scored.append((score, -position, topic))
    best = max(scored)
    return best[2] if best[0] else TOPICS[0]


def _resolve(reference: Reference) -> dict[str, Any]:
    path = REPO_ROOT / reference.path
    if not path.is_file():
        return {"path": reference.path, "line": None, "location": reference.path, "status": "missing"}
    raw = path.read_bytes()
    text = raw.decode('utf-8')
    line = None
    for number, value in enumerate(text.splitlines(), 1):
        if reference.needle in value:
            line = number
            break
    location = f"{reference.path}:{line}" if line else reference.path
    if line is None:
        return {"path": reference.path, "line": None, "location": location, "status": "UNRESOLVED"}
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return {"path": reference.path, "line": line, "location": location, "status": "SYNTAX_ERROR"}
    containing = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.lineno <= line <= n.end_lineno]
    node = min(containing, key=lambda n: n.end_lineno - n.lineno) if containing else None
    start, end = (node.lineno, node.end_lineno) if node else (line, line)
    return {"path": reference.path, "line": start, "end_line": end,
            "location": f'{reference.path}:{start}', "status": "STATIC_CODE_FACTS_ONLY",
            "sha256": hashlib.sha256(raw).hexdigest(),
            "source": '\n'.join(text.splitlines()[start-1:end])}
