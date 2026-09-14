"""Reasoning Engine — Non-LLM inference for 6-1-6 maps.

Run standalone: uvicorn plugins.reasoning_engine:app --port 5051 --reload
"""

from .engine import app, ReasoningEngine, engine

__all__ = ["app", "ReasoningEngine", "engine"]
