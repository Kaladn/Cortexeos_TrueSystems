"""Source registry for SecureCore sensor readers."""

from __future__ import annotations

from enum import Enum


class SourceMode(str, Enum):
    MIRROR = "mirror"
    INDEX = "index"
    WAKE_ONLY = "wake_only"
    DISABLED = "disabled"


def default_source_registry() -> dict[str, dict]:
    return {
        "windows.application": {
            "source_name": "Application",
            "sensor_class": "system",
            "mode": SourceMode.INDEX.value,
            "privacy_level": "metadata",
            "event_ids_of_interest": [1000, 1001, 1002, 1026, 11707, 11708],
            "forge_destination": "sensor_eventlog",
        },
        "windows.system": {
            "source_name": "System",
            "sensor_class": "system",
            "mode": SourceMode.INDEX.value,
            "privacy_level": "metadata",
            "event_ids_of_interest": [41, 55, 6005, 6006, 6008, 7000, 7001, 7031, 7034, 7036, 7040, 7045],
            "forge_destination": "sensor_eventlog",
        },
        "windows.defender.operational": {
            "source_name": "Microsoft-Windows-Windows Defender/Operational",
            "sensor_class": "security",
            "mode": SourceMode.MIRROR.value,
            "privacy_level": "metadata",
            "event_ids_of_interest": [1006, 1007, 1015, 1116, 1117, 5007],
            "forge_destination": "sensor_eventlog",
        },
        "windows.security": {
            "source_name": "Security",
            "sensor_class": "security",
            "mode": SourceMode.INDEX.value,
            "privacy_level": "metadata",
            "event_ids_of_interest": [4624, 4625, 4672, 4688, 4719, 4720, 4732, 1102],
            "forge_destination": "sensor_eventlog",
        },
        "windows.powershell.operational": {
            "source_name": "Microsoft-Windows-PowerShell/Operational",
            "sensor_class": "security",
            "mode": SourceMode.MIRROR.value,
            "privacy_level": "metadata",
            "event_ids_of_interest": [4103, 4104, 4105, 4106],
            "forge_destination": "sensor_eventlog",
        },
        "windows.wmi.activity": {
            "source_name": "Microsoft-Windows-WMI-Activity/Operational",
            "sensor_class": "security",
            "mode": SourceMode.MIRROR.value,
            "privacy_level": "metadata",
            "event_ids_of_interest": [5857, 5858, 5859, 5860, 5861],
            "forge_destination": "sensor_eventlog",
        },
        "windows.firewall": {
            "source_name": "Microsoft-Windows-Windows Firewall With Advanced Security/Firewall",
            "sensor_class": "network",
            "mode": SourceMode.INDEX.value,
            "privacy_level": "metadata",
            "event_ids_of_interest": [],
            "forge_destination": "sensor_eventlog",
        },
        "windows.task_scheduler.operational": {
            "source_name": "Microsoft-Windows-TaskScheduler/Operational",
            "sensor_class": "system",
            "mode": SourceMode.INDEX.value,
            "privacy_level": "metadata",
            "event_ids_of_interest": [106, 140, 141, 200, 201, 203],
            "forge_destination": "sensor_eventlog",
        },
        "windows.bits_client.operational": {
            "source_name": "Microsoft-Windows-Bits-Client/Operational",
            "sensor_class": "network",
            "mode": SourceMode.INDEX.value,
            "privacy_level": "metadata",
            "event_ids_of_interest": [3, 4, 59, 60, 61],
            "forge_destination": "sensor_eventlog",
        },
        "windows.terminal_services.local_session_manager.operational": {
            "source_name": "Microsoft-Windows-TerminalServices-LocalSessionManager/Operational",
            "sensor_class": "security",
            "mode": SourceMode.INDEX.value,
            "privacy_level": "metadata",
            "event_ids_of_interest": [21, 22, 23, 24, 25, 39, 40],
            "forge_destination": "sensor_eventlog",
        },
        "windows.user_profile_service.operational": {
            "source_name": "Microsoft-Windows-User Profile Service/Operational",
            "sensor_class": "security",
            "mode": SourceMode.INDEX.value,
            "privacy_level": "metadata",
            "event_ids_of_interest": [1, 2, 3, 4, 5, 6, 1530],
            "forge_destination": "sensor_eventlog",
        },
        "windows.codeintegrity.operational": {
            "source_name": "Microsoft-Windows-CodeIntegrity/Operational",
            "sensor_class": "security",
            "mode": SourceMode.MIRROR.value,
            "privacy_level": "metadata",
            "event_ids_of_interest": [3001, 3002, 3033, 3063, 3076, 3077],
            "forge_destination": "sensor_eventlog",
        },
        "windows.app_locker.executable_dll": {
            "source_name": "Microsoft-Windows-AppLocker/EXE and DLL",
            "sensor_class": "security",
            "mode": SourceMode.MIRROR.value,
            "privacy_level": "metadata",
            "event_ids_of_interest": [8002, 8003, 8004],
            "forge_destination": "sensor_eventlog",
        },
        "windows.dns_client.operational": {
            "source_name": "Microsoft-Windows-DNS-Client/Operational",
            "sensor_class": "network",
            "mode": SourceMode.INDEX.value,
            "privacy_level": "metadata",
            "event_ids_of_interest": [3006, 3008, 3010, 3018, 3020],
            "forge_destination": "sensor_eventlog",
        },
        "windows.network_profile.operational": {
            "source_name": "Microsoft-Windows-NetworkProfile/Operational",
            "sensor_class": "network",
            "mode": SourceMode.INDEX.value,
            "privacy_level": "metadata",
            "event_ids_of_interest": [10000, 10001],
            "forge_destination": "sensor_eventlog",
        },
        "windows.process.diff": {
            "source_name": "process_snapshot_diff",
            "sensor_class": "process",
            "mode": SourceMode.INDEX.value,
            "privacy_level": "metadata",
            "event_ids_of_interest": [],
            "forge_destination": "sensor_process",
        },
        "windows.network.diff": {
            "source_name": "network_connection_diff",
            "sensor_class": "network",
            "mode": SourceMode.INDEX.value,
            "privacy_level": "metadata",
            "event_ids_of_interest": [],
            "forge_destination": "sensor_network",
        },
        "windows.open_window.diff": {
            "source_name": "open_window_snapshot_diff",
            "sensor_class": "window",
            "mode": SourceMode.INDEX.value,
            "privacy_level": "metadata",
            "event_ids_of_interest": [],
            "forge_destination": "sensor_window",
        },
        "truevision.state_change": {
            "source_name": "visual_state_change",
            "sensor_class": "vision",
            "mode": SourceMode.WAKE_ONLY.value,
            "privacy_level": "metadata",
            "event_ids_of_interest": [],
            "forge_destination": "sensor_vision",
        },
        "truevision.camera.recognition": {
            "source_name": "camera_recognition",
            "sensor_class": "vision",
            "mode": SourceMode.DISABLED.value,
            "privacy_level": "sensitive",
            "event_ids_of_interest": [],
            "forge_destination": "sensor_vision",
        },
        "audio.microphone.recognition": {
            "source_name": "microphone_recognition",
            "sensor_class": "hid",
            "mode": SourceMode.DISABLED.value,
            "privacy_level": "sensitive",
            "event_ids_of_interest": [],
            "forge_destination": "sensor_hid",
        },
    }


def validate_source_registry(registry: dict[str, dict]) -> None:
    allowed_modes = {item.value for item in SourceMode}
    for source_id, row in registry.items():
        if row.get("mode") not in allowed_modes:
            raise ValueError(f"{source_id} has invalid mode: {row.get('mode')}")
        if not row.get("source_name"):
            raise ValueError(f"{source_id} missing source_name")
        if not row.get("sensor_class"):
            raise ValueError(f"{source_id} missing sensor_class")
        if not row.get("privacy_level"):
            raise ValueError(f"{source_id} missing privacy_level")
        if not row.get("forge_destination"):
            raise ValueError(f"{source_id} missing forge_destination")
