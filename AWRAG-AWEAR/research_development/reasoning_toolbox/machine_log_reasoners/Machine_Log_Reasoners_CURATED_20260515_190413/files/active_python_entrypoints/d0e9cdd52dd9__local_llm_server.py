"""Local LLM Server - Clearbox AI Studio Direct llama-cpp-python Inference

Direct in-process GPU inference via llama-cpp-python. Loads GGUF models from
the models/ directory, runs with n_gpu_layers=-1 (all layers on GPU — RTX 4080).
All governance, citation, session, and auth logic remains in-process.
Zero Ollama. Zero LM Studio. Direct CUDA via llama-cpp-python.
"""
import asyncio
import json
import logging
import re
import socket
import sys
import time as _time
from pathlib import Path
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import httpx

# ── Windows console UTF-8 fix for emoji support ───────────────
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ── Workspace root (this file lives in scripts/) ──────────────
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

# ── Governed session persistence ──────────────────────────────
from scripts.session_manager import session as _session

# ── GGUF model storage (read from clearbox.config.json, default ./models) ─────
def _resolve_models_dir() -> Path:
    """Read models_path from workspace clearbox.config.json. Absolute or WORKSPACE_ROOT-relative."""
    try:
        _cfg_path = WORKSPACE_ROOT / "clearbox.config.json"
        _mp = json.loads(_cfg_path.read_text(encoding="utf-8")).get("models_path", "./models")
        p = Path(_mp)
        return (WORKSPACE_ROOT / p) if not p.is_absolute() else p
    except Exception:
        return WORKSPACE_ROOT / "models"

MODELS_DIR = _resolve_models_dir()
_llm = None  # Active llama_cpp.Llama instance (None until model is loaded)

# ── UTC ISO-8601 helper (system-wide time standard) ────────────
def now_utc_iso() -> str:
    """Canonical UTC timestamp: YYYY-MM-DDTHH:MM:SS.mmmZ"""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + \
        f"{datetime.now(timezone.utc).microsecond // 1000:03d}Z"


def now_utc_display() -> str:
    """Human-readable UTC clock line for system prompt injection."""
    now = datetime.now(timezone.utc)
    weekday = now.strftime("%A")  # e.g. "Saturday"
    return f"Current UTC datetime: {now.strftime('%Y-%m-%dT%H:%M:%SZ')} ({weekday})"


# Load logging configuration

# ── Secure data paths (all user data in %LOCALAPPDATA%\ClearboxAI) ────────
from security.data_paths import (
    CLEARBOX_CONFIG_PATH, LOGGING_CONFIG_PATH,
    CHAT_THREADS_DIR, CHAT_SUMMARIES_DIR, CHAT_CITATIONS_DIR,
    CITATION_FLAGS_PATH as _SEC_CITATION_FLAGS,
    SOURCE_ROOT, PACKS_DIR,
)
from Conversations.threads.citation_store import CitationStore
from Conversations.threads.note_store import NoteStore
from Conversations.threads.sidechat_store import SideChatStore, normalize_side_chat_description
import json as _json
from security.secure_storage import (
    secure_read_text, secure_write_text,
    secure_append_line, secure_read_lines,
    secure_count_lines,
)
from security.directory_law import boot_validate
CONFIG_PATH = LOGGING_CONFIG_PATH

# ── TLS detection (read once at import for CORS + internal URLs) ──
_TLS = False
try:
    with open(CLEARBOX_CONFIG_PATH, encoding="utf-8") as _f:
        _TLS = _json.load(_f).get("server", {}).get("tls", False)
except Exception:
    pass
_PROTO = "https" if _TLS else "http"

# ── Auto-migrate configs on first run ──────────────────────────────────
def _ensure_secure_config():
    """Ensure secure config exists. Uses default template, never workspace config."""
    ws_root = WORKSPACE_ROOT
    config_sources = [
        (ws_root / "clearbox.config.default.json", CLEARBOX_CONFIG_PATH),
        (ws_root / "config" / "logging.json", LOGGING_CONFIG_PATH),
    ]
    for src, dst in config_sources:
        if not dst.exists() and src.exists():
            print(f"\U0001f512 Initializing config from template: {src.name} → {dst}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            text = src.read_text(encoding="utf-8-sig")
            secure_write_text(dst, text)

_ensure_secure_config()
SYSTEM_IDENTITY = None
USER_DISPLAY_NAME = None
ARCHIVE_INSTRUCTION = None
USER_PROFILE = None

_DEFAULT_ARCHIVE_INSTRUCTION = (
    "The user may include retrieved messages from their personal chat archive. "
    "Use these as supporting context when relevant. "
    "Answer using your full reasoning and general knowledge. "
    "Only say you don't know when the question is genuinely unknowable."
)

if CONFIG_PATH.exists():
    try:
        with open(CONFIG_PATH, encoding="utf-8") as _f:
            config = _json.load(_f)
    except Exception as e:
        print(f"⚠️  Failed to load config: {e}")

def _load_clearbox_config():
    """Load identity, user profile, and archive instruction from clearbox.config.json."""
    global SYSTEM_IDENTITY, USER_DISPLAY_NAME, ARCHIVE_INSTRUCTION, USER_PROFILE
    if CLEARBOX_CONFIG_PATH.exists():
        try:
            with open(CLEARBOX_CONFIG_PATH, encoding="utf-8") as _f:
                _clearbox_cfg = _json.load(_f)
            SYSTEM_IDENTITY = _clearbox_cfg.get("identity")
            USER_DISPLAY_NAME = _clearbox_cfg.get("user_display_name")
            ARCHIVE_INSTRUCTION = _clearbox_cfg.get("archive_instruction")
            USER_PROFILE = _clearbox_cfg.get("user_profile")
            if SYSTEM_IDENTITY:
                print(f"🌲 Identity loaded: {SYSTEM_IDENTITY.get('name', 'unnamed')}")
            if USER_DISPLAY_NAME:
                print(f"👤 User display name: {USER_DISPLAY_NAME}")
            if USER_PROFILE:
                print(f"👤 User profile loaded")
            if ARCHIVE_INSTRUCTION:
                print(f"📜 Archive instruction loaded ({len(ARCHIVE_INSTRUCTION)} chars)")
        except Exception as e:
            print(f"⚠️  Failed to load identity config: {e}")

_load_clearbox_config()

# Unified logging — daily JSONL with UUID identity + integrity hashing
from Conversations.threads import log_message
print("📓 Logging: UNIFIED (daily JSONL + UUID identity + SHA-256 integrity)")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("local_llm_server")


# ══════════════════════════════════════════════════════════════
# LLAMA-CPP-PYTHON DIRECT INFERENCE ENGINE — full GPU, zero Ollama
# ══════════════════════════════════════════════════════════════

def _llm_ready() -> bool:
    """Check if a model is loaded and ready for inference."""
    return _llm is not None


def _gpu_query() -> dict:
    """Query GPU hardware info via bridges.gpu_backend."""
    info = {"gpu_detected": False, "gpu_name": None, "vram_mb": None}
    try:
        from bridges.gpu_backend import query_gpu_json
        stats = query_gpu_json()
        if stats:
            info["gpu_detected"] = True
            info["gpu_name"] = stats.get("name")
            if stats.get("mem_total_mb") is not None:
                info["vram_mb"] = int(stats["mem_total_mb"])
    except Exception:
        pass
    return info


def _infer_family(name: str) -> str:
    n = name.lower()
    for family in ("llama", "mistral", "phi", "gemma", "qwen", "deepseek", "falcon", "vicuna", "orca"):
        if family in n:
            return family
    return "gguf"


def _infer_param_size(name: str) -> str:
    m = re.search(r"(\d+(?:\.\d+)?)[bB]", name)
    return f"{m.group(1)}B" if m else ""


def _infer_quant(name: str) -> str:
    m = re.search(r"(Q\d+_[KSM]+|Q\d+|F16|F32|BF16)", name, re.IGNORECASE)
    return m.group(1).upper() if m else ""


def _scan_gguf_models() -> dict[str, dict]:
    """Scan MODELS_DIR for .gguf files and return a registry dict."""
    registry: dict[str, dict] = {}
    if not MODELS_DIR.exists():
        logger.warning(f"Models directory not found: {MODELS_DIR}")
        return registry
    for path in sorted(MODELS_DIR.glob("**/*.gguf")):
        try:
            size_bytes = path.stat().st_size
        except OSError:
            continue
        display_name = path.stem
        registry[display_name] = {
            "name": display_name,
            "filename": path.name,
            "path": str(path),
            "size": size_bytes,
            "size_gb": round(size_bytes / (1024 ** 3), 2),
            "family": _infer_family(display_name),
            "parameter_size": _infer_param_size(display_name),
            "quantization": _infer_quant(display_name),
        }
    return registry


# ── Model configuration ─────────────────────────────────────────
N_CTX = 8192
TEMPERATURE = 0.7
MAX_TOKENS = 4096
INFERENCE_DEFAULTS = {
    "temperature": 0.7,
    "max_tokens": 4096,
    "top_p": 1.0,
    "top_k": 40,
    "repeat_penalty": 1.1,
    "frequency_penalty": 0.0,
    "presence_penalty": 0.0,
    "seed": -1,
    "mirostat_mode": 0,
    "mirostat_tau": 5.0,
    "mirostat_eta": 0.1,
}
inference_config: dict = dict(INFERENCE_DEFAULTS)
MODEL_REGISTRY: dict[str, dict] = {}

current_model_name: Optional[str] = None
current_conversation_id: Optional[UUID] = None

_gpu_info: dict = {}
_SIDE_CHAT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

app = FastAPI(title="Local LLM Server", version="2.5.0")

citation_store = CitationStore(max_cached_days=14)
note_store = NoteStore(max_cached_days=14)
side_chat_store = SideChatStore()

from security.middleware import AuthMiddleware
app.add_middleware(AuthMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5050", "http://127.0.0.1:5050",
        "https://localhost:5050", "https://127.0.0.1:5050",
        "http://localhost:8080", "http://127.0.0.1:8080",
        "https://localhost:8080", "https://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Clearbox-CSRF", "X-Trace-Id"],
)


