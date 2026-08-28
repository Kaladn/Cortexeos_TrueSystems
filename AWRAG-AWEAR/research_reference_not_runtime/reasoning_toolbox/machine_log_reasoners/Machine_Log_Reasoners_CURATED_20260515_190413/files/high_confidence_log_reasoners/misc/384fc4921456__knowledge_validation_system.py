"""
Knowledge Validation System Integration with Truth Engine for Kali Ka

This module integrates the specialized validation modules with the Truth Engine
to create a complete knowledge validation system for Kali Ka.

Author: Manus
Date: April 9, 2025
"""

import os
import sys
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from dataclasses import dataclass, field, asdict

# Import enhancements and modules
sys.path.append('/home/ubuntu/nexus_project')
from knowledge_validation_enhancements import ValidationContext, ValidationLogger, ValidatedKnowledgeUnit
from source_credibility_assessment import SourceCredibilityAssessment
from cross_reference_verification import CrossReferenceVerification
from temporal_relevance_checker import TemporalRelevanceChecker
from truth_engine_wrapper import TruthEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/nexus_project/knowledge_validation/logs/validation_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class KnowledgeValidationSystem:
    """
    Integrated Knowledge Validation System for Kali Ka.
    
    This system coordinates all specialized validation modules and the Truth Engine
    to provide comprehensive validation of knowledge units.
    """
    
    def __init__(self, 
                 config_path: str = None,
                 validation_dir: str = "/home/ubuntu/nexus_project/knowledge_validation"):
        """
        Initialize the Knowledge Validation System.
        
        Args:
            config_path: Path to configuration file
            validation_dir: Directory for validation files
        """
        # Set up validation directory
        self.validation_dir = validation_dir
        os.makedirs(os.path.join(validation_dir, "logs"), exist_ok=True)
        os.makedirs(os.path.join(validation_dir, "verified"), exist_ok=True)
        os.makedirs(os.path.join(validation_dir, "unverified"), exist_ok=True)
        os.makedirs(os.path.join(validation_dir, "truth_trails"), exist_ok=True)
        
        # Set up logger
        self.logger = ValidationLogger(os.path.join(validation_dir, "logs"))
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize validation modules
        self.source_credibility_assessor = SourceCredibilityAssessment(
            config_path=None, logger=self.logger
        )
        
        self.cross_reference_verifier = CrossReferenceVerification(
            config_path=None, logger=self.logger
        )
        
        self.temporal_relevance_checker = TemporalRelevanceChecker(
            config_path=None, logger=self.logger
        )
        
        # Initialize Truth Engine
        self.truth_engine = TruthEngine()
        
        # Statistics
        self.stats = {
            'total_validations': 0,
            'verified_units': 0,
            'unverified_units': 0,
            'avg_validation_duration': 0.0,
            'validation_results': {
                'high_confidence': 0,
                'medium_confidence': 0,
                'low_confidence': 0,
                'rejected': 0
            }
        }
    
    def _load_config(self, config_path: str = None) -> Dict[str, Any]:
        """
        Load configuration from file or use default.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        default_config = {
            'validation_thresholds': {
                'high_confidence': 0.8,
                'medium_confidence': 0.6,
                'low_confidence': 0.4,
                'rejection': 0.2
            },
            'module_weights': {
                'source_credibility': 0.3,
                'cross_reference': 0.3,
                'temporal_relevance': 0.2,
                'truth_engine': 0.2
            },
            'truth_trail_options': {
                'generate_hash': True,
                'store_full_trail': True,
                'include_validation_context': True
            }
        }
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    # Merge with default config
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                return config
            except Exception as e:
                logger.error(f"Error loading configuration: {str(e)}")
                return default_config
        else:
            return default_config
    
    def validate_knowledge_unit(self, knowledge_unit: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a knowledge unit using all validation modules.
        
        Args:
            knowledge_unit: The knowledge unit to validate
            
        Returns:
            Validation result
        """
        # Create validation context
        context = ValidationContext(knowledge_unit=knowledge_unit)
        
        # Log validation start
        unit_id = knowledge_unit.get('uuid', 'unknown')
        self.logger.log_validation_start(unit_id)
        self.logger.log_info(f"Starting validation for knowledge unit: {unit_id}")
        
        try:
            # Update statistics
            self.stats['total_validations'] += 1
            
            # Step 1: Assess source credibility
            self.logger.log_validation_step("1", "Assessing source credibility")
            source_info = knowledge_unit.get('source', {})
            context.credibility_result = self.assess_source_credibility(source_info, context)
            
            # Step 2: Verify cross-references
            self.logger.log_validation_step("2", "Verifying cross-references")
            content = knowledge_unit.get('content', '')
            domain = knowledge_unit.get('domain', {}).get('primary', 'default')
            context.cross_reference_result = self.verify_cross_references(content, domain, context)
            
            # Step 3: Check temporal relevance
            self.logger.log_validation_step("3", "Checking temporal relevance")
            context.temporal_result = self.check_temporal_relevance(knowledge_unit, context)
            
            # Step 4: Verify with Truth Engine
            self.logger.log_validation_step("4", "Verifying with Truth Engine")
            context.truth_engine_result = self.verify_with_truth_engine(knowledge_unit, context)
            
            # Step 5: Generate truth trail
            self.logger.log_validation_step("5", "Generating truth trail")
            context.truth_trail = self.generate_truth_trail(knowledge_unit, context)
            
            # Step 6: Synthesize validation results
            self.logger.log_validation_step("6", "Synthesizing validation results")
            context.validation_result = self.synthesize_validation_results(context)
            
            # Step 7: Determine validation status
            self.logger.log_validation_step("7", "Determining validation status")
            context.validation_status = self.determine_validation_status(context.validation_result)
            
            # Step 8: Save validation result
            self.logger.log_validation_step("8", "Saving validation result")
            self._save_validation_result(unit_id, context)
            
            # Update statistics
            if context.validation_status == 'verified':
                self.stats['verified_units'] += 1
            else:
                self.stats['unverified_units'] += 1
            
            confidence_level = context.validation_result.get('confidence_level', 'low')
            self.stats['validation_results'][confidence_level] += 1
            
            # Complete validation
            context.complete_validation()
            
            # Update average validation duration
            total_validations = self.stats['total_validations']
            if total_validations <= 1:
                self.stats['avg_validation_duration'] = context.validation_duration
            else:
                self.stats['avg_validation_duration'] = (
                    (self.stats['avg_validation_duration'] * (total_validations - 1) + 
                     context.validation_duration) / total_validations
                )
            
            # Log validation completion
            self.logger.log_validation_complete(
                unit_id, context.validation_status, context.validation_duration
            )
            
            return context.validation_result
            
        except Exception as e:
            self.logger.log_error(f"Validation failed: {str(e)}")
            
            # Complete validation with error
            context.validation_status = 'error'
            context.complete_validation()
            
            # Return error result
            return {
                'validation_status': 'error',
                'confidence_score': 0.0,
                'confidence_level': 'rejected',
                'error': str(e)
            }
    
    def assess_source_credibility(self, source: Dict[str, Any], context: ValidationContext) -> Dict[str, Any]:
        """
        Assess the credibility of a knowledge source.
        
        Args:
            source: Source information
            context: Validation context
            
        Returns:
            Source credibility assessment result
        """
        try:
            return self.source_credibility_assessor.assess_source_credibility(source, context)
        except Exception as e:
            self.logger.log_error(f"Source credibility assessment failed: {str(e)}")
            return {
                'source_type': 'unknown',
                'credibility_score': 0.5,
                'error': str(e)
            }
    
    def verify_cross_references(self, content: str, domain: str, context: ValidationContext) -> Dict[str, Any]:
        """
        Verify content by cross-referencing with other sources.
        
        Args:
            content: Content to verify
            domain: Knowledge domain
            context: Validation context
            
        Returns:
            Cross-reference verification result
        """
        try:
            return self.cross_reference_verifier.verify_cross_references(content, domain, context)
        except Exception as e:
            self.logger.log_error(f"Cross-reference verification failed: {str(e)}")
            return {
                'consensus_confidence': 0.5,
                'contradiction_flags': [],
                'error': str(e)
            }
    
    def check_temporal_relevance(self, knowledge_unit: Dict[str, Any], context: ValidationContext) -> Dict[str, Any]:
        """
        Check the temporal relevance of a knowledge unit.
        
        Args:
            knowledge_unit: Knowledge unit to check
            context: Validation context
            
        Returns:
            Temporal relevance check result
        """
        try:
            return self.temporal_relevance_checker.check_temporal_relevance(knowledge_unit, context)
        except Exception as e:
            self.logger.log_error(f"Temporal relevance check failed: {str(e)}")
            return {
                'temporal_validity': 'unknown',
                'freshness_score': 0.5,
                'error': str(e)
            }
    
    def verify_with_truth_engine(self, knowledge_unit: Dict[str, Any], context: ValidationContext) -> Dict[str, Any]:
        """
        Verify a knowledge unit with the Truth Engine.
        
        Args:
            knowledge_unit: Knowledge unit to verify
            context: Validation context
            
        Returns:
            Truth Engine verification result
        """
        try:
            # Verify with Truth Engine
            verification_result = self.truth_engine.verify_knowledge_unit(knowledge_unit)
            
            # Extract verification score
            verification_score = verification_result.get('confidence', 0.5)
            
            # Create result
            result = {
                'verification_score': verification_score,
                'verification_details': verification_result,
                'verification_confidence': verification_score
            }
            
            return result
        except Exception as e:
            self.logger.log_error(f"Truth Engine verification failed: {str(e)}")
            return {
                'verification_score': 0.5,
                'error': str(e)
            }
    
    def generate_truth_trail(self, knowledge_unit: Dict[str, Any], context: ValidationContext) -> Dict[str, Any]:
        """
        Generate a truth trail for a knowledge unit.
        
        Args:
            knowledge_unit: Knowledge unit
            context: Validation context
            
        Returns:
            Truth trail
        """
        try:
            # Extract unit ID
            unit_id = knowledge_unit.get('uuid', 'unknown')
            
            # Create truth trail
            truth_trail = {
                'unit_id': unit_id,
                'timestamp': datetime.now().isoformat(),
                'validation_modules': {
                    'source_credibility': {
                        'score': context.credibility_result.get('credibility_score', 0.0),
                        'source_type': context.credibility_result.get('source_type', 'unknown')
                    },
                    'cross_reference': {
                        'score': context.cross_reference_result.get('consensus_confidence', 0.0),
                        'contradictions': len(context.cross_reference_result.get('contradiction_flags', []))
                    },
                    'temporal_relevance': {
                        'score': context.temporal_result.get('freshness_score', 0.0),
                        'validity': context.temporal_result.get('temporal_validity', 'unknown')
                    },
                    'truth_engine': {
                        'score': context.truth_engine_result.get('verification_score', 0.0)
                    }
                }
            }
            
            # Include validation context if configured
            if self.config['truth_trail_options'].get('include_validation_context', True):
                truth_trail['validation_context'] = {
                    'start_time': context.validation_start_time,
                    'end_time': time.time(),
                    'duration': time.time() - context.validation_start_time
                }
            
            # Generate hash if configured
            if self.config['truth_trail_options'].get('generate_hash', True):
                import hashlib
                
                # Create hash input
                hash_input = f"{unit_id}:{truth_trail['timestamp']}:{truth_trail['validation_modules']}"
                
                # Generate hash
                truth_trail['hash'] = hashlib.sha256(hash_input.encode()).hexdigest()
            
            # Save truth trail if configured
            if self.config['truth_trail_options'].get('store_full_trail', True):
                trail_path = os.path.join(self.validation_dir, "truth_trails", f"{unit_id}.json")
                with open(trail_path, 'w') as f:
                    json.dump(truth_trail, f, indent=2)
            
            return truth_trail
        except Exception as e:
            self.logger.log_error(f"Truth trail generation failed: {str(e)}")
            return {
                'unit_id':
(Content truncated due to size limit. Use line ranges to read in chunks)