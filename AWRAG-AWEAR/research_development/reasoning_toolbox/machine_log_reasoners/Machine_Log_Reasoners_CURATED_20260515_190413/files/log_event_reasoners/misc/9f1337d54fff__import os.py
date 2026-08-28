import os

def create_project_structure(base_dir):
    structure = {
        "Cortex_Cyber_Suite": {
            "ai_modules": ["threat_analysis.py", "deception_engine.py", "countermeasures.py", "global_tracker.py"],
            "iot_integration": ["device_manager.py", "protocol_adapter.py"],
            "perimeter_defense": ["firewall_manager.py", "ips_engine.py", "threat_intelligence.py"],
            "endpoint_protection": ["behavior_analytics.py", "adaptive_encryption.py", "remote_access_monitor.py"],
            "communication_security": ["secure_messaging.py", "biometric_auth.py", "stealth_tunnels.py"],
            "dashboard": ["war_room_dashboard.py", "real_time_monitor.py"],
            "data_forensics": ["forensic_collector.py", "incident_reporter.py"],
            "osint_monitoring": ["darkweb_scanner.py", "osint_correlator.py"],
            "utilities": ["logger.py", "config_loader.py"]
        }
    }

    def create_dirs(base_path, tree):
        for key, value in tree.items():
            folder_path = os.path.join(base_path, key)
            os.makedirs(folder_path, exist_ok=True)
            for file in value:
                file_path = os.path.join(folder_path, file)
                with open(file_path, 'w') as f:
                    f.write("# Placeholder for {}".format(file))

    create_dirs(base_dir, structure)

if __name__ == "__main__":
    base_directory = os.path.expanduser("~\\Desktop")  # Creates on Desktop
    create_project_structure(base_directory)
