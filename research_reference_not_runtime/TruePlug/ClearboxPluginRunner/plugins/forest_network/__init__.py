"""Forest Network Plugin — Phase 1.

Authenticated bridge-to-bridge file sharing.
Mounts at /api/network/ on Forest AI Bridge.

Phase 1 scope:  browse, read, hash, write + auth + allow_roots security.
Phase 2 scope:  directory sync + delta + integrity verification.
"""

PLUGIN_ID = "forest_network"
PLUGIN_VERSION = "1.0.0"
PLUGIN_PHASE = 1
