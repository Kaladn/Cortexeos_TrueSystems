"""
Temporal Relevance Checking Module for Kali Ka - "The Time Oracle"

This module evaluates the freshness and validity period of knowledge based on
domain-specific requirements, identifies outdated information, and applies
appropriate decay functions to confidence scores.

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

# Import enhancements
sys.path.append('/home/ubuntu/nexus_project')
from knowledge_validation_enhancements import ValidationContext, ValidationLogger

# Configure logging
logger = logging.getLogger(__name__)

class TemporalRelevanceChecker:
    """
    The Time Oracle: Checks the temporal relevance of knowledge.
    
    This module tags knowledge with temporal validity periods, identifies outdated
    information, and applies domain-specific freshness requirements.
    """
    
    def __init__(self, 
                 config_path: str = None, 
                 logger: ValidationLogger = None):
        """
        Initialize the Temporal Relevance Checker module.
        
        Args:
            config_path: Path to configuration file
            logger: ValidationLogger instance
        """
        # Set up logger
        self.logger = logger or ValidationLogger()
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize domain freshness rules
        self.domain_freshness_rules = self.config.get('domain_freshness_rules', {})
        
        # Initialize temporal validity calculator
        self.validity_calculator = TemporalValidityCalculator(self.domain_freshness_rules)
        
        # Initialize freshness evaluator
        self.freshness_evaluator = FreshnessEvaluator(self.config.get('freshness_thresholds', {}))
        
        # Initialize refresh action recommender
        self.refresh_recommender = RefreshActionRecommender(self.config.get('refresh_thresholds', {}))
        
        # Statistics
        self.stats = {
            'total_checks': 0,
            'outdated_knowledge': 0,
            'current_knowledge': 0,
            'future_knowledge': 0,
            'avg_freshness_score': 0.0,
            'domain_freshness': {},
            'refresh_recommendations': {
                'immediate': 0,
                'high_priority': 0,
                'medium_priority': 0,
                'low_priority': 0,
                'no_action': 0
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
            'domain_freshness_rules': {
                # Domain: (validity_period_days, grace_period_days)
                'security': (365, 30),  # 1 year validity, 30 days grace
                'cybersecurity': (180, 15),  # 6 months validity, 15 days grace
                'cryptography': (730, 60),  # 2 years validity, 60 days grace
                'ai_ethics': (730, 90),  # 2 years validity, 90 days grace
                'machine_learning': (365, 60),  # 1 year validity, 60 days grace
                'computer_science': (1825, 180),  # 5 years validity, 180 days grace
                'mathematics': (3650, 365),  # 10 years validity, 365 days grace
                'physics': (3650, 365),  # 10 years validity, 365 days grace
                'medicine': (730, 90),  # 2 years validity, 90 days grace
                'law': (365, 30),  # 1 year validity, 30 days grace
                'default': (730, 90)  # 2 years validity, 90 days grace
            },
            'freshness_thresholds': {
                'high_freshness': 0.8,
                'medium_freshness': 0.5,
                'low_freshness': 0.3
            },
            'refresh_thresholds': {
                'immediate_refresh': 0.2,
                'high_priority_refresh': 0.4,
                'medium_priority_refresh': 0.6,
                'low_priority_refresh': 0.8
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
    
    def check_temporal_relevance(self, knowledge_unit: Dict[str, Any], context: ValidationContext = None) -> Dict[str, Any]:
        """
        Check the temporal relevance of a knowledge unit.
        
        Args:
            knowledge_unit: The knowledge unit to check
            context: ValidationContext instance (optional)
            
        Returns:
            Temporal relevance check result
        """
        self.logger.log_info(f"Checking temporal relevance for knowledge unit: {knowledge_unit.get('uuid', 'unknown')}")
        
        # Update statistics
        self.stats['total_checks'] += 1
        
        try:
            # Extract domain and temporal information
            domain_info = knowledge_unit.get('domain', {})
            temporal_info = knowledge_unit.get('temporal', {})
            
            # Get primary domain
            domain = domain_info.get('primary', 'default')
            
            # Extract timestamps
            created_timestamp = temporal_info.get('created', '')
            valid_from_timestamp = temporal_info.get('valid_from', '')
            valid_until_timestamp = temporal_info.get('valid_until', '')
            last_updated_timestamp = temporal_info.get('last_updated', '')
            
            # Calculate temporal validity
            validity_result = self.validity_calculator.calculate_validity(
                domain, created_timestamp, valid_from_timestamp, valid_until_timestamp, last_updated_timestamp
            )
            
            # Evaluate freshness
            freshness_result = self.freshness_evaluator.evaluate_freshness(
                domain, validity_result
            )
            
            # Recommend refresh action
            refresh_result = self.refresh_recommender.recommend_action(
                domain, freshness_result
            )
            
            # Update statistics
            self._update_statistics(domain, validity_result, freshness_result, refresh_result)
            
            # Create result
            result = {
                'temporal_validity': validity_result['validity_period'],
                'freshness_score': freshness_result['freshness_score'],
                'recommended_refresh_action': refresh_result['action'],
                'validity_details': {
                    'valid_from': validity_result['valid_from'],
                    'valid_until': validity_result['valid_until'],
                    'is_current': validity_result['is_current'],
                    'days_until_expiry': validity_result['days_until_expiry'],
                    'days_since_creation': validity_result['days_since_creation'],
                    'days_since_update': validity_result['days_since_update']
                },
                'domain_specific_rules': {
                    'domain': domain,
                    'validity_period_days': validity_result['validity_period_days'],
                    'grace_period_days': validity_result['grace_period_days']
                }
            }
            
            self.logger.log_info(f"Temporal relevance check complete. Freshness score: {freshness_result['freshness_score']:.2f}")
            
            return result
            
        except Exception as e:
            self.logger.log_error(f"Temporal relevance check failed: {str(e)}")
            
            # Return default result on error
            return {
                'temporal_validity': "unknown",
                'freshness_score': 0.5,  # Default score
                'recommended_refresh_action': None,
                'error': str(e)
            }
    
    def _update_statistics(self, 
                         domain: str, 
                         validity_result: Dict[str, Any],
                         freshness_result: Dict[str, Any],
                         refresh_result: Dict[str, Any]) -> None:
        """
        Update statistics based on check results.
        
        Args:
            domain: Knowledge domain
            validity_result: Temporal validity result
            freshness_result: Freshness evaluation result
            refresh_result: Refresh action recommendation
        """
        # Update temporal status counts
        if validity_result['is_current']:
            self.stats['current_knowledge'] += 1
        elif validity_result['days_until_expiry'] < 0:
            self.stats['outdated_knowledge'] += 1
        else:
            self.stats['future_knowledge'] += 1
        
        # Update average freshness score
        total_checks = self.stats['total_checks']
        if total_checks <= 1:
            self.stats['avg_freshness_score'] = freshness_result['freshness_score']
        else:
            self.stats['avg_freshness_score'] = (
                (self.stats['avg_freshness_score'] * (total_checks - 1) + 
                 freshness_result['freshness_score']) / total_checks
            )
        
        # Update domain freshness
        if domain not in self.stats['domain_freshness']:
            self.stats['domain_freshness'][domain] = {
                'count': 0,
                'avg_freshness': 0.0
            }
        
        domain_stats = self.stats['domain_freshness'][domain]
        domain_stats['count'] += 1
        
        if domain_stats['count'] <= 1:
            domain_stats['avg_freshness'] = freshness_result['freshness_score']
        else:
            domain_stats['avg_freshness'] = (
                (domain_stats['avg_freshness'] * (domain_stats['count'] - 1) + 
                 freshness_result['freshness_score']) / domain_stats['count']
            )
        
        # Update refresh recommendation counts
        action = refresh_result['action']
        if action == 'immediate_refresh':
            self.stats['refresh_recommendations']['immediate'] += 1
        elif action == 'high_priority_refresh':
            self.stats['refresh_recommendations']['high_priority'] += 1
        elif action == 'medium_priority_refresh':
            self.stats['refresh_recommendations']['medium_priority'] += 1
        elif action == 'low_priority_refresh':
            self.stats['refresh_recommendations']['low_priority'] += 1
        else:
            self.stats['refresh_recommendations']['no_action'] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get temporal relevance statistics.
        
        Returns:
            Temporal relevance statistics
        """
        return self.stats
    
    def print_stats(self) -> None:
        """Print temporal relevance statistics to console"""
        print("\n" + "="*50)
        print(" TEMPORAL RELEVANCE CHECKING - STATISTICS")
        print("="*50)
        
        print(f"Total checks: {self.stats['total_checks']}")
        print(f"Current knowledge: {self.stats['current_knowledge']}")
        print(f"Outdated knowledge: {self.stats['outdated_knowledge']}")
        print(f"Future knowledge: {self.stats['future_knowledge']}")
        
        print(f"\nAverage freshness score: {self.stats['avg_freshness_score']:.2f}")
        
        print("\nDomain Freshness:")
        for domain, stats in self.stats['domain_freshness'].items():
            print(f"  {domain}: {stats['avg_freshness']:.2f} ({stats['count']} units)")
        
        print("\nRefresh Recommendations:")
        for action, count in self.stats['refresh_recommendations'].items():
            print(f"  {action.replace('_', ' ').title()}: {count}")
        
        print("="*50 + "\n")


