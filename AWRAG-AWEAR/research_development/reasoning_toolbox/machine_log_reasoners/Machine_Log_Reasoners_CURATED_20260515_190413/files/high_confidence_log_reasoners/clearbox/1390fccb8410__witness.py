"""Witness — executes actions, captures evidence, writes proof.

The Witness never trusts the Masher.  It independently observes:
  - HTTP response (code, latency, body hash, top-level keys)
  - Port liveness (5050, 8080, 11434, 11435)
  - Filesystem deltas (optional, --watch-fs)
  - Error body capture (4xx/5xx → artifact file)

Verdict logic:
  CONFIRMED — HTTP code in expected set AND response has expected keys
  DENIED    — code outside expected set, connection refused, or timeout
  SKIPPED   — action was gated by safety rules
  ERROR     — witness itself failed during observation
"""

from __future__ import annotations

import hashlib
import json
import socket
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse

import httpx

from .temporal import BOOT_ID, ts_utc, mono_ns, validate_temporal

TIMEOUT = 10  # seconds per HTTP request
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
_SECURE_CLIENT = httpx.Client(timeout=TIMEOUT, follow_redirects=True)
_INSECURE_LOOPBACK_CLIENT = httpx.Client(
    timeout=TIMEOUT,
    verify=False,
    follow_redirects=True,
)
_CSRF_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


def _pick_client(url: str) -> httpx.Client:
    host = (urlparse(url).hostname or "").lower()
    if host in _LOOPBACK_HOSTS:
        # Smoke probes local self-signed TLS endpoints during bridge bring-up.
        return _INSECURE_LOOPBACK_CLIENT
    return _SECURE_CLIENT


# ── Data Structures ──────────────────────────────────────────────

@dataclass
class HttpObservation:
    code: int = 0
    lat_ms: float = 0.0
    body_sha256: str = ""
    body_bytes: int = 0
    json_keys: List[str] = field(default_factory=list)
    content_type: str = ""
    body_preview: str = ""  # first 512 bytes of response body (for error diagnostics)
    retries: int = 0


@dataclass
class PortSnapshot:
    port_5050: bool = False
    port_8080: bool = False
    port_11434: bool = False
    port_11435: bool = False


@dataclass
class FsDelta:
    path: str = ""
    event: str = ""  # created | modified
    size: int = 0


@dataclass
class Observations:
    http: Optional[HttpObservation] = None
    ports: Optional[PortSnapshot] = None
    fs_delta: List[FsDelta] = field(default_factory=list)
    error_artifact: str = ""


@dataclass
class Proof:
    run_id: str = ""
    seq: int = 0
    ts_utc: str = ""       # RFC3339 UTC with Z + milliseconds
    mono_ns: int = 0       # monotonic nanoseconds (process-relative)
    boot_id: str = ""      # GUID per process start
    proof_of_seq: int = 0
    observations: Dict[str, Any] = field(default_factory=dict)
    verdict: str = ""  # CONFIRMED | DENIED | SKIPPED | ERROR


# ── Witness ──────────────────────────────────────────────────────

