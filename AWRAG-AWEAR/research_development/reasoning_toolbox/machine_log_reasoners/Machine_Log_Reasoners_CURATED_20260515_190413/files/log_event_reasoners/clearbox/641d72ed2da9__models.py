"""visual_io Pydantic models."""
from pydantic import BaseModel
from typing import Any, Optional


class SessionStartRequest(BaseModel):
    label: str = ""
    fps: float = 2.0
    grid_size: int = 32
    capture_region: Optional[dict] = None


class ConfigUpdateRequest(BaseModel):
    fps: Optional[float] = None
    grid_size: Optional[int] = None
    capture_region: Optional[dict] = None


class SessionEventsRequest(BaseModel):
    limit: int = 50
