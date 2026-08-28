"""
Agent Module: Financial Decoy Agent (FDA)

Generates and manages decoy financial data, including bait WAV files with
encoded information, mirrored financial records, and honey-ledgers.

Based on design in: docs/financial_decoy_agent_design.md
"""

import time
import json
import hashlib
import random
import os
import wave # For generating placeholder WAV files
import struct # For WAV data
import uuid # For unique IDs
import math # For sine wave in WAV

# from ..binary_symbolic_lexicon import BinarySymbolicLexiconAdapter
# from .forensic_archiver_agent import ForensicArchiverAgent
# from .deception_commander_agent import DeceptionCommanderAgent # For coordination

class FinancialDecoyAgent:
    def __init__(self, bsl_adapter, forensic_archiver, dca_ref=None, agent_config=None):
        self.bsl_adapter = bsl_adapter
        self.forensic_archiver = forensic_archiver
        self.dca_ref = dca_ref # Reference to Deception Commander Agent
        self.config = agent_config if agent_config else {}
        self.base_decoy_path = "/home/ubuntu/cortex_quantum_project/prototypes/financial_decoys"
        os.makedirs(os.path.join(self.base_decoy_path, "wav_bait"), exist_ok=True)
        os.makedirs(os.path.join(self.base_decoy_path, "honey_ledgers"), exist_ok=True)
        print("FinancialDecoyAgent initialized.")

    def _log_fda_event(self, event_type, event_details, severity="info"):
        if self.forensic_archiver:
            self.forensic_archiver.log_event("FinancialDecoyAgent", event_type, event_details, severity)
        else:
            print(f"FDA_LOG (no archiver): Agent: FinancialDecoyAgent, Type: {event_type}, Severity: {severity}, Details: {json.dumps(event_details)}")

    def generate_bait_wav(self, decoy_name, bait_info_dict):
        """Generates a placeholder WAV file and logs its associated bait info."""
        safe_decoy_name = decoy_name.replace(' ', '_').lower()
        filename = f"{safe_decoy_name}_{int(time.time())}.wav"
        filepath = os.path.join(self.base_decoy_path, "wav_bait", filename)

        sample_rate = 44100
        duration_seconds = 1 
        frequency = 440 
        num_samples = int(sample_rate * duration_seconds)
        max_amplitude = 32767 // 2 

        try:
            with wave.open(filepath, "wb") as wf:
                wf.setnchannels(1) 
                wf.setsampwidth(2) 
                wf.setframerate(sample_rate)
                for i in range(num_samples):
                    value = int(max_amplitude * math.sin(2 * math.pi * frequency * i / sample_rate)) # A simple tone
                    # value = 0 # Or just silence
                    data = struct.pack("<h", value)
                    wf.writeframesraw(data)
            self._log_fda_event("bait_wav_generated", {"filename": filename, "filepath": filepath, "bait_info": bait_info_dict})
            print(f"FDA: Generated bait WAV file: {filepath} with bait: {bait_info_dict}")
            return filepath
        except Exception as e:
            self._log_fda_event("bait_wav_generation_failed", {"decoy_name": decoy_name, "error": str(e)}, "error")
            print(f"FDA Error: Failed to generate WAV {decoy_name}: {e}")
            return None

    def generate_honey_ledger(self, ledger_name, num_transactions=50):
        """Generates a fake financial ledger (JSON)."""
        safe_ledger_name = ledger_name.replace(' ', '_').lower()
        filename = f"{safe_ledger_name}_{int(time.time())}.json"
        filepath = os.path.join(self.base_decoy_path, "honey_ledgers", filename)
        ledger_data = []
        start_date_offset = random.randint(30, 365) # Start transactions from 30 to 365 days ago
        current_timestamp = time.time()

        for i in range(num_transactions):
            # Transactions spread out over the period leading up to today
            tx_timestamp = current_timestamp - ((start_date_offset - (i * (start_date_offset / num_transactions))) * 24 * 60 * 60) 
            tx_date = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(tx_timestamp))
            descriptions = ["Online Purchase", "Service Subscription", "Funds Transfer", "ATM Withdrawal", "Point of Sale Payment", "Consulting Fee", "Software License"]
            tx_amount = round(random.uniform(-5000, 5000) if random.random() > 0.1 else random.uniform(-50000, 50000), 2) # Occasional large transactions
            fake_account_id = f"ACC{random.randint(100000, 999999)}DEC"
            ledger_data.append({
                "transaction_id": f"TXN{uuid.uuid4().hex[:12].upper()}",
                "date": tx_date,
                "description": random.choice(descriptions),
                "amount": tx_amount,
                "currency": "USD",
                "beneficiary_account_sim": f"BEN{random.randint(1000,9999)}SIM{random.choice(['A', 'B', 'C'])}",
                "source_account_sim": fake_account_id
            })
        try:
            with open(filepath, "w") as f:
                json.dump(ledger_data, f, indent=2)
            self._log_fda_event("honey_ledger_generated", {"filename": filename, "filepath": filepath, "num_transactions": num_transactions})
            print(f"FDA: Generated honey ledger: {filepath} with {num_transactions} transactions.")
            return filepath
        except Exception as e:
            self._log_fda_event("honey_ledger_generation_failed", {"ledger_name": ledger_name, "error": str(e)}, "error")
            print(f"FDA Error: Failed to generate ledger {ledger_name}: {e}")
            return None

    def process_decoy_interaction(self, decoy_id, attacker_info, interaction_details):
        """Processes a report of interaction with a financial decoy."""
        timestamp = time.time()
        log_details = {
            "decoy_id": decoy_id,
            "attacker_info": attacker_info,
            "interaction_details": interaction_details,
            "timestamp": timestamp
        }
        self._log_fda_event("financial_decoy_interaction", log_details, "warning")
        print(f"FDA: Processing interaction with decoy \t'{decoy_id}\' by attacker \t'{attacker_info.get('ip')}\'.")
        harvested_intel_neuron_id = f"fai_{attacker_info.get(	unknownip	).replace(	.	, 	_	)}_{int(timestamp)}"
        harvested_intel = {
            "type": "harvested_financial_attacker_intel",
            "neuron_id": harvested_intel_neuron_id,
            "concept_text": json.dumps({"summary": "Attacker interacted with financial decoy", **log_details}),
            "attributes": {
                "attacker_ip": attacker_info.get("ip"),
                "decoy_id": decoy_id,
                "interaction_type": interaction_details.get("action"),
                "timestamp": timestamp
            }
        }
        # Simulate BSL logging for harvested intel
        if self.bsl_adapter and hasattr(self.bsl_adapter, "add_neuron"):
             self.bsl_adapter.add_neuron(harvested_intel)
        else:
            print(f"FDA (sim_bsl): Add Neuron for harvested intel: {harvested_intel_neuron_id}")
        
        print(f"FDA: Logged harvested intelligence to BSL (simulated): {harvested_intel_neuron_id}")
        return harvested_intel

    def run_periodic_tasks(self):
        """Generates new decoy content periodically or checks status."""
        print("FDA: Running periodic tasks...")
        if random.random() < 0.3: 
            self.generate_bait_wav(f"periodic_wav_{random.randint(100,999)}", {"tracker_id": f"PWAV{random.randint(1000,9999)}", "decoy_type": "periodic_audio_lure"})
        if random.random() < 0.2: 
            self.generate_honey_ledger(f"periodic_ledger_{random.randint(100,999)}", num_transactions=random.randint(20,60))
        self._log_fda_event("periodic_task_cycle_complete", {"new_bait_generated_chance": 0.3, "new_ledger_generated_chance": 0.2})
        print("FDA: Periodic tasks executed.")

