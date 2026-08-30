"""Deterministic source-intake builders for operator-training material."""

from .code_intake import COMPONENT_ROOTS, build_training_corpus
from .external_source_intake import build_external_source_intake
from .selection import Eligibility, TrainingRole, build_releases

__all__ = [
    "COMPONENT_ROOTS", "Eligibility", "TrainingRole", "build_external_source_intake",
    "build_releases", "build_training_corpus",
]
