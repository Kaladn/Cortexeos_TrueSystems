from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


@dataclass(frozen=True)
class ClearboxSocialConfig:
    plugin_id: str = "clearbox_ai_social"
    api_prefix: str = "/api/clearbox-social"
    display_name: str = "Clearbox AI Social"

    # Keep this standalone and branded cleanly.
    data_root_env: str = "CLEARBOX_AI_SOCIAL_ROOT"
    default_subdir: str = "ClearboxAISocial"

    enable_manual_sync: bool = True
    enable_listings: bool = True
    enable_profile: bool = True

    @property
    def data_root(self) -> Path:
        override = os.environ.get(self.data_root_env)
        if override:
            return Path(override).expanduser().resolve()
        return (Path.home() / self.default_subdir).resolve()

    @property
    def identity_dir(self) -> Path:
        return self.data_root / "identity"

    @property
    def profile_dir(self) -> Path:
        return self.data_root / "profile"

    @property
    def marketplace_dir(self) -> Path:
        return self.data_root / "marketplace"

    @property
    def peers_dir(self) -> Path:
        return self.data_root / "peers"


CONFIG = ClearboxSocialConfig()