# Example Usage (for testing the agent directly)
if __name__ == "__main__":
    class MockBSLAdapter:
        def __init__(self):
            print("MockBSLAdapter initialized for FDA test.")
        def add_neuron(self, neuron_data):
            print(f"MockBSL (FDA_Test): Add Neuron: Type: {neuron_data.get(	"type"	)}, ID: {neuron_data.get(	"neuron_id"	)}")

    class MockForensicArchiverAgent:
        def __init__(self, bsl_adapter):
            self.bsl_adapter = bsl_adapter
            print("MockForensicArchiverAgent initialized for FDA test.")
        def log_event(self, source_agent_id, event_type, event_details, severity="info"):
            print(f"MockFAA (FDA_Test): Logged by {source_agent_id}: {event_type} - {json.dumps(event_details)} (Severity: {severity})")

    mock_bsl = MockBSLAdapter()
    mock_faa = MockForensicArchiverAgent(bsl_adapter=mock_bsl)
    fda_instance = FinancialDecoyAgent(bsl_adapter=mock_bsl, forensic_archiver=mock_faa)

    print("\n--- Testing FDA: Generate Bait WAV File ---")
    bait_wav_path = fda_instance.generate_bait_wav("CEO_Voice_Sample_Decoy", {"tracker_id": "CEO_VS_001", "sensitivity": "high", "target_profile": "executive_impersonation"})
    if bait_wav_path:
        print(f"FDA Test: Bait WAV generated at: {bait_wav_path}")
        assert os.path.exists(bait_wav_path)
    else:
        print("FDA Test Error: Bait WAV generation failed.")

    print("\n--- Testing FDA: Generate Honey Ledger ---")
    honey_ledger_path = fda_instance.generate_honey_ledger("Q4_Financial_Projections_Decoy", num_transactions=75)
    if honey_ledger_path:
        print(f"FDA Test: Honey Ledger generated at: {honey_ledger_path}")
        assert os.path.exists(honey_ledger_path)
        with open(honey_ledger_path, "r") as f_ledger:
            ledger_content = json.load(f_ledger)
            assert len(ledger_content) == 75
    else:
        print("FDA Test Error: Honey Ledger generation failed.")

    print("\n--- Testing FDA: Process Decoy Interaction ---")
    attacker_details = {"ip": "192.168.1.101", "user_agent": "curl/7.68.0", "machine_id_sim": "MAC_FINGERPRINT_SIM_XYZ"}
    interaction = {"action": "file_accessed", "target_file": bait_wav_path if bait_wav_path else "sim_bait.wav", "access_method": "HTTP_GET"}
    harvested_intel_report = fda_instance.process_decoy_interaction("DecoyWAV_CEO_VS_001", attacker_details, interaction)
    if harvested_intel_report:
        print(f"FDA Test: Decoy interaction processed. Harvested Intel Neuron ID: {harvested_intel_report[	"neuron_id"	]}")
        assert harvested_intel_report["attributes"]["attacker_ip"] == "192.168.1.101"
    else:
        print("FDA Test Error: Decoy interaction processing failed.")

    print("\n--- Testing FDA: Run Periodic Tasks ---")
    fda_instance.run_periodic_tasks()
    # Check if new files were created in periodic tasks (visual check of logs for now)

    print("\nFinancialDecoyAgent test completed.")

