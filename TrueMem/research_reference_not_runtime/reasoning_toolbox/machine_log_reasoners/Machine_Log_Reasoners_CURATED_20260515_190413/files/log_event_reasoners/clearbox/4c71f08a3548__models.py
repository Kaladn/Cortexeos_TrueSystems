"""audio_io Pydantic models."""
from pydantic import BaseModel
from typing import Optional


class SessionStartRequest(BaseModel):
    label: str = ""
    device_index: Optional[int] = None


class SessionEventsRequest(BaseModel):
    limit: int = 50