class TemporalValidityCalculator:
    """
    Calculates temporal validity periods for knowledge units.
    """
    
    def __init__(self, domain_freshness_rules: Dict[str, Tuple[int, int]]):
        """
        Initialize the Temporal Validity Calculator.
        
        Args:
            domain_freshness_rules: Domain-specific freshness rules
        """
        self.domain_freshness_rules = domain_freshness_rules
    
    def calculate_validity(self, 
                         domain: str,
                         created_timestamp: str,
                         valid_from_timestamp: str,
                         valid_until_timestamp: str,
                         last_updated_timestamp: str) -> Dict[str, Any]:
        """
        Calculate temporal validity for a knowledge unit.
        
        Args:
            domain: Knowledge domain
            created_timestamp: Creation timestamp
            valid_from_timestamp: Valid from timestamp
            valid_until_timestamp: Valid until timestamp
            last_updated_timestamp: Last updated timestamp
            
        Returns:
            Temporal validity result
        """
        # Get current time
        current_time = datetime.now()
        
        # Get domain-specific rules
        validity_period_days, grace_period_days = self.domain_freshness_rules.get(
            domain, self.domain_freshness_rules.get('default', (730, 90))
        )
        
        # Parse timestamps
        created_time = self._parse_timestamp(created_timestamp) or current_time
        valid_from_time = self._parse_timestamp(valid_from_timestamp) or created_time
        last_updated_time = self._parse_timestamp(last_updated_timestamp) or created_time
        
        # Calculate valid until time
        if valid_until_timestamp:
            valid_until_time = self._parse_timestamp(valid_until_timestamp)
        else:
            # If not specified, calculate based on domain rules
            valid_until_time = valid_from_time + timedelta(days=validity_period_days)
        
        # Calculate days since creation and update
        days_since_creation = (current_time - created_time).days
        days_since_update = (current_time - last_updated_time).days
        
        # Calculate days until expiry
        days_until_expiry = (valid_until_time - current_time).days
        
        # Determine if knowledge is current
        is_current = days_until_expiry >= -grace_period_days
        
        # Format validity period
        validity_period = f"{valid_from_time.year}-{valid_until_time.year}"
        
        return {
            'valid_from': valid_from_time.isoformat(),
            'valid_until': valid_until_time.isoformat(),
            'validity_period': validity_period,
            'is_current': is_current,
            'days_until_expiry': days_until_expiry,
            'days_since_creation': days_since_creation,
            'days_since_update': days_since_update,
            'validity_period_days': validity_period_days,
            'grace_period_days': grace_period_days
        }
    
    def _parse_timestamp(self, timestamp: str) -> Optional[datetime]:
        """
        Parse a timestamp string to datetime.
        
        Args:
            timestamp: Timestamp string
            
        Returns:
            Datetime object or None if parsing fails
        """
        if not timestamp:
            return None
        
        try:
            # Handle different timestamp formats
            if 'T' in timestamp:
                # ISO format with 
(Content truncated due to size limit. Use line ranges to read in chunks)