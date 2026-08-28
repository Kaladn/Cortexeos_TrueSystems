"""Service liveness probe — port checks and HTTP health endpoints.

Checks ports 5050 (bridge), 8080 (UI), 11434 (Ollama), 11435 (LLM proxy).
Then hits health/status endpoints on reachable services.
"""

from __future__ import annotations

import hashlib
import socket
import time
from typing import Any, Dict, List

import httpx

from .base import Probe, RunContext, ProbeResult, make_result

_SERVICES = [
    {"name": "bridge", "port": 5050, "health": ["/api/stats"], "scheme": "https"},
    {"name": "ui", "port": 8080, "health": ["/", "/clearbox_ai_production.html", "/index.html"], "scheme": "http"},
    {"name": "ollama", "port": 11434, "health": ["/api/tags"], "scheme": "http"},
    {"name": "llm_proxy", "port": 11435, "health": ["/health", "/v1/models"], "scheme": "https"},
]


def _probe_port(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect((host, port))
            return True
    except OSError:
        return False


def _probe_http(url: str, timeout: float = 5.0) -> Dict[str, Any]:
    """Hit a URL and return observation dict."""
    obs: Dict[str, Any] = {"url": url}
    t0 = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout, verify=False, follow_redirects=True) as client:
            r = client.get(url)
        obs["lat_ms"] = (time.perf_counter() - t0) * 1000
        obs["code"] = r.status_code
        obs["content_type"] = r.headers.get("content-type", "")
        obs["body_bytes"] = len(r.content)
        obs["body_sha256"] = hashlib.sha256(r.content).hexdigest()
        if r.status_code >= 400:
            obs["body_preview"] = r.content[:512].decode("utf-8", errors="replace")
        if "json" in obs.get("content_type", ""):
            try:
                body = r.json()
                if isinstance(body, dict):
                    obs["json_keys"] = sorted(body.keys())
            except Exception:
                pass
    except httpx.ConnectError:
        obs["lat_ms"] = (time.perf_counter() - t0) * 1000
        obs["code"] = 0
    except httpx.TimeoutException:
        obs["lat_ms"] = timeout * 1000
        obs["code"] = 408
    except Exception as e:
        obs["lat_ms"] = (time.perf_counter() - t0) * 1000
        obs["code"] = -1
        obs["error"] = str(e)
    return obs


class ServiceLivenessProbe:
    """Port liveness + HTTP health for core services."""

    probe_id = "service_liveness"
    description = "Port and HTTP health for bridge, UI, Ollama, LLM proxy"

    def run(self, ctx: RunContext) -> List[ProbeResult]:
        results: List[ProbeResult] = []

        for svc in _SERVICES:
            name = svc["name"]
            port = svc["port"]
            scheme = svc["scheme"]
            health_path = svc["health"]

            # Skip LLM/Ollama if requested
            if ctx.skip_llm and name == "llm_proxy":
                results.append(make_result(
                    ctx, self.probe_id, f"svc.{name}.port",
                    "SKIPPED", skip_reason="LLM proxy — omit --skip-llm to probe",
                ))
                results.append(make_result(
                    ctx, self.probe_id, f"svc.{name}.health",
                    "SKIPPED", skip_reason="LLM proxy — omit --skip-llm to probe",
                ))
                continue
            if ctx.skip_ollama and name == "ollama":
                results.append(make_result(
                    ctx, self.probe_id, f"svc.{name}.port",
                    "SKIPPED", skip_reason="Ollama — omit --skip-ollama to probe",
                ))
                results.append(make_result(
                    ctx, self.probe_id, f"svc.{name}.health",
                    "SKIPPED", skip_reason="Ollama — omit --skip-ollama to probe",
                ))
                continue

            # Port probe
            t0 = time.perf_counter()
            alive = _probe_port("127.0.0.1", port)
            lat = (time.perf_counter() - t0) * 1000
            results.append(make_result(
                ctx, self.probe_id, f"svc.{name}.port",
                "CONFIRMED" if alive else "DENIED",
                lat_ms=lat,
                detail={"port": port, "alive": alive},
            ))

            # HTTP health (only if port is alive)
            if not alive:
                results.append(make_result(
                    ctx, self.probe_id, f"svc.{name}.health",
                    "SKIPPED", skip_reason=f"Port {port} not listening — start the service first",
                ))
                continue

            # Try each candidate health path; also try HTTPS fallback
            health_paths = svc["health"]
            best_obs = None
            for hp in health_paths:
                url = f"{scheme}://127.0.0.1:{port}{hp}"
                obs = _probe_http(url)
                code = obs.get("code", 0)
                if 200 <= code < 400:
                    best_obs = obs
                    break
                # HTTPS fallback if HTTP failed
                if code <= 0 and scheme == "http":
                    obs = _probe_http(f"https://127.0.0.1:{port}{hp}")
                    code = obs.get("code", 0)
                    if 200 <= code < 400:
                        best_obs = obs
                        break
                if best_obs is None:
                    best_obs = obs  # keep first failure for diagnostics

            code = best_obs.get("code", 0)
            verdict = "CONFIRMED" if 200 <= code < 400 else "DENIED"
            results.append(make_result(
                ctx, self.probe_id, f"svc.{name}.health",
                verdict,
                lat_ms=best_obs.get("lat_ms", 0),
                detail=best_obs,
            ))

        return results
