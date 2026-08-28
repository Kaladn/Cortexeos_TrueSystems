"""
Agent Module: Forensic Archiver Agent (FAA)

Responsible for securely logging all significant events, actions, and data
from other agents and system components into the Binary-Symbolic Lexicon (BSL).

Based on design in: docs/forensic_archiver_agent_design.md
"""

import time
import json
import hashlib # For conceptual hash
import uuid # For unique log IDs

# from ..binary_symbolic_lexicon import BinarySymbolicLexiconAdapter

class ForensicArchiverAgent:
    def __init__(self, bsl_adapter, agent_config=None):
        self.bsl_adapter = bsl_adapter
        self.config = agent_config if agent_config else {}
        self.log_buffer = [] # Optional: for batching, though direct BSL write is simpler for prototype
        print("ForensicArchiverAgent initialized.")

    def _generate_conceptual_hash(self, data_dict):
        """Generates a SHA256 hash of a dictionary for conceptual immutability."""
        encoded_data = json.dumps(data_dict, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded_data).hexdigest()

    def log_event(self, source_agent_id, event_type, event_details, severity="info"):
        """Receives an event from another agent and logs it to the BSL."""
        timestamp = time.time()
        log_id = str(uuid.uuid4()) # Unique ID for the log entry
        
        conceptual_hash = self._generate_conceptual_hash({
            "timestamp": timestamp,
            "source_agent_id": source_agent_id,
            "event_type": event_type,
            "details": event_details,
            "severity": severity
        })

        bsl_neuron_id = f"log_entry_{log_id}" # BSL neuron ID
        bsl_payload = {
            "neuron_id": bsl_neuron_id,
            "concept_text": json.dumps(event_details), # Core details as JSON string
            "type": "forensic_event_log",
            "attributes": {
                "log_uuid": log_id,
                "timestamp": timestamp,
                "source_agent_id": source_agent_id,
                "event_type": event_type,
                "severity": severity,
                "conceptual_hash": conceptual_hash,
                "archival_status": "active"
            }
        }

        print(f"BSL_LOG_SIM (FAA): Logging event. Neuron ID: {bsl_neuron_id}, Type: {event_type}, Source: {source_agent_id}, Details: {json.dumps(event_details)}")
        # self.bsl_adapter.add_neuron(bsl_payload) # Actual BSL call
        self.log_buffer.append(bsl_payload) # Store locally for test inspection
        return log_id

    def simulate_cold_storage_handoff(self, cutoff_age_seconds=(48 * 60 * 60)):
        """Simulates identifying old logs and marking them for cold storage."""
        print(f"FAA: Simulating cold storage handoff for logs older than {cutoff_age_seconds / 3600} hours.")
        current_time = time.time()
        archived_count = 0
        
        # Simulate iterating through locally buffered logs for this prototype
        logs_to_keep = []
        for log_payload in self.log_buffer:
            if log_payload["attributes"]["timestamp"] < (current_time - cutoff_age_seconds) and log_payload["attributes"]["archival_status"] == "active":
                log_payload["attributes"]["archival_status"] = "archived_to_cold_storage_simulated"
                neuron_id_val = log_payload["neuron_id"]
                print(f"FAA: Marked log {neuron_id_val} for simulated cold storage.")
                archived_count += 1
            logs_to_keep.append(log_payload) # Keep all logs in buffer for now, just update status
        self.log_buffer = logs_to_keep

        log_event_details = {
            "cutoff_age_seconds": cutoff_age_seconds,
            "simulated_action": "Checked buffered logs and marked for archival.",
            "archived_count_simulated": archived_count
        }
        self.log_event("ForensicArchiverAgent", "cold_storage_cycle_executed", log_event_details, severity="info")
        print(f"FAA: Cold storage handoff simulation complete. {archived_count} logs marked (simulated).")
        return archived_count

    def run_periodic_tasks(self):
        """Method for periodic tasks like cold storage handoff."""
        print("FAA: Running periodic tasks...")
        self.simulate_cold_storage_handoff()
        print("FAA: Periodic tasks executed.")

# Example Usage (for testing the agent directly)
if __name__ == "__main__":
    class MockBSLAdapter:
        def __init__(self):
            print("MockBSLAdapter initialized for FAA test.")
        def add_neuron(self, neuron_data):
            # This would be the actual call in a real integration
            print(f"MockBSL (FAA): Add Neuron called with Type: {neuron_data.get(	'type'	)}, ID: {neuron_data.get(	'neuron_id'	)}")

    mock_bsl = MockBSLAdapter()
    faa_instance = ForensicArchiverAgent(bsl_adapter=mock_bsl)

    print("\n--- Testing Event Logging ---")
    log_id1 = faa_instance.log_event("PerimeterDefenseAgent", "firewall_rule_added", {"rule_id": "FR001", "action": "block", "source_ip": "1.2.3.4"}, "medium")
    log_id2 = faa_instance.log_event("EndpointGuardianAgent", "unwhitelisted_usb_detected", {"device_vid": "0xBAD", "device_pid": "0xC0DE"}, "high")
    log_id3 = faa_instance.log_event("DeceptionCommanderAgent", "honeypot_interaction", {"honeypot_id": "HP005", "attacker_ip": "5.6.7.8", "action": "login_attempt"}, "medium")
    
    # Simulate some time passing for cold storage
    # To do this effectively in a test, we might need to manipulate timestamps or have a dedicated old log
    # For now, the buffer check will be immediate.
    print(f"FAA Log Buffer has {len(faa_instance.log_buffer)} entries.")

    print("\n--- Testing Cold Storage Handoff (Simulated) ---")
    # Manually adjust a log's timestamp to be older for testing
    if faa_instance.log_buffer:
        faa_instance.log_buffer[0]["attributes"]["timestamp"] = time.time() - (49 * 60 * 60) # Make first log 49 hours old
        neuron_id_to_age = faa_instance.log_buffer[0]["neuron_id"]
        print(f"Manually aged log: {neuron_id_to_age}")

    faa_instance.simulate_cold_storage_handoff()
    
    print("\n--- Testing Periodic Tasks ---")
    faa_instance.run_periodic_tasks() # This will run cold storage again

    print("\nForensicArchiverAgent test completed.")
    print(f"Final FAA Log Buffer content ({len(faa_instance.log_buffer)} entries):")
    for log_entry in faa_instance.log_buffer:
        print(json.dumps(log_entry, indent=2))

