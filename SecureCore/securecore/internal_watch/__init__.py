"""Internal self-audit receipts for SecureCore.

This package is intentionally separate from normal operational logging. It
observes SecureCore health and authority boundaries, then writes independent
receipts. It does not approve, mutate, recover, or suppress runtime behavior.
"""

from securecore.internal_watch.self_logger import (
    InternalSelfLogger,
    build_self_audit_receipt,
    build_system_trust_receipt,
    validate_self_audit_receipt,
    validate_system_trust_receipt,
)

__all__ = [
    "InternalSelfLogger",
    "build_self_audit_receipt",
    "build_system_trust_receipt",
    "validate_self_audit_receipt",
    "validate_system_trust_receipt",
]
