"""USB device detection for Forest AI mobile node pairing.

Detects USB-connected mobile devices via:
  1. ADB (Android Debug Bridge) — subprocess `adb devices -l`
  2. WMI fallback — Win32_PnPEntity for portable devices

No new pip dependencies — uses subprocess + built-in Windows tools.
"""

import logging
import re
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

LOGGER = logging.getLogger("forest.node.usb")


@dataclass
class USBDevice:
    """Detected USB device info."""
    serial: str
    vendor: str = ""
    model: str = ""
    platform: str = "unknown"  # "android", "ios", "unknown"
    transport_id: Optional[str] = None


def detect_adb_devices() -> List[USBDevice]:
    """Detect Android devices via ADB.

    Parses output of `adb devices -l`:
        R5CX12345          device usb:1-3 product:a55 model:SM_A556B transport_id:1
    """
    devices = []
    try:
        result = subprocess.run(
            ["adb", "devices", "-l"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            LOGGER.debug("ADB not available: %s", result.stderr.strip())
            return devices

        for line in result.stdout.strip().splitlines()[1:]:  # skip header
            line = line.strip()
            if not line or line.startswith("*"):
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            serial = parts[0]
            state = parts[1]
            if state != "device":
                LOGGER.debug("ADB device %s in state: %s (skipping)", serial, state)
                continue

            # Parse key:value pairs from the rest
            props = {}
            for part in parts[2:]:
                if ":" in part:
                    k, v = part.split(":", 1)
                    props[k] = v

            devices.append(USBDevice(
                serial=serial,
                vendor=props.get("product", ""),
                model=props.get("model", "").replace("_", " "),
                platform="android",
                transport_id=props.get("transport_id"),
            ))

    except FileNotFoundError:
        LOGGER.debug("ADB not found on PATH")
    except subprocess.TimeoutExpired:
        LOGGER.warning("ADB timed out")
    except Exception as e:
        LOGGER.warning("ADB detection error: %s", e)

    return devices


def detect_wmi_devices() -> List[USBDevice]:
    """Detect USB portable devices via WMIC (Windows fallback).

    Looks for devices under WPD (Windows Portable Devices) class.
    """
    devices = []
    try:
        result = subprocess.run(
            ["wmic", "path", "Win32_PnPEntity", "where",
             "PNPClass='WPD'", "get", "Name,DeviceID", "/format:csv"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return devices

        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if not line or line.startswith("Node"):
                continue
            parts = line.split(",")
            if len(parts) < 3:
                continue
            device_id = parts[1].strip()
            name = parts[2].strip()
            if not name:
                continue

            # Extract serial from device ID if possible
            serial_match = re.search(r'\\([A-Za-z0-9_]+)$', device_id)
            serial = serial_match.group(1) if serial_match else device_id[-12:]

            platform = "unknown"
            name_lower = name.lower()
            if "iphone" in name_lower or "ipad" in name_lower or "apple" in name_lower:
                platform = "ios"
            elif "samsung" in name_lower or "pixel" in name_lower or "android" in name_lower:
                platform = "android"

            devices.append(USBDevice(
                serial=serial,
                vendor="",
                model=name,
                platform=platform,
            ))

    except FileNotFoundError:
        LOGGER.debug("WMIC not available")
    except subprocess.TimeoutExpired:
        LOGGER.warning("WMIC timed out")
    except Exception as e:
        LOGGER.warning("WMI detection error: %s", e)

    return devices


def detect_usb_devices() -> List[USBDevice]:
    """Detect all USB-connected mobile devices.

    Tries ADB first (best for Android), falls back to WMI.
    Deduplicates by serial.
    """
    seen_serials = set()
    devices = []

    # ADB first -- most reliable for Android
    for dev in detect_adb_devices():
        if dev.serial not in seen_serials:
            seen_serials.add(dev.serial)
            devices.append(dev)

    # WMI fallback -- catches iOS and non-ADB devices
    for dev in detect_wmi_devices():
        if dev.serial not in seen_serials:
            seen_serials.add(dev.serial)
            devices.append(dev)

    LOGGER.info("USB detection: found %d device(s)", len(devices))
    return devices


def adb_push_file(serial: str, local_path: str, remote_path: str) -> bool:
    """Push a file to an Android device via ADB.

    Args:
        serial: Device serial number
        local_path: Local file path to push
        remote_path: Target path on device (e.g., /sdcard/Download/ForestAI/)

    Returns:
        True if push succeeded
    """
    try:
        result = subprocess.run(
            ["adb", "-s", serial, "push", local_path, remote_path],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            LOGGER.info("ADB push to %s: %s -> %s", serial, local_path, remote_path)
            return True
        else:
            LOGGER.warning("ADB push failed: %s", result.stderr.strip())
            return False
    except Exception as e:
        LOGGER.warning("ADB push error: %s", e)
        return False
