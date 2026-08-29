"""av_security Pydantic models."""
from pydantic import BaseModel
from typing import Optional


class CorrelateRequest(BaseModel):
    visual_session_dir: str
    audio_session_dir: str


class SecurityEventsRequest(BaseModel):
    limit: int = 100
