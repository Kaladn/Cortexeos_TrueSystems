"""Genesis Citation Tool — read-only citation lookup for Clearbox AI Studio training corpus.

Provides:
  - Direct lookup: G-ID → canonical citation object
  - BM25 search: query string → ranked citation candidates
  - FastAPI router: mounted at /api/genesis/ on the Clearbox AI Studio Bridge (port 5050)

The LLM may ONLY cite what this tool returns. No inference from context.
Every factual claim about Clearbox AI Studio must be anchored to a G-ID returned here.
"""

from .engine import CitationEngine
from .router import router

__all__ = ["CitationEngine", "router"]
