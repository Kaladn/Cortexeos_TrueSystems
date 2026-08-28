"""
Agent Module: Secure Communications Agent (SCA)

Ensures secure and authenticated communication channels between AI agents.
Manages encryption (simulated post-quantum), message integrity, and adaptive
biometric authentication (simulated).

Based on design in: docs/secure_communications_agent_design.md
"""

import time
import json
import hashlib
import base64
import os # For random challenge generation

# from ..binary_symbolic_lexicon import BinarySymbolicLexiconAdapter
# from .forensic_archiver_agent import ForensicArchiverAgent # For logging

class SecureCommunicationsAgent:
    def __init__(self, bsl_adapter, forensic_archiver, agent_config=None):
        self.bsl_adapter = bsl_adapter
        self.forensic_archiver = forensic_archiver
        self.config = agent_config if agent_config else {}
        self.agent_keys = {} # {agent_id: shared_secret_string}
        self.active_challenges = {} # {challenge_id: {recipient_agent_id, expected_response, timestamp}}
        self._initialize_agent_keys() # Simulate loading/registering agent keys
        print("SecureCommunicationsAgent initialized.")

    def _log_sca_event(self, event_type, event_details, severity="info"):
        if self.forensic_archiver:
            # Call the log_event method of the passed ForensicArchiverAgent instance
            self.forensic_archiver.log_event("SecureCommunicationsAgent", event_type, event_details, severity)
        else:
            # Fallback print if no archiver is provided (e.g., during standalone testing)
            print(f"SCA_LOG (no archiver): Agent: SecureCommunicationsAgent, Type: {event_type}, Severity: {severity}, Details: {json.dumps(event_details)}")

    def _initialize_agent_keys(self):
        """Simulates registering agents and their shared secrets with SCA."""
        self.agent_keys["PerimeterDefenseAgent_01"] = "pda_secret_key_alpha_secure"
        self.agent_keys["EndpointGuardianAgent_01"] = "ega_secret_key_beta_secure"
        self.agent_keys["DeceptionCommanderAgent_01"] = "dca_secret_key_gamma_secure"
        self.agent_keys["ForensicArchiverAgent_01"] = "faa_secret_key_delta_secure"
        self.agent_keys["SecureCommunicationsAgent_01"] = "sca_secret_key_epsilon_secure" # SCA might need its own key for some ops
        self.agent_keys["TestAgent_Alice"] = "alice_key_for_testing"
        self.agent_keys["TestAgent_Bob"] = "bob_key_for_testing"
        self._log_sca_event("agent_keys_initialized", {"registered_agents_count": len(self.agent_keys)})
        print(f"SCA: Initialized shared keys for {len(self.agent_keys)} agents (simulated).")

    def _sim_encrypt(self, plaintext_json, key):
        """Simulates encryption. XOR with key and then Base64 encode."""
        plaintext_bytes = plaintext_json.encode("utf-8")
        key_bytes = key.encode("utf-8")
        encrypted_bytes = bytearray()
        for i in range(len(plaintext_bytes)):
            encrypted_bytes.append(plaintext_bytes[i] ^ key_bytes[i % len(key_bytes)])
        return base64.b64encode(encrypted_bytes).decode("utf-8")

    def _sim_decrypt(self, ciphertext_b64, key):
        """Simulates decryption. Base64 decode then XOR with key."""
        encrypted_bytes = base64.b64decode(ciphertext_b64.encode("utf-8"))
        key_bytes = key.encode("utf-8")
        decrypted_bytes = bytearray()
        for i in range(len(encrypted_bytes)):
            decrypted_bytes.append(encrypted_bytes[i] ^ key_bytes[i % len(key_bytes)])
        return decrypted_bytes.decode("utf-8")

    def _sim_generate_signature(self, data_str, key):
        """Simulates generating a signature (HMAC-SHA256 concept)."""
        return hashlib.sha256((key + data_str).encode("utf-8")).hexdigest()

    def _sim_verify_signature(self, data_str, signature, key):
        """Simulates verifying a signature."""
        expected_signature = self._sim_generate_signature(data_str, key)
        return signature == expected_signature

    def register_agent(self, agent_id, shared_key):
        """Allows a new agent to register with SCA."""
        if agent_id in self.agent_keys:
            self._log_sca_event("agent_registration_failed", {"agent_id": agent_id, "reason": "already_exists"}, "warning")
            return False
        self.agent_keys[agent_id] = shared_key
        self._log_sca_event("agent_registered", {"agent_id": agent_id})
        print(f"SCA: Agent {agent_id} registered successfully.")
        return True

    def send_message(self, sender_agent_id, recipient_agent_id, message_type, payload, requires_biometric_auth=False, biometric_challenge_response=None):
        """Sends a secure message from one agent to another."""
        if sender_agent_id not in self.agent_keys or recipient_agent_id not in self.agent_keys:
            self._log_sca_event("message_send_failed", {"sender": sender_agent_id, "recipient": recipient_agent_id, "reason": "unknown_agent"}, "error")
            return None

        sender_key = self.agent_keys[sender_agent_id]

        if requires_biometric_auth:
            if not biometric_challenge_response or not self._verify_biometric_challenge(recipient_agent_id, biometric_challenge_response, sender_agent_id):
                self._log_sca_event("message_send_failed_bio_auth", {"sender": sender_agent_id, "recipient": recipient_agent_id, "reason": "biometric_auth_failed"}, "warning")
                return None
            self._log_sca_event("biometric_auth_success_for_send", {"sender": sender_agent_id, "recipient": recipient_agent_id})

        message_content = {
            "sender_agent_id": sender_agent_id,
            "recipient_agent_id": recipient_agent_id, 
            "timestamp": time.time(),
            "message_type": message_type,
            "payload": payload,
            "requires_biometric_auth_fulfilled": requires_biometric_auth
        }
        plaintext_json = json.dumps(message_content)
        encrypted_data = self._sim_encrypt(plaintext_json, sender_key) # Encrypt with sender key
        signature = self._sim_generate_signature(encrypted_data, sender_key)

        secure_envelope = {
            "encrypted_payload": encrypted_data,
            "signature": signature,
            "sender_id_clear": sender_agent_id 
        }
        self._log_sca_event("message_sent", {"sender": sender_agent_id, "recipient": recipient_agent_id, "type": message_type, "size_bytes_encrypted": len(json.dumps(secure_envelope))})
        return secure_envelope

    def receive_message(self, secure_envelope, recipient_agent_id):
        """Processes a received secure envelope for a recipient agent."""
        if recipient_agent_id not in self.agent_keys:
            self._log_sca_event("message_receive_failed", {"recipient": recipient_agent_id, "reason": "unknown_recipient"}, "error")
            return None
        
        sender_agent_id = secure_envelope.get("sender_id_clear")
        if not sender_agent_id or sender_agent_id not in self.agent_keys:
            self._log_sca_event("message_receive_failed", {"recipient": recipient_agent_id, "reason": "unknown_sender_in_envelope"}, "error")
            return None

        sender_key = self.agent_keys[sender_agent_id]
        encrypted_data = secure_envelope.get("encrypted_payload")
        signature = secure_envelope.get("signature")

        if not self._sim_verify_signature(encrypted_data, signature, sender_key):
            self._log_sca_event("message_integrity_check_failed", {"sender": sender_agent_id, "recipient": recipient_agent_id}, "warning")
            return None
        
        try:
            decrypted_json = self._sim_decrypt(encrypted_data, sender_key) # Decrypt with sender key
            message_content = json.loads(decrypted_json)
            # Final check: ensure the message was indeed intended for this recipient if recipient_id is in payload
            if message_content.get("recipient_agent_id") != recipient_agent_id:
                self._log_sca_event("message_recipient_mismatch", {"sender": sender_agent_id, "intended_recipient": message_content.get("recipient_agent_id"), "actual_recipient": recipient_agent_id}, "warning")
                return None # Or handle as a more severe security event

            self._log_sca_event("message_received_decrypted", {"sender": message_content["sender_agent_id"], "recipient": recipient_agent_id, "type": message_content["message_type"]})
            return message_content
        except Exception as e:
            self._log_sca_event("message_decryption_failed", {"sender": sender_agent_id, "recipient": recipient_agent_id, "error": str(e)}, "error")
            return None

    def request_biometric_challenge(self, requesting_agent_id, target_agent_id_for_message):
        """Generates a biometric challenge for a target agent (simulated)."""
        if target_agent_id_for_message not in self.agent_keys or requesting_agent_id not in self.agent_keys:
            self._log_sca_event("bio_challenge_request_failed", {"requester": requesting_agent_id, "target": target_agent_id_for_message, "reason": "unknown_agent"}, "warning")
            return None
        
        challenge_id = base64.urlsafe_b64encode(os.urandom(8)).decode("utf-8")
        expected_response = challenge_id 
        self.active_challenges[challenge_id] = {
            "recipient_agent_id_for_message": target_agent_id_for_message, 
            "requesting_agent_id": requesting_agent_id, 
            "expected_response": expected_response,
            "timestamp": time.time()
        }
        self._log_sca_event("bio_challenge_issued", {"challenge_id": challenge_id, "requester": requesting_agent_id, "target_for_message": target_agent_id_for_message})
        return {"challenge_id": challenge_id, "challenge_data": "RespondWithChallengeID"}

    def _verify_biometric_challenge(self, recipient_agent_id_for_message, challenge_response, actual_sender_id):
        """Verifies a biometric challenge response (simulated)."""
        challenge_id = challenge_response.get("challenge_id")
        response_data = challenge_response.get("response_data")

        if challenge_id in self.active_challenges:
            challenge_info = self.active_challenges[challenge_id]
            if challenge_info["recipient_agent_id_for_message"] == recipient_agent_id_for_message and \
               challenge_info["requesting_agent_id"] == actual_sender_id and \
               (time.time() - challenge_info["timestamp"]) < 60:
                if response_data == challenge_info["expected_response"]:
                    del self.active_challenges[challenge_id] 
                    return True
        self._log_sca_event("bio_challenge_verification_failed", {"challenge_id": challenge_id, "recipient_for_message": recipient_agent_id_for_message, "actual_sender": actual_sender_id}, "warning")
        return False

    def run_periodic_tasks(self):
        """Clean up expired challenges, etc."""
        print("SCA: Running periodic tasks...")
        expired_count = 0
        current_time = time.time()
        challenges_to_keep = {}
        for cid, cinfo in list(self.active_challenges.items()): # Iterate over a copy for safe deletion
            if (current_time - cinfo["timestamp"]) < 300: 
                challenges_to_keep[cid] = cinfo
            else:
                expired_count += 1
                del self.active_challenges[cid]
        if expired_count > 0:
            self._log_sca_event("bio_challenges_expired_cleaned", {"count": expired_count})
        print(f"SCA: Periodic tasks executed. {expired_count} expired challenges cleaned.")

