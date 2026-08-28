# netlog — Maniac-level internet traffic logging
# Clearbox AI Studio Plugin — mounts at /api/netlog
# See CONTRACT.md for full boundary contract and API surface

from .api.router import router, plugin_post

__all__ = ["router", "plugin_post"]

VERSION = "0.1.0"
