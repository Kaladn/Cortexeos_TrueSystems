"""Help System API -- Pydantic request/response models.

All response fields have defaults -- serialization never crashes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel


class HelpStatusResponse(BaseModel):
    """Plugin status + content stats."""
    version: str = ""
    enabled: bool = False
    total_ids: int = 0
    categories: Dict[str, int] = {}
    layers_coverage: Dict[str, int] = {}
    error: Optional[Dict[str, Any]] = None


class HelpContentResponse(BaseModel):
    """Help entry for a specific help_id."""
    help_id: str = ""
    found: bool = False
    label: str = ""
    category: str = ""
    icon: str = ""
    layer1: Optional[Dict[str, str]] = None
    layer2: Optional[Dict[str, Any]] = None
    layer3: Optional[Dict[str, Any]] = None
    tutorial_available: Union[str, bool] = False
    difficulty: str = ""
    error: Optional[Dict[str, Any]] = None


class HelpSearchResponse(BaseModel):
    """Search results across help content."""
    query: str = ""
    results: List[Dict[str, Any]] = []
    total: int = 0
    error: Optional[Dict[str, Any]] = None


class HelpIdsResponse(BaseModel):
    """List of all registered help IDs."""
    ids: List[Dict[str, str]] = []
    total: int = 0
    error: Optional[Dict[str, Any]] = None
