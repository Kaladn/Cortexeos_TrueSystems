"""
AI Deception Modules: Honeypot Generation Framework

This module contains the HoneypotGenerator and HoneypotInstance classes
for creating, deploying, and managing simulated honeypots as part of the
Cortex Quantum Dominion Security Doctrine prototype.

Based on design in: docs/honeypot_framework_design.md
"""

import json
import os
import uuid
import time
# Assuming bsl_adapter is imported from the src directory structure
# from ..binary_symbolic_lexicon import BinarySymbolicLexiconAdapter

# Placeholder for actual BSL Adapter import if it's in a different relative path or installed module
# For now, we'll assume it's passed during instantiation.

SIMULATED_HONEYPOT_ACTIVE_DIR = "/home/ubuntu/cortex_quantum_project/prototypes/active_honeypots"
DEFAULT_TEMPLATE_DIR = "/home/ubuntu/cortex_quantum_project/prototypes/honeypot_templates"

class HoneypotInstance:
    def __init__(self, honeypot_id, template_name, template_config, deployed_config, base_log_path):
        self.id = honeypot_id
        self.template_name = template_name
        self.template_config = template_config # Original template
        self.deployed_config = deployed_config # Actual running config, potentially with dynamic elements
        self.status = "pending_deployment" # States: pending_deployment, active, compromised, inactive, error
        self.interaction_log_file = os.path.join(base_log_path, f"{self.id}_interaction.log")
        self.creation_time = time.time()
        self.last_interaction_time = None
        self.simulated_process = None # Placeholder for a simulated process/thread

        os.makedirs(base_log_path, exist_ok=True)
        with open(self.interaction_log_file, "w") as f:
            f.write(f"Honeypot Instance {self.id} ({self.template_name}) created at {self.creation_time}\n")

    def start_simulation(self, generator_ref):
        """Starts the simulated honeypot behavior."""
        # This would be specific to the honeypot type
        # e.g., for a fake SSH, it might open a socket and listen
        # For a fake file, it might monitor a path
        self.status = "active"
        print(f"Honeypot {self.id} ({self.template_name}) simulation started.")
        self.record_interaction(f"Honeypot {self.id} deployed and active.", "SYSTEM_EVENT", generator_ref)
        # Example: if type is 'ssh_service', start a mock SSH listener thread
        # For now, just log activation

    def stop_simulation(self, generator_ref):
        """Stops the simulated honeypot behavior."""
        self.status = "inactive"
        print(f"Honeypot {self.id} ({self.template_name}) simulation stopped.")
        self.record_interaction(f"Honeypot {self.id} stopped/teared down.", "SYSTEM_EVENT", generator_ref)
        # Example: stop mock SSH listener thread

    def record_interaction(self, event_details, event_type="ATTACKER_INTERACTION", generator_ref=None):
        """Records an interaction event and logs it.
           `generator_ref` is the HoneypotGenerator instance to call log_interaction.
        """
        timestamp = time.time()
        log_entry = f"{timestamp} [{event_type}]: {event_details}\n"
        with open(self.interaction_log_file, "a") as f:
            f.write(log_entry)
        self.last_interaction_time = timestamp
        print(f"Interaction recorded for Honeypot {self.id}: {event_details}")
        
        if generator_ref and event_type != "SYSTEM_EVENT": # Avoid logging system events back to BSL via this path for now
            # Prepare data for BSL logging via the generator
            bsl_log_data = {
                "honeypot_id": self.id,
                "template_name": self.template_name,
                "timestamp": timestamp,
                "event_type": event_type,
                "details": event_details,
                "attacker_ip": "SIMULATED_IP_127.0.0.1", # Placeholder
                "deployed_config": self.deployed_config
            }
            generator_ref.log_interaction_to_bsl(self.id, bsl_log_data)

