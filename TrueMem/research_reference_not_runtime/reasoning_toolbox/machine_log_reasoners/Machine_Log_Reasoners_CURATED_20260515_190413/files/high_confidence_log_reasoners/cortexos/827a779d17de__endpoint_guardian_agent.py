"""
Agent Module: Endpoint Guardian Agent (EGA)

Responsible for endpoint security, including behavioral anomaly detection,
USB device monitoring/whitelisting, and adaptive file encryption management.

Based on design in: docs/endpoint_guardian_agent_design.md
"""

import time
import json # For potential BSL interaction formatting
# Assuming bsl_adapter is imported from the src directory structure
# from ..binary_symbolic_lexicon import BinarySymbolicLexiconAdapter

class EndpointGuardianAgent:
    def __init__(self, bsl_adapter, agent_config=None, endpoint_id="endpoint_01"):
        self.bsl_adapter = bsl_adapter
        self.config = agent_config if agent_config else {}
        self.endpoint_id = endpoint_id
        self.behavioral_baselines = {} # {user_id: {allowed_processes, ...}}
        self.usb_whitelist = [] # List of {vendor_id, product_id, serial_number}
        self.sensitive_files_map = {} # {filepath: {encrypted_status, key_id}}
        self.event_log = [] # Local log for simulation
        self._load_initial_state()
        print(f"EndpointGuardianAgent for {self.endpoint_id} initialized.")

    def _load_initial_state(self):
        """Loads baselines, whitelists, sensitive file info from BSL/config (simulated)."""
        # Simulated loading
        self.behavioral_baselines["user_default"] = {
            "allowed_processes": ["explorer.exe", "notepad.exe", "chrome.exe", "outlook.exe"],
            "typical_network_dest_ports": {80, 443, 22, 3389},
            "sensitive_file_access_allowed_processes": ["notepad.exe", "word.exe"]
        }
        self.usb_whitelist.append({"vendor_id": "0x123", "product_id": "0xABC", "serial_number": "SN001", "description": "Standard Keyboard"})
        self.usb_whitelist.append({"vendor_id": "0x456", "product_id": "0xDEF", "serial_number": "SN002", "description": "Approved USB Drive"})
        self.sensitive_files_map["/sensitive/report.docx"] = {"encrypted_status": False, "key_id": "default_key"}
        self.sensitive_files_map["/personal/photos/image.jpg"] = {"encrypted_status": False, "key_id": "personal_key"}
        print(f"EGA ({self.endpoint_id}): Initial state (baselines, USB whitelist, sensitive files) loaded (simulated).")

    def _log_to_bsl_simulation(self, event_type, event_data):
        """Simulates logging an event to the BSL (would be via Forensic Archiver Agent)."""
        timestamp = time.time()
        log_entry_id = f"ega_log_{self.endpoint_id}_{event_type}_{timestamp}"
        bsl_payload = {
            "neuron_id": log_entry_id,
            "concept_text": json.dumps(event_data),
            "type": f"ega_event_log",
            "event_subtype": event_type,
            "timestamp": timestamp,
            "agent_id": "EndpointGuardianAgent",
            "endpoint_id": self.endpoint_id
        }
        # In a real system: self.forensic_archiver.log_event(bsl_payload)
        # For prototype: self.bsl_adapter.add_neuron(bsl_payload) # (if BSL adapter supports generic add_neuron)
        print(f"BSL_LOG_SIM (EGA - {self.endpoint_id}): Type: {event_type}, Data: {event_data}")
        self.event_log.append(bsl_payload)

    # --- Behavioral Anomaly Detection ---
    def monitor_process_activity(self, process_name, user_id="user_default", command_line=""):
        """Simulates monitoring a new process and checking for anomalies."""
        event_data = {"process_name": process_name, "user_id": user_id, "command_line": command_line}
        is_anomalous = False
        anomaly_reason = "No specific anomaly detected."

        baseline_user = user_id if user_id in self.behavioral_baselines else "user_default"
        user_baseline = self.behavioral_baselines.get(baseline_user, {})

        if process_name not in user_baseline.get("allowed_processes", []):
            is_anomalous = True
            anomaly_reason = f"Process 	'{process_name}' not in baseline allowed list for user 	'{baseline_user}'"
        
        # Add more sophisticated checks here, e.g., command line arguments, parent process, etc.

        if is_anomalous:
            print(f"EGA ({self.endpoint_id}): ANOMALY DETECTED - Process: {process_name} by {user_id}. Reason: {anomaly_reason}")
            event_data["anomaly_reason"] = anomaly_reason
            self._log_to_bsl_simulation("behavioral_anomaly_process", event_data)
            # Trigger response: e.g., alert WarRoom, increase monitoring, attempt to terminate (simulated)
            self.trigger_adaptive_encryption(threat_level="high", reason=f"Anomalous process: {process_name}")
        else:
            print(f"EGA ({self.endpoint_id}): Process activity normal: {process_name} by {user_id}")
            self._log_to_bsl_simulation("process_activity_normal", event_data)
        return not is_anomalous

    def monitor_file_access(self, file_path, process_name, access_type="read", user_id="user_default"):
        """Simulates monitoring file access and checking for anomalies."""
        event_data = {"file_path": file_path, "process_name": process_name, "access_type": access_type, "user_id": user_id}
        is_anomalous = False
        anomaly_reason = "No specific anomaly detected."

        if file_path in self.sensitive_files_map:
            baseline_user = user_id if user_id in self.behavioral_baselines else "user_default"
            user_baseline = self.behavioral_baselines.get(baseline_user, {})
            if process_name not in user_baseline.get("sensitive_file_access_allowed_processes", []):
                is_anomalous = True
                anomaly_reason = f"Process 	'{process_name}	' not allowed to access sensitive file 	'{file_path}	' for user 	'{baseline_user}	'"
        
        if is_anomalous:
            print(f"EGA ({self.endpoint_id}): ANOMALY DETECTED - File Access: {file_path} by {process_name}. Reason: {anomaly_reason}")
            event_data["anomaly_reason"] = anomaly_reason
            self._log_to_bsl_simulation("behavioral_anomaly_file_access", event_data)
            self.trigger_adaptive_encryption(threat_level="critical", reason=f"Anomalous file access: {file_path} by {process_name}")
        else:
            print(f"EGA ({self.endpoint_id}): File access normal: {file_path} by {process_name}")
            self._log_to_bsl_simulation("file_access_normal", event_data)
        return not is_anomalous

    # --- USB Device Monitoring ---
    def handle_usb_insertion(self, vendor_id, product_id, serial_number):
        """Simulates handling a USB device insertion."""
        device_info = {"vendor_id": vendor_id, "product_id": product_id, "serial_number": serial_number}
        is_whitelisted = any(
            d["vendor_id"] == vendor_id and 
            d["product_id"] == product_id and 
            (d["serial_number"] == serial_number or not d.get("serial_number")) # Allow if SN not in whitelist entry
            for d in self.usb_whitelist
        )

        if not is_whitelisted:
            print(f"EGA ({self.endpoint_id}): UNWHITELISTED USB DETECTED - VID:{vendor_id}, PID:{product_id}, SN:{serial_number}")
            self._log_to_bsl_simulation("unwhitelisted_usb_detected", device_info)
            # Trigger response: e.g., alert, simulate block, request endpoint isolation
            self.trigger_adaptive_encryption(threat_level="high", reason=f"Unwhitelisted USB: VID:{vendor_id},PID:{product_id}")
        else:
            print(f"EGA ({self.endpoint_id}): Whitelisted USB device inserted: VID:{vendor_id}, PID:{product_id}, SN:{serial_number}")
            self._log_to_bsl_simulation("whitelisted_usb_inserted", device_info)
        return is_whitelisted

    # --- Adaptive File Encryption ---
    def trigger_adaptive_encryption(self, threat_level="medium", reason="generic_threat_increase"):
        """Simulates triggering encryption of sensitive files based on threat level."""
        print(f"EGA ({self.endpoint_id}): Adaptive encryption triggered. Reason: 	'{reason}', Level: {threat_level}")
        self._log_to_bsl_simulation("adaptive_encryption_triggered", {"threat_level": threat_level, "reason": reason})
        encrypted_count = 0
        for file_path, file_meta in self.sensitive_files_map.items():
            if not file_meta["encrypted_status"]:
                self._simulate_encrypt_file(file_path, file_meta["key_id"])
                encrypted_count += 1
        if encrypted_count > 0:
            print(f"EGA ({self.endpoint_id}): {encrypted_count} sensitive files newly encrypted.")
        else:
            print(f"EGA ({self.endpoint_id}): No new files needed encryption or no sensitive files defined.")

    def _simulate_encrypt_file(self, file_path, key_id):
        """Simulates encrypting a file."""
        if file_path in self.sensitive_files_map:
            self.sensitive_files_map[file_path]["encrypted_status"] = True
            print(f"EGA ({self.endpoint_id}): File 	'{file_path}' SIMULATED ENCRYPTION with key 	'{key_id}'.")
            self._log_to_bsl_simulation("file_encrypted", {"file_path": file_path, "key_id": key_id})
        else:
            print(f"EGA ({self.endpoint_id}): File 	'{file_path}' not in sensitive map for encryption.")

    def _simulate_decrypt_file(self, file_path, key_id, user_id="user_default"):
        """Simulates decrypting a file (e.g., on authorized access)."""
        # Add a check: only decrypt if threat level is low or user is highly privileged (conceptual)
        if file_path in self.sensitive_files_map and self.sensitive_files_map[file_path]["encrypted_status"]:
            self.sensitive_files_map[file_path]["encrypted_status"] = False
            print(f"EGA ({self.endpoint_id}): File 	'{file_path}' SIMULATED DECRYPTION with key 	'{key_id}' for user 	'{user_id}'.")
            self._log_to_bsl_simulation("file_decrypted", {"file_path": file_path, "key_id": key_id, "user_id": user_id})
        elif file_path in self.sensitive_files_map and not self.sensitive_files_map[file_path]["encrypted_status"]:
            print(f"EGA ({self.endpoint_id}): File 	'{file_path}' already decrypted.")
        else:
            print(f"EGA ({self.endpoint_id}): File 	'{file_path}' not in sensitive map for decryption.")

    def run_periodic_tasks(self):
        """Method for periodic checks, baseline adjustments, etc."""
        print(f"EGA ({self.endpoint_id}): Running periodic tasks...")
        # Example: Re-evaluate baselines, check for stale encrypted files, etc.
        # For instance, if a threat level reduces, some files might be decrypted.
        # self.check_threat_level_and_adjust_encryption()
        self._log_to_bsl_simulation("periodic_task_execution", {"status": "completed"})

