"""
Agent Module: Threat Hunting Overseer (THO) Agent

Proactively searches for, identifies, and analyzes potential threats and
anomalous patterns across the monitored environment. Correlates data from
various sources to uncover sophisticated or hidden attack campaigns.

Based on design in: docs/threat_hunting_overseer_agent_design.md
"""

import time
import json
import random

# from ..binary_symbolic_lexicon import BinarySymbolicLexiconAdapter
# from .forensic_archiver_agent import ForensicArchiverAgent

class ThreatHuntingOverseerAgent:
    def __init__(self, bsl_adapter, forensic_archiver, other_agents_refs=None, agent_config=None):
        self.bsl_adapter = bsl_adapter
        self.forensic_archiver = forensic_archiver
        self.other_agents_refs = other_agents_refs if other_agents_refs else {}
        self.config = agent_config if agent_config else {}
        self.active_hunts = {}  # {hunt_id: {details, status, findings}}
        self.threat_hypotheses = []  # List of current hypotheses
        print("ThreatHuntingOverseerAgent initialized.")

    def _log_tho_event(self, event_type, event_details, severity="info"):
        if self.forensic_archiver:
            self.forensic_archiver.log_event("ThreatHuntingOverseerAgent", event_type, event_details, severity)
        else:
            print(f"THO_LOG (no archiver): Agent: ThreatHuntingOverseerAgent, Type: {event_type}, Severity: {severity}, Details: {json.dumps(event_details)}")

    def _query_bsl_for_patterns(self, indicators):
        """Simulates querying BSL for patterns related to given indicators."""
        print(f"THO: Querying BSL for patterns related to indicators: {indicators}")
        mock_bsl_findings = []
        if "1.2.3.4" in indicators:
            mock_bsl_findings.append({"neuron_id": "bsl_threat_intel_001", "type": "known_malicious_ip", "details": {"ip": "1.2.3.4", "threat_actor": "TA505_sim"}})
        if "suspicious_process.exe" in indicators:
            mock_bsl_findings.append({"neuron_id": "bsl_malware_sig_002", "type": "malware_signature", "details": {"process_name": "suspicious_process.exe", "family": "GenericDropper_sim"}})
        self._log_tho_event("bsl_pattern_query", {"indicators": indicators, "findings_count": len(mock_bsl_findings)})
        return mock_bsl_findings

    def _correlate_events(self, event_list):
        """Simulates correlating a list of events to find suspicious sequences."""
        print(f"THO: Correlating {len(event_list)} events.")
        correlated_threats = []
        if len(event_list) > 1 and random.choice([True, False]):
            event_types_sample = [str(event.get("event_type", "unknown_type")) for event in event_list[:2]] # Get first two event types
            correlated_threat_details = {
                "description": "Simulated correlated threat: High-risk activity sequence detected.",
                "involved_events_sample": event_types_sample,
                "confidence": "medium"
            }
            correlated_threats.append(correlated_threat_details)
            self._log_tho_event("events_correlated_threat_found", correlated_threat_details, "warning")
        return correlated_threats

    def initiate_hunt_campaign(self, campaign_name, initial_indicators=None, hunt_rules=None):
        """Starts a new threat hunting campaign."""
        hunt_id = f"hunt_{campaign_name.replace(' ', '_').lower()}_{int(time.time())}"
        self.active_hunts[hunt_id] = {
            "name": campaign_name,
            "start_time": time.time(),
            "status": "active",
            "indicators": initial_indicators if initial_indicators else [],
            "rules": hunt_rules if hunt_rules else [],
            "findings": [],
            "hypotheses": []
        }
        self._log_tho_event("hunt_campaign_initiated", {"hunt_id": hunt_id, "name": campaign_name, "indicators": initial_indicators})
        print(f"THO: Initiated Hunt Campaign '{campaign_name}' (ID: {hunt_id}).")
        self.process_hunt_iteration(hunt_id) # Process one iteration immediately
        return hunt_id

    def process_hunt_iteration(self, hunt_id):
        """Processes one iteration of an active hunt campaign."""
        if hunt_id not in self.active_hunts or self.active_hunts[hunt_id]["status"] != "active":
            print(f"THO: Hunt campaign {hunt_id} not active or not found.")
            self._log_tho_event("hunt_iteration_failed", {"hunt_id": hunt_id, "reason": "not_active_or_found"}, "error")
            return

        hunt_data = self.active_hunts[hunt_id]
        print(f"THO: Processing iteration for hunt '{hunt_data['name']}'.")

        bsl_findings = self._query_bsl_for_patterns(hunt_data["indicators"])
        for finding in bsl_findings:
            hunt_data["findings"].append({"source": "BSL_sim", "data": finding, "timestamp": time.time()})

        mock_events_from_faa = []
        if self.forensic_archiver: # Check if FAA is available
            # Simulate querying FAA based on indicators - this is a simplification
            # Real FAA would have a query method.
            for log_entry in getattr(self.forensic_archiver, 'log_buffer', []): # Accessing FAA's log_buffer if it exists
                log_details_str = log_entry.get("concept_text", "")
                try:
                    log_details = json.loads(log_details_str)
                except json.JSONDecodeError:
                    log_details = {}
                
                matches_indicator = False
                for indicator in hunt_data["indicators"]:
                    if indicator in str(log_details) or indicator in log_entry.get("attributes", {}).get("event_type", ""):
                        matches_indicator = True
                        break
                if matches_indicator:
                    mock_events_from_faa.append(log_entry)
        
        for event in mock_events_from_faa:
            hunt_data["findings"].append({"source": "FAA_sim_query", "data": event, "timestamp": time.time()})

        all_current_findings_data = [f["data"] for f in hunt_data["findings"]]
        correlated_threats = self._correlate_events(all_current_findings_data)
        for threat in correlated_threats:
            hypothesis = f"Hypothesis: {threat['description']} based on indicators {hunt_data['indicators']}. Confidence: {threat['confidence']}"
            hunt_data["hypotheses"].append(hypothesis)
            self.threat_hypotheses.append(hypothesis)
            self._log_tho_event("threat_hypothesis_generated", {"hunt_id": hunt_id, "hypothesis": hypothesis, "details": threat}, "warning")

        if correlated_threats:
            print(f"THO: Hunt '{hunt_data['name']}' found {len(correlated_threats)} correlated threats. Alerting War Room (simulated)." )
            if "war_room" in self.other_agents_refs and hasattr(self.other_agents_refs["war_room"], "receive_alert"):
                self.other_agents_refs["war_room"].receive_alert("ThreatHuntingOverseerAgent", "correlated_threat_detected", threat, "high")
            # Simulate adding confirmed findings to BSL
            # for threat_detail in correlated_threats:
            # self.bsl_adapter.add_neuron({ "type": "confirmed_threat_finding", ... }) 

        self._log_tho_event("hunt_iteration_processed", {"hunt_id": hunt_id, "findings_count": len(hunt_data["findings"]), "hypotheses_count": len(hunt_data["hypotheses"])})
        print(f"THO: Hunt '{hunt_data['name']}' iteration complete.")
        # Mark as completed after one iteration for prototype simplicity in tests
        self.active_hunts[hunt_id]["status"] = "completed_iteration_manual"

    def review_active_hypotheses(self):
        print(f"THO: Reviewing {len(self.threat_hypotheses)} active threat hypotheses.")
        for hypo in self.threat_hypotheses:
            print(f"  - {hypo}")
        self._log_tho_event("hypotheses_review_cycle", {"count": len(self.threat_hypotheses)})

    def run_periodic_tasks(self):
        """Method for periodic hunting tasks or hypothesis reviews."""
        print("THO: Running periodic tasks...")
        if not self.active_hunts or random.random() < 0.2: # 20% chance to start a general hunt
            self.initiate_hunt_campaign("general_anomaly_sweep_periodic", initial_indicators=["unusual_data_transfer_sim", "multiple_auth_failures_sim"])
        
        self.review_active_hypotheses()
        
        for hunt_id in list(self.active_hunts.keys()):
            if self.active_hunts[hunt_id]["status"] == "active": # Only process if still active (not completed by initiate_hunt)
                 self.process_hunt_iteration(hunt_id)
                 self.active_hunts[hunt_id]["status"] = "completed_iteration_periodic"

        print("THO: Periodic tasks executed.")

