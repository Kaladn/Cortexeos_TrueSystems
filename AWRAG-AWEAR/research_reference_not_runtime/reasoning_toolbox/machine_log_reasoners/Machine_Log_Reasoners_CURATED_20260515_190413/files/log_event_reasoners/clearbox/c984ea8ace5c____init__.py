# audio_io — Live mic/speaker capture with MFCC fingerprinting
# Clearbox AI Studio Plugin — mounts at /api/audio_io
# See CONTRACT.md for full boundary contract and API surface

from .api.router import router, plugin_post

__all__ = ["router", "plugin_post"]

VERSION = "0.1.0"
