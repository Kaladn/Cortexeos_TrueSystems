import psutil

class MonitoringUtility:
    def collect_metrics(self):
        """
        Collect real-time system metrics.
        """
        return {
            "cpu_usage": psutil.cpu_percent(percpu=True),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_io": psutil.disk_io_counters(),
        }
