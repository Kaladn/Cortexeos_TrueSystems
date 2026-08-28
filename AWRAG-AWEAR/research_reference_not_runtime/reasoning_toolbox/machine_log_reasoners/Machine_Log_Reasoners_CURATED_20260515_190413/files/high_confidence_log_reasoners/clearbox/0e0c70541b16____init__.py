# visual_io — Screen capture and vector analysis
# Clearbox AI Studio Plugin — mounts at /api/visual_io
# See CONTRACT.md for full boundary contract and API surface

from .api.router import router, plugin_post

__all__ = ["router", "plugin_post"]

VERSION = "0.1.0"