class Witness:
    """Observes actions, captures evidence, writes proof."""

    def __init__(
        self,
        run_id: str,
        logs_dir: Path,
        artifacts_dir: Path,
        watch_fs: bool = False,
        fs_watch_dirs: List[Path] = None,
        bridge_auth_headers: Optional[Dict[str, str]] = None,
        bridge_auth_cookies: Optional[Dict[str, str]] = None,
        rate_limit_retries: int = 2,
        rate_limit_backoff_ms: int = 300,
        rate_limit_as_skip: bool = True,
    ):
        self.run_id = run_id
        self.logs_dir = logs_dir
        self.artifacts_dir = artifacts_dir
        self.watch_fs = watch_fs
        self.fs_watch_dirs = fs_watch_dirs or []
        self.bridge_auth_headers = bridge_auth_headers or {}
        self.bridge_auth_cookies = bridge_auth_cookies or {}
        self.rate_limit_retries = max(0, int(rate_limit_retries))
        self.rate_limit_backoff_ms = max(0, int(rate_limit_backoff_ms))
        self.rate_limit_as_skip = bool(rate_limit_as_skip)

        self.proof_path = logs_dir / f"{run_id}.proof.jsonl"
        self._seq = 0

        # Temporal integrity tracking (separate streams for action vs proof)
        self._action_last_seq = 0
        self._action_last_mono_ns = 0
        self._action_last_ts_utc = ""
        self._proof_last_seq = 0
        self._proof_last_mono_ns = 0
        self._proof_last_ts_utc = ""
        self._temporal_warnings: List[str] = []

    # ── Temporal Integrity Gate ─────────────────────────────

    def _check_action_temporal(self, action: dict) -> None:
        """Validate temporal + causal ordering on incoming action."""
        warnings, self._action_last_seq, self._action_last_mono_ns, self._action_last_ts_utc = (
            validate_temporal(action, self._action_last_seq,
                              self._action_last_mono_ns,
                              self._action_last_ts_utc, label="action")
        )
        self._temporal_warnings.extend(warnings)

    def _check_proof_temporal(self, proof_dict: dict) -> None:
        """Validate temporal + causal ordering on outgoing proof."""
        warnings, self._proof_last_seq, self._proof_last_mono_ns, self._proof_last_ts_utc = (
            validate_temporal(proof_dict, self._proof_last_seq,
                              self._proof_last_mono_ns,
                              self._proof_last_ts_utc, label="proof")
        )
        self._temporal_warnings.extend(warnings)

    # ── Port Probing ─────────────────────────────────────────

    @staticmethod
    def probe_port(host: str, port: int, timeout: float = 1.0) -> bool:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                sock.connect((host, port))
                return True
        except OSError:
            return False

    def snapshot_ports(self, host: str = "127.0.0.1") -> PortSnapshot:
        return PortSnapshot(
            port_5050=self.probe_port(host, 5050),
            port_8080=self.probe_port(host, 8080),
            port_11434=self.probe_port(host, 11434),
            port_11435=self.probe_port(host, 11435),
        )

    # ── FS Delta ─────────────────────────────────────────────

    def _scan_mtimes(self) -> Dict[str, float]:
        """Snapshot file mtimes in watched directories."""
        if not self.watch_fs:
            return {}
        mtimes = {}
        for d in self.fs_watch_dirs:
            if not d.exists():
                continue
            for f in d.rglob("*"):
                if f.is_file():
                    try:
                        mtimes[str(f)] = f.stat().st_mtime
                    except OSError:
                        pass
        return mtimes

    @staticmethod
    def _compute_fs_delta(
        before: Dict[str, float], after: Dict[str, float]
    ) -> List[FsDelta]:
        deltas = []
        for path, mtime in after.items():
            if path not in before:
                try:
                    size = Path(path).stat().st_size
                except OSError:
                    size = 0
                deltas.append(FsDelta(path=path, event="created", size=size))
            elif mtime > before[path]:
                try:
                    size = Path(path).stat().st_size
                except OSError:
                    size = 0
                deltas.append(FsDelta(path=path, event="modified", size=size))
        return deltas

    # ── HTTP Execution ───────────────────────────────────────

    @staticmethod
    def _retry_after_seconds(value: str) -> Optional[float]:
        """Parse numeric Retry-After header value (seconds)."""
        try:
            return max(0.0, float(value.strip()))
        except Exception:
            return None

    def execute_http(
        self,
        method: str,
        url: str,
        payload: Optional[dict] = None,
        apply_bridge_auth: bool = False,
    ) -> HttpObservation:
        obs = HttpObservation()
        t0 = time.perf_counter()
        try:
            client = _pick_client(url)
            request_kwargs: Dict[str, Any] = {
                "json": payload if method != "GET" else None
            }
            if apply_bridge_auth:
                if self.bridge_auth_headers:
                    request_kwargs["headers"] = dict(self.bridge_auth_headers)
                if self.bridge_auth_cookies:
                    request_kwargs["cookies"] = dict(self.bridge_auth_cookies)
                if method.upper() in _CSRF_METHODS:
                    headers = request_kwargs.setdefault("headers", {})
                    headers.setdefault("X-Clearbox-CSRF", "smoke-test")
            retries = 0
            r = client.request(method, url, **request_kwargs)
            while r.status_code == 429 and retries < self.rate_limit_retries:
                retry_after = self._retry_after_seconds(r.headers.get("Retry-After", ""))
                if retry_after is not None:
                    sleep_s = retry_after
                else:
                    sleep_s = (self.rate_limit_backoff_ms / 1000.0) * (2 ** retries)
                time.sleep(max(0.0, sleep_s))
                retries += 1
                r = client.request(method, url, **request_kwargs)
            obs.retries = retries

            obs.lat_ms = (time.perf_counter() - t0) * 1000
            obs.code = r.status_code
            obs.content_type = r.headers.get("content-type", "")
            obs.body_bytes = len(r.content)
            obs.body_sha256 = hashlib.sha256(r.content).hexdigest()

            # Capture body preview for error responses (4xx/5xx)
            if r.status_code >= 400:
                obs.body_preview = r.content[:512].decode("utf-8", errors="replace")

            if "json" in obs.content_type:
                try:
                    body = r.json()
                    if isinstance(body, dict):
                        obs.json_keys = sorted(body.keys())
                    elif isinstance(body, list):
                        obs.json_keys = ["__list__"]
                except Exception:
                    pass

        except httpx.ConnectError:
            obs.lat_ms = (time.perf_counter() - t0) * 1000
            obs.code = 0  # connection refused
        except httpx.TimeoutException:
            obs.lat_ms = TIMEOUT * 1000
            obs.code = 408
        except Exception:
            obs.lat_ms = (time.perf_counter() - t0) * 1000
            obs.code = -1

        return obs

    def execute_ws(self, url: str, apply_bridge_auth: bool = False) -> HttpObservation:
        """Probe a WebSocket endpoint — connect + immediate close.

        Requires websocket-client library. Returns code -2 if not installed
        (no raw socket fallback — that fakes success without a real WS handshake).
        """
        obs = HttpObservation()
        t0 = time.perf_counter()

        try:
            import websocket as ws_lib
            host = (urlparse(url).hostname or "").lower()
            ws_headers: List[str] = []
            if apply_bridge_auth:
                for key, value in self.bridge_auth_headers.items():
                    ws_headers.append(f"{key}: {value}")
                if self.bridge_auth_cookies:
                    cookie_header = "; ".join(
                        [f"{k}={v}" for k, v in self.bridge_auth_cookies.items()]
                    )
                    ws_headers.append(f"Cookie: {cookie_header}")
                # Keep CSRF convention consistent for stateful bridge sessions.
                if not any(h.lower().startswith("x-clearbox-csrf:") for h in ws_headers):
                    ws_headers.append("X-Clearbox-CSRF: smoke-test")
            if host in _LOOPBACK_HOSTS:
                sock = ws_lib.create_connection(
                    url,
                    timeout=3,
                    sslopt={"cert_reqs": 0},
                    header=ws_headers or None,
                )
            else:
                sock = ws_lib.create_connection(url, timeout=3, header=ws_headers or None)
            sock.close()
            obs.code = 101
            obs.lat_ms = (time.perf_counter() - t0) * 1000
            return obs
        except ImportError:
            obs.code = -2  # websocket-client not installed
            obs.lat_ms = 0
            return obs
        except Exception:
            obs.code = 0
            obs.lat_ms = (time.perf_counter() - t0) * 1000
            return obs

    # ── Error Artifact ───────────────────────────────────────

    def _save_error_artifact(self, seq: int, http_obs: HttpObservation) -> str:
        if http_obs.code < 400:
            return ""
        artifact_name = f"seq_{seq:04d}_error.json"
        artifact_path = self.artifacts_dir / artifact_name
        try:
            artifact_path.write_text(
                json.dumps({
                    "seq": seq,
                    "http_code": http_obs.code,
                    "content_type": http_obs.content_type,
                    "body_sha256": http_obs.body_sha256,
                    "body_bytes": http_obs.body_bytes,
                    "body_preview": http_obs.body_preview,
                }, indent=2),
                encoding="utf-8",
            )
        except OSError:
            return ""
        return str(artifact_path.relative_to(self.artifacts_dir.parent.parent))

    # ── OpenAPI Snapshot ─────────────────────────────────────

    def capture_openapi(self, bridge_url: str) -> Optional[dict]:
        """Fetch and save OpenAPI spec as seq=0 artifact."""
        try:
            openapi_url = f"{bridge_url}/openapi.json"
            request_kwargs: Dict[str, Any] = {}
            if self.bridge_auth_headers:
                request_kwargs["headers"] = dict(self.bridge_auth_headers)
            if self.bridge_auth_cookies:
                request_kwargs["cookies"] = dict(self.bridge_auth_cookies)
            r = _pick_client(openapi_url).get(openapi_url, **request_kwargs)
            if r.status_code != 200:
                return None
            spec = r.json()
            artifact_path = self.artifacts_dir / "openapi_snapshot.json"
            artifact_path.write_text(
                json.dumps(spec, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            return spec
        except Exception:
            return None

    # ── Core: Observe an Action ──────────────────────────────

    def observe(self, action: dict) -> Proof:
        """Execute an action and produce a proof.

        Args:
            action: Action dict from the Masher (must have seq, action, url, payload, expected, intent)

        Returns:
            Proof with observations and verdict
        """
        self._seq += 1
        self._check_action_temporal(action)
        seq = action.get("seq", self._seq)
        intent = action.get("intent", "READ_ONLY")
        method = action.get("action", "GET")
        url = action.get("url", "")
        payload = action.get("payload")
        expected = action.get("expected", {})
        is_bridge_target = action.get("target") == "bridge"

        proof = Proof(
            run_id=self.run_id,
            seq=self._seq,
            ts_utc=ts_utc(),
            mono_ns=mono_ns(),
            boot_id=BOOT_ID,
            proof_of_seq=seq,
        )

        # Skipped actions — just record the skip
        if intent == "SKIP":
            proof.verdict = "SKIPPED"
            proof.observations = {"reason": action.get("skip_reason", "safety gate")}
            self._append_proof(proof)
            return proof

        try:
            # Before snapshot
            before_mtimes = self._scan_mtimes()
            ports_before = self.snapshot_ports()

            # Execute
            if method == "WS":
                http_obs = self.execute_ws(url, apply_bridge_auth=is_bridge_target)
                # websocket-client not installed → SKIPPED, not DENIED
                if http_obs.code == -2:
                    proof.verdict = "SKIPPED"
                    proof.observations = {
                        "http": asdict(http_obs),
                        "reason": "websocket-client not installed",
                    }
                    self._append_proof(proof)
                    return proof
            else:
                http_obs = self.execute_http(
                    method,
                    url,
                    payload,
                    apply_bridge_auth=is_bridge_target,
                )

                # HTTPS fallback: if HTTP failed (or returned empty body on 200) and try_https is set
                _empty_200 = http_obs.code == 200 and http_obs.body_bytes == 0
                if (http_obs.code <= 0 or _empty_200) and expected.get("try_https") and url.startswith("http://"):
                    https_url = "https://" + url[len("http://"):]
                    http_obs = self.execute_http(
                        method,
                        https_url,
                        payload,
                        apply_bridge_auth=is_bridge_target,
                    )

            # After snapshot
            fs_deltas = []
            if self.watch_fs:
                after_mtimes = self._scan_mtimes()
                fs_deltas = self._compute_fs_delta(before_mtimes, after_mtimes)

            # Error artifact
            error_artifact = ""
            if http_obs.code >= 400:
                error_artifact = self._save_error_artifact(seq, http_obs)

            # Build observations
            obs_dict: Dict[str, Any] = {
                "http": asdict(http_obs),
                "ports": asdict(ports_before),
            }
            if fs_deltas:
                obs_dict["fs_delta"] = [asdict(d) for d in fs_deltas]
            if error_artifact:
                obs_dict["error_artifact"] = error_artifact

            proof.observations = obs_dict

            # Verdict
            expected_codes = expected.get("http", [200])
            expected_shape = expected.get("shape", "")

            if http_obs.code == 429 and 429 not in expected_codes and self.rate_limit_as_skip:
                proof.verdict = "SKIPPED"
                proof.observations["reason"] = "rate_limited"
                self._append_proof(proof)
                return proof

            if http_obs.code in expected_codes:
                # Check shape if specified
                if expected_shape:
                    expected_keys = set(expected_shape.split(","))
                    actual_keys = set(http_obs.json_keys)
                    if expected_keys.issubset(actual_keys) or not expected_keys:
                        proof.verdict = "CONFIRMED"
                    else:
                        proof.verdict = "DENIED"
                        proof.observations["shape_mismatch"] = {
                            "expected": sorted(expected_keys),
                            "actual": sorted(actual_keys),
                        }
                else:
                    proof.verdict = "CONFIRMED"
            else:
                proof.verdict = "DENIED"

        except Exception as e:
            proof.verdict = "ERROR"
            proof.observations = {"exception": str(e)}

        self._append_proof(proof)
        return proof

    # ── JSONL Writer ─────────────────────────────────────────

    def _append_proof(self, proof: Proof) -> None:
        proof_dict = asdict(proof)
        self._check_proof_temporal(proof_dict)
        line = json.dumps(proof_dict, separators=(",", ":"), sort_keys=True)
        with open(self.proof_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
