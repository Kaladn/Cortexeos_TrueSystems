"""Spellcheck model-assist service."""
from __future__ import annotations

from typing import Any

from bridges.helpers import _safe_error
from bridges.state import LOGGER


class SpellcheckAssistService:
    """Runs spellcheck model-assist inference against local Ollama."""

    def __init__(self, *, state: Any, default_model: str) -> None:
        self.state = state
        self.default_model = default_model

    async def suggest(self, token: str, context: str) -> dict[str, Any]:
        client = await self.state.get_ollama_client()
        prompt = (
            f'The word "{token}" appears in the following context: "{context}"\n'
            "This word is not in the dictionary. What is the most likely correct "
            "spelling? Respond with ONLY the corrected word, nothing else."
        )
        try:
            resp = await client.post(
                f"{self.state.get_ollama_base_url()}/api/generate",
                json={"model": self.default_model, "prompt": prompt, "stream": False},
                timeout=30.0,
            )
            resp.raise_for_status()
            data = resp.json()
            suggestion = data.get("response", "").strip().lower().split()[0] if data.get("response") else ""
            return {"token": token, "suggestion": suggestion, "source": "model"}
        except Exception as exc:
            LOGGER.warning("model-assist failed for %r: %s", token, exc)
            return {"token": token, "suggestion": None, "error": _safe_error(exc)}