class HoneypotGenerator:
    def __init__(self, bsl_adapter, deception_commander_config=None, template_dir=DEFAULT_TEMPLATE_DIR):
        self.bsl_adapter = bsl_adapter
        self.config = deception_commander_config if deception_commander_config else {}
        self.active_honeypots = {}  # {honeypot_id: HoneypotInstance}
        self.template_dir = template_dir
        self.honeypot_templates = self._load_templates()
        self.log_path_base = os.path.join(SIMULATED_HONEYPOT_ACTIVE_DIR, "logs")
        os.makedirs(self.log_path_base, exist_ok=True)
        print(f"HoneypotGenerator initialized. Loaded {len(self.honeypot_templates)} templates.")

    def _load_templates(self):
        """Loads honeypot templates from configuration files (JSON/YAML)."""
        templates = {}
        if not os.path.exists(self.template_dir):
            print(f"Warning: Template directory {self.template_dir} not found.")
            return templates
        for filename in os.listdir(self.template_dir):
            if filename.endswith(".json") or filename.endswith(".yaml") or filename.endswith(".yml"):
                filepath = os.path.join(self.template_dir, filename)
                try:
                    with open(filepath, "r") as f:
                        # Basic loader, can be expanded for YAML
                        if filename.endswith(".json"):
                            template_data = json.load(f)
                        else: # basic YAML or treat as JSON for now
                            # For full YAML, would need PyYAML
                            print(f"Note: Assuming {filename} is JSON-compatible for prototype.")
                            template_data = json.load(f) 
                        template_name = template_data.get("template_name", os.path.splitext(filename)[0])
                        templates[template_name] = template_data
                        print(f"Loaded template: {template_name}")
                except Exception as e:
                    print(f"Error loading template {filename}: {e}")
        return templates

    def create_honeypot_instance(self, template_name, custom_params=None):
        """Creates a honeypot instance from a template.
           Returns a HoneypotInstance object (not yet deployed).
        """
        if template_name not in self.honeypot_templates:
            print(f"Error: Template 	'{template_name}' not found.")
            return None

        template_config = self.honeypot_templates[template_name]
        deployed_config = template_config.get("default_config", {}).copy()
        if custom_params:
            deployed_config.update(custom_params)
        
        # Adapt configuration using BSL intelligence (conceptual)
        # attacker_profile = self.bsl_adapter.get_neuron_data("attacker_profile_X") # Example
        # if attacker_profile: deployed_config["banner"] = f"Welcome {attacker_profile.get("username_preference")}"

        honeypot_id = str(uuid.uuid4())
        instance = HoneypotInstance(honeypot_id, template_name, template_config, deployed_config, self.log_path_base)
        print(f"Created HoneypotInstance {honeypot_id} from template {template_name}.")
        return instance

    def deploy_honeypot(self, honeypot_instance):
        """Deploys a created honeypot instance (simulated).
           Assigns a unique ID, starts simulated services/monitoring.
        """
        if not honeypot_instance or not isinstance(honeypot_instance, HoneypotInstance):
            print("Error: Invalid honeypot instance provided for deployment.")
            return False

        if honeypot_instance.id in self.active_honeypots:
            print(f"Error: Honeypot {honeypot_instance.id} is already active or ID collision.")
            return False

        self.active_honeypots[honeypot_instance.id] = honeypot_instance
        honeypot_instance.start_simulation(self) # Pass self for callback logging
        print(f"Honeypot {honeypot_instance.id} deployed. Total active: {len(self.active_honeypots)}")
        # Store metadata about the active honeypot in BSL (conceptual)
        # self.bsl_adapter.add_neuron({
        #     "neuron_id": f"honeypot_meta_{honeypot_instance.id}", 
        #     "concept_text": json.dumps(honeypot_instance.deployed_config),
        #     "type": "honeypot_metadata",
        #     "status": "active"
        # })
        return True

    def teardown_honeypot(self, honeypot_id):
        """Tears down an active honeypot instance (simulated)."""
        if honeypot_id not in self.active_honeypots:
            print(f"Error: Honeypot {honeypot_id} not found for teardown.")
            return False
        
        instance = self.active_honeypots.pop(honeypot_id)
        instance.stop_simulation(self)
        print(f"Honeypot {honeypot_id} torn down. Total active: {len(self.active_honeypots)}")
        # Update BSL metadata (conceptual)
        # self.bsl_adapter.update_neuron_field(f"honeypot_meta_{honeypot_id}", "status", "inactive")
        return True

    def rotate_honeypot(self, honeypot_id_to_rotate, new_template_name=None, new_params=None):
        """Rotates an existing honeypot."""
        print(f"Rotating honeypot {honeypot_id_to_rotate}...")
        current_instance = self.active_honeypots.get(honeypot_id_to_rotate)
        if not current_instance:
            print(f"Error: Cannot rotate honeypot {honeypot_id_to_rotate}, it is not active.")
            return False

        # Determine new template and params
        if not new_template_name:
            # Simple rotation: use the same template or pick another one randomly/strategically
            new_template_name = current_instance.template_name 
            # Potentially vary parameters slightly, e.g., change a port or banner
            if new_params is None and "default_config" in current_instance.template_config:
                new_params = current_instance.template_config["default_config"].copy()
                if "port" in new_params and isinstance(new_params["port"], int):
                    new_params["port"] += 1 # Simple variation for simulation
        
        self.teardown_honeypot(honeypot_id_to_rotate)
        
        new_instance = self.create_honeypot_instance(new_template_name, new_params)
        if new_instance:
            self.deploy_honeypot(new_instance)
            print(f"Honeypot {honeypot_id_to_rotate} rotated to new instance {new_instance.id} ({new_template_name}).")
            return new_instance.id
        else:
            print(f"Error: Failed to create new instance for rotating honeypot {honeypot_id_to_rotate}.")
            # Potentially try to redeploy the old one or an emergency default
            return False

    def log_interaction_to_bsl(self, honeypot_id, interaction_data):
        """Logs an interaction to be sent to BSL (via Forensic Archiver in a full system).
           For prototype, we can directly use bsl_adapter or queue it.
        """
        print(f"BSL LOG (Honeypot: {honeypot_id}): {interaction_data}")
        # This is where the Forensic Archiver Agent would typically take over.
        # For direct BSL interaction in prototype:
        timestamp_for_log = interaction_data.get("timestamp", time.time())
        log_neuron_id = f"honeypot_log_{honeypot_id}_{timestamp_for_log}"
        log_concept_text = json.dumps(interaction_data)
        # self.bsl_adapter.add_neuron({
        #     "neuron_id": log_neuron_id,
        #     "concept_text": log_concept_text,
        #     "type": "honeypot_interaction_log",
        #     "source_honeypot_id": honeypot_id,
        #     "creation_timestamp": interaction_data.get("timestamp", time.time())
        # })
        # Note: The BSL adapter's add_neuron expects specific fields as per its current simulation.
        # We might need a more generic logging structure or adapt the BSL add_neuron for logs.

    def get_active_honeypot_details(self, honeypot_id):
        instance = self.active_honeypots.get(honeypot_id)
        if instance:
            return {
                "id": instance.id,
                "template_name": instance.template_name,
                "status": instance.status,
                "deployed_config": instance.deployed_config,
                "creation_time": instance.creation_time,
                "last_interaction_time": instance.last_interaction_time
            }
        return None