# Example Usage (for testing the agent directly)
if __name__ == "__main__":
    class MockBSLAdapter:
        def __init__(self):
            print("MockBSLAdapter initialized for THO test.")
        def add_neuron(self, neuron_data):
            print(f"MockBSL (THO): Add Neuron: {neuron_data.get('type')} - {neuron_data.get('neuron_id')}")
        def query_neurons(self, query_params):
            print(f"MockBSL (THO): Query Neurons with: {query_params}")
            return [] # Return empty list for simplicity

    class MockForensicArchiverAgent:
        def __init__(self, bsl_adapter):
            self.bsl_adapter = bsl_adapter
            self.log_buffer = []
            print("MockForensicArchiverAgent initialized for THO test.")
            # Populate with some sample logs for THO to find
            self.log_event("PerimeterDefenseAgent", "suspicious_connection_blocked", {"ip": "1.2.3.4", "port": 4444, "reason": "known_bad_ip"}, "medium")
            self.log_event("EndpointGuardianAgent", "process_anomaly", {"process_name": "suspicious_process.exe", "user": "system", "path": "C:\\Windows\\Temp"}, "high")
            self.log_event("DeceptionCommanderAgent", "honeypot_login_attempt", {"honeypot_id": "ssh_decoy_01", "username": "root", "ip": "10.0.0.5"}, "medium")

        def log_event(self, source_agent_id, event_type, event_details, severity="info"):
            timestamp = time.time()
            log_id = f"mocklog_{event_type}_{str(timestamp)[-5:]}"
            log_entry = {
                "neuron_id": log_id, # Mimicking FAA structure
                "concept_text": json.dumps(event_details),
                "type": "forensic_event_log",
                "attributes": {
                    "log_uuid": log_id,
                    "timestamp": timestamp,
                    "source_agent_id": source_agent_id,
                    "event_type": event_type,
                    "severity": severity,
                    "archival_status": "active"
                }
            }
            self.log_buffer.append(log_entry)
            print(f"MockFAA (THO_Test): Logged by {source_agent_id}: {event_type} - {json.dumps(event_details)} (Severity: {severity})")

    class MockWarRoomAgent:
        def __init__(self):
            print("MockWarRoomAgent initialized for THO test.")
        def receive_alert(self, source_agent_id, alert_type, alert_details, severity):
            print(f"MockWarRoom: Received ALERT from {source_agent_id}! Type: {alert_type}, Severity: {severity}, Details: {json.dumps(alert_details)}")

    mock_bsl = MockBSLAdapter()
    mock_faa = MockForensicArchiverAgent(bsl_adapter=mock_bsl)
    mock_war_room = MockWarRoomAgent()
    
    tho_instance = ThreatHuntingOverseerAgent(
        bsl_adapter=mock_bsl, 
        forensic_archiver=mock_faa, 
        other_agents_refs={"war_room": mock_war_room}
    )

    print("\n--- Testing THO: Initiate Hunt Campaign ---")
    hunt1_id = tho_instance.initiate_hunt_campaign("Suspicious IP Activity", initial_indicators=["1.2.3.4", "suspicious_connection_blocked"])
    print(f"THO Test: Hunt campaign {hunt1_id} initiated. Current state: {tho_instance.active_hunts.get(hunt1_id)}")

    print("\n--- Testing THO: Initiate Another Hunt Campaign ---")
    hunt2_id = tho_instance.initiate_hunt_campaign("Malware Process Hunt", initial_indicators=["suspicious_process.exe"], hunt_rules=["rule_look_for_c2_traffic_after_process_detection_sim"])
    print(f"THO Test: Hunt campaign {hunt2_id} initiated. Current state: {tho_instance.active_hunts.get(hunt2_id)}")

    print("\n--- Testing THO: Review Active Hypotheses (should have some now) ---")
    tho_instance.review_active_hypotheses()

    print("\n--- Testing THO: Run Periodic Tasks (may start new hunts or process existing) ---")
    tho_instance.run_periodic_tasks()
    print(f"THO Test: Active hunts after periodic: {json.dumps(tho_instance.active_hunts, indent=2)}")
    print(f"THO Test: All hypotheses after periodic: {json.dumps(tho_instance.threat_hypotheses, indent=2)}")

    print("\nThreatHuntingOverseerAgent test completed.")

