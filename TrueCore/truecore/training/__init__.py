"""Deterministic source-intake builders for operator-training material."""

from .code_intake import COMPONENT_ROOTS, build_training_corpus
from .bridge_resolver import FrozenBridgeAuthority, evaluate_bridge_resolver, resolve_query
from .external_source_intake import build_external_source_intake
from .selection import Eligibility, TrainingRole, build_releases

__all__ = [
    "COMPONENT_ROOTS", "Eligibility", "FrozenBridgeAuthority", "TrainingRole",
    "build_external_source_intake", "build_releases", "build_training_corpus",
    "evaluate_bridge_resolver", "resolve_query",
]
