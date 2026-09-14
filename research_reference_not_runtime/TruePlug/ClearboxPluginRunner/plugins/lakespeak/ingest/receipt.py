"""Ingest receipt creation — immutable provenance record.

receipt_id format: rcpt_{YYYYMMDD}_{HHMMSS}_{random_hex8}
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone

from lakespeak.schemas import IngestReceipt, INGEST_RECEIPT_VERSION


def make_receipt_id() -> str:
    """Generate a deterministic-format receipt ID with random suffix."""
    now = datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d")
    time_part = now.strftime("%H%M%S")
    rand_part = uuid.uuid4().hex[:8]
    return f"rcpt_{date_part}_{time_part}_{rand_part}"


def source_hash(text: str) -> str:
    """SHA-256 hash of source text, prefixed."""
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"sha256:{h}"


def create_receipt(
    receipt_id: str,
    source_type: str,
    raw_text: str,
    chunk_count: int,
    anchor_count: int,
    relation_count: int,
    lexicon_version: str = "",
    source_path: str = None,
    created_by: str = "system",
) -> IngestReceipt:
    """Create an ingest receipt with provenance fields."""
    return IngestReceipt(
        schema_version=INGEST_RECEIPT_VERSION,
        receipt_id=receipt_id,
        source_type=source_type,
        source_path=source_path,
        source_hash=source_hash(raw_text),
        source_size_bytes=len(raw_text.encode("utf-8")),
        chunk_count=chunk_count,
        anchor_count=anchor_count,
        relation_count=relation_count,
        lexicon_version=lexicon_version,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        created_by=created_by,
    )