class GenerateRequest(BaseModel):
    model: str = ""
    prompt: str
    side_chat_id: Optional[str] = None
    stream: bool = False
    tools_enabled: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    repeat_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    presence_penalty: Optional[float] = None
    seed: Optional[int] = None
    mirostat_mode: Optional[int] = None
    mirostat_tau: Optional[float] = None
    mirostat_eta: Optional[float] = None
    system_prompt: Optional[str] = None


class GenerateResponse(BaseModel):
    model: str
    created_at: str
    response: str
    done: bool


def port_in_use(host: str, port: int, timeout: float = 0.2) -> bool:
    """Check if a port is already in use by attempting to connect to it."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def set_active_model(model_name: Optional[str] = None):
    """Resolve target model, load it into llama-cpp-python with full GPU offload."""
    global current_model_name, MODEL_REGISTRY, _llm

    MODEL_REGISTRY.update(_scan_gguf_models())
    if not MODEL_REGISTRY:
        raise FileNotFoundError(
            f"No .gguf models found in {MODELS_DIR}. "
            "Place a GGUF model file there and restart."
        )

    if model_name and model_name in MODEL_REGISTRY:
        target = model_name
    elif model_name:
        candidates = [k for k in MODEL_REGISTRY if model_name.lower() in k.lower()]
        target = candidates[0] if candidates else list(MODEL_REGISTRY.keys())[0]
    else:
        target = list(MODEL_REGISTRY.keys())[0]

    # Skip reload if the same model is already loaded
    if target == current_model_name and _llm is not None:
        logger.info(f"Model already loaded: {target}")
        return

    model_path = MODEL_REGISTRY[target]["path"]
    size_gb = MODEL_REGISTRY[target]["size_gb"]
    logger.info(f"Loading: {target} ({size_gb} GB) — n_gpu_layers=-1 (full GPU)")

    try:
        from llama_cpp import Llama
        new_llm = Llama(
            model_path=model_path,
            n_gpu_layers=-1,
            n_ctx=N_CTX,
            verbose=False,
        )
    except Exception as e:
        raise RuntimeError(f"Failed to load model '{target}': {e}") from e

    _llm = new_llm
    current_model_name = target
    logger.info(f"✅ Model loaded: {target}")

    try:
        _session.set("active_model", target)
    except Exception as e:
        logger.warning(f"Session persist (model) failed: {e}")


def _run_llm_inference(messages: list, **kwargs) -> dict:
    """Synchronous llama-cpp inference — called via asyncio.to_thread in async endpoints."""
    return _llm.create_chat_completion(messages=messages, **kwargs)


@app.on_event("startup")
async def startup_event():
    global MODEL_REGISTRY, current_conversation_id, _gpu_info

    # Validate sandbox directory structure
    boot_validate()

    MODEL_REGISTRY = _scan_gguf_models()
    logger.info(f"Discovered {len(MODEL_REGISTRY)} GGUF model(s): {list(MODEL_REGISTRY.keys())}")

    _gpu_info = _gpu_query()
    if _gpu_info.get("gpu_detected"):
        logger.info(f"🎮 GPU: {_gpu_info.get('gpu_name', 'detected')} ({_gpu_info.get('vram_mb', '?')} MB VRAM)")
    else:
        logger.warning("⚠️  No GPU detected via bridges.gpu_backend")

    try:
        saved_model = _session.get("active_model")
        saved_conv = _session.get("current_conversation_id")
        if saved_conv:
            current_conversation_id = UUID(saved_conv)
            logger.info(f"Session restored: conversation {saved_conv}")
        if saved_model and saved_model in MODEL_REGISTRY:
            logger.info(f"Session restored: active model {saved_model}")
            await asyncio.to_thread(set_active_model, saved_model)
        elif MODEL_REGISTRY:
            await asyncio.to_thread(set_active_model)
    except Exception as e:
        logger.warning(f"Session restore / model load failed: {e}")
        if MODEL_REGISTRY:
            try:
                await asyncio.to_thread(set_active_model)
            except Exception as e2:
                logger.error(f"Model load failed at startup: {e2}")


def is_first_message_of_day() -> bool:
    """Check if this is the first message today (for context injection)."""
    try:
        from Conversations.threads.daily_logger import get_today_stats
        stats = get_today_stats()
        return stats["message_count"] == 1
    except Exception:
        return False


def build_previous_context() -> str:
    """Build session debrief context for first-message-of-day injection.

    If a debrief exists for the most recent prior session, injects it with
    a directive telling the LLM to present it as its opening response.
    If no debrief exists yet, attempts on-demand generation.

    Citation coords ([ref YYYY-MM-DD:L##]) are embedded in the debrief
    for fast tracing back to the original JSONL lines.
    """
    import re
    from datetime import date

    THREADS_DIR = CHAT_THREADS_DIR
    SUMMARIES_DIR = CHAT_SUMMARIES_DIR
    _DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    def _most_recent_thread_day() -> str | None:
        today_str = date.today().isoformat()
        if not THREADS_DIR.exists():
            return None
        candidates = []
        for p in THREADS_DIR.glob("*.jsonl"):
            d = p.stem
            if _DATE_RE.match(d) and d < today_str:
                try:
                    if secure_count_lines(p) > 0:
                        candidates.append(d)
                except Exception:
                    pass
        return sorted(candidates)[-1] if candidates else None

    def _load_debrief(day: str) -> str | None:
        fp = SUMMARIES_DIR / f"{day}.txt"
        try:
            if not fp.exists():
                return None
            txt = secure_read_text(fp).strip()
            return txt if txt else None
        except Exception:
            return None

    def _generate_debrief_now(day: str) -> str | None:
        """On-demand debrief generation (blocking, ~30s)."""
        try:
            from Conversations.threads.summarizer import generate_debrief
            text = generate_debrief(day)
            return text if text else None
        except Exception as e:
            logger.warning("On-demand debrief generation failed for %s: %s", day, e)
            return None

    try:
        last_day = _most_recent_thread_day()
        if not last_day:
            return ""

        debrief = _load_debrief(last_day)

        # If no debrief on disk, try generating now (first message = LLM is warm)
        if not debrief:
            logger.info("No debrief for %s — generating on demand", last_day)
            debrief = _generate_debrief_now(last_day)

        if not debrief:
            return (
                "\n\nSESSION DEBRIEF INSTRUCTION:\n"
                f"The previous session ({last_day}) has no debrief available yet. "
                "Briefly acknowledge this and proceed to answer the user's message.\n"
            )

        return (
            "\n\nSESSION DEBRIEF INSTRUCTION:\n"
            "This is the user's first message today. Before answering their message, "
            "present the following session debrief from the previous session. "
            "Output the debrief exactly as written (it contains citation coords "
            "for tracing — preserve them). After the debrief, respond to the user's "
            "actual message normally.\n\n"
            f"{debrief}\n"
        )

    except Exception as e:
        logger.warning("Could not build debrief context: %s", e)
        return ""


@app.post("/api/generate")
async def generate(request: GenerateRequest):
    """Direct llama-cpp-python generation endpoint with dual-mode logging."""
    global current_conversation_id

    if not _llm_ready():
        raise HTTPException(status_code=503, detail="No model loaded. Place a .gguf file in models/ and call /api/model/switch.")

    if not current_model_name:
        raise HTTPException(status_code=503, detail="No model selected")

    requested = request.model
    if requested and requested != current_model_name and requested in MODEL_REGISTRY:
        logger.info(f"Auto-switching model: {current_model_name} → {requested}")
        set_active_model(requested)

    try:
        logger.info(f"Generating response for prompt ({len(request.prompt)} chars) [model={current_model_name}]")

        branch = (request.side_chat_id or "").strip() or "main"
        if branch != "main" and not _SIDE_CHAT_ID_RE.match(branch):
            raise HTTPException(status_code=400, detail="Invalid side_chat_id format")

        user_log_result = log_message(
            sender="user",
            content=request.prompt,
            branch=branch,
            conversation_id=str(current_conversation_id) if current_conversation_id else None,
        )
        if current_conversation_id is None and user_log_result.get("conversation_uuid"):
            current_conversation_id = user_log_result["conversation_uuid"]
            logger.info(f"Started new conversation: {current_conversation_id}")
            try:
                _session.set("current_conversation_id", str(current_conversation_id))
            except Exception:
                pass
        if user_log_result.get("cutoff_warning"):
            logger.warning(f"⏰ {user_log_result['cutoff_warning']}")

        yesterday_context = ""
        if branch == "main" and not request.system_prompt and is_first_message_of_day():
            yesterday_context = build_previous_context()
            if yesterday_context:
                logger.info("📜 Injecting previous session context")

        history_context = ""
        retrieval_hits = []
        if not request.system_prompt:
            try:
                # Primary: LakeSpeak chat index (BM25 over ingested chat history)
                from security.data_paths import LAKESPEAK_CHATS_DIR as _CHATS_DIR
                from core.lakespeak.index.bm25 import BM25Index as _BM25
                _chat_bm25 = _BM25(index_dir=_CHATS_DIR / "bm25")
                if _chat_bm25._ensure_loaded():
                    _chat_hits = _chat_bm25.query(request.prompt, topk=5)
                    if _chat_hits:
                        _parts = []
                        for _sc in _chat_hits:
                            _cf = _CHATS_DIR / _sc.receipt_id / "chunks.jsonl"
                            if _cf.exists():
                                for _ln in _cf.read_text(encoding="utf-8").splitlines():
                                    if not _ln.strip():
                                        continue
                                    _ck = _json.loads(_ln)
                                    if _ck.get("chunk_id") == _sc.chunk_id:
                                        _parts.append(_ck.get("text", "")[:800])
                                        break
                        if _parts:
                            history_context = "CHAT HISTORY (LakeSpeak retrieval):\n\n" + "\n\n".join(_parts)
                            retrieval_hits = [
                                {"coord": f"CHAT:{_sc.receipt_id}#{_sc.chunk_id}", "score": round(_sc.score, 4)}
                                for _sc in _chat_hits[:len(_parts)]
                            ]
                            logger.info(f"🔍 Chat LakeSpeak context ({len(history_context)} chars, {len(retrieval_hits)} hits)")
                # Fallback: brute-force history_retriever if chat index not available
                if not history_context:
                    from Conversations.threads.history_retriever import build_history_context
                    history_context, retrieval_hits = build_history_context(
                        request.prompt, max_chars=4000, days_limit=30, branch=branch,
                        return_hits=True,
                    )
                    if history_context:
                        logger.info(f"📚 Retrieved history context ({len(history_context)} chars, {len(retrieval_hits)} hits)")
            except Exception as e:
                logger.warning(f"History retrieval failed: {e}")

        # ── System block assembly ──────────────────────────────
        if request.system_prompt:
            system_block = request.system_prompt
            logger.info(f"🔧 Custom system_prompt ({len(system_block)} chars) — skipping archive/history")
        else:
            # Per-model identity lookup (falls back to global)
            _per_model_id = None
            try:
                from security.identity_profiles import load_profile as _load_ident
                _per_model_id = _load_ident(current_model_name)
            except Exception:
                pass

            parts = []
            if _per_model_id and _per_model_id.get("identity_role"):
                parts.append(_per_model_id["identity_role"])
            elif SYSTEM_IDENTITY and SYSTEM_IDENTITY.get("role"):
                parts.append(SYSTEM_IDENTITY["role"])
            else:
                parts.append("You are a helpful assistant.")

            if USER_PROFILE:
                profile_lines = []
                if USER_PROFILE.get("display_name"):
                    profile_lines.append(f"Name: {USER_PROFILE['display_name']}")
                if USER_PROFILE.get("role"):
                    profile_lines.append(f"Role: {USER_PROFILE['role']}")
                if USER_PROFILE.get("context"):
                    profile_lines.append(f"Context: {USER_PROFILE['context']}")
                if USER_PROFILE.get("style"):
                    profile_lines.append(f"Style: {USER_PROFILE['style']}")
                if USER_PROFILE.get("level"):
                    profile_lines.append(f"Level: {USER_PROFILE['level']}")
                if USER_PROFILE.get("notes"):
                    profile_lines.append(f"Notes: {USER_PROFILE['notes']}")
                if profile_lines:
                    parts.append("USER PROFILE:\n" + "\n".join(profile_lines))

            if _per_model_id and _per_model_id.get("archive_instruction"):
                archive_text = _per_model_id["archive_instruction"]
            else:
                archive_text = ARCHIVE_INSTRUCTION or _DEFAULT_ARCHIVE_INSTRUCTION
            parts.append(archive_text)

            if yesterday_context:
                parts.append(yesterday_context)

            if branch != "main":
                side_meta = side_chat_store.get(branch)
                if side_meta:
                    parts.append(
                        "SIDE CHAT CONTEXT:\n"
                        f"Thread: {side_meta.get('side_chat_id', branch)}\n"
                        f"Summary: {side_meta.get('description', 'Side-chat continuation')}\n"
                        f"Origin day: {side_meta.get('source_day', '?')}"
                    )

            parts.append(now_utc_display())

            system_block = "\n\n".join(parts)

        user_block = request.prompt
        if request.system_prompt:
            pass  # Custom system_prompt mode — no history wrapping
        elif history_context:
            cleaned = history_context.replace(
                "HISTORY_CONTEXT (retrieved from full local chat archive):\n", ""
            )
            user_block = (
                "Here are relevant messages from my chat archive:\n"
                + cleaned
                + "\n===\nBased on the messages above and your own reasoning, answer this: "
                + request.prompt
            )
        else:
            # No history found - encourage inference and reasoning
            user_block = (
                "No directly relevant history found. "
                "Use your reasoning and general knowledge to answer: "
                + request.prompt
            )

        # ── Resolve inference parameters ──────────────────────
        def _p(name):
            v = getattr(request, name, None)
            if v is not None:
                return v
            return inference_config.get(name, INFERENCE_DEFAULTS[name])

        inf_temperature = _p("temperature")
        inf_max_tokens  = _p("max_tokens")
        inf_top_p       = _p("top_p")
        inf_top_k       = _p("top_k")
        inf_repeat      = _p("repeat_penalty")
        inf_freq_pen    = _p("frequency_penalty")
        inf_pres_pen    = _p("presence_penalty")
        inf_seed        = _p("seed")
        inf_miro_mode   = _p("mirostat_mode")
        inf_miro_tau    = _p("mirostat_tau")
        inf_miro_eta    = _p("mirostat_eta")

        # ── Direct llama-cpp-python inference ────────────────

        # Tool definitions (OpenAI-compatible schema, shared with Ollama path)
        _tools_active = False
        _tool_defs = None
        _tool_trace = []
        if request.tools_enabled:
            try:
                from bridges.tool_defs import TOOL_DEFINITIONS, TOOL_SYSTEM_PROMPT
                if TOOL_DEFINITIONS:
                    _tools_active = True
                    _tool_defs = TOOL_DEFINITIONS
                    system_block = TOOL_SYSTEM_PROMPT + "\n\n" + system_block
                    logger.info(f"🔧 Tools enabled: {len(TOOL_DEFINITIONS)} definitions loaded")
            except Exception as e:
                logger.warning(f"Tool loading failed: {e}")

        messages = [
            {"role": "system", "content": system_block},
            {"role": "user", "content": user_block},
        ]
        llm_kwargs: dict = {
            "temperature": inf_temperature,
            "max_tokens": inf_max_tokens,
            "top_p": inf_top_p,
            "top_k": inf_top_k,
            "repeat_penalty": inf_repeat,
            "frequency_penalty": inf_freq_pen,
            "presence_penalty": inf_pres_pen,
        }
        if inf_seed >= 0:
            llm_kwargs["seed"] = inf_seed
        if inf_miro_mode > 0:
            llm_kwargs["mirostat_mode"] = inf_miro_mode
            llm_kwargs["mirostat_tau"] = inf_miro_tau
            llm_kwargs["mirostat_eta"] = inf_miro_eta

        # Pass tool definitions to llama-cpp if tools are active
        if _tools_active:
            llm_kwargs["tools"] = _tool_defs
            llm_kwargs["tool_choice"] = "auto"

        _t0 = _time.perf_counter()
        llm_resp = await asyncio.to_thread(_run_llm_inference, messages, **llm_kwargs)
        _elapsed_ms = round((_time.perf_counter() - _t0) * 1000)

        resp_message = llm_resp["choices"][0]["message"]
        response_text = resp_message.get("content") or ""

        # ── Tool call handling ────────────────────────────────
        if _tools_active:
            _parsed_tools = []

            # Path A: native tool_calls from llama-cpp (Qwen2.5 emits these)
            if resp_message.get("tool_calls"):
                for tc in resp_message["tool_calls"][:3]:
                    fn = tc.get("function", {})
                    fn_name = fn.get("name", "")
                    if fn_name.startswith("tool."):
                        fn_name = fn_name[5:]
                    fn_args = fn.get("arguments", {})
                    if isinstance(fn_args, str):
                        try:
                            fn_args = _json.loads(fn_args)
                        except Exception:
                            fn_args = {}
                    if fn_name:
                        _parsed_tools.append({"name": fn_name, "arguments": fn_args})

            # Path B: parse from content text (fallback for models that embed tool calls)
            if not _parsed_tools and response_text:
                try:
                    from bridges.tool_defs import parse_tool_calls
                    _parsed_tools = parse_tool_calls(response_text)
                except Exception:
                    pass

            # Execute at most ONE tool per round
            _parsed_tools = _parsed_tools[:1]

            if _parsed_tools:
                from bridges.tool_defs import execute_tool, strip_tool_calls

                _first_reply_clean = strip_tool_calls(response_text) if response_text else ""
                messages.append({"role": "assistant", "content": _first_reply_clean or "(calling tool)"})

                for tc in _parsed_tools:
                    t0_tool = _time.perf_counter()
                    result_str = await execute_tool(
                        tc["name"],
                        tc["arguments"],
                        session_id=str(current_conversation_id) if current_conversation_id else None,
                        model_name=current_model_name,
                    )
                    _tool_ms = int((_time.perf_counter() - t0_tool) * 1000)
                    _tool_trace.append({
                        "tool": tc["name"],
                        "args": tc["arguments"],
                        "ms": _tool_ms,
                        "result_preview": result_str[:200],
                    })
                    logger.info(f"🔧 Tool executed: {tc['name']} ({_tool_ms}ms)")
                    messages.append({
                        "role": "system",
                        "content": f"[TOOL RESULT — {tc['name']}]\n{result_str}\n[END TOOL RESULT]\nNow summarize this result for the user. Do NOT call another tool.",
                    })

                # Second call — summarize tool results, no tools passed
                _summary_kwargs = {k: v for k, v in llm_kwargs.items() if k not in ("tools", "tool_choice")}
                llm_resp2 = await asyncio.to_thread(_run_llm_inference, messages, **_summary_kwargs)
                _second_reply = llm_resp2["choices"][0]["message"].get("content") or ""
                response_text = _second_reply if _second_reply.strip() else _first_reply_clean
                _elapsed_ms += round((_time.perf_counter() - _t0) * 1000) - _elapsed_ms

        # Strip any remaining tool call artifacts from final response
        if response_text and ("tool_call" in response_text or "<tool_call>" in response_text):
            try:
                from bridges.tool_defs import strip_tool_calls
                response_text = strip_tool_calls(response_text)
            except Exception:
                pass

        _usage = llm_resp.get("usage", {})
        _completion_tokens = _usage.get("completion_tokens", 0)
        _tokens_per_sec = round(_completion_tokens / max(_elapsed_ms / 1000, 0.001), 1) if _completion_tokens else None

        # ── Citation enforcement gate ──────────────────────────
        citation_payload = {}
        if not request.system_prompt:
            # Skip citation enforcement for custom-system-prompt calls (revisions)
            try:
                from Conversations.threads.citations import enforce_citations
                response_text, cite_report = enforce_citations(
                    user_prompt=request.prompt,
                    response_text=response_text,
                    history_was_injected=bool(history_context),
                )
                citation_payload = cite_report.to_dict()
                if cite_report.valid_count:
                    logger.info(
                        f"📎 {cite_report.valid_count} valid citation(s), "
                        f"{cite_report.invalid_count} invalid"
                    )
                if cite_report.id_mismatch_count:
                    logger.warning(
                        f"⚠️  {cite_report.id_mismatch_count} citation(s) have "
                        f"id≠line mismatch"
                    )
            except Exception as e:
                logger.warning(f"Citation processing failed (non-fatal): {e}")

        model_identity = {
            "provider": "llama_cpp",
            "model": current_model_name or "unknown",
            "engine": "llama_cpp",
            "gpu": _gpu_info.get("gpu_name", "unknown"),
        }

        ai_log_result = log_message(
            sender="ai",
            content=response_text,
            branch=branch,
            model_identity=model_identity,
            conversation_id=str(current_conversation_id) if current_conversation_id else None,
        )
        logger.info(f"Logged conversation turn: msg {user_log_result['message_id']} → {ai_log_result['message_id']}")

        result = {
            "model": current_model_name,
            "created_at": now_utc_iso(),
            "response": response_text,
            "done": True,
            "side_chat_id": branch if branch != "main" else None,
            "user_message_id": user_log_result.get("message_id"),
            "ai_message_id": ai_log_result.get("message_id"),
            "inference_params": {
                "temperature": inf_temperature,
                "max_tokens": inf_max_tokens,
                "top_p": inf_top_p,
                "top_k": inf_top_k,
                "repeat_penalty": inf_repeat,
                "frequency_penalty": inf_freq_pen,
                "presence_penalty": inf_pres_pen,
                "seed": inf_seed,
                "mirostat_mode": inf_miro_mode,
            },
            "backend": {
                "engine": "llama_cpp",
                "gpu": _gpu_info.get("gpu_name"),
                "eval_duration_ms": _elapsed_ms,
                "tokens_per_second": _tokens_per_sec,
                "completion_tokens": _completion_tokens,
                "prompt_tokens": _usage.get("prompt_tokens", 0),
            },
        }
        if citation_payload:
            result["citations"] = citation_payload
        if retrieval_hits:
            result["retrieval_context"] = {
                "query": request.prompt[:200],
                "hits": retrieval_hits,
            }
        if _tool_trace:
            result["tool_trace"] = _tool_trace
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Generation failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/tags")
async def list_models():
    """List available GGUF models with active indicator."""
    global MODEL_REGISTRY
    MODEL_REGISTRY = _scan_gguf_models()
    models = []
    for name, info in MODEL_REGISTRY.items():
        models.append({
            "name": name,
            "filename": info.get("filename", ""),
            "path": info.get("path", ""),
            "size": info.get("size", 0),
            "size_gb": info.get("size_gb", 0),
            "active": (name == current_model_name),
            "family": info.get("family", ""),
            "parameter_size": info.get("parameter_size", ""),
            "quantization": info.get("quantization", ""),
        })
    return {"models": models}


# ── Inference config endpoints ──────────────────────────────────

@app.get("/api/inference/config")
async def get_inference_config():
    """Return current live inference parameters."""
    return {"config": dict(inference_config), "defaults": dict(INFERENCE_DEFAULTS)}


# ── System prompt & user profile endpoints ──────────────────────

def _save_clearbox_config_key(key: str, value):
    """Update a single key in clearbox.config.json and reload globals."""
    cfg = {}
    if CLEARBOX_CONFIG_PATH.exists():
        with open(CLEARBOX_CONFIG_PATH, encoding="utf-8") as _f:
            cfg = _json.load(_f)
    cfg[key] = value
    CLEARBOX_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CLEARBOX_CONFIG_PATH, "w", encoding="utf-8") as _f:
        _json.dump(cfg, _f, indent=2, ensure_ascii=False)
    _load_clearbox_config()


@app.get("/api/system-prompt")
async def get_system_prompt():
    """Return all editable system prompt pieces + computed auto pieces + assembled preview."""
    identity_role = ""
    if SYSTEM_IDENTITY and SYSTEM_IDENTITY.get("role"):
        identity_role = SYSTEM_IDENTITY["role"]
    archive_instruction = ARCHIVE_INSTRUCTION or _DEFAULT_ARCHIVE_INSTRUCTION
    user_profile = USER_PROFILE or {}

    yesterday_ctx = ""
    try:
        if is_first_message_of_day():
            yesterday_ctx = build_previous_context()
    except Exception:
        pass
    clock = now_utc_display()

    parts = []
    parts.append(identity_role or "You are a helpful assistant.")
    if user_profile:
        profile_lines = []
        for k in ["display_name", "role", "context", "style", "level", "notes"]:
            if user_profile.get(k):
                profile_lines.append(f"{k.replace('_', ' ').title()}: {user_profile[k]}")
        if profile_lines:
            parts.append("USER PROFILE:\n" + "\n".join(profile_lines))
    parts.append(archive_instruction)
    if yesterday_ctx:
        parts.append(yesterday_ctx)
    parts.append(clock)
    assembled = "\n\n".join(parts)

    return {
        "identity_role": identity_role,
        "archive_instruction": archive_instruction,
        "user_profile": user_profile,
        "auto": {
            "yesterday_context": yesterday_ctx,
            "clock": clock,
        },
        "assembled_preview": assembled,
        "char_count": len(assembled),
        "default_archive_instruction": _DEFAULT_ARCHIVE_INSTRUCTION,
    }


@app.post("/api/system-prompt")
async def set_system_prompt(request: dict):
    """Update identity and/or archive instruction. Hot-reloads globals."""
    updated = {}
    if "identity_role" in request:
        cfg = {}
        if CLEARBOX_CONFIG_PATH.exists():
            with open(CLEARBOX_CONFIG_PATH, encoding="utf-8") as _f:
                cfg = _json.load(_f)
        identity = cfg.get("identity", {})
        identity["role"] = request["identity_role"]
        _save_clearbox_config_key("identity", identity)
        updated["identity_role"] = request["identity_role"]
        logger.info(f"🌲 Identity role updated ({len(request['identity_role'])} chars)")

    if "archive_instruction" in request:
        _save_clearbox_config_key("archive_instruction", request["archive_instruction"])
        updated["archive_instruction"] = request["archive_instruction"]
        logger.info(f"📜 Archive instruction updated ({len(request['archive_instruction'])} chars)")

    return {"updated": updated, "status": "ok"}


@app.get("/api/user-profile")
async def get_user_profile():
    """Return current user profile."""
    return {"user_profile": USER_PROFILE or {}}


@app.post("/api/user-profile")
async def set_user_profile(request: dict):
    """Update user profile fields. Hot-reloads globals."""
    profile = request.get("user_profile", request)
    allowed = {"display_name", "role", "context", "style", "level", "notes"}
    clean = {k: v for k, v in profile.items() if k in allowed and v}
    _save_clearbox_config_key("user_profile", clean)
    if clean.get("display_name"):
        _save_clearbox_config_key("user_display_name", clean["display_name"])
    logger.info(f"👤 User profile updated: {list(clean.keys())}")
    return {"user_profile": clean, "status": "ok"}


@app.post("/api/inference/config")
async def set_inference_config(request: dict):
    """Update live inference parameters. Only provided keys are changed."""
    allowed = set(INFERENCE_DEFAULTS.keys())
    updated = {}
    for key, value in request.items():
        if key in allowed:
            inference_config[key] = value
            updated[key] = value
        else:
            logger.warning(f"Ignoring unknown inference param: {key}")
    logger.info(f"🎛️  Inference config updated: {updated}")
    return {"config": dict(inference_config), "updated": updated}


@app.post("/api/inference/reset")
async def reset_inference_config():
    """Reset all inference parameters to factory defaults."""
    inference_config.clear()
    inference_config.update(INFERENCE_DEFAULTS)
    logger.info("🎛️  Inference config reset to defaults")
    return {"config": dict(inference_config)}


@app.post("/api/model/switch")
async def switch_model(request: dict):
    """Hot-swap to a different model.

    Body: {"model": "gpt-oss:20b"}
    """
    model_name = request.get("model", "")
    if not model_name:
        raise HTTPException(status_code=400, detail="model name required")

    MODEL_REGISTRY.update(_scan_gguf_models())
    if model_name not in MODEL_REGISTRY:
        available = list(MODEL_REGISTRY.keys())
        raise HTTPException(
            status_code=404,
            detail=f"Model '{model_name}' not found. Available: {available}"
        )

    try:
        await asyncio.to_thread(set_active_model, model_name)
        return {
            "status": "ok",
            "model": current_model_name,
            "size_gb": MODEL_REGISTRY[current_model_name]["size_gb"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    ready = _llm_ready()
    health_info = {
        "status": "healthy" if ready else "degraded",
        "model_loaded": ready,
        "active_model": current_model_name,
        "available_models": list(MODEL_REGISTRY.keys()),
        "logging_mode": "unified",
        "logging_backend": "Conversations.threads",
        "user_display_name": USER_DISPLAY_NAME,
        "gpu": _gpu_info,
        "engine": "llama_cpp",
    }

    health_info["current_conversation_id"] = str(current_conversation_id) if current_conversation_id else None
    try:
        from Conversations.threads.daily_logger import get_today_stats
        stats = get_today_stats()
        health_info["today_stats"] = stats
    except Exception as e:
        health_info["today_stats"] = {"error": str(e)}

    return health_info


@app.get("/api/conversation/history")
async def get_conversation_history(day: Optional[str] = None, branch: str = "main"):
    """Get conversation history for UI display.

    Default (no param): today only.
    With ?day=YYYY-MM-DD: that specific day.
    """
    try:
        from Conversations.threads.reader import load_today, load_day
        from Conversations.threads.models import backfill_actor_seat

        selected_branch = (branch or "main").strip() or "main"

        if day:
            messages = load_day(day)
            target_day = day
        else:
            messages = load_today()
            target_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        if selected_branch not in {"all", "*"}:
            messages = [m for m in messages if m.branch == selected_branch]

        history = []
        for msg in messages:
            # Backfill actor/seat for legacy (pre-v2) records
            backfill_actor_seat(msg)

            entry = {
                "id": msg.id,
                "sender": msg.sender,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "branch": msg.branch,
                "model": msg.model.model if msg.model else None,
                # Envelope v2: authoritative identity
                "actor": msg.actor,
                "seat": msg.seat.model_dump() if msg.seat else None,
                # display_name is decorative only — never use for role
                "display_name": USER_DISPLAY_NAME if msg.actor == "user" else (
                    msg.seat.model if msg.seat else (
                        msg.model.model if msg.model else None
                    )
                ),
            }
            history.append(entry)

        try:
            day_cites = citation_store.get_day_cites_by_block(target_day)
        except Exception:
            day_cites = {}

        return {
            "messages": history,
            "count": len(history),
            "date": target_day,
            "mode": "unified",
            "branch": selected_branch,
            "window_days": 1,
            "user_display_name": USER_DISPLAY_NAME,
            "citations_by_block": day_cites,
        }
    except Exception as e:
        logger.exception("Failed to load conversation history")
        return {"messages": [], "count": 0, "error": str(e)}


@app.get("/api/conversation/days")
async def get_conversation_days():
    """List available conversation days (newest first) with message counts."""
    import re as _re
    _DATE_RE = _re.compile(r"^\d{4}-\d{2}-\d{2}$")
    try:
        from security.secure_storage import secure_count_lines
        days = []
        if CHAT_THREADS_DIR.exists():
            for p in sorted(CHAT_THREADS_DIR.glob("*.jsonl"), reverse=True):
                d = p.stem
                if _DATE_RE.match(d) and p.stat().st_size > 0:
                    try:
                        count = secure_count_lines(p)
                    except Exception:
                        count = 0
                    days.append({"day": d, "message_count": count})
        return {"days": days, "total": len(days)}
    except Exception as e:
        logger.exception("Failed to list conversation days")
        return {"days": [], "total": 0, "error": str(e)}


@app.get("/api/conversation/day/{day}")
async def get_conversation_day(day: str, branch: str = "main"):
    """Load a specific day's conversation (read-only explorer)."""
    import re as _re
    if not _re.match(r"^\d{4}-\d{2}-\d{2}$", day):
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    try:
        from Conversations.threads.reader import load_day
        from Conversations.threads.models import backfill_actor_seat

        selected_branch = (branch or "main").strip() or "main"
        messages = load_day(day)
        if selected_branch not in {"all", "*"}:
            messages = [m for m in messages if m.branch == selected_branch]
        history = []
        for msg in messages:
            backfill_actor_seat(msg)
            history.append({
                "id": msg.id,
                "sender": msg.sender,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "branch": msg.branch,
                "model": msg.model.model if msg.model else None,
                "actor": msg.actor,
                "seat": msg.seat.model_dump() if msg.seat else None,
                "display_name": USER_DISPLAY_NAME if msg.actor == "user" else (
                    msg.seat.model if msg.seat else (
                        msg.model.model if msg.model else None
                    )
                ),
            })

        try:
            day_cites = citation_store.get_day_cites_by_block(day)
        except Exception:
            day_cites = {}

        return {
            "messages": history,
            "count": len(history),
            "date": day,
            "mode": "explorer",
            "branch": selected_branch,
            "user_display_name": USER_DISPLAY_NAME,
            "citations_by_block": day_cites,
        }
    except Exception as e:
        logger.exception("Failed to load conversation day %s", day)
        return {"messages": [], "count": 0, "date": day, "error": str(e)}


def _auto_side_description(content: str) -> str:
    compact = " ".join((content or "").split())
    return normalize_side_chat_description(compact)


async def _start_side_chat(payload: dict) -> dict:
    from_day = (payload.get("from_day") or "").strip()
    message_id_raw = payload.get("message_id")
    content = (payload.get("content") or "").strip()
    actor = (payload.get("actor") or "assistant").strip() or "assistant"
    requested_description = (payload.get("description") or "").strip()

    if not from_day or not content:
        raise HTTPException(status_code=400, detail="from_day and content required")

    try:
        message_id = int(message_id_raw) if message_id_raw is not None else None
    except Exception:
        message_id = None

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    description = normalize_side_chat_description(requested_description or _auto_side_description(content))
    conv_id = str(current_conversation_id) if current_conversation_id else None

    side_meta = side_chat_store.create(
        main_day=today,
        source_day=from_day,
        source_message_id=message_id,
        actor=actor,
        description=description,
        content=content,
        conversation_id=conv_id,
    )
    side_chat_id = side_meta["side_chat_id"]

    main_link_text = f"SIDE CHAT -> {side_chat_id} | {description}"
    main_link = log_message(
        sender="ai",
        content=main_link_text,
        branch="main",
        kind="SIDE_CHAT_LINK",
        actor="system",
        conversation_id=conv_id,
    )

    side_seed_text = (
        f"Linked from {from_day}#{message_id if message_id is not None else '?'} ({actor}).\n"
        f"Summary: {description}\n\n"
        f"{content}"
    )
    side_seed = log_message(
        sender="ai",
        content=side_seed_text,
        branch=side_chat_id,
        fork_point=main_link.get("message_id"),
        parent=main_link.get("message_id"),
        kind="SIDE_CHAT_CONTEXT",
        actor="system",
        conversation_id=conv_id,
    )

    logger.info(
        "Created side chat %s from %s#%s (%d chars)",
        side_chat_id,
        from_day,
        message_id,
        len(content),
    )
    return {
        "ok": True,
        "side_chat_id": side_chat_id,
        "description": description,
        "main_link_message_id": main_link.get("message_id"),
        "side_seed_message_id": side_seed.get("message_id"),
        "main_branch": "main",
        "side_branch": side_chat_id,
    }


@app.post("/api/conversation/side/start")
async def start_side_chat(request: Request):
    """Create a side-chat branch and persist main<->side links."""
    body = await request.json()
    return await _start_side_chat(body)


@app.post("/api/conversation/bring_forward")
async def bring_forward(request: Request):
    """Legacy alias: converts bring-forward payload into a linked side-chat."""
    body = await request.json()
    result = await _start_side_chat(body)
    result["deprecated"] = "Use /api/conversation/side/start"
    return result


@app.get("/api/conversation/forwarded")
async def get_forwarded():
    """Deprecated endpoint retained for compatibility."""
    return {
        "contexts": [],
        "count": 0,
        "deprecated": "Forwarded queue removed. Use /api/conversation/side/start",
    }


@app.post("/api/conversation/clear_forwarded")
async def clear_forwarded():
    """Deprecated no-op retained for compatibility."""
    return {
        "ok": True,
        "cleared": 0,
        "deprecated": "Forwarded queue removed. Use /api/conversation/side/start",
    }


@app.get("/api/summary/previous")
async def get_previous_summary():
    """Return the most recent prior-day session debrief for UI display.

    The debrief contains citation coords ([ref YYYY-MM-DD:L##]) for
    fast tracing back to the original chat JSONL lines.
    """
    from datetime import date as _date
    import re as _re

    THREADS_DIR = CHAT_THREADS_DIR
    SUMMARIES_DIR = CHAT_SUMMARIES_DIR
    _DATE_RE = _re.compile(r"^\d{4}-\d{2}-\d{2}$")
    today_str = _date.today().isoformat()

    prior_day = None
    if THREADS_DIR.exists():
        for p in sorted(THREADS_DIR.glob("*.jsonl"), reverse=True):
            d = p.stem
            if _DATE_RE.match(d) and d < today_str and p.stat().st_size > 0:
                prior_day = d
                break

    if not prior_day:
        return {"has_debrief": False, "has_summary": False, "reason": "no_prior_sessions"}

    debrief_text = None
    debrief_path = SUMMARIES_DIR / f"{prior_day}.txt"
    if debrief_path.exists():
        txt = secure_read_text(debrief_path).strip()
        if txt:
            debrief_text = txt

    summary_set = set()
    if SUMMARIES_DIR.exists():
        for sp in SUMMARIES_DIR.glob("*.txt"):
            if _DATE_RE.match(sp.stem):
                summary_set.add(sp.stem)
    pending = 0
    if THREADS_DIR.exists():
        for tp in THREADS_DIR.glob("*.jsonl"):
            d2 = tp.stem
            if _DATE_RE.match(d2) and d2 < today_str and tp.stat().st_size > 0 and d2 not in summary_set:
                pending += 1

    return {
        "has_debrief": debrief_text is not None,
        "has_summary": debrief_text is not None,  # backward compat
        "date": prior_day,
        "debrief": debrief_text,
        "summary": debrief_text,  # backward compat
        "pending_days": pending,
        "reason": "ok" if debrief_text else "debrief_not_generated",
    }


@app.post("/api/summary/generate")
async def generate_summary(request: dict = {}):
    """Trigger summary generation for a specific date (or most recent unsummarized day)."""
    from datetime import date as _date
    import re as _re

    ROOT = Path(__file__).resolve().parent
    THREADS_DIR = CHAT_THREADS_DIR
    SUMMARIES_DIR = CHAT_SUMMARIES_DIR
    _DATE_RE = _re.compile(r"^\d{4}-\d{2}-\d{2}$")
    today_str = _date.today().isoformat()

    target_date = request.get("date") if isinstance(request, dict) else None

    if not target_date:
        summary_set = set()
        if SUMMARIES_DIR.exists():
            for sp in SUMMARIES_DIR.glob("*.txt"):
                if _DATE_RE.match(sp.stem):
                    summary_set.add(sp.stem)
        if THREADS_DIR.exists():
            for p in sorted(THREADS_DIR.glob("*.jsonl"), reverse=True):
                d = p.stem
                if _DATE_RE.match(d) and d < today_str and p.stat().st_size > 0 and d not in summary_set:
                    target_date = d
                    break

    if not target_date:
        return {"status": "nothing_to_summarize"}

    try:
        from Conversations.threads.summarizer import generate_debrief
        debrief_text = generate_debrief(target_date)
        if debrief_text:
            return {"status": "ok", "date": target_date, "debrief": debrief_text, "summary": debrief_text}
        else:
            return {"status": "failed", "date": target_date, "error": "Debrief generation returned empty"}
    except Exception as e:
        logger.exception(f"Debrief generation failed for {target_date}")
        return {"status": "error", "date": target_date, "error": str(e)}


@app.post("/api/conversation/new")
async def new_conversation():
    """Start a new conversation (resets conversation_id)."""
    global current_conversation_id
    old_id = current_conversation_id
    current_conversation_id = None
    logger.info(f"Conversation reset: {old_id} → None (will start fresh on next message)")

    try:
        _session.delete("current_conversation_id")
    except Exception as e:
        logger.warning(f"Session persist (conversation reset) failed: {e}")

    return {
        "status": "reset",
        "previous_conversation_id": str(old_id) if old_id else None,
        "next_message_will_start_new": True
    }


@app.get("/api/conversation/current")
async def get_current_conversation():
    """Get current conversation ID."""
    return {
        "conversation_id": str(current_conversation_id) if current_conversation_id else None,
        "status": "active" if current_conversation_id else "no_active_conversation"
    }


# ── Citation endpoints ──────────────────────────────────────

class CitationFlagRequest(BaseModel):
    cite: str
    reason: str
    note: Optional[str] = None
    citation_meta: Optional[dict] = None


@app.post("/api/citations/flag")
async def flag_citation(req: CitationFlagRequest):
    """Append a user citation flag to the audit ledger."""
    _SEC_CITATION_FLAGS.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "flagged_at": now_utc_iso(),
        "cite": req.cite,
        "reason": req.reason,
        "note": req.note,
        "citation_meta": req.citation_meta,
    }

    try:
        secure_append_line(_SEC_CITATION_FLAGS, json.dumps(record, ensure_ascii=False))
        logger.info(f"🚩 Citation flagged: {req.cite} ({req.reason})")
        return {"ok": True, "cite": req.cite}
    except Exception as e:
        logger.exception("Citation flag write failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/citations/resolve")
async def resolve_citation(cite: Optional[str] = None, day: Optional[str] = None):
    """Resolve a single citation or retrieve a full day's messages."""
    import re as _re

    threads_dir = CHAT_THREADS_DIR

    if cite:
        # Try date-prefixed block format: YYYY-MM-DD:SID:N:BLK:N
        block_match = _re.match(r"^(\d{4}-\d{2}-\d{2}):SID:(\d+):BLK:(\d+)$", cite)
        # Also accept legacy SID:N:BLK:N (no date — search recent days)
        sid_match = _re.match(r"^SID:(\d+):BLK:(\d+)$", cite) if not block_match else None

        if block_match or sid_match:
            from datetime import datetime, timedelta

            if block_match:
                target_day = block_match.group(1)
                server_id = int(block_match.group(2))
                blk_idx = int(block_match.group(3))
                search_days = [target_day]
            else:
                server_id = int(sid_match.group(1))
                blk_idx = int(sid_match.group(2))
                today = datetime.now()
                search_days = [(today - timedelta(days=d)).strftime("%Y-%m-%d") for d in range(7)]

            for check_day in search_days:
                fp = threads_dir / f"{check_day}.jsonl"
                if not fp.exists():
                    continue
                try:
                    lines = secure_read_lines(fp)
                    for raw in lines:
                        raw = raw.strip()
                        if not raw:
                            continue
                        try:
                            obj = json.loads(raw)
                            msg_server_id = obj.get("serverId") or obj.get("server_id") or obj.get("id")
                            if msg_server_id == server_id:
                                blocks = obj.get("blocks", [])
                                if blk_idx < len(blocks):
                                    block = blocks[blk_idx]
                                    content = block.get("text") or block.get("content", "")
                                    return {
                                        "cite": cite,
                                        "found": True,
                                        "content": content,
                                        "sender": obj.get("sender"),
                                        "branch": obj.get("branch"),
                                        "timestamp": obj.get("timestamp"),
                                    }
                        except json.JSONDecodeError:
                            continue
                except Exception:
                    continue

            return {"cite": cite, "found": False, "content": None}

        # Try legacy day:line format
        m = _re.match(r"^(\d{4}-\d{2}-\d{2}):L(\d+)$", cite)
        if not m:
            raise HTTPException(status_code=400, detail=f"Invalid citation format: {cite}")

        cite_day = m.group(1)
        cite_line = int(m.group(2))
        fp = threads_dir / f"{cite_day}.jsonl"

        if not fp.exists():
            return {"cite": cite, "found": False, "content": None}

        try:
            lines = secure_read_lines(fp)
            for i, raw in enumerate(lines, start=1):
                if i == cite_line:
                    obj = json.loads(raw.strip())
                    return {
                        "cite": cite,
                        "found": True,
                        "content": obj.get("content", ""),
                        "sender": obj.get("sender"),
                        "branch": obj.get("branch"),
                        "timestamp": obj.get("timestamp"),
                        "hash": obj.get("hash"),
                        "id": obj.get("id"),
                    }
            return {"cite": cite, "found": False, "content": None}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    if day:
        if not _re.match(r"^\d{4}-\d{2}-\d{2}$", day):
            raise HTTPException(status_code=400, detail=f"Invalid day format: {day}")

        fp = threads_dir / f"{day}.jsonl"
        if not fp.exists():
            return {"day": day, "found": False, "messages": []}

        messages = []
        try:
            lines = secure_read_lines(fp)
            for raw in lines:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    obj = json.loads(raw)
                    messages.append({
                        "sender": obj.get("sender", "unknown"),
                        "content": obj.get("content", ""),
                        "branch": obj.get("branch", "main"),
                        "timestamp": obj.get("timestamp"),
                        "id": obj.get("id"),
                    })
                except json.JSONDecodeError:
                    continue
            return {"day": day, "found": True, "messages": messages, "count": len(messages)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    raise HTTPException(status_code=400, detail="Provide ?cite= or ?day= parameter")


# ── Citation persistence endpoints ─────────────────────────

class CitationAttachRequest(BaseModel):
    day: str
    message_id: str
    block_id: str
    block_ordinal: int
    canonical: str
    subject: Optional[str] = None
    note: Optional[str] = None
    source: str = "manual"


class CitationDetachRequest(BaseModel):
    day: str
    message_id: str
    block_id: str
    cite_id: str


@app.post("/api/citations/attach")
async def attach_citation(req: CitationAttachRequest):
    """Persist a citation to the day-sharded sidecar."""
    try:
        record = citation_store.attach(
            day=req.day,
            message_id=req.message_id,
            block_id=req.block_id,
            block_ordinal=req.block_ordinal,
            canonical=req.canonical,
            subject=req.subject,
            note=req.note,
            source=req.source,
        )
        logger.info(f"\U0001f4cc Citation attached: {req.canonical} -> {req.message_id}:{req.block_id}")
        return {"ok": True, "cite": record}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.exception("Citation attach failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/citations/detach")
async def detach_citation(req: CitationDetachRequest):
    """Remove a citation from a block."""
    try:
        removed = citation_store.detach(
            day=req.day,
            message_id=req.message_id,
            block_id=req.block_id,
            cite_id=req.cite_id,
        )
        if not removed:
            raise HTTPException(status_code=404, detail="Citation not found on that block")
        logger.info(f"\U0001f5d1\ufe0f Citation detached: {req.cite_id} from {req.message_id}:{req.block_id}")
        return {"ok": True, "cite_id": req.cite_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Citation detach failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/citations/block")
async def get_block_citations(
    day: str = Query(...),
    message_id: str = Query(...),
    block_id: str = Query(...),
):
    """Get all citations attached to a specific block (hot path)."""
    try:
        cites = citation_store.get_block_cites(day, message_id, block_id)
        return {"cites": cites, "count": len(cites)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/citations/id/{cite_id}")
async def get_citation_by_id(cite_id: str):
    """Resolve a single citation by its ID."""
    record = citation_store.get_citation(cite_id)
    if not record:
        raise HTTPException(status_code=404, detail="cite_id not found")
    return {"cite": record}


class CitationSearchRequest(BaseModel):
    query: str
    limit: int = 5


@app.post("/api/citations/search")
async def search_citations(req: CitationSearchRequest):
    """Search existing citations by keyword matching on subject, note, and coord.

    Simple text search across recent citation sidecars. Returns ranked results.
    """
    query_lower = req.query.lower().split()
    if not query_lower:
        return {"results": [], "count": 0}

    results = []
    try:
        # Search recent 14 days of sidecars
        all_days = list(reversed(citation_store.list_days()))[:14]
        for day in all_days:
            sc = citation_store.load_day(day)
            for cid, rec in sc.by_id.items():
                # Build searchable text from record fields
                haystack = " ".join(filter(None, [
                    rec.get("subject", ""),
                    rec.get("note", ""),
                    rec.get("coord", ""),
                ])).lower()
                # Score: count how many query tokens match
                score = sum(1 for t in query_lower if t in haystack)
                if score > 0:
                    results.append({
                        "cite_id": cid,
                        "coord": rec.get("coord"),
                        "subject": rec.get("subject"),
                        "note": rec.get("note"),
                        "snippet": (rec.get("subject") or rec.get("note") or rec.get("coord", ""))[:120],
                        "day": day,
                        "score": score,
                    })

        # Sort by score desc, take top N
        results.sort(key=lambda x: -x["score"])
        results = results[:req.limit]
    except Exception as e:
        logger.exception("Citation search failed")
        raise HTTPException(status_code=500, detail=str(e))

    return {"results": results, "count": len(results)}


class AutoCiteRequest(BaseModel):
    block_text: str
    limit: int = 5


@app.post("/api/citations/autocite")
async def autocite_llm(req: AutoCiteRequest):
    """Use the local LLM to find related citations for a block.

    Sends the block text + recent citation context to the LLM with a
    creative prompt. The LLM reasons about relationships and returns
    structured suggestions. Prompt-first approach — no hardcoded logic.
    """
    if not _llm_ready() or not current_model_name:
        raise HTTPException(status_code=503, detail="LLM not available")

    # Gather recent citations as context (last 7 days)
    context_lines = []
    try:
        all_days = list(reversed(citation_store.list_days()))[:7]
        for day in all_days:
            sc = citation_store.load_day(day)
            for cid, rec in sc.by_id.items():
                subj = rec.get("subject") or ""
                note = rec.get("note") or ""
                coord = rec.get("coord", "")
                context_lines.append(f"- {coord}: {subj} {note}".strip())
                if len(context_lines) >= 30:
                    break
            if len(context_lines) >= 30:
                break
    except Exception:
        pass

    citations_context = "\n".join(context_lines) if context_lines else "(no existing citations)"

    system_prompt = (
        "You are a citation analyst for the Clearbox AI system. "
        "Your job: given a text block and a list of existing citations, "
        "identify which existing citations are related to the block. "
        "Also suggest what subject/topic tags would be appropriate.\n\n"
        "Respond ONLY in this JSON format, no other text:\n"
        '{"related": [{"coord": "...", "reason": "..."}], '
        '"suggested_subject": "...", "suggested_note": "..."}\n\n'
        "If no citations relate, return empty related array."
    )

    user_prompt = (
        f"## Text Block\n{req.block_text[:800]}\n\n"
        f"## Existing Citations (last 7 days)\n{citations_context}\n\n"
        f"Find up to {req.limit} related citations and suggest tags."
    )

    try:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        llm_resp = await asyncio.to_thread(
            _run_llm_inference, messages, temperature=0.3, max_tokens=500
        )
        response_text = llm_resp["choices"][0]["message"]["content"]

        # Try to parse JSON from LLM response
        import re as _re
        json_match = _re.search(r"\{.*\}", response_text, _re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            return {
                "related": parsed.get("related", [])[:req.limit],
                "suggested_subject": parsed.get("suggested_subject"),
                "suggested_note": parsed.get("suggested_note"),
                "raw": response_text,
            }
        else:
            return {"related": [], "suggested_subject": None, "suggested_note": None, "raw": response_text}

    except json.JSONDecodeError:
        return {"related": [], "suggested_subject": None, "suggested_note": None, "raw": response_text}
    except Exception as e:
        logger.exception("Auto-cite LLM failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/citations/day/{day}")
async def get_day_citations(day: str):
    """Get all citations for a day, grouped by block key (archive hydration)."""
    try:
        by_block = citation_store.get_day_cites_by_block(day)
        return {"day": day, "by_block": by_block, "count": sum(len(v) for v in by_block.values())}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Citations Manager endpoints (browse / health / edit) ──────


@app.get("/api/citations/all")
async def get_all_citations(cursor: Optional[str] = None, limit: int = 5):
    """Paginated browse: all citations across all days, newest first.

    Query params:
        cursor: day string to start AFTER (exclusive). Omit for first page.
        limit:  max days per page (default 5).
    Returns: { days, items, next_cursor, total_days }
    """
    try:
        return citation_store.get_all_paginated(cursor=cursor, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/citations/distribution")
async def citations_distribution():
    """Citation count per day — for Explorer day-distribution chart and date strip."""
    try:
        return citation_store.distribution()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/citations/health")
async def citations_health(days: Optional[int] = None):
    """Structural health check across citation sidecars.

    Query params:
        days: Max recent days to scan. Omit to scan all.
    """
    try:
        return citation_store.health_check(days=days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CitationEditRequest(BaseModel):
    cite_id: str
    subject: Optional[str] = None
    note: Optional[str] = None
    coord: Optional[str] = None


@app.post("/api/citations/edit")
async def edit_citation(req: CitationEditRequest):
    """Update mutable fields on a citation (subject, note, coord)."""
    fields = {}
    if req.subject is not None:
        fields["subject"] = req.subject
    if req.note is not None:
        fields["note"] = req.note
    if req.coord is not None:
        fields["coord"] = req.coord

    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    try:
        updated = citation_store.update_cite(req.cite_id, fields)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Citation not found: {req.cite_id}")
        return {"ok": True, "cite": updated}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Citation edit failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class CitationDeleteRequest(BaseModel):
    cite_id: str
    hard: bool = False


@app.post("/api/citations/delete")
async def delete_citation(req: CitationDeleteRequest):
    """Delete a citation. hard=false detaches, hard=true removes from all indexes."""
    try:
        if req.hard:
            removed = citation_store.hard_delete(req.cite_id)
        else:
            # Soft delete: find the cite, detach it from its block
            rec = citation_store.get_citation(req.cite_id)
            if not rec:
                raise HTTPException(status_code=404, detail=f"Citation not found: {req.cite_id}")
            day = rec.get("day", "")
            msg_id = rec.get("message_id", "")
            block_id = rec.get("block_id", "")
            removed = citation_store.detach(day, msg_id, block_id, req.cite_id)

        if not removed:
            raise HTTPException(status_code=404, detail=f"Citation not found: {req.cite_id}")
        return {"ok": True, "cite_id": req.cite_id, "hard": req.hard}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Citation delete failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Note persistence endpoints ─────────────────────────────────

class NoteAttachRequest(BaseModel):
    day: str
    message_id: str
    block_id: str
    block_ordinal: int
    note: str


class NoteDetachRequest(BaseModel):
    day: str
    message_id: str
    block_id: str
    note_id: str


@app.post("/api/notes/attach")
async def attach_note(req: NoteAttachRequest):
    """Persist a note to the day-sharded sidecar."""
    try:
        record = note_store.attach(
            day=req.day,
            message_id=req.message_id,
            block_id=req.block_id,
            block_ordinal=req.block_ordinal,
            note_text=req.note,
        )
        logger.info(f"Note attached: {req.message_id}:{req.block_id}")
        return {"ok": True, "note": record}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.exception("Note attach failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notes/detach")
async def detach_note(req: NoteDetachRequest):
    """Remove a note from a block."""
    try:
        removed = note_store.detach(
            day=req.day,
            message_id=req.message_id,
            block_id=req.block_id,
            note_id=req.note_id,
        )
        if not removed:
            raise HTTPException(status_code=404, detail="Note not found on that block")
        logger.info(f"Note detached: {req.note_id} from {req.message_id}:{req.block_id}")
        return {"ok": True, "note_id": req.note_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Note detach failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notes/block")
async def get_block_notes(
    day: str = Query(...),
    message_id: str = Query(...),
    block_id: str = Query(...),
):
    """Get all notes attached to a specific block."""
    try:
        notes = note_store.get_block_notes(day, message_id, block_id)
        return {"notes": notes, "count": len(notes)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class NoteEditRequest(BaseModel):
    note_id: str
    note: str


class NoteDeleteRequest(BaseModel):
    note_id: str


@app.get("/api/notes/all")
async def get_all_notes(
    cursor: Optional[str] = Query(None),
    limit: int = Query(5, ge=1, le=50),
):
    """Paginated note browse (newest day first)."""
    return note_store.get_all_paginated(cursor=cursor, limit=limit)


@app.get("/api/notes/distribution")
async def note_distribution():
    """Note count per day for distribution chart."""
    return note_store.distribution()


@app.post("/api/notes/edit")
async def edit_note(req: NoteEditRequest):
    """Update a note's text."""
    try:
        rec = note_store.update_note(req.note_id, req.note)
        if not rec:
            raise HTTPException(status_code=404, detail="Note not found")
        return {"ok": True, "note": rec}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Note edit failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notes/delete")
async def delete_note(req: NoteDeleteRequest):
    """Permanently remove a note."""
    try:
        removed = note_store.hard_delete(req.note_id)
        if not removed:
            raise HTTPException(status_code=404, detail="Note not found")
        return {"ok": True, "note_id": req.note_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Note delete failed")
        raise HTTPException(status_code=500, detail=str(e))


# ── Citation-Map Library endpoints ────────────────────────────

from Conversations.threads.map_manager import map_manager


class CitationCreateRequest(BaseModel):
    content: str
    filename: str
    metadata: Optional[dict] = None


class MapCreateRequest(BaseModel):
    cite_id: str
    window_size: int = 6
    device: str = "cpu"


class MapQueryRequest(BaseModel):
    keywords: List[str]
    limit: int = 10


@app.post("/api/library/citations/create")
async def create_citation_endpoint(req: CitationCreateRequest, request: Request):
    """Create citation for uploaded document (idempotent)."""
    try:
        citation = map_manager.create_citation(
            content=req.content,
            filename=req.filename,
            metadata=req.metadata
        )
        logger.info(f"📎 Citation created: {citation.cite_id} ({citation.filename})")
        return {
            "cite_id": citation.cite_id,
            "canonical": citation.canonical,
            "filename": citation.filename,
            "filesize": citation.filesize,
            "uploaded_at": citation.uploaded_at
        }
    except Exception as e:
        logger.exception("Citation creation failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/library/citations")
async def list_citations_endpoint(limit: int = 100):
    """List all citations in library."""
    try:
        citations = map_manager.list_citations(limit=limit)
        return {
            "citations": [
                {
                    "cite_id": c.cite_id,
                    "canonical": c.canonical,
                    "filename": c.filename,
                    "filesize": c.filesize,
                    "uploaded_at": c.uploaded_at,
                    "content_preview": c.content_preview
                }
                for c in citations
            ],
            "count": len(citations)
        }
    except Exception as e:
        logger.exception("List citations failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/library/citations/{cite_id}")
async def get_citation_endpoint(cite_id: str):
    """Get citation details."""
    citation = map_manager.get_citation(cite_id)
    if not citation:
        raise HTTPException(status_code=404, detail="Citation not found")

    return {
        "cite_id": citation.cite_id,
        "canonical": citation.canonical,
        "filename": citation.filename,
        "filesize": citation.filesize,
        "uploaded_at": citation.uploaded_at,
        "source_hash": citation.source_hash,
        "content_preview": citation.content_preview,
        "metadata": citation.metadata
    }


@app.get("/api/library/citations/{cite_id}/content")
async def get_citation_content_endpoint(cite_id: str):
    """Get full text content for a citation (used by grove ingestion)."""
    content = map_manager.get_citation_content(cite_id)
    if not content:
        raise HTTPException(status_code=404, detail="Citation content not found")
    return {"cite_id": cite_id, "content": content}


@app.post("/api/library/maps/create")
async def create_map_endpoint(req: MapCreateRequest, request: Request):
    """Create 6-1-6 map for a cited document."""
    try:
        # Load citation content
        content = map_manager.get_citation_content(req.cite_id)
        if not content:
            raise HTTPException(status_code=404, detail="Citation content not found")

        # Run 6-1-6 mapping via bridge server
        bridge_url = f"{_PROTO}://127.0.0.1:5050/api/map"
        try:
            bridge_resp = httpx.post(
                bridge_url,
                json={"text": content, "source": req.cite_id, "device": req.device},
                timeout=60.0,
                verify=not _TLS,  # skip cert verify for self-signed
            )
            if bridge_resp.status_code != 200:
                raise Exception(f"Bridge mapping failed: {bridge_resp.status_code}")

            map_data = bridge_resp.json()
        except httpx.ConnectError:
            raise HTTPException(
                status_code=503,
                detail="Clearbox Bridge not reachable at localhost:5050. Start bridge server first."
            )

        # Store map with citation link
        map_record = map_manager.create_map(
            cite_id=req.cite_id,
            map_data=map_data,
            window_size=req.window_size
        )

        logger.info(f"🗺️  Map created: {map_record.map_id} for {req.cite_id}")

        return {
            "map_id": map_record.map_id,
            "cite_id": map_record.cite_id,
            "created_at": map_record.created_at,
            "window_size": map_record.window_size,
            "stats": map_record.stats
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Map creation failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/library/maps")
async def list_maps_endpoint(cite_id: Optional[str] = None, limit: int = 100):
    """List maps (optionally filtered by citation)."""
    try:
        maps = map_manager.list_maps(cite_id=cite_id, limit=limit)
        return {
            "maps": [
                {
                    "map_id": m.map_id,
                    "cite_id": m.cite_id,
                    "created_at": m.created_at,
                    "window_size": m.window_size,
                    "stats": m.stats
                }
                for m in maps
            ],
            "count": len(maps)
        }
    except Exception as e:
        logger.exception("List maps failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/library/maps/{map_id}")
async def get_map_endpoint(map_id: str):
    """Get full map data by map_id or cite_id.

    First tries to interpret as map_id. If not found and looks like cite_id,
    tries to find the most recent map for that citation.
    """
    # Try as map_id first
    map_record = map_manager.get_map(map_id)

    # If not found and looks like a cite_id, find map for that citation
    if not map_record and map_id.startswith("cite_"):
        maps = map_manager.list_maps(cite_id=map_id, limit=1)
        if maps:
            map_record = maps[0]
            map_id = map_record.map_id

    if not map_record:
        raise HTTPException(status_code=404, detail="Map not found")

    map_data = map_manager.get_map_data(map_id)
    if not map_data:
        raise HTTPException(status_code=404, detail="Map data file not found")

    return map_data


@app.post("/api/library/query")
async def query_maps_endpoint(req: MapQueryRequest):
    """Search maps by keywords."""
    try:
        results = map_manager.query_maps(req.keywords, limit=req.limit)
        return {
            "query": req.keywords,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        import traceback
        print(f"\n❌ ERROR in /api/library/query: {repr(e)}")
        traceback.print_exc()
        logger.exception("Map query failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/library/summary")
async def library_summary_endpoint():
    """Get library statistics."""
    try:
        summary = map_manager.get_library_summary()
        return summary
    except Exception as e:
        logger.exception("Library summary failed")
        raise HTTPException(status_code=500, detail=str(e))


# ── Authentication endpoints ──────────────────────────────────

from security.auth import (
    has_registered_credential, validate_session, revoke_session,
)
from security.middleware import COOKIE_NAME


@app.get("/api/auth/status")
async def auth_status(request: Request):
    """Check if caller is authenticated and if credentials exist."""
    from fastapi import Request as _Req
    token = request.cookies.get(COOKIE_NAME)
    return {
        "authenticated": validate_session(token),
        "has_credential": has_registered_credential(),
    }


@app.post("/api/auth/logout")
async def auth_logout(request: Request):
    """Revoke session and clear cookie."""
    from fastapi import Request as _Req
    from fastapi.responses import JSONResponse as _JSONResponse
    token = request.cookies.get(COOKIE_NAME)
    if token:
        revoke_session(token)
    response = _JSONResponse(content={"ok": True})
    response.delete_cookie(key=COOKIE_NAME, path="/")
    logger.info("🔒 Session ended")
    return response


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Local LLM Server (llama-cpp-python direct)")
    parser.add_argument("--host", default=None, help="Host to bind")
    parser.add_argument("--port", default=11435, type=int, help="Port to bind (default 11435)")
    args = parser.parse_args()

    # Read bind host from config if not passed via CLI
    _llm_config = {}
    try:
        with open(CLEARBOX_CONFIG_PATH, encoding="utf-8") as _f:
            _llm_config = _json.load(_f).get("server", {})
    except Exception:
        pass
    if args.host is None:
        args.host = _llm_config.get("host", "127.0.0.1")

    if port_in_use("127.0.0.1", args.port) or port_in_use("localhost", args.port):
        logger.error(f"❌ Port {args.port} is already in use")
        logger.error(f"   Kill the process: Get-NetTCPConnection -LocalPort {args.port} | Stop-Process -Id {{$_.OwningProcess}} -Force")
        sys.exit(1)

    gpu = _gpu_query()
    MODEL_REGISTRY.update(_scan_gguf_models())

    print("🧠 Clearbox AI Studio — Local LLM Server v2.5.0 (llama-cpp-python direct)")
    print("=" * 60)
    print(f"Engine:    llama-cpp-python (n_gpu_layers=-1, full GPU)")
    print(f"Models:    {list(MODEL_REGISTRY.keys()) if MODEL_REGISTRY else f'NONE — place .gguf files in {MODELS_DIR}'}")
    if gpu.get("gpu_detected"):
        print(f"GPU:       ✅ {gpu.get('gpu_name', 'detected')} ({gpu.get('vram_mb', '?')} MB VRAM)")
    else:
        print(f"GPU:       ⚠️  Not detected via bridges.gpu_backend")
    _ep_proto = "https" if _llm_config.get("tls", False) else "http"
    print(f"Endpoint:  {_ep_proto}://{args.host}:{args.port}/api/generate")
    print(f"Switch:    POST /api/model/switch")
    print(f"✅ Port {args.port} is available")
    print("=" * 60)

    # TLS if configured
    ssl_kw = {}
    if _llm_config.get("tls", False):
        try:
            from security.tls import ensure_tls
            tls_result = ensure_tls()
            if tls_result:
                ssl_kw["ssl_certfile"] = tls_result[0]
                ssl_kw["ssl_keyfile"] = tls_result[1]
                print(f"TLS:       enabled ({tls_result[0]})")
        except Exception as e:
            print(f"TLS:       setup failed, plain HTTP ({e})")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info", **ssl_kw)
