"""
Agent Module: Deception Commander Agent (DCA)

Orchestrates AI Deception Modules, including dynamic honeypot management,
deception strategy execution, and attacker sandboxing (simulated).

Based on design in: docs/deception_commander_agent_design.md
"""

import time
import json

# Assuming HoneypotGenerator is in src.deception.honeypot_framework
# from ..deception.honeypot_framework import HoneypotGenerator
# from ..binary_symbolic_lexicon import BinarySymbolicLexiconAdapter

class DeceptionCommanderAgent:
    def __init__(self, bsl_adapter, honeypot_generator, agent_config=None):
        self.bsl_adapter = bsl_adapter
        self.honeypot_generator = honeypot_generator # Instance of HoneypotGenerator
        self.config = agent_config if agent_config else {}
        self.active_deception_strategies = {}
        self.active_honeypots = {} # {honeypot_id: {template_name, deployment_details, status}}
        self.event_log = [] # Local log for simulation
        self._load_initial_strategies()
        print("DeceptionCommanderAgent initialized.")

    def _load_initial_strategies(self):
        """Loads initial deception strategies from BSL or config (simulated)."""
        # Example: strat = self.bsl_adapter.get_neuron_data("dca_strategy_default_lure")
        # self.active_deception_strategies[strat["id"]] = strat
        default_strategy = {
            "id": "default_passive_lure", 
            "description": "Generic passive data exposure honeypots",
            "triggers": ["unsolicited_network_scan", "suspicious_dns_query"],
            "honeypot_templates": ["ssh_decoy", "wav_lure"], # from earlier templates
            "rotation_interval_hours": 24
        }
        self.active_deception_strategies[default_strategy["id"]] = default_strategy
        financial_lure_strategy = {
            "id": "financial_attacker_lure_01",
            "description": "Lure attackers interested in financial data with WAV decoys and fake DBs.",
            "triggers": ["access_to_financial_decoy_share", "query_for_financial_keywords_in_honeypot_logs"],
            "honeypot_templates": ["wav_lure", "ssh_decoy"], # ssh_decoy could be configured as a fake DB server
            "escalation_policy": "log_and_monitor_medium_then_sandbox_high_confidence"
        }
        self.active_deception_strategies[financial_lure_strategy["id"]] = financial_lure_strategy
        print(f"DCA: Initial deception strategies loaded (simulated): {len(self.active_deception_strategies)} strategies.")

    def _log_to_bsl_simulation(self, event_type, event_data):
        """Simulates logging an event to the BSL (would be via Forensic Archiver Agent)."""
        timestamp = time.time()
        log_entry_id = f"dca_log_{event_type}_{timestamp}"
        bsl_payload = {
            "neuron_id": log_entry_id,
            "concept_text": json.dumps(event_data),
            "type": f"dca_event_log",
            "event_subtype": event_type,
            "timestamp": timestamp,
            "agent_id": "DeceptionCommanderAgent"
        }
        print(f"BSL_LOG_SIM (DCA): Type: {event_type}, Data: {event_data}")
        self.event_log.append(bsl_payload)

    def request_honeypot_deployment(self, template_name, reason="generic_request", custom_config=None, target_info=None):
        """Requests the HoneypotGenerator to create and deploy a honeypot."""
        print(f"DCA: Received request to deploy honeypot 	'{template_name}' for reason: {reason}")
        honeypot_id = self.honeypot_generator.create_honeypot(template_name, custom_config)
        if honeypot_id:
            deployment_details = {"network_segment": "sim_segment_A", "ip_address": f"192.168.100.{len(self.active_honeypots)+10}"}
            if self.honeypot_generator.deploy_honeypot(honeypot_id, deployment_details):
                self.active_honeypots[honeypot_id] = {
                    "template_name": template_name,
                    "deployment_details": deployment_details,
                    "status": "active",
                    "reason": reason,
                    "target_info": target_info,
                    "creation_time": time.time()
                }
                self._log_to_bsl_simulation("honeypot_deployed", {"honeypot_id": honeypot_id, "template": template_name, "details": deployment_details, "reason": reason})
                print(f"DCA: Honeypot {honeypot_id} ('{template_name}') deployed successfully at {deployment_details['ip_address']}.")
                return honeypot_id
            else:
                print(f"DCA: Failed to deploy honeypot {honeypot_id}.")
                self._log_to_bsl_simulation("honeypot_deployment_failed", {"honeypot_id": honeypot_id, "template": template_name})
        else:
            print(f"DCA: Failed to create honeypot from template '{template_name}'.")
            self._log_to_bsl_simulation("honeypot_creation_failed", {"template": template_name})
        return None

    def handle_threat_trigger(self, trigger_type, trigger_data):
        """Handles a threat trigger by selecting and executing a deception strategy."""
        print(f"DCA: Received threat trigger: '{trigger_type}' with data: {trigger_data}")
        self._log_to_bsl_simulation("threat_trigger_received", {"trigger_type": trigger_type, "data": trigger_data})
        activated_strategy = False
        for strat_id, strategy in self.active_deception_strategies.items():
            if trigger_type in strategy.get("triggers", []):
                print(f"DCA: Activating strategy 	'{strat_id}' for trigger 	'{trigger_type}'.")
                for template_name in strategy.get("honeypot_templates", []):
                    self.request_honeypot_deployment(template_name, reason=f"Strategy '{strat_id}' activation", target_info=trigger_data)
                activated_strategy = True
                # In a real system, might only activate one strategy or have priorities
                break 
        
        if not activated_strategy:
            print(f"DCA: No specific strategy found for trigger 	'{trigger_type}'. Deploying default SSH decoy.")
            self.request_honeypot_deployment("ssh_decoy", reason=f"Default response to '{trigger_type}'", target_info=trigger_data)
        return activated_strategy

    def process_honeypot_interaction(self, honeypot_id, interaction_data):
        """Processes interaction data from a honeypot, typically called by the HoneypotInstance or HoneypotGenerator."""
        if honeypot_id not in self.active_honeypots:
            print(f"DCA Error: Received interaction for unknown or inactive honeypot {honeypot_id}.")
            return
        
        print(f"DCA: Processing interaction for honeypot {honeypot_id}: {interaction_data}")
        enriched_data = {
            "honeypot_id": honeypot_id,
            "template_name": self.active_honeypots[honeypot_id]["template_name"],
            "interaction": interaction_data,
            "timestamp": time.time(), # DCA timestamp of processing
            "original_timestamp": interaction_data.get("timestamp", time.time()) # from honeypot
        }
        self._log_to_bsl_simulation("honeypot_interaction_processed", enriched_data)

        # Conceptual: Trigger sandboxing for high-confidence attacker
        # This confidence score would ideally come from the BSL or a dedicated analysis module
        attacker_ip = interaction_data.get("source_ip", "unknown_ip")
        if interaction_data.get("severity", "low") == "high" or interaction_data.get("is_confirmed_attacker", False):
            self.trigger_simulated_sandboxing(attacker_ip, honeypot_id, interaction_data)

    def trigger_simulated_sandboxing(self, attacker_ip, honeypot_id, interaction_details):
        """Simulates triggering automated attacker sandboxing."""
        print(f"DCA: High-confidence attacker ({attacker_ip}) detected in honeypot {honeypot_id}. SIMULATING SANDBOXING INITIATION.")
        sandbox_event = {
            "attacker_ip": attacker_ip,
            "honeypot_id": honeypot_id,
            "interaction_summary": interaction_details,
            "action": "sandboxing_initiated_simulated",
            "sandbox_id_simulated": f"sandbox_{attacker_ip.replace('.', '_')}_{time.time()}"
        }
        self._log_to_bsl_simulation("attacker_sandboxing_simulated", sandbox_event)
        # In a real system, this would involve complex orchestration with other security tools.

    def run_periodic_tasks(self):
        """Periodically rotate honeypots based on strategy, check health, etc."""
        print("DCA: Running periodic tasks...")
        # This calls the method on the HoneypotGenerator instance
        rotated_count = self.honeypot_generator.rotate_all_active_honeypots()
        self._log_to_bsl_simulation("periodic_rotation_cycle", {"status": "completed", "rotated_count": rotated_count})
        print(f"DCA: Periodic tasks (rotation) executed. {rotated_count} honeypots were rotated by the generator.")

