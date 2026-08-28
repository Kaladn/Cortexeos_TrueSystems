"""Probe registry — discovers and returns all available probes."""

from __future__ import annotations

from typing import List

from .base import Probe


def discover_probes() -> List[Probe]:
    """Return all registered probes in execution order."""
    probes: List[Probe] = []

    from .environment import EnvironmentProbe
    probes.append(EnvironmentProbe())

    from .service_liveness import ServiceLivenessProbe
    probes.append(ServiceLivenessProbe())

    from .observe_sensors import ObserveSensorsProbe
    probes.append(ObserveSensorsProbe())

    from .log_integrity import LogIntegrityProbe
    probes.append(LogIntegrityProbe())

    from .api_smoke import ApiSmokeProbe
    probes.append(ApiSmokeProbe())

    from .temporal_audit import TemporalAuditProbe
    probes.append(TemporalAuditProbe())

    return probes