# Example Usage (for testing the agent directly)
if __name__ == "__main__":
    class MockBSLAdapter:
        def __init__(self):
            print("MockBSLAdapter initialized for EGA test.")
        def add_neuron(self, neuron_data):
            print(f"MockBSL (EGA): Add Neuron called with Type: {neuron_data.get(	'type	')}, ID: {neuron_data.get(	'neuron_id	')}")
        def get_neuron_data(self, neuron_id):
            print(f"MockBSL (EGA): Get Neuron Data for {neuron_id}")
            return None # Simulate no data found for simplicity

    mock_bsl = MockBSLAdapter()
    ega = EndpointGuardianAgent(bsl_adapter=mock_bsl, endpoint_id="test_endpoint_001")

    print("\n--- Testing Process Monitoring ---")
    ega.monitor_process_activity("notepad.exe", user_id="user_default")
    ega.monitor_process_activity("evil_process.exe", user_id="user_default")
    ega.monitor_process_activity("chrome.exe", user_id="user_guest") # Test unknown user

    print("\n--- Testing File Access Monitoring ---")
    ega.monitor_file_access("/sensitive/report.docx", "notepad.exe", user_id="user_default")
    ega.monitor_file_access("/sensitive/report.docx", "evil_process.exe", user_id="user_default")
    ega.monitor_file_access("/regular/document.txt", "notepad.exe", user_id="user_default")

    print("\n--- Testing USB Device Handling ---")
    ega.handle_usb_insertion("0x123", "0xABC", "SN001") # Whitelisted
    ega.handle_usb_insertion("0xBAD", "0xC0DE", "SN_EVIL") # Not whitelisted

    print("\n--- Testing Adaptive Encryption ---")
    print(f"Initial encryption status for /sensitive/report.docx: {ega.sensitive_files_map[	'/sensitive/report.docx'	][	'encrypted_status'	]}")
    ega.trigger_adaptive_encryption(threat_level="medium", reason="Suspicious network scan detected by PDA")
    print(f"Post-trigger encryption status for /sensitive/report.docx: {ega.sensitive_files_map[	'/sensitive/report.docx'	][	'encrypted_status'	]}")
    ega._simulate_decrypt_file("/sensitive/report.docx", "default_key", user_id="user_default")
    print(f"Post-decryption status for /sensitive/report.docx: {ega.sensitive_files_map[	'/sensitive/report.docx'	][	'encrypted_status'	]}")

    print("\n--- Testing Periodic Tasks ---")
    ega.run_periodic_tasks()

    print("\nEndpointGuardianAgent test completed.")

