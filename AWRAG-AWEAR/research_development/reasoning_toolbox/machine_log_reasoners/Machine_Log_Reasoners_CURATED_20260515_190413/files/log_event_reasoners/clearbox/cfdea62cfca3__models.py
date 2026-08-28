"""netlog Pydantic models."""
from pydantic import BaseModel


class SessionStartRequest(BaseModel):
    label: str = ""


class QueryRequest(BaseModel):
    proc: str = ""
    raddr_contains: str = ""
    alert_type: str = ""
    limit: int = 100
