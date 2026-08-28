"""
Agharmonic Compliance Interface for CortexOS Neural Engine
Defines the required interfaces for all modules to comply with the Agharmonic Law
"""

from abc import ABC, abstractmethod

class AgharmonicCompliant(ABC):
    """
    Abstract base class defining the seven required interfaces for Agharmonic Law compliance.
    All CortexOS modules must implement these interfaces to ensure system-wide resonance integrity.
    """
    
    @abstractmethod
    def harmonic_signature(self):
        """
        Establishes frequency compatibility parameters for resonance.
        Required for Agharmonic Law Tenet 1: Harmonic Resonance Principle.
        
        Returns:
            dict: Harmonic signature parameters including frequency range and phase alignment
        """
        pass
    
    @abstractmethod
    def interface_contract(self, operation=None, payload=None):
        """
        Defines and validates interface boundaries.
        Required for Agharmonic Law Tenet 2: Cognitive Isolation.
        
        Args:
            operation (str, optional): Requested operation
            payload (dict, optional): Operation parameters
            
        Returns:
            bool or dict: True if data meets contract requirements, or contract specification if no data
        """
        pass
    
    @abstractmethod
    def cognitive_energy_flow(self, input_signal=None, source_credibility=1.0):
        """
        Normalizes signal amplitude and information flow.
        Required for Agharmonic Law Tenet 3: Balanced Information Flow.
        
        Args:
            input_signal: Input signal to normalize
            source_credibility (float): Credibility score of the source (0-1)
            
        Returns:
            dict or float: Normalized signal or energy level
        """
        pass
    
    @abstractmethod
    def sync_clock(self, global_sync_manager=None):
        """
        Connects to the master temporal framework for synchronized processing.
        Required for Agharmonic Law Tenet 4: Temporal Synchronization.
        
        Args:
            global_sync_manager: Optional external sync manager to use
            
        Returns:
            dict or bool: Synchronization status
        """
        pass
    
    @abstractmethod
    def self_regulate(self):
        """
        Implements internal feedback loops to maintain stable operation.
        Required for Agharmonic Law Tenet 5: Self-Regulation Mechanisms.
        
        Returns:
            dict: Self-regulation metrics and actions taken, must include fallback_level
        """
        pass
    
    @abstractmethod
    def graceful_fallback(self, error, context=None):
        """
        Provides mechanisms for partial operation when operating in suboptimal conditions.
        Required for Agharmonic Law Tenet 6: Graceful Degradation.
        
        Args:
            error: Error object or string triggering fallback
            context (dict, optional): Error context information
            
        Returns:
            dict: Fallback status and actions taken, must include fallback_action field
        """
        pass
    
    @abstractmethod
    def resonance_chain_validator(self, result=None):
        """
        Verifies resonance integrity across the processing chain.
        Required for Agharmonic Law Tenet 7: Resonance Chain Integrity.
        
        Args:
            result (dict, optional): Result to validate
            
        Returns:
            bool or dict: True/valid status if result maintains resonance integrity
        """
        pass
