"""AI brief catalog/read/pin service."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from bridges.state import LOGGER


class AIBriefService:
    """Owns AI brief allowlist, provider mapping, and pin behavior."""

    _BRIEF_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
    _DISPLAY_LIMIT = 20_000
    _DIGEST_LIMIT = 6_000
    _PROVIDER_BRIEF_MAP = {
        "local": "local",
        "ollama": "local",
        "google": "gemini",
        "gemini": "gemini",
        "openai": "openai",
        "anthropic": "anthropic",
        "claude": "anthropic",
    }

    def __init__(self, *, base_dir: Path) -> None:
        self._brief_dir = base_dir / "docs" / "ai"
        self._allowlist: dict[str, Path] = {}
        if self._brief_dir.is_dir():
            for path in sorted(self._brief_dir.glob("*.ai.md")):
                base = path.stem.removesuffix(".ai")
                if not path.is_symlink():
                    self._allowlist[base] = path.resolve()
        LOGGER.info("AI Brief allowlist: %s", list(self._allowlist.keys()))

    @staticmethod
    def _brief_sha(content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @staticmethod
    def _extract_digest(content: str) -> str | None:
        start = content.find("<!-- BRIEF_DIGEST -->")
        end = content.find("<!-- END_BRIEF_DIGEST -->")
        if start == -1 or end == -1 or end <= start:
            return None
        return content[start + len("<!-- BRIEF_DIGEST -->") : end].strip()

    def _brief_response(self, name: str, path: Path) -> dict[str, Any]:
        content = path.read_text(encoding="utf-8")
        total_chars = len(content)
        truncated = total_chars > self._DISPLAY_LIMIT
        display = content[: self._DISPLAY_LIMIT] if truncated else content
        digest = self._extract_digest(content)
        return {
            "name": name,
            "file": path.name,
            "content": display,
            "sha256": self._brief_sha(content),
            "content_truncated": truncated,
            "content_total_chars": total_chars,
            "digest_present": digest is not None,
            "digest": digest,
        }

    def _find_todays_pin(self) -> dict[str, Any] | None:
        try:
            from Conversations.threads.daily_logger import get_today_file
            from security.secure_storage import secure_read_lines

            today_file = get_today_file()
            if not today_file.exists():
                return None
            for line in secure_read_lines(today_file):
                try:
                    obj = json.loads(line)
                    if obj.get("kind") == "AI_BRIEF" and obj.get("content"):
                        return obj
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass
        return None

    def list_briefs(self) -> dict[str, Any]:
        briefs = [{"name": key, "file": f"{key}.ai.md"} for key in sorted(self._allowlist)]
        return {"briefs": briefs, "provider_map": dict(self._PROVIDER_BRIEF_MAP)}

    def get_for_provider(self, provider: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "global": None,
            "global_sha256": None,
            "model": None,
            "model_sha256": None,
            "provider": provider,
        }
        global_path = self._allowlist.get("CLEARBOX")
        if global_path and global_path.is_file():
            global_content = global_path.read_text(encoding="utf-8")
            result["global"] = global_content[: self._DISPLAY_LIMIT]
            result["global_sha256"] = self._brief_sha(global_content)

        model_key = self._PROVIDER_BRIEF_MAP.get((provider or "").lower())
        if model_key:
            model_path = self._allowlist.get(model_key)
            if model_path and model_path.is_file():
                model_content = model_path.read_text(encoding="utf-8")
                result["model"] = model_content[: self._DISPLAY_LIMIT]
                result["model_sha256"] = self._brief_sha(model_content)
        return result

    def pin_status(self) -> dict[str, Any]:
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        pin = self._find_todays_pin()
        if pin:
            content = pin.get("content", "")
            sha = self._brief_sha(content) if content else ""
            return {"pinned": True, "sha256": sha, "date": today_str}
        return {"pinned": False, "date": today_str}

    def pin_for_provider(self, provider: str) -> dict[str, Any]:
        from Conversations.threads import log_message as _log_message

        existing = self._find_todays_pin()
        if existing:
            return {
                "pinned": False,
                "reason": "already_pinned",
                "sha256": existing.get("integrity_hash", "")[:16],
            }

        digests: list[str] = []
        brief_names: list[str] = []

        global_path = self._allowlist.get("CLEARBOX")
        if global_path and global_path.is_file():
            digest = self._extract_digest(global_path.read_text(encoding="utf-8"))
            if digest:
                digests.append(digest)
                brief_names.append("CLEARBOX.ai.md")

        model_key = self._PROVIDER_BRIEF_MAP.get((provider or "").lower(), "")
        if model_key:
            model_path = self._allowlist.get(model_key)
            if model_path and model_path.is_file():
                digest = self._extract_digest(model_path.read_text(encoding="utf-8"))
                if digest:
                    digests.append(digest)
                    brief_names.append(f"{model_key}.ai.md")

        if not digests:
            return {"pinned": False, "reason": "missing_digest_markers"}

        combined = "\n\n---\n\n".join(digests)
        if len(combined) > self._DIGEST_LIMIT:
            return {
                "pinned": False,
                "reason": "digest_too_large",
                "chars": len(combined),
                "limit": self._DIGEST_LIMIT,
            }

        sha = self._brief_sha(combined)

        try:
            _log_message(
                sender="ai",
                content=combined,
                actor="system",
                seat={"provider": "clearbox_bridge", "model": "ai_brief"},
                kind="AI_BRIEF",
            )
        except Exception as exc:
            LOGGER.exception("Failed to pin AI brief")
            return {"pinned": False, "reason": f"write_error: {exc}"}

        return {
            "pinned": True,
            "sha256": sha,
            "chars": len(combined),
            "briefs": brief_names,
        }

    def get_brief(self, name: str) -> dict[str, Any]:
        if not self._BRIEF_NAME_RE.match(name):
            raise HTTPException(400, "Invalid brief name")
        path = self._allowlist.get(name)
        if not path or not path.is_file():
            raise HTTPException(404, "Brief not found")
        return self._brief_response(name, path)

