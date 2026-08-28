import unittest

from securecore.sensors.source_registry import (
    SourceMode,
    default_source_registry,
    validate_source_registry,
)


class SourceRegistryTests(unittest.TestCase):
    def test_default_registry_marks_defender_as_mirror(self):
        registry = default_source_registry()
        source = registry["windows.defender.operational"]
        self.assertEqual(source["mode"], SourceMode.MIRROR.value)
        self.assertEqual(source["privacy_level"], "metadata")

    def test_default_registry_keeps_camera_and_mic_disabled(self):
        registry = default_source_registry()
        self.assertEqual(registry["truevision.camera.recognition"]["mode"], SourceMode.DISABLED.value)
        self.assertEqual(registry["audio.microphone.recognition"]["mode"], SourceMode.DISABLED.value)

    def test_validate_rejects_unknown_mode(self):
        registry = default_source_registry()
        registry["windows.defender.operational"]["mode"] = "copy_everything"
        with self.assertRaises(ValueError):
            validate_source_registry(registry)

    def test_default_registry_covers_core_windows_eventlog_channels(self):
        registry = default_source_registry()
        expected = {
            "windows.application",
            "windows.system",
            "windows.security",
            "windows.defender.operational",
            "windows.powershell.operational",
            "windows.wmi.activity",
            "windows.task_scheduler.operational",
            "windows.bits_client.operational",
            "windows.terminal_services.local_session_manager.operational",
            "windows.user_profile_service.operational",
            "windows.codeintegrity.operational",
            "windows.app_locker.executable_dll",
            "windows.firewall",
            "windows.dns_client.operational",
            "windows.network_profile.operational",
        }

        self.assertTrue(expected.issubset(set(registry)))
        for source_id in expected:
            self.assertEqual(registry[source_id]["privacy_level"], "metadata")
            self.assertEqual(registry[source_id]["forge_destination"], "sensor_eventlog")


if __name__ == "__main__":
    unittest.main()
