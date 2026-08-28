"""
Neural Gatekeeper module for CortexOS Temporal Cognition.

This module provides security and verification for neural operations, ensuring
that context, user intent, and safety parameters are validated before triggering
sensitive neurons or executing critical operations.

Part of the CortexOS Temporal Cognition v2.1 architecture.
"""

import logging
import time
import numpy as np
import threading
import json
from collections import deque
from datetime import datetime

# Import core dependencies
try:
    from trust_filter import TrustFilter
    from global_sync_manager import GlobalSyncManager
except ImportError:
    logging.warning("Core dependencies not found, operating in isolated mode")

class NeuralGatekeeper:
    """
    Security and verification system for CortexOS neural architecture.
    
    Validates all neural operations against safety parameters, user intent,
    and operational context before allowing execution of sensitive operations.
    Implements the Agharmonic Law through strict interface contracts and
    resonance chain validation.
    """
    
    def __init__(self, security_threshold=0.8, verification_timeout=2.0):
        """
        Initialize the neural gatekeeper system.
        
        Args:
            security_threshold (float): Threshold for security validation (0.0-1.0)
            verification_timeout (float): Maximum time for verification in seconds
        """
        # Setup logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        self.logger.info("Initializing NeuralGatekeeper module")
        
        # Configuration
        self.security_threshold = security_threshold
        self.verification_timeout = verification_timeout
        self.max_verification_attempts = 3
        self.verification_cooldown = 1.0  # seconds
        
        # State tracking
        self.is_active = True
        self.verification_history = deque(maxlen=100)
        self.last_verification_time = 0
        self.verification_in_progress = False
        self.security_lock = threading.RLock()
        self.anomaly_counter = 0
        self.last_sync_time = time.time()
        self.sync_interval = 5.0  # seconds
        
        # Security policies
        self.security_policies = {}
        self.restricted_operations = set()
        self.authorized_sources = set()
        
        # Agharmonic compliance
        self.input_frequency_range = (0.6, 1.4)  # in Hz cognitive equivalent
        self.output_phase_alignment = 0.0
        self.resonance_threshold = 0.85  # Higher threshold for security
        self.degradation_levels = ["normal", "heightened", "restricted", "emergency"]
        self.current_degradation_level = "normal"
        
        # Initialize security policies
        self._init_security_policies()
        
        # Initialize trust filter with fallback mechanism
        try:
            self.trust_filter = TrustFilter()
        except Exception as e:
            self.logger.warning(f"Failed to initialize TrustFilter: {e}")
            self.trust_filter = self._create_minimal_trust_filter()
        
        # Try to connect to global sync manager
        try:
            self.global_sync = GlobalSyncManager()
        except Exception as e:
            self.logger.warning(f"Failed to connect to GlobalSyncManager: {e}")
            self.global_sync = None
        
        self.logger.info("NeuralGatekeeper module initialized successfully")
    
    def harmonic_signature(self):
        """
        Establish frequency compatibility for Agharmonic Law compliance.
        
        Returns:
            dict: Harmonic signature parameters
        """
        return {
            "module": "neural_gatekeeper",
            "input_frequency_range": self.input_frequency_range,
            "output_phase_alignment": self.output_phase_alignment,
            "resonance_threshold": self.resonance_threshold,
            "signature_version": "2.1.0",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def interface_contract(self, operation=None, context=None, source_id=None, credentials=None, payload=None):
        """
        Define and validate interface contract for Agharmonic Law compliance.
        
        Args:
            operation: Operation to validate
            context: Context to validate
            source_id: Source ID to validate
            credentials: Credentials to validate
            payload: Payload to validate
            
        Returns:
            bool: True if valid, raises exception otherwise
            
        Raises:
            ValueError: If contract is violated
        """
        # Define interface specifications
        interface_spec = {
            "inputs": {
                "operation": {"type": str, "required": True},
                "context": {"type": dict, "required": False},
                "source_id": {"type": str, "required": False},
                "credentials": {"type": dict, "required": False},
                "payload": {"type": (dict, list), "required": False}
            },
            "outputs": {
                "verification_result": {"type": dict, "required": True},
                "security_level": {"type": float, "required": True},
                "access_token": {"type": str, "required": False},
                "audit_record": {"type": dict, "required": True}
            }
        }
        
        # If no arguments provided, return the interface specification
        if operation is None:
            return interface_spec
        
        # Validate inputs
        if not isinstance(operation, interface_spec["inputs"]["operation"]["type"]):
            raise ValueError(f"Operation must be of type {interface_spec['inputs']['operation']['type'].__name__}")
        
        if context is not None and not isinstance(context, interface_spec["inputs"]["context"]["type"]):
            raise ValueError(f"Context must be of type {interface_spec['inputs']['context']['type'].__name__}")
        
        if source_id is not None and not isinstance(source_id, interface_spec["inputs"]["source_id"]["type"]):
            raise ValueError(f"Source ID must be of type {interface_spec['inputs']['source_id']['type'].__name__}")
        
        if credentials is not None and not isinstance(credentials, interface_spec["inputs"]["credentials"]["type"]):
            raise ValueError(f"Credentials must be of type {interface_spec['inputs']['credentials']['type'].__name__}")
        
        if payload is not None and not isinstance(payload, interface_spec["inputs"]["payload"]["type"]):
            raise ValueError(f"Payload must be of type {' or '.join([t.__name__ for t in interface_spec['inputs']['payload']['type']])}")
        
        return True
    
    def cognitive_energy_flow(self, signal):
        """
        Normalize signal amplitude for Agharmonic Law compliance.
        
        Args:
            signal: Input signal to normalize
            
        Returns:
            Normalized signal with balanced information flow
        """
        # Handle different signal types
        if isinstance(signal, (list, np.ndarray)):
            signal = np.array(signal)
            if signal.size > 0:
                signal_min = signal.min()
                signal_max = signal.max()
                if signal_max > signal_min:
                    normalized = (signal - signal_min) / (signal_max - signal_min)
                    # Apply sigmoid-like function for smoother transitions
                    return 1.0 / (1.0 + np.exp(-5 * (normalized - 0.5)))
                return np.zeros_like(signal)
            return signal
        
        elif isinstance(signal, (int, float)):
            # Single value normalization to [0,1]
            return max(0.0, min(1.0, signal))
        
        elif isinstance(signal, dict):
            # For dictionaries, normalize numeric values
            result = {}
            for key, value in signal.items():
                if isinstance(value, (int, float)):
                    result[key] = max(0.0, min(1.0, value))
                else:
                    result[key] = value
            return result
        
        # Return original signal if type not supported
        return signal
    
    def sync_clock(self):
        """
        Synchronize with global temporal framework for Agharmonic Law compliance.
        
        Returns:
            dict: Synchronization status
        """
        current_time = time.time()
        
        # Check if it's time to sync
        if current_time - self.last_sync_time < self.sync_interval:
            return {"synced": False, "reason": "interval_not_reached"}
        
        # Try to sync with global sync manager if available
        if self.global_sync:
            try:
                sync_result = self.global_sync.request_sync({
                    "module": "neural_gatekeeper",
                    "timestamp": current_time,
                    "security_level": self.security_threshold
                })
                
                self.last_sync_time = current_time
                
                # Adjust parameters based on sync result if provided
                if isinstance(sync_result, dict):
                    if "security_threshold" in sync_result:
                        self.security_threshold = sync_result["security_threshold"]
                    if "verification_timeout" in sync_result:
                        self.verification_timeout = sync_result["verification_timeout"]
                
                self.logger.debug(f"Clock synchronized with GlobalSyncManager: {current_time}")
                return {"synced": True, "timestamp": current_time, "source": "global_sync"}
            
            except Exception as e:
                self.logger.warning(f"Failed to sync with GlobalSyncManager: {e}")
        
        # Fallback to local sync
        self.last_sync_time = current_time
        self.logger.debug(f"Clock synchronized locally: {current_time}")
        return {"synced": True, "timestamp": current_time, "source": "local"}
    
    def self_regulate(self):
        """
        Implement self-regulation for Agharmonic Law compliance.
        
        Returns:
            dict: Self-regulation status and actions taken
        """
        regulation_actions = []
        
        # Check if we're getting too many verification requests
        recent_verifications = sum(1 for v in self.verification_history 
                                  if time.time() - v['timestamp'] < 60)
        
        # Check for anomalies in verification patterns
        if recent_verifications > 50:
            # Too many verifications, increase security threshold temporarily
            old_threshold = self.security_threshold
            self.security_threshold = min(0.95, self.security_threshold * 1.1)
            self.logger.warning(f"Self-regulation: Increased security threshold from {old_threshold:.2f} to {self.security_threshold:.2f}")
            regulation_actions.append("increased_security_threshold")
            self.anomaly_counter += 1
        
        # If very few verifications, gradually return to normal threshold
        if recent_verifications < 5 and self.security_threshold > 0.8:
            old_threshold = self.security_threshold
            self.security_threshold = max(0.8, self.security_threshold * 0.98)
            self.logger.info(f"Self-regulation: Decreased security threshold from {old_threshold:.2f} to {self.security_threshold:.2f}")
            regulation_actions.append("decreased_security_threshold")
        
        # Check for repeated verification failures
        recent_failures = sum(1 for v in self.verification_history 
                             if time.time() - v['timestamp'] < 300 and not v['result']['verified'])
        
        if recent_failures > 10:
            self.logger.warning(f"Self-regulation: Detected {recent_failures} verification failures in last 5 minutes")
            regulation_actions.append("detected_verification_failures")
            self.anomaly_counter += 1
        
        # Check for potential security breach attempts
        if self.anomaly_counter > 5:
            old_level = self.current_degradation_level
            self._escalate_degradation_level()
            self.logger.warning(f"Self-regulation: Escalated degradation level from {old_level} to {self.current_degradation_level}")
            regulation_actions.append("escalated_degradation_level")
            
            # Reset anomaly counter after taking action
            self.anomaly_counter = 0
        
        # Periodically reduce anomaly counter if no new anomalies
        if time.time() % 300 < 1 and self.anomaly_counter > 0:
            self.anomaly_counter -= 1
        
        # Periodically try to recover from degraded states
        if time.time() % 600 < 1 and self.current_degradation_level != "normal":
            if recent_failures == 0 and recent_verifications < 30:
                old_level = self.current_degradation_level
                self._deescalate_degradation_level()
                self.logger.info(f"Self-regulation: De-escalated degradation level from {old_level} to {self.current_degradation_level}")
                regulation_actions.append("deescalated_degradation_level")
        
        return {
            "regulated": len(regulation_actions) > 0,
            "actions": regulation_actions,
            "security_threshold": self.security_threshold,
            "degradation_level": self.current_degradation_level,
            "anomaly_counter": self.anomaly_counter
        }
    
    def graceful_fallback(self, error_type=None, context=None):
        """
        Implement graceful degradation for Agharmonic Law compliance.
        
        Args:
            error_type (str, optional): Type of error triggering fallback
            context (dict, optional): Context information for fallback
            
        Returns:
            dict: Fallback status and actions taken
        """
        fallback_actions = []
        context = context or {}
        
        # If trust filter is unavailable, use internal minimal filter
        if not hasattr(self, 'trust_filter') or self.trust_filter is None:
            self.logger.warning("Graceful fallback: TrustFilter unavailable, using minimal filter")
            self.trust_filter = self._create_minimal_trust_filter()
            fallback_actions.append("created_minimal_trust_filter")
        
        # If global sync is unavailable, operate in standalone mode
        if not hasattr(self, 'global_sync') or self.global_sync is None:
            self.logger.warning("Graceful fallback: GlobalSyncManager unavailable, operating in standalone mode")
            fallback_actions.append("standalone_mode_activated")
        
        # Handle specific error types
        if error_type == "verification_timeout":
            # Increase verification timeout temporarily
            old_timeout = self.verification_timeout
            self.verification_timeout = min(10.0, self.verification_timeout * 1.5)
            self.logger.warning(f"Graceful fallback: Increased verification timeout from {old_timeout:.2f}s to {self.verification_timeout:.2f}s")
            fallback_actions.append("increased_verification_timeout")
        
        elif error_type == "security_breach":
            # Enter emergency mode
            self.current_degradation_level = "emergency"
            self.security_threshold = 0.95
            self.logger.critical("Graceful fallback: Entered emergency mode due to security breach")
            fallback_actions.append("entered_emergency_mode")
            
            # Restrict all non-essential operations
            self._restrict_non_essential_operations()
            fallback_actions.append("restricted_non_essential_operations")
        
        elif error_type == "trust_filter_error":
            # Try to repair trust filter
            try:
                self.trust_filter = TrustFilter()
                self.logger.info("Graceful fallback: Successfully repaired TrustFilter")
                fallback_actions.append("repaired_trust_filter")
            except Exception as e:
                self.logger.warning(f"Graceful fallback: Failed to repair TrustFilter: {e}")
                self.trust_filter = self._create_minimal_trust_filter()
                fallback_actions.append("created_minimal_trust_filter")
        
        # Load fallback chains from configuration if available
        try:
            with open("data/fallback_chains.json", "r") as f:
                fallback_chains = json.load(f)
                
            # Apply appropriate fallback chain if available
            chain_key = error_type if error_type in fallback_chains else "default"
            if chain_key in fallback_chains:
                chain = fallback_chains[chain_key]
                self.logger.info(f"Graceful fallback: Applying fallback chain '{chain_key}'")
                
                # Execute fallback actions in chain
                for action in chain.get("actions", []):
                    if action["type"] == "set_threshold" and "value" in action:
                        self.security_threshold = action["value"]
                        fallback_actions.append(f"set_threshold_{action['value']}")
                    
                    elif action["type"] == "set_degradation" and "level" in action:
                        if action["level"] in self.degradation_levels:
                            self.current_degradation_level = action["level"]
                            fallback_actions.append(f"set_degradation_{action['level']}")
                
                fallback_actions.append(f"applied_fallback_chain_{chain_key}")
        except Exception as e:
            self.logger.warning(f"Graceful fallback: Failed to load fallback chains: {e}")
        
        # Return fallback status
        return {
            "fallback_activated": len(fallback_actions) > 0,
            "actions": fallback_actions,
            "degradation_level": self.current_degradation_level,
            "security_threshold": self.security_threshold,
            "error_type": error_type
        }
    
    def resonance_chain_validator(self, verification_result):
        """
        Validate resonance chain integrity for Agharmonic Law compliance.
        
        Args:
            verification_result: Verification result to validate
            
        Returns:
            dict: Validation results
            
        Raises:
            ValueError: If resonance chain integrity is compromised
        """
        validation_results = {
            "valid": False,
            "checks_passed": [],
            "checks_failed": [],
            "timestamp": time.time()
        }
        
        try:
            # Basic structure validation
            if not verification_result or not isinstance(verification_result, dict):
                validation_results["checks_failed"].append("structure_invalid")
                raise ValueError("Invalid verification result format")
            
            validation_results["checks_passed"].append("structure_valid")
            
            # Required keys validation
            required_keys = ['verified', 'security_level', 'timestamp', 'operation']
            missing_keys = [k for k in required_keys if k not in verification_result]
            
            if missing_keys:
                validation_results["checks_failed"].append("missing_required_keys")
                validation_results["missing_keys"] = missing_keys
                raise ValueError(f"Verification result missing required keys: {missing_keys}")
            
            validation_results["checks_passed"].append("required_keys_present")
            
            # Timestamp validation
            if abs(time.time() - verification_result['timestamp']) > 30:
                validation_results["checks_failed"].append("timestamp_out_of_range")
                raise ValueError("Verification result timestamp outside acceptable range")
            
            validation_results["checks_passed"].append("timestamp_valid")
            
            # Security level validation
            if not isinstance(verification_result['security_level'], (int, float)) or \
               verification_result['security_level'] < 0 or verification_result['security_level'] > 1:
                validation_results["checks_failed"].append("security_level_invalid")
                raise ValueError("Security level must be a number between 0 and 1")
            
            validation_results["checks_passed"].append("security_level_valid")
            
            # Operation validation
            if not isinstance(verification_result['operation'], str) or not verification_result['operation']:
                validation_results["checks_failed"].append("operation_invalid")
                raise ValueError("Operation must be a non-empty string")
            
            validation_results["checks_passed"].append("operation_valid")
            
            # Verified flag validation
            if not isinstance(verification_result['verified'], bool):
                validation_results["checks_failed"].append("verified_flag_invalid")
                raise ValueError("Verified flag must be a boolean")
            
            validation_results["checks_passed"].append("verified_flag_valid")
            
            # Access token validation if present
            if 'access_token' in verification_result:
                if not isinstance(verification_result['access_token'], str) or not verification_result['access_token']:
                    validation_results["checks_failed"].append("access_token_invalid")
                    raise ValueError("Access token must be a non-empty string")
                
                validation_results["checks_passed"].append("access_token_valid")
            
            # All checks passed
            validation_results["valid"] = True
            return validation_results
            
        except ValueError as e:
            # Add error message to validation results
            validation_results["error"] = str(e)
            return validation_results
    
    def verify_operation(self, operation, context=None, source_id=None, credentials=None, payload=None):
        """
        Verify if an operation is allowed to execute.
        
        Args:
            operation (str): Operation to verify
            context (dict, optional): Operation context
            source_id (str, optional): Source identifier
            credentials (dict, optional): Authentication credentials
            payload (dict, optional): Operation payload
            
        Returns:
            dict: Verification results
        """
        # Validate interface contract
        try:
            self.interface_contract(operation, context, source_id, credentials, payload)
        except ValueError as e:
            self.logger.warning(f"Interface contract violation: {e}")
            return {
                'verified': False,
                'security_level': 0,
                'reason': f'interface_contract_violation: {str(e)}',
                'operation': operation,
                'timestamp': time.time()
            }
        
        # Initialize context if None
        context = context or {}
        
        # Check if gatekeeper is active
        if not self.is_active:
            self.logger.warning("Neural gatekeeper is inactive, operations cannot be verified")
            return {
                'verified': False,
                'security_level': 0,
                'reason': 'gatekeeper_inactive',
                'operation': operation,
                'timestamp': time.time()
            }
        
        # Check if we're in cooldown period
        if time.time() - self.last_verification_time < self.verification_cooldown:
            self.logger.debug("Verification in cooldown period, waiting...")
            time.sleep(self.verification_cooldown)
        
        # Sync clock before verification
        self.sync_clock()
        
        # Set verification in progress
        with self.security_lock:
            self.verification_in_progress = True
            self.last_verification_time = time.time()
            
            try:
                # Start verification timer
                start_time = time.time()
                
                # Check degradation level
                if self.current_degradation_level == "emergency":
                    # In emergency mode, only allow essential operations
                    if operation not in self._get_essential_operations():
                        self.logger.warning(f"Operation {operation} denied due to emergency mode")
                        verification_result = {
                            'verified': False,
                            'security_level': 0,
                            'reason': 'emergency_mode_active',
                            'operation': operation,
                            'timestamp': time.time()
                        }
                        return verification_result
                
                # Check if operation is restricted
                if operation in self.restricted_operations:
                    self.logger.warning(f"Operation {operation} is restricted")
                    verification_result = {
                        'verified': False,
                        'security_level': 0,
                        'reason': 'operation_restricted',
                        'operation': operation,
                        'timestamp': time.time()
                    }
                    return verification_result
                
                # Check source authorization if provided
                if source_id and self.authorized_sources and source_id not in self.authorized_sources:
                    self.logger.warning(f"Source {source_id} is not authorized")
                    verification_result = {
                        'verified': False,
                        'security_level': 0,
                        'reason': 'source_unauthorized',
                        'operation': operation,
                        'timestamp': time.time()
                    }
                    return verification_result
                
                # Apply trust filter to operation and context
                try:
                    trust_result = self.trust_filter.evaluate(operation, context)
                except Exception as e:
                    self.logger.error(f"Trust filter error: {e}")
                    # Attempt graceful fallback
                    fallback_result = self.graceful_fallback("trust_filter_error")
                    if fallback_result["fallback_activated"]:
                        # Retry with minimal trust filter
                        trust_result = self.trust_filter.evaluate(operation, context)
                    else:
                        verification_result = {
                            'verified': False,
                            'security_level': 0,
                            'reason': f'trust_filter_error: {str(e)}',
                            'operation': operation,
                            'timestamp': time.time()
                        }
                        return verification_result
                
                # Apply cognitive energy flow to normalize trust score
                trust_result['trust_score'] = self.cognitive_energy_flow(trust_result['trust_score'])
                
                if trust_result['trust_score'] < self.security_threshold:
                    self.logger.warning(f"Trust score {trust_result['trust_score']:.2f} below threshold {self.security_threshold:.2f}")
                    verification_result = {
                        'verified': False,
                        'security_level': trust_result['trust_score'],
                        'reason': 'trust_score_below_threshold',
                        'trust_details': trust_result,
                        'operation': operation,
                        'timestamp': time.time()
                    }
                    return verification_result
                
                # Get security policy for operation
                policy = self._get_security_policy(operation)
                
                # Apply security policy
                if policy:
                    policy_result = self._apply_security_policy(policy, operation, context, source_id, credentials, payload)
                    if not policy_result['passed']:
                        self.logger.warning(f"Security policy check failed: {policy_result['reason']}")
                        verification_result = {
                            'verified': False,
                            'security_level': policy_result.get('security_level', 0),
                            'reason': f"policy_check_failed: {policy_result['reason']}",
                            'policy': policy['name'],
                            'operation': operation,
                            'timestamp': time.time()
                        }
                        return verification_result
                
                # Check verification timeout
                if time.time() - start_time > self.verification_timeout:
                    self.logger.warning(f"Verification timeout for operation {operation}")
                    # Attempt graceful fallback
                    fallback_result = self.graceful_fallback("verification_timeout")
                    verification_result = {
                        'verified': False,
                        'security_level': 0,
                        'reason': 'verification_timeout',
                        'fallback_applied': fallback_result["fallback_activated"],
                        'operation': operation,
                        'timestamp': time.time()
                    }
                    return verification_result
                
                # All checks passed, generate access token
                access_token = self._generate_access_token(operation, source_id)
                
                # Create verification result
                verification_result = {
                    'verified': True,
                    'security_level': trust_result['trust_score'],
                    'access_token': access_token,
                    'operation': operation,
                    'timestamp': time.time(),
                    'audit_record': {
                        'operation': operation,
                        'source_id': source_id,
                        'context_hash': self._hash_context(context) if context else None,
                        'verification_time': time.time() - start_time,
                        'degradation_level': self.current_degradation_level
                    }
                }
                
                # Record verification
                self._record_verification(operation, verification_result)
                
                # Self-regulation
                regulation_result = self.self_regulate()
                if regulation_result["regulated"]:
                    verification_result["regulation_applied"] = regulation_result["actions"]
                
                # Validate resonance chain
                validation_result = self.resonance_chain_validator(verification_result)
                if not validation_result["valid"]:
                    self.logger.warning(f"Resonance chain validation failed: {validation_result.get('error', 'Unknown error')}")
                    verification_result['resonance_warning'] = validation_result
                
                return verification_result
                
            except Exception as e:
                self.logger.error(f"Error during verification: {e}")
                # Attempt graceful fallback
                fallback_result = self.graceful_fallback("verification_error", {"error": str(e)})
                return {
                    'verified': False,
                    'security_level': 0,
                    'reason': f'verification_error: {str(e)}',
                    'fallback_applied': fallback_result["fallback_activated"],
                    'operation': operation,
                    'timestamp': time.time()
                }
            finally:
                # Clear verification in progress flag
                self.verification_in_progress = False
    
    def register_security_policy(self, name, operation_pattern, check_func, security_level=0.8):
        """
        Register a new security policy.
        
        Args:
            name (str): Policy name
            operation_pattern (str): Operation pattern to match
            check_func (callable): Function to check policy compliance
            security_level (float): Security level of policy (0.0-1.0)
            
        Returns:
            bool: Success status
        """
        if name in self.security_policies:
            self.logger.warning(f"Security policy {name} already exists, overwriting")
        
        policy = {
            'name': name,
            'operation_pattern': operation_pattern,
            'check_func': check_func,
            'security_level': security_level
        }
        
        self.security_policies[name] = policy
        self.logger.info(f"Registered security policy {name} for {operation_pattern}")
        
        return True
    
    def restrict_operation(self, operation):
        """
        Add an operation to the restricted list.
        
        Args:
            operation (str): Operation to restrict
            
        Returns:
            bool: Success status
        """
        self.restricted_operations.add(operation)
        self.logger.info(f"Added {operation} to restricted operations")
        return True
    
    def authorize_source(self, source_id):
        """
        Add a source to the authorized list.
        
        Args:
            source_id (str): Source to authorize
            
        Returns:
            bool: Success status
        """
        self.authorized_sources.add(source_id)
        self.logger.info(f"Added {source_id} to authorized sources")
        return True
    
    def get_verification_history(self, limit=10):
        """
        Get recent verification history.
        
        Args:
            limit (int): Maximum number of records to return
            
        Returns:
            list: Recent verification history
        """
        return list(self.verification_history)[-limit:]
    
    def get_security_status(self):
        """
        Get current security status.
        
        Returns:
            dict: Security status
        """
        return {
            'is_active': self.is_active,
            'security_threshold': self.security_threshold,
            'verification_timeout': self.verification_timeout,
            'degradation_level': self.current_degradation_level,
            'recent_verifications': len(self.verification_history),
            'anomaly_counter': self.anomaly_counter,
            'last_sync_time': self.last_sync_time,
            'harmonic_signature': self.harmonic_signature()
        }
    
    def _init_security_policies(self):
        """Initialize default security policies."""
        # Example policy: Require authentication for sensitive operations
        self.register_security_policy(
            name="require_auth",
            operation_pattern="sensitive_",
            check_func=lambda op, ctx, src, cred, payload: {
                'passed': cred is not None and 'auth_token' in cred,
                'reason': 'missing_credentials' if cred is None else 'missing_auth_token' if 'auth_token' not in cred else None
            },
            security_level=0.9
        )
        
        # Example policy: Rate limit for high-frequency operations
        self.register_security_policy(
            name="rate_limit",
            operation_pattern="batch_",
            check_func=lambda op, ctx, src, cred, payload: {
                'passed': len(self.verification_history) < 100 or sum(1 for v in self.verification_history 
                                                                     if time.time() - v['timestamp'] < 60 and v['operation'] == op) < 10,
                'reason': 'rate_limit_exceeded' if sum(1 for v in self.verification_history 
                                                      if time.time() - v['timestamp'] < 60 and v['operation'] == op) >= 10 else None
            },
            security_level=0.7
        )
    
    def _get_security_policy(self, operation):
        """
        Get security policy for operation.
        
        Args:
            operation (str): Operation to get policy for
            
        Returns:
            dict: Security policy or None
        """
        for policy in self.security_policies.values():
            if policy['operation_pattern'] in operation:
                return policy
        return None
    
    def _apply_security_policy(self, policy, operation, context, source_id, credentials, payload):
        """
        Apply security policy.
        
        Args:
            policy (dict): Security policy to apply
            operation (str): Operation to check
            context (dict): Operation context
            source_id (str): Source identifier
            credentials (dict): Authentication credentials
            payload (dict): Operation payload
            
        Returns:
            dict: Policy check result
        """
        try:
            result = policy['check_func'](operation, context, source_id, credentials, payload)
            result['security_level'] = policy['security_level']
            return result
        except Exception as e:
            self.logger.error(f"Error applying security policy {policy['name']}: {e}")
            return {
                'passed': False,
                'reason': f'policy_error: {str(e)}',
                'security_level': policy['security_level']
            }
    
    def _generate_access_token(self, operation, source_id=None):
        """
        Generate access token for verified operation.
        
        Args:
            operation (str): Verified operation
            source_id (str, optional): Source identifier
            
        Returns:
            str: Access token
        """
        import hashlib
        import base64
        
        # Generate token components
        timestamp = str(time.time())
        nonce = str(np.random.randint(10000, 99999))
        source = source_id or "system"
        
        # Combine components
        token_data = f"{operation}:{source}:{timestamp}:{nonce}"
        
        # Hash token data
        token_hash = hashlib.sha256(token_data.encode()).digest()
        
        # Encode token
        token = base64.urlsafe_b64encode(token_hash).decode()
        
        return token
    
    def _record_verification(self, operation, result):
        """
        Record verification in history.
        
        Args:
            operation (str): Verified operation
            result (dict): Verification result
        """
        record = {
            'operation': operation,
            'timestamp': time.time(),
            'result': result
        }
        
        self.verification_history.append(record)
    
    def _create_minimal_trust_filter(self):
        """
        Create minimal trust filter for fallback.
        
        Returns:
            object: Minimal trust filter
        """
        class MinimalTrustFilter:
            def evaluate(self, operation, context=None):
                # Simple trust evaluation based on operation name
                trust_score = 0.5  # Default moderate trust
                
                # Higher trust for read operations
                if operation.startswith(('get_', 'read_', 'view_', 'list_')):
                    trust_score = 0.8
                
                # Lower trust for write/delete operations
                elif operation.startswith(('set_', 'write_', 'delete_', 'remove_')):
                    trust_score = 0.3
                
                # Very low trust for system operations
                elif operation.startswith(('system_', 'admin_', 'config_')):
                    trust_score = 0.1
                
                return {
                    'trust_score': trust_score,
                    'confidence': 0.5,
                    'reason': 'minimal_trust_filter'
                }
        
        return MinimalTrustFilter()
    
    def _hash_context(self, context):
        """
        Generate hash of context for audit records.
        
        Args:
            context (dict): Context to hash
            
        Returns:
            str: Context hash
        """
        import hashlib
        import json
        
        # Convert context to JSON string
        context_json = json.dumps(context, sort_keys=True)
        
        # Hash context
        context_hash = hashlib.sha256(context_json.encode()).hexdigest()
        
        return context_hash
    
    def _escalate_degradation_level(self):
        """Escalate to next degradation level."""
        current_index = self.degradation_levels.index(self.current_degradation_level)
        if current_index < len(self.degradation_levels) - 1:
            self.current_degradation_level = self.degradation_levels[current_index + 1]
    
    def _deescalate_degradation_level(self):
        """De-escalate to previous degradation level."""
        current_index = self.degradation_levels.index(self.current_degradation_level)
        if current_index > 0:
            self.current_degradation_level = self.degradation_levels[current_index - 1]
    
    def _restrict_non_essential_operations(self):
        """Restrict all non-essential operations."""
        essential_ops = self._get_essential_operations()
        
        # Clear existing restrictions
        self.restricted_operations.clear()
        
        # Add all operations except essential ones to restricted list
        for op in ["write_", "delete_", "modify_", "create_", "update_", "execute_", "admin_"]:
            self.restricted_operations.add(op)
    
    def _get_essential_operations(self):
        """Get list of essential operations that are allowed in emergency mode."""
        return [
            "read_status",
            "get_security_status",
            "emergency_override",
            "system_recovery",
            "reset_security",
            "view_logs"
        ]
