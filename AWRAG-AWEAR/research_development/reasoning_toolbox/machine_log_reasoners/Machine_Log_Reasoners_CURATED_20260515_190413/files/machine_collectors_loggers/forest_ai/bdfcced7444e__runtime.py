'''
Core module for loading and managing the layered configuration of Forest AI.
'''

import os
import json
from pathlib import Path

class ConfigLoader:
    '''
A class to manage the layered configuration of the Forest AI system.

    It loads configuration from multiple sources in a specific order of precedence:
    1. defaults.json (base)
    2. profile.json (e.g., dev.json, prod.json)
    3. forest.config.json (user overrides)
    4. Environment variables (highest precedence)
    '''

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.config_path = base_path / "config"
        self.user_config_path = base_path / "forest.config.json"
        self.runtime_vars_path = self.config_path / "runtime_vars.json"

        self.config = self._load_config()

    def _load_config(self) -> dict:
        '''Loads the configuration from all sources.'''
        # 1. Load defaults
        defaults_path = self.config_path / "defaults.json"
        if not defaults_path.exists():
            raise FileNotFoundError(f"Critical: Default config not found at {defaults_path}")
        with open(defaults_path, "r") as f:
            config = json.load(f)

        # 2. Load runtime vars to find the active profile
        active_profile = "dev" # Default to dev if not specified
        if self.runtime_vars_path.exists():
            with open(self.runtime_vars_path, "r") as f:
                runtime_vars = json.load(f)
                active_profile = runtime_vars.get("active_profile", active_profile)

        # 3. Load and merge the active profile
        profile_path = self.config_path / "profiles" / f"{active_profile}.json"
        if profile_path.exists():
            with open(profile_path, "r") as f:
                profile_config = json.load(f)
                self._deep_merge(config, profile_config)

        # 4. Load and merge user config
        if self.user_config_path.exists():
            with open(self.user_config_path, "r") as f:
                user_config = json.load(f)
                self._deep_merge(config, user_config)

        # 5. Override with environment variables (e.g., FOREST_LOG_LEVEL=debug)
        for key, value in os.environ.items():
            if key.startswith("FOREST_"):
                # Convert FOREST_SOME_KEY to some.key
                config_key = key.replace("FOREST_", "").lower().replace("_", ".")
                self._set_nested_key(config, config_key, value)

        return config

    def get(self, key: str, default=None):
        '''Retrieves a configuration value using dot notation.'''
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value

    def _deep_merge(self, base: dict, new: dict):
        '''Recursively merges dictionaries.'''
        for key, value in new.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _set_nested_key(self, d: dict, key: str, value):
        '''Sets a value in a nested dictionary using dot notation.'''
        keys = key.split('.')
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        # Attempt to parse value as JSON (for bools, numbers)
        try:
            d[keys[-1]] = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            d[keys[-1]] = value

# Example usage (would be in launch.py)
if __name__ == "__main__":
    # Assuming the script is run from the project root
    project_root = Path(__file__).parent.parent
    config_loader = ConfigLoader(project_root)
    print("Loaded Config:", json.dumps(config_loader.config, indent=2))
    print("\nLog Level:", config_loader.get("log.level"))
    print("Server Port:", config_loader.get("server.port"))

