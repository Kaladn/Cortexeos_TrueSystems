"""Observe sensors probe — CPU, RAM, GPU, disk, net snapshot.

Uses observe/reader.py and observe/catalog.py directly to read
machine sensors and verify the observe subsystem works.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List

from .base import Probe, RunContext, ProbeResult, make_result

# Key sensors to sample (one per category to keep it fast)
_SENSOR_SAMPLE = [
    "cpu.percent",
    "ram.percent",
    "ram.used_gb",
    "disk.percent",
    "net.bytes_sent",
    "gpu.util_percent",
    "os.platform",
    "os.python_version",
]


class ObserveSensorsProbe:
    """Snapshot machine sensors via the observe subsystem."""

    probe_id = "observe_sensors"
    description = "CPU, RAM, GPU, disk, net snapshot via observe/reader"

    def run(self, ctx: RunContext) -> List[ProbeResult]:
        results: List[ProbeResult] = []

        # Try to import observe modules
        try:
            from observe.catalog import build_catalog
            from observe.reader import read_sensors
        except ImportError as e:
            results.append(make_result(
                ctx, self.probe_id, "observe.import",
                "ERROR", error_detail=f"Cannot import observe: {e}",
            ))
            return results

        # Build catalog
        t0 = time.perf_counter()
        try:
            catalog = build_catalog()
        except Exception as e:
            lat = (time.perf_counter() - t0) * 1000
            results.append(make_result(
                ctx, self.probe_id, "observe.catalog",
                "ERROR", lat_ms=lat, error_detail=str(e),
            ))
            return results
        lat = (time.perf_counter() - t0) * 1000

        catalog_ids = {s["id"] for s in catalog}
        results.append(make_result(
            ctx, self.probe_id, "observe.catalog",
            "CONFIRMED",
            lat_ms=lat,
            detail={"sensor_count": len(catalog), "categories": sorted({s["category"] for s in catalog})},
        ))

        # Read sample sensors
        available = [sid for sid in _SENSOR_SAMPLE if sid in catalog_ids]
        missing = [sid for sid in _SENSOR_SAMPLE if sid not in catalog_ids]

        if missing:
            results.append(make_result(
                ctx, self.probe_id, "observe.missing_sensors",
                "SKIPPED",
                skip_reason=f"Sensors not in catalog: {', '.join(missing)} — check observe policy config",
                detail={"missing": missing},
            ))

        if not available:
            return results

        t0 = time.perf_counter()
        try:
            readings = read_sensors(available, catalog)
        except Exception as e:
            lat = (time.perf_counter() - t0) * 1000
            results.append(make_result(
                ctx, self.probe_id, "observe.read",
                "ERROR", lat_ms=lat, error_detail=str(e),
            ))
            return results
        lat = (time.perf_counter() - t0) * 1000

        # One result per sensor read
        for sid in available:
            if sid in readings:
                reading = readings[sid]
                results.append(make_result(
                    ctx, self.probe_id, f"observe.sensor.{sid}",
                    "CONFIRMED",
                    lat_ms=lat / max(len(available), 1),
                    detail={"value": reading.get("value"), "unit": reading.get("unit", "")},
                ))
            else:
                results.append(make_result(
                    ctx, self.probe_id, f"observe.sensor.{sid}",
                    "SKIPPED",
                    skip_reason=f"Sensor '{sid}' returned no data — verify it is online and readable",
                ))

        return results
