"""Configuration for the TrueCore help subsystem."""

from __future__ import annotations

import os
from pathlib import Path


def load_help_config() -> dict:
    repo_root = Path(__file__).resolve().parent.parent.parent
    truecore_root = repo_root / "truecore"
    help_root = Path(os.getenv("TRUECORE_HELP_DIR", truecore_root / "data" / "help"))

    return {
        "repo_root": repo_root,
        "truecore_root": truecore_root,
        "help_root": help_root,
        "agent_dir": Path(os.getenv("TRUECORE_HELP_AGENT_DIR", truecore_root / "live_agents" / "AGENTS" / "agents")),
        "mirror_dir": help_root / "mirror",
        "index_path": help_root / "code_index.json",
        "manifest_path": help_root / "mirror_manifest.jsonl",
        "content_path": Path(os.getenv("TRUECORE_HELP_CONTENT", Path(__file__).resolve().parent / "content" / "help_content.json")),
        "system_prompt_path": Path(os.getenv("TRUECORE_HELP_PROMPT", repo_root / "docs" / "operations" / "TrueCore Help Bot System Prompt.md")),
        "include_roots": [
            truecore_root,
            repo_root / "tests",
            repo_root / "README.md",
        ],
        "exclude_dirs": {
            ".git",
            ".pytest_cache",
            "__pycache__",
            "node_modules",
            "venv",
            ".venv",
            "instance",
            "data",
            "logs",
            "docs",
        },
        "exclude_suffixes": {
            ".pyc",
            ".pyo",
            ".db",
            ".sqlite",
            ".sqlite3",
            ".jsonl",
        },
        "exclude_names": {
            ".env",
        },
        "mirror_extensions": {
            ".py",
            ".md",
            ".txt",
            ".json",
            ".html",
            ".js",
            ".css",
            ".toml",
            ".yaml",
            ".yml",
        },
        "max_context_chars": int(os.getenv("TRUECORE_HELP_MAX_CONTEXT_CHARS", "24000")),
        "default_tier": int(os.getenv("TRUECORE_HELP_DEFAULT_TIER", "1")),
        "search_limit": int(os.getenv("TRUECORE_HELP_SEARCH_LIMIT", "12")),
    }
