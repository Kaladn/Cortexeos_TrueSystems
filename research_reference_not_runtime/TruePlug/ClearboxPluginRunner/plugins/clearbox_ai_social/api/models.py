from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# Required pattern from plugin contract:
# response fields should have defaults, and error should always be optional.


class BaseResponse(BaseModel):
    ok: bool = False
    message: str = ""
    error: Optional[Dict[str, Any]] = None


class StatusResponse(BaseResponse):
    plugin_id: str = "clearbox_ai_social"
    version: str = "0.1.0"
    initialized: bool = False
    node_id: str = ""
    features: Dict[str, bool] = Field(default_factory=dict)


class IdentityResponse(BaseResponse):
    node_id: str = ""
    public_key_pem: str = ""


class SignedObjectEnvelope(BaseModel):
    type: str = ""
    version: int = 1
    timestamp: int = 0
    node_id: str = ""
    hash: str = ""
    signature: str = ""
    payload: Dict[str, Any] = Field(default_factory=dict)


class ProfilePayload(BaseModel):
    display_name: str = ""
    bio: str = ""
    interests: List[str] = Field(default_factory=list)
    top_3_needs: List[str] = Field(default_factory=list)
    featured_plugins: List[str] = Field(default_factory=list)


class ListingPayload(BaseModel):
    plugin_id: str = ""
    name: str = ""
    description: str = ""
    plugin_version: str = ""
    manifest_url: str = ""
    category: str = ""
    price: int = 0
    downloads: int = 0


class SaveProfileRequest(BaseModel):
    display_name: str = ""
    bio: str = ""
    interests: List[str] = Field(default_factory=list)
    top_3_needs: List[str] = Field(default_factory=list)
    featured_plugins: List[str] = Field(default_factory=list)


class SaveProfileResponse(BaseResponse):
    profile: SignedObjectEnvelope = Field(default_factory=SignedObjectEnvelope)


class CreateListingRequest(BaseModel):
    plugin_id: str = ""
    name: str = ""
    description: str = ""
    plugin_version: str = ""
    manifest_url: str = ""
    category: str = ""
    price: int = 0


class CreateListingResponse(BaseResponse):
    listing: SignedObjectEnvelope = Field(default_factory=SignedObjectEnvelope)


class SearchListingsRequest(BaseModel):
    category: str = ""
    author_node_id: str = ""
    sort_by: Literal["downloads", "name", "first_seen"] = "downloads"


class SearchListingsResponse(BaseResponse):
    listings: List[Dict[str, Any]] = Field(default_factory=list)


class PeerSyncRequest(BaseModel):
    node_id: str = ""
    host: str = ""
    port: int = 0
    scheme: Literal["http", "https"] = "http"


class PeerSyncResponse(BaseResponse):
    peer_node_id: str = ""
    imported_profile: bool = False
    imported_listings: int = 0
