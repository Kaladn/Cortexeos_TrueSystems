"""
Agent Module: Perimeter Defense Agent (PDA)

Responsible for managing the network perimeter, including firewall management,
threat intelligence updates, and DNS filtering/reputation scoring.

Based on design in: docs/perimeter_defense_agent_design.md
"""

import time
import json # For potential BSL interaction formatting
# Assuming bsl_adapter is imported from the src directory structure
# from ..binary_symbolic_lexicon import BinarySymbolicLexiconAdapter
# from ..deception.honeypot_framework import HoneypotGenerator # For potential coordination

class PerimeterDefenseAgent:
    def __init__(self, bsl_adapter, agent_config=None, deception_commander_ref=None):
        """Initializes the Perimeter Defense Agent.
        
        Args:
            bsl_adapter: Instance of BinarySymbolicLexiconAdapter.
            agent_config (dict, optional): Configuration specific to this agent.
            deception_commander_ref (object, optional): Reference to DeceptionCommanderAgent for coordination.
        """
        self.bsl_adapter = bsl_adapter
        self.config = agent_config if agent_config else {}
        self.deception_commander = deception_commander_ref # To request honeypot deployment
        
        self.firewall_rules = []  # List of rule dicts: {"id", "action", "source_ip", ...}
        self.dns_blacklist = {}   # {domain: {"reputation_score", "last_seen", "source_intel"}}
        self.simulated_traffic_log = []
        
        self._load_initial_state()
        print("PerimeterDefenseAgent initialized.")

    def _load_initial_state(self):
        """Loads initial firewall rules and DNS blacklist from BSL or config (simulated)."""
        # In a real system, this would involve querying BSL or loading from persistent config
        # Example: self.firewall_rules = self.bsl_adapter.get_neuron_data("pda_firewall_ruleset_default") or []
        # Example: self.dns_blacklist = self.bsl_adapter.get_neuron_data("pda_dns_blacklist_default") or {}
        self.firewall_rules.append({
            "id": "default_deny_all", 
            "action": "deny", 
            "source_ip": "any", 
            "dest_ip": "any", 
            "port": "any", 
            "protocol": "any", 
            "description": "Default deny all rule", 
            "priority": 1000, # Lowest priority
            "last_updated": time.time()
        })
        self.dns_blacklist["maliciousdomain.example.com"] = {"reputation_score": 10, "last_seen": time.time(), "source_intel": "manual_entry"}
        print(f"PDA: Initial firewall rules ({len(self.firewall_rules)}) and DNS blacklist ({len(self.dns_blacklist)}) loaded (simulated).")

    def _log_to_bsl(self, event_type, event_data):
        """Simulates logging an event to the BSL (would be via Forensic Archiver Agent)."""
        timestamp = time.time()
        log_entry_id = f"pda_log_{event_type}_{timestamp}"
        bsl_payload = {
            "neuron_id": log_entry_id,
            "concept_text": json.dumps(event_data),
            "type": f"pda_event_log",
            "event_subtype": event_type,
            "timestamp": timestamp,
            "agent_id": "PerimeterDefenseAgent"
        }
        # In a real system: self.forensic_archiver.log_event(bsl_payload)
        # For prototype: self.bsl_adapter.add_neuron(bsl_payload) # (if BSL adapter supports generic add_neuron)
        print(f"BSL_LOG_SIM (PDA): {bsl_payload}")
        # For now, we can also store it locally for inspection if needed
        self.simulated_traffic_log.append(bsl_payload)

    def update_firewall_rule(self, rule_data, action="add_or_update"):
        """Adds, updates, or removes a firewall rule (simulated).
           rule_data must contain an 'id'. If action is 'remove', only 'id' is needed.
        """
        rule_id = rule_data.get("id")
        if not rule_id:
            print("PDA Error: Rule ID is required for update_firewall_rule.")
            return False

        if action == "remove":
            self.firewall_rules = [r for r in self.firewall_rules if r["id"] != rule_id]
            log_event = {"rule_id": rule_id, "change": "removed"}
        elif action == "add_or_update":
            existing_rule_index = next((i for i, r in enumerate(self.firewall_rules) if r["id"] == rule_id), None)
            rule_data["last_updated"] = time.time()
            if existing_rule_index is not None:
                self.firewall_rules[existing_rule_index].update(rule_data)
                log_event = {"rule_id": rule_id, "change": "updated", "data": rule_data}
            else:
                self.firewall_rules.append(rule_data)
                # Sort by priority (lower number = higher priority)
                self.firewall_rules.sort(key=lambda r: r.get("priority", 9999))
                log_event = {"rule_id": rule_id, "change": "added", "data": rule_data}
        else:
            print(f"PDA Error: Invalid action 	'{action}' for firewall rule update.")
            return False
        
        self._log_to_bsl("firewall_rule_change", log_event)
        print(f"PDA: Firewall rule 	'{rule_id}' {log_event['change']}. Total rules: {len(self.firewall_rules)}.")
        return True

    def process_network_traffic(self, source_ip, dest_ip, dest_port, protocol):
        """Simulates processing network traffic against firewall rules.
           Returns 'allowed' or 'denied' and the ID of the matching rule.
        """
        traffic_details = {"source_ip": source_ip, "dest_ip": dest_ip, "dest_port": dest_port, "protocol": protocol}
        print(f"PDA: Processing traffic: {source_ip} -> {dest_ip}:{dest_port} ({protocol})")
        
        for rule in self.firewall_rules:
            # Simplified matching logic for simulation
            match = True
            if rule.get("source_ip") != "any" and rule.get("source_ip") != source_ip:
                match = False
            if rule.get("dest_ip") != "any" and rule.get("dest_ip") != dest_ip:
                match = False
            if rule.get("port") != "any" and rule.get("port") != dest_port:
                match = False
            if rule.get("protocol") != "any" and rule.get("protocol") != protocol:
                match = False
            
            if match:
                result = rule.get("action", "deny") # Default to deny if action not specified
                log_event = {"traffic": traffic_details, "action_taken": result, "matching_rule_id": rule["id"]}
                self._log_to_bsl("traffic_processed", log_event)
                print(f"PDA: Traffic matched rule 	'{rule['id']}'. Action: {result}")
                return result, rule["id"]
        
        # Should not happen if there's a default deny all, but as a fallback:
        log_event = {"traffic": traffic_details, "action_taken": "denied", "matching_rule_id": "implicit_deny"}
        self._log_to_bsl("traffic_processed_implicit_deny", log_event)
        print("PDA: Traffic implicitly denied (no matching rule found before default deny).")
        return "denied", "implicit_deny"

    def fetch_and_apply_threat_intelligence(self):
        """Fetches new threat intel from BSL and updates rules/blacklist (simulated)."""
        print("PDA: Fetching and applying threat intelligence (simulated)...")
        # Example: new_malicious_ips = self.bsl_adapter.get_neuron_data("latest_malicious_ips_feed")
        # if new_malicious_ips and isinstance(new_malicious_ips.get("concept_text"), list):
        #     for ip_info in new_malicious_ips.get("concept_text"):
        #         ip = ip_info.get("ip")
        #         reason = ip_info.get("reason", "BSL Threat Intel")
        #         if ip:
        #             rule_id = f"block_mal_ip_{ip.replace('.', '_')}"
        #             self.update_firewall_rule({
        #                 "id": rule_id, "action": "deny", "source_ip": ip, "dest_ip": "any",
        #                 "port": "any", "protocol": "any", "description": reason, "priority": 10
        #             })
        #             self.dns_blacklist[f"host.{ip}.example.com"] = {"reputation_score": 10, "source_intel": reason} # Add related domain
        self._log_to_bsl("threat_intel_update_cycle", {"status": "completed", "new_rules_simulated": 0})

    def filter_dns_query(self, domain_name):
        """Simulates DNS filtering. Returns IP address or block/redirect status."""
        query_event_data = {"domain_name": domain_name}
        if domain_name in self.dns_blacklist:
            reputation_info = self.dns_blacklist[domain_name]
            print(f"PDA: DNS Query for \t'{domain_name}' is blacklisted (Rep: {reputation_info.get('reputation_score')}). Redirecting/Blocking (simulated).")
            query_event_data["action"] = "blocked_or_redirected"
            query_event_data["reason"] = f"Blacklisted: {reputation_info}"
            self._log_to_bsl("dns_query_filtered", query_event_data)
            # Conceptual: Coordinate with Deception Commander to get a honeypot IP
            # if self.deception_commander:
            #     honeypot_ip = self.deception_commander.request_dynamic_honeypot_for_target(domain_name)
            #     return honeypot_ip or "HONEYPOT_IP_UNAVAILABLE"
            return "REDIRECT_TO_HONEYPOT_SIMULATED"
        
        print(f"PDA: DNS Query for 	'{domain_name}' allowed (simulated).")
        query_event_data["action"] = "allowed"
        self._log_to_bsl("dns_query_processed", query_event_data)
        return f"RESOLVED_IP_FOR_{domain_name.replace('.', '_')}_SIMULATED"

    def request_isp_block(self, target_identifier, reason):
        """Simulates requesting an ISP-level block for an IP or domain."""
        log_entry = {
            "target_identifier": target_identifier,
            "reason": reason,
            "status": "request_sent_simulated"
        }
        self._log_to_bsl("isp_block_request", log_entry)
        print(f"PDA: ISP-level block requested for 	'{target_identifier}' due to: {reason} (simulated and logged).")

    def run_periodic_tasks(self):
        """Method to be called periodically to perform routine checks/updates."""
        print("PDA: Running periodic tasks...")
        self.fetch_and_apply_threat_intelligence()
        self._log_to_bsl("periodic_task_execution", {"status": "completed"})
        print("PDA: Periodic tasks executed.")

