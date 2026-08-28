# Multi-AI Orchestrator — Clearbox Plugin + VSCode Extension
# See CONTRACT.md for full boundary contract

# Clearbox plugin runner exports (used when mounted via bridge)
try:
    from .api.multi_ai_api import ROUTES
    from .api.multi_ai_api import handle_chat, handle_sessions, handle_session, handle_help
    __all__ = ["ROUTES", "handle_chat", "handle_sessions", "handle_session", "handle_help"]
except ImportError:
    # Running standalone as VSCode extension — Clearbox not required
    ROUTES = {}
    __all__ = ["ROUTES"]