# Example Usage (for testing the agent directly)
if __name__ == "__main__":
    # Mock BSL Adapter for standalone testing
    class MockBSLAdapter:
        def __init__(self):
            print("MockBSLAdapter initialized for SCA test.")
        def add_neuron(self, neuron_data):
            print(f"MockBSL (SCA): Add Neuron called with Type: {neuron_data.get(	'type'	)}, ID: {neuron_data.get(	'neuron_id'	)}")
        def get_neuron_data(self, neuron_id):
            print(f"MockBSL (SCA): Get Neuron Data for {neuron_id}")
            return None 

    # Mock Forensic Archiver Agent for standalone testing
    class MockForensicArchiverAgent:
        def __init__(self, bsl_adapter):
            self.bsl_adapter = bsl_adapter
            self.log_buffer = []
            print("MockForensicArchiverAgent initialized for SCA test.")
        def log_event(self, source_agent_id, event_type, event_details, severity="info"):
            timestamp = time.time()
            log_id = f"mock_log_{event_type}_{timestamp}"
            log_entry = {"id": log_id, "source": source_agent_id, "type": event_type, "details": event_details, "severity": severity, "timestamp": timestamp}
            self.log_buffer.append(log_entry)
            print(f"MockFAA: Logged by {source_agent_id}: {event_type} - {json.dumps(event_details)} (Severity: {severity})")

    mock_bsl = MockBSLAdapter()
    mock_faa = MockForensicArchiverAgent(bsl_adapter=mock_bsl)
    sca_instance = SecureCommunicationsAgent(bsl_adapter=mock_bsl, forensic_archiver=mock_faa)

    alice_id = "TestAgent_Alice"
    bob_id = "TestAgent_Bob"

    print("\n--- Testing Basic Message Send/Receive (No Biometrics) ---")
    payload_to_bob = {"command": "get_status", "param": "all"}
    secure_msg_to_bob = sca_instance.send_message(alice_id, bob_id, "command", payload_to_bob)
    
    if secure_msg_to_bob:
        print(f"SCA Test: Alice sent to Bob (encrypted): {json.dumps(secure_msg_to_bob)[:100]}...")
        received_msg_by_bob = sca_instance.receive_message(secure_msg_to_bob, bob_id)
        if received_msg_by_bob:
            print(f"SCA Test: Bob received from Alice (decrypted): {received_msg_by_bob}")
            assert received_msg_by_bob["payload"] == payload_to_bob
        else:
            print("SCA Test Error: Bob failed to receive/decrypt message.")
    else:
        print("SCA Test Error: Alice failed to send message.")

    print("\n--- Testing Message Send/Receive (WITH Biometrics) ---")
    critical_payload_to_alice = {"action": "shutdown_sector_alpha", "confirmation_code": "AX789-BY001"}
    
    # Bob requests challenge for Alice
    challenge_details = sca_instance.request_biometric_challenge(bob_id, alice_id)
    if challenge_details:
        print(f"SCA Test: Bob obtained challenge for Alice: {challenge_details}")
        challenge_id = challenge_details["challenge_id"]
        # Bob prepares response (in simulation, it	_s just the challenge_id itself)
        bio_response = {"challenge_id": challenge_id, "response_data": challenge_id}
        
        secure_critical_msg = sca_instance.send_message(bob_id, alice_id, "critical_command", critical_payload_to_alice, requires_biometric_auth=True, biometric_challenge_response=bio_response)
        if secure_critical_msg:
            print(f"SCA Test: Bob sent critical to Alice (encrypted): {json.dumps(secure_critical_msg)[:100]}...")
            received_critical_by_alice = sca_instance.receive_message(secure_critical_msg, alice_id)
            if received_critical_by_alice:
                print(f"SCA Test: Alice received critical from Bob (decrypted): {received_critical_by_alice}")
                assert received_critical_by_alice["payload"] == critical_payload_to_alice
                assert received_critical_by_alice["requires_biometric_auth_fulfilled"] == True
            else:
                print("SCA Test Error: Alice failed to receive/decrypt critical message.")
        else:
            print("SCA Test Error: Bob failed to send critical message with biometrics.")
    else:
        print("SCA Test Error: Bob failed to obtain biometric challenge.")

    print("\n--- Testing Failed Biometric Auth ---")
    invalid_bio_response = {"challenge_id": "fake_id", "response_data": "wrong_response"}
    failed_secure_msg = sca_instance.send_message(bob_id, alice_id, "critical_command", {"data": "test_fail"}, requires_biomet
(Content truncated due to size limit. Use line ranges to read in chunks)