"""Canonical TrueCore time helpers."""

from __future__ import annotations

import re
from datetime import UTC, datetime


UTC_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")


def utc_now() -> str:
    """Return canonical UTC event time.

    TrueCore event timestamps use one sortable wire format:
    YYYY-MM-DDTHH:MM:SS.ffffffZ
    """

    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def is_canonical_utc_timestamp(value: str) -> bool:
    return bool(UTC_TIMESTAMP_RE.match(value))