# Example Usage (for testing the framework directly)
if __name__ == "__main__":
    # Mock BSL Adapter for standalone testing
    class MockBSLAdapter:
        def __init__(self):
            print("MockBSLAdapter initialized.")
        def add_neuron(self, neuron_data):
            print(f"MockBSL: Add Neuron called with {neuron_data}")
        def get_neuron_data(self, neuron_id):
            print(f"MockBSL: Get Neuron Data for {neuron_id}")
            return None # Or mock data

    # Create dummy template files for testing _load_templates
    os.makedirs(DEFAULT_TEMPLATE_DIR, exist_ok=True)
    dummy_ssh_template = {
        "template_name": "ssh_decoy_basic",
        "honeypot_type": "ssh_service",
        "default_config": {
            "port": 2222,
            "banner": "SSH-2.0-OpenSSH_7.4p1 Debian-10+deb9u7",
            "log_level": "info"
        },
        "interaction_triggers": [{"event": "connection_attempt", "action": "log_high"}]
    }
    with open(os.path.join(DEFAULT_TEMPLATE_DIR, "ssh_decoy.json"), "w") as f:
        json.dump(dummy_ssh_template, f, indent=4)

    dummy_wav_template = {
        "template_name": "wav_trigger_lure1",
        "honeypot_type": "wav_trigger",
        "default_config": {
            "filename": "confidential_meeting_audio.wav",
            "trigger_on_access": True
        }
    }
    with open(os.path.join(DEFAULT_TEMPLATE_DIR, "wav_lure.json"), "w") as f:
        json.dump(dummy_wav_template, f, indent=4)

    mock_bsl = MockBSLAdapter()
    generator = HoneypotGenerator(bsl_adapter=mock_bsl)

    # Test create and deploy
    ssh_instance = generator.create_honeypot_instance("ssh_decoy_basic", {"port": 2223})
    if ssh_instance:
        generator.deploy_honeypot(ssh_instance)
        ssh_instance_id = ssh_instance.id
        print(f"Deployed SSH honeypot details: {generator.get_active_honeypot_details(ssh_instance_id)}")
        # Simulate an interaction
        ssh_instance.record_interaction("Connection attempt from 192.168.1.100", generator_ref=generator)

    wav_instance = generator.create_honeypot_instance("wav_trigger_lure1")
    if wav_instance:
        generator.deploy_honeypot(wav_instance)
        wav_instance_id = wav_instance.id
        # Simulate access
        wav_instance.record_interaction(f"Metadata access for {wav_instance.deployed_config['filename']}", generator_ref=generator)

    # Test rotation
    if ssh_instance and ssh_instance.id in generator.active_honeypots:
        print("Attempting to rotate SSH honeypot...")
        new_ssh_id = generator.rotate_honeypot(ssh_instance.id, new_template_name="ssh_decoy_basic", new_params={"port": 2224, "banner": "New Banner!"})
        if new_ssh_id:
            print(f"Rotated to new SSH honeypot ID: {new_ssh_id}")
            rotated_details = generator.get_active_honeypot_details(new_ssh_id)
            if rotated_details: print(f"New SSH honeypot details: {rotated_details['deployed_config']}")

    # Test teardown
    if wav_instance and wav_instance.id in generator.active_honeypots:
        generator.teardown_honeypot(wav_instance.id)

    if new_ssh_id and new_ssh_id in generator.active_honeypots:
         generator.teardown_honeypot(new_ssh_id)

    print("HoneypotGenerator test completed.")