# Example Usage (for testing the agent directly)
if __name__ == "__main__":
    # Mock BSL Adapter for standalone testing
    class MockBSLAdapter:
        def __init__(self):
            print("MockBSLAdapter initialized for DCA test.")
        def add_neuron(self, neuron_data):
            print(f"MockBSL (DCA): Add Neuron called with Type: {neuron_data.get('type')}, ID: {neuron_data.get('neuron_id')}")
        def get_neuron_data(self, neuron_id):
            print(f"MockBSL (DCA): Get Neuron Data for {neuron_id}")
            return None # Simulate no data found for simplicity

    # Mock HoneypotGenerator from the AI Deception Modules
    # This needs to align with the actual HoneypotGenerator's interface
    class MockHoneypotGenerator:
        def __init__(self, bsl_adapter):
            self.bsl_adapter = bsl_adapter
            self.active_honeypots = {}
            self.template_path = "../../prototypes/honeypot_templates" # Relative to this file if run directly
            self.next_honeypot_numeric_id = 1
            print("MockHoneypotGenerator initialized for DCA test.")

        def create_honeypot(self, template_name, custom_config=None):
            honeypot_id = f"mock_hp_{template_name}_{self.next_honeypot_numeric_id}"
            self.next_honeypot_numeric_id += 1
            self.active_honeypots[honeypot_id] = {
                "template_name": template_name,
                "config": custom_config or {},
                "status": "created",
                "interaction_log": []
            }
            print(f"MockHG: Created honeypot {honeypot_id} from template {template_name}")
            return honeypot_id

        def deploy_honeypot(self, honeypot_id, deployment_details):
            if honeypot_id in self.active_honeypots:
                self.active_honeypots[honeypot_id]["status"] = "deployed"
                self.active_honeypots[honeypot_id]["deployment"] = deployment_details
                print(f"MockHG: Deployed honeypot {honeypot_id} to {deployment_details}")
                return True
            return False

        def log_interaction(self, honeypot_id, interaction_data):
            if honeypot_id in self.active_honeypots:
                self.active_honeypots[honeypot_id]["interaction_log"].append(interaction_data)
                # In a real scenario, this might also directly notify DCA or another observer
                print(f"MockHG: Logged interaction for {honeypot_id}: {interaction_data}")
                # Simulate DCA being notified by the honeypot itself or the generator
                if dca_instance: # Global reference for test
                    dca_instance.process_honeypot_interaction(honeypot_id, interaction_data)
                return True
            return False

        def rotate_all_active_honeypots(self):
            print(f"MockHG: Rotating all active honeypots (simulated). Count: {len(self.active_honeypots)}")
            # Simplified: just log, doesn't actually recreate/redeploy in this mock
            # A real one would undeploy old, deploy new based on strategies
            return len(self.active_honeypots) 

    mock_bsl = MockBSLAdapter()
    mock_hg = MockHoneypotGenerator(bsl_adapter=mock_bsl)
    
    dca_instance = DeceptionCommanderAgent(bsl_adapter=mock_bsl, honeypot_generator=mock_hg)

    print("\n--- Testing Honeypot Deployment Request ---")
    dca_instance.request_honeypot_deployment("ssh_decoy", reason="Test deployment")
    dca_instance.request_honeypot_deployment("wav_lure", reason="Another test")

    print("\n--- Testing Threat Trigger Handling ---")
    dca_instance.handle_threat_trigger("unsolicited_network_scan", {"source_ip": "1.2.3.4", "target_port": 22})
    dca_instance.handle_threat_trigger("access_to_financial_decoy_share", {"source_ip": "10.10.10.5", "share_name": "finance_docs"})
    dca_instance.handle_threat_trigger("unknown_threat_type", {"details": "some data"})

    print("\n--- Testing Honeypot Interaction Processing (simulated via MockHG) ---")
    # Simulate an interaction being logged by a honeypot, which then calls DCA's process_honeypot_interaction
    # We need an active honeypot ID from previous deployments
    active_hp_ids = list(dca_instance.active_honeypots.keys())
    if active_hp_ids:
        first_honeypot_id = active_hp_ids[0]
        mock_hg.log_interaction(first_honeypot_id, {"source_ip": "5.6.7.8", "action": "login_attempt", "username": "root", "password": "password123", "severity": "medium"})
        mock_hg.log_interaction(first_honeypot_id, {"source_ip": "9.9.9.9", "action": "payload_dropped", "filename": "evil.exe", "severity": "high", "is_confirmed_attacker": True})
    else:
        print("DCA Test: No active honeypots to simulate interaction with.")

    print("\n--- Testing Periodic Tasks (Rotation) ---")
    dca_instance.run_periodic_tasks()

    print("\nDeceptionCommanderAgent test completed.")

