"""Self-signed TLS certificate generator for Clearbox AI LAN access.

Generates a cert + key on first run, stored in %LOCALAPPDATA%\ClearboxAI\auth\tls/.
Subject includes machine hostname + all local IPs as SANs.
Valid 365 days, auto-regenerates when expired.
"""

import datetime
import ipaddress
import logging
import os
import socket
from pathlib import Path
from typing import List, Optional, Tuple

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from security.data_paths import TLS_DIR

LOGGER = logging.getLogger("clearbox.tls")

CERT_PATH = TLS_DIR / "clearbox_ai.crt"
KEY_PATH  = TLS_DIR / "clearbox_ai.key"
VALIDITY_DAYS = 365


def _get_local_ips() -> List[str]:
    """Get all non-loopback IPv4 addresses on this machine."""
    ips = set()
    try:
        hostname = socket.gethostname()
        for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
            addr = info[4][0]
            if not addr.startswith("127."):
                ips.add(addr)
    except Exception:
        pass
    # Also try connecting to a public IP to find the default route
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    return sorted(ips)


def _generate_cert() -> Tuple[Path, Path]:
    """Generate a self-signed cert + key with hostname + LAN IP + Tailscale SANs."""
    hostname = socket.gethostname()
    local_ips = _get_local_ips()

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Clearbox AI"),
        x509.NameAttribute(NameOID.COMMON_NAME, hostname),
    ])

    # Build SANs: hostname + localhost + all local IPs + Tailscale
    san_entries: list = [
        x509.DNSName(hostname),
        x509.DNSName("localhost"),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
    ]
    for ip in local_ips:
        try:
            san_entries.append(x509.IPAddress(ipaddress.IPv4Address(ip)))
        except ValueError:
            pass

    # Include Tailscale IP + hostname if available
    try:
        from security.network import get_tailscale_info
        ts = get_tailscale_info()
        if ts.get("ipv4"):
            san_entries.append(x509.IPAddress(ipaddress.IPv4Address(ts["ipv4"])))
            LOGGER.info("TLS cert includes Tailscale IP: %s", ts["ipv4"])
        if ts.get("hostname"):
            san_entries.append(x509.DNSName(ts["hostname"]))
            LOGGER.info("TLS cert includes Tailscale hostname: %s", ts["hostname"])
    except Exception as e:
        LOGGER.debug("Tailscale detection skipped: %s", e)

    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=VALIDITY_DAYS))
        .add_extension(x509.SubjectAlternativeName(san_entries), critical=False)
        .sign(key, hashes.SHA256())
    )

    TLS_DIR.mkdir(parents=True, exist_ok=True)

    KEY_PATH.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )

    # Restrict key file permissions to current user only (Windows ACL)
    try:
        import subprocess
        subprocess.run(
            ["icacls", str(KEY_PATH), "/inheritance:r",
             "/grant:r", f"{os.environ.get('USERNAME', 'SYSTEM')}:(R,W)"],
            capture_output=True, timeout=5,
        )
        LOGGER.info("TLS key permissions restricted: %s", KEY_PATH)
    except Exception as e:
        LOGGER.warning("Could not restrict TLS key permissions: %s", e)

    CERT_PATH.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

    LOGGER.info("TLS cert generated: CN=%s, SANs=%s, valid %d days",
                hostname, [str(s) for s in san_entries], VALIDITY_DAYS)
    return CERT_PATH, KEY_PATH


def _cert_valid() -> bool:
    """Check if existing cert is present and not expired."""
    if not CERT_PATH.exists() or not KEY_PATH.exists():
        return False
    try:
        cert_data = CERT_PATH.read_bytes()
        cert = x509.load_pem_x509_certificate(cert_data)
        now = datetime.datetime.now(datetime.timezone.utc)
        return cert.not_valid_after_utc > now
    except Exception:
        return False


def _cert_covers_tailscale() -> bool:
    """Check if the cert already includes the Tailscale IP (if Tailscale is available)."""
    try:
        from security.network import get_tailscale_ipv4
        ts_ip = get_tailscale_ipv4()
        if not ts_ip:
            return True  # No Tailscale = nothing to cover
        current_ips = get_cert_san_ips()
        return ts_ip in current_ips
    except Exception:
        return True


def ensure_tls() -> Optional[Tuple[str, str]]:
    """Ensure TLS cert exists, is valid, and covers Tailscale. Returns (cert_path, key_path)."""
    if _cert_valid():
        if not _cert_covers_tailscale():
            LOGGER.info("Tailscale detected but not in cert SANs -- regenerating...")
            cert_path, key_path = _generate_cert()
            return str(cert_path), str(key_path)
        LOGGER.info("TLS cert valid: %s", CERT_PATH)
        return str(CERT_PATH), str(KEY_PATH)

    LOGGER.info("Generating new TLS certificate...")
    cert_path, key_path = _generate_cert()
    return str(cert_path), str(key_path)


def get_cert_fingerprint() -> Optional[str]:
    """Get SHA-256 fingerprint of the current cert (for enrollment bundles)."""
    if not CERT_PATH.exists():
        return None
    try:
        cert_data = CERT_PATH.read_bytes()
        cert = x509.load_pem_x509_certificate(cert_data)
        fp = cert.fingerprint(hashes.SHA256())
        return "sha256:" + fp.hex()
    except Exception:
        return None


def get_cert_san_ips() -> List[str]:
    """Get all IP SANs from the current cert (for CORS origin list)."""
    if not CERT_PATH.exists():
        return []
    try:
        cert_data = CERT_PATH.read_bytes()
        cert = x509.load_pem_x509_certificate(cert_data)
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        return [str(ip) for ip in san.value.get_values_for_type(x509.IPAddress)]
    except Exception:
        return []


def get_cert_san_hostnames() -> List[str]:
    """Get all DNS SANs from the current cert (for CORS with Tailscale)."""
    if not CERT_PATH.exists():
        return []
    try:
        cert_data = CERT_PATH.read_bytes()
        cert = x509.load_pem_x509_certificate(cert_data)
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        return [name for name in san.value.get_values_for_type(x509.DNSName)
                if name not in ("localhost",)]
    except Exception:
        return []
