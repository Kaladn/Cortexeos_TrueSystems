import psutil

class CPUCoreRecovery:
    def detect_and_recover(self, core_metrics):
        """
        Detect buggy cores and recover them.
        """
        buggy_core = self._find_buggy_core(core_metrics)
        if buggy_core is not None:
            print(f"Buggy core detected: {buggy_core}. Rebooting core...")
            self._reboot_core(buggy_core)

    def _find_buggy_core(self, core_metrics):
        """
        Identify buggy cores based on usage patterns.
        """
        for i, usage in enumerate(core_metrics):
            if usage > 95 or usage < 5:  # Anomaly thresholds
                return i
        return None

    def _reboot_core(self, core_index):
        """
        Reboot the specified CPU core.
        """
        print(f"Rebooting core {core_index}.")
        # Placeholder logic for rebooting CPU cores
