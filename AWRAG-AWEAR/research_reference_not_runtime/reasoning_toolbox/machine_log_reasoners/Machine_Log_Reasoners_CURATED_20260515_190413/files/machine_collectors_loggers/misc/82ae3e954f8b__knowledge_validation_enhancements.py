"""
Knowledge Validation System Enhancements for Kali Ka

This module provides enhancements to the core Knowledge Validation System:
1. ValidationContext - Holds shared state throughout the validation process
2. Standardized Result Schema - Ensures consistent output formatting
3. Validation Logger - Provides detailed logging for debugging

Author: Manus
Date: April 9, 2025
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from dataclasses import dataclass, field, asdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/nexus_project/knowledge_validation/logs/validation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class ValidationContext:
    """
    Holds shared state throughout the validation process.
    
    This class maintains the original knowledge unit and all intermediate
    validation results, providing a clean way to pass state between
    validation modules.
    """
    # Original knowledge unit
    knowledge_unit: Dict[str, Any]
    
    # Extracted metadata for convenience
    uuid: str = field(default="")
    content: str = field(default="")
    source: Dict[str, Any] = field(default_factory=dict)
    domain: Dict[str, Any] = field(default_factory=dict)
    temporal: Dict[str, Any] = field(default_factory=dict)
    
    # Validation results from each module
    credibility_result: Dict[str, Any] = field(default_factory=dict)
    cross_reference_result: Dict[str, Any] = field(default_factory=dict)
    temporal_result: Dict[str, Any] = field(default_factory=dict)
    domain_result: Dict[str, Any] = field(default_factory=dict)
    truth_engine_result: Dict[str, Any] = field(default_factory=dict)
    truth_trail: Dict[str, Any] = field(default_factory=dict)
    
    # Final validation result
    validation_result: Dict[str, Any] = field(default_factory=dict)
    validation_status: str = field(default="unverified")
    
    # Validation metadata
    validation_start_time: float = field(default_factory=time.time)
    validation_end_time: float = field(default=0.0)
    validation_duration: float = field(default=0.0)
    
    def __post_init__(self):
        """Extract metadata from knowledge unit for convenience"""
        if self.knowledge_unit:
            self.uuid = self.knowledge_unit.get('uuid', "")
            self.content = self.knowledge_unit.get('content', "")
            self.source = self.knowledge_unit.get('source', {})
            self.domain = self.knowledge_unit.get('domain', {})
            self.temporal = self.knowledge_unit.get('temporal', {})
    
    def complete_validation(self):
        """Mark validation as complete and calculate duration"""
        self.validation_end_time = time.time()
        self.validation_duration = self.validation_end_time - self.validation_start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary"""
        return asdict(self)


@dataclass
class ValidatedKnowledgeUnit:
    """
    Standardized schema for validated knowledge units.
    
    This class ensures consistent output formatting for all validated
    knowledge units, making it easier to work with validation results.
    """
    # Original knowledge unit
    uuid: str
    content: str
    content_format: str
    source: Dict[str, Any]
    domain: Dict[str, Any]
    temporal: Dict[str, Any]
    verification: Dict[str, Any]
    relationships: Dict[str, Any] = field(default_factory=dict)
    emotional_context: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_knowledge_unit(cls, knowledge_unit: Dict[str, Any], verification: Dict[str, Any]) -> 'ValidatedKnowledgeUnit':
        """Create a ValidatedKnowledgeUnit from a knowledge unit and verification result"""
        return cls(
            uuid=knowledge_unit.get('uuid', ""),
            content=knowledge_unit.get('content', ""),
            content_format=knowledge_unit.get('content_format', "text"),
            source=knowledge_unit.get('source', {}),
            domain=knowledge_unit.get('domain', {}),
            temporal=knowledge_unit.get('temporal', {}),
            relationships=knowledge_unit.get('relationships', {}),
            emotional_context=knowledge_unit.get('emotional_context', {}),
            verification=verification
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    def to_json(self, indent=2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent)


class ValidationLogger:
    """
    Provides detailed logging for the validation process.
    
    This class offers structured logging with different levels of detail,
    making it easier to debug and monitor the validation process.
    """
    
    def __init__(self, log_dir="/home/ubuntu/nexus_project/knowledge_validation/logs"):
        """Initialize the ValidationLogger"""
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger("validation_logger")
        self.logger.setLevel(logging.DEBUG)
        
        # Create file handler
        log_file = os.path.join(log_dir, f"validation_{datetime.now().strftime('%Y%m%d')}.log")
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        
        # Create console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers to logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log_validation_start(self, knowledge_unit_id: str):
        """Log the start of a validation process"""
        self.logger.info(f"Starting validation for knowledge unit: {knowledge_unit_id}")
    
    def log_validation_step(self, step: str, message: str):
        """Log a validation step"""
        self.logger.info(f"Step {step}: {message}")
    
    def log_validation_result(self, result: Dict[str, Any]):
        """Log a validation result"""
        self.logger.info(f"Validation result: {json.dumps(result, indent=2)}")
    
    def log_validation_complete(self, knowledge_unit_id: str, status: str, duration: float):
        """Log the completion of a validation process"""
        self.logger.info(f"Validation completed for knowledge unit: {knowledge_unit_id}")
        self.logger.info(f"Status: {status}")
        self.logger.info(f"Duration: {duration:.2f} seconds")
    
    def log_error(self, message: str, error: Exception = None):
        """Log an error"""
        if error:
            self.logger.error(f"{message}: {str(error)}")
        else:
            self.logger.error(message)
    
    def log_debug(self, message: str):
        """Log a debug message"""
        self.logger.debug(message)
    
    def log_info(self, message: str):
        """Log an info message"""
        self.logger.info(message)
    
    def log_warning(self, message: str):
        """Log a warning message"""
        self.logger.warning(message)
    
    def log_module_result(self, module_name: str, result: Dict[str, Any]):
        """Log a module result"""
        self.logger.info(f"{module_name} result: {json.dumps(result, indent=2)}")