# Example Usage (for testing the agent directly)
if __name__ == "__main__":
    # Mock BSL Adapter for standalone testing
    class MockBSLAdapter:
        def __init__(self):
            print("MockBSLAdapter initialized for PDA test.")
        def add_neuron(self, neuron_data):
            print(f"MockBSL (PDA): Add Neuron called with {neuron_data['type']}: {neuron_data['neuron_id']}")
        def get_neuron_data(self, neuron_id):
            print(f"MockBSL (PDA): Get Neuron Data for {neuron_id}")
            if neuron_id == "pda_firewall_ruleset_default": return [] # Simulate empty initial rules
            if neuron_id == "pda_dns_blacklist_default": return {} # Simulate empty initial blacklist
            return None
        def update_neuron_field(self, neuron_id, field, value):
            print(f"MockBSL (PDA): Update Neuron {neuron_id}, field {field} to {value}")

    mock_bsl = MockBSLAdapter()
    pda = PerimeterDefenseAgent(bsl_adapter=mock_bsl)

    # Test firewall rule update
    pda.update_firewall_rule({
        "id": "allow_web_traffic", "action": "allow", "source_ip": "any", "dest_ip": "192.168.1.10",
        "port": 80, "protocol": "tcp", "description": "Allow HTTP to webserver", "priority": 100
    })
    pda.update_firewall_rule({
        "id": "allow_dns_out", "action": "allow", "source_ip": "any", "dest_ip": "any",
        "port": 53, "protocol": "udp", "description": "Allow DNS outbound", "priority": 90
    })

    # Test traffic processing
    pda.process_network_traffic("10.0.0.5", "192.168.1.10", 80, "tcp") # Should be allowed
    pda.process_network_traffic("10.0.0.5", "192.168.1.10", 22, "tcp") # Should be denied by default
    pda.process_network_traffic("10.0.0.5", "8.8.8.8", 53, "udp") # Should be allowed

    # Test DNS filtering
    pda.filter_dns_query("google.com")
    pda.filter_dns_query("maliciousdomain.example.com")

    # Test threat intel update (simulated)
    pda.fetch_and_apply_threat_intelligence()

    # Test ISP block request
    pda.request_isp_block("1.2.3.4", "Confirmed C2 Server")

    # Test periodic tasks
    pda.run_periodic_tasks()

    print("PerimeterDefenseAgent test completed.")


