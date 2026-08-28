"""
Cross-Reference Verification Module for Kali Ka - "The Consensus Seeker"

This module verifies facts by cross-referencing multiple sources to establish
consensus, identify contradictions, and assign confidence scores based on
agreement levels across different sources.

Author: Manus
Date: April 9, 2025
"""

import os
import sys
import json
import time
import logging
import re
import hashlib
import nltk
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from dataclasses import dataclass, field, asdict
from collections import defaultdict, Counter

# Try to download NLTK data if not already present
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt', quiet=True)

try:
    nltk.data.find('taggers/averaged_perceptron_tagger')
except LookupError:
    nltk.download('averaged_perceptron_tagger', quiet=True)

# Import enhancements
sys.path.append('/home/ubuntu/nexus_project')
from knowledge_validation_enhancements import ValidationContext, ValidationLogger

# Configure logging
logger = logging.getLogger(__name__)

class CrossReferenceVerification:
    """
    The Consensus Seeker: Verifies facts by cross-referencing multiple sources.
    
    This module compares facts across multiple independent sources to establish
    consensus, identifies contradictions, and assigns confidence scores.
    """
    
    def __init__(self, 
                 config_path: str = None, 
                 logger: ValidationLogger = None,
                 knowledge_base_dir: str = "/home/ubuntu/nexus_project/knowledge_base"):
        """
        Initialize the Cross-Reference Verification module.
        
        Args:
            config_path: Path to configuration file
            logger: ValidationLogger instance
            knowledge_base_dir: Path to knowledge base directory
        """
        # Set up logger
        self.logger = logger or ValidationLogger()
        
        # Set up knowledge base directory
        self.knowledge_base_dir = knowledge_base_dir
        os.makedirs(knowledge_base_dir, exist_ok=True)
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize fact extraction
        self.fact_extractor = FactExtractor()
        
        # Initialize fact comparison
        self.fact_comparator = FactComparator(self.config.get('comparison_thresholds', {}))
        
        # Initialize consensus calculator
        self.consensus_calculator = ConsensusCalculator(self.config.get('consensus_weights', {}))
        
        # Initialize contradiction detector
        self.contradiction_detector = ContradictionDetector()
        
        # Initialize propagation tracer
        self.propagation_tracer = PropagationTracer()
        
        # Statistics
        self.stats = {
            'total_verifications': 0,
            'facts_extracted': 0,
            'sources_compared': 0,
            'contradictions_found': 0,
            'propagation_chains_detected': 0,
            'avg_consensus_confidence': 0.0,
            'avg_contradiction_rate': 0.0,
            'avg_sources_per_verification': 0.0
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
            'comparison_thresholds': {
                'semantic_similarity': 0.75,  # Threshold for semantic similarity
                'syntactic_similarity': 0.6,  # Threshold for syntactic similarity
                'fact_match': 0.7  # Threshold for considering facts as matching
            },
            'consensus_weights': {
                'source_credibility': 0.4,  # Weight for source credibility
                'fact_specificity': 0.3,  # Weight for fact specificity
                'source_independence': 0.3  # Weight for source independence
            },
            'contradiction_thresholds': {
                'direct_contradiction': 0.8,  # Threshold for direct contradiction
                'partial_contradiction': 0.5  # Threshold for partial contradiction
            },
            'min_sources_for_high_confidence': 3,  # Minimum sources needed for high confidence
            'max_sources_to_consider': 10  # Maximum sources to consider for a single fact
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
    
    def verify_cross_references(self, content: str, domain: str, context: ValidationContext = None) -> Dict[str, Any]:
        """
        Verify content by cross-referencing with other sources.
        
        Args:
            content: The content to verify
            domain: The knowledge domain
            context: ValidationContext instance (optional)
            
        Returns:
            Cross-reference verification result
        """
        self.logger.log_info(f"Verifying cross-references for content in domain: {domain}")
        
        # Update statistics
        self.stats['total_verifications'] += 1
        
        try:
            # Step 1: Extract facts from content
            facts = self.fact_extractor.extract_facts(content)
            self.stats['facts_extracted'] += len(facts)
            
            # Step 2: Retrieve related sources from knowledge base
            related_sources = self._retrieve_related_sources(facts, domain)
            self.stats['sources_compared'] += len(related_sources)
            self.stats['avg_sources_per_verification'] = (
                (self.stats['avg_sources_per_verification'] * (self.stats['total_verifications'] - 1) + 
                 len(related_sources)) / self.stats['total_verifications']
            )
            
            # Step 3: Compare facts with related sources
            comparison_results = self._compare_with_sources(facts, related_sources)
            
            # Step 4: Calculate consensus confidence
            consensus_confidence = self.consensus_calculator.calculate_consensus(
                facts, comparison_results, related_sources
            )
            
            # Update average consensus confidence
            self.stats['avg_consensus_confidence'] = (
                (self.stats['avg_consensus_confidence'] * (self.stats['total_verifications'] - 1) + 
                 consensus_confidence) / self.stats['total_verifications']
            )
            
            # Step 5: Detect contradictions
            contradictions = self.contradiction_detector.detect_contradictions(
                facts, comparison_results
            )
            
            # Update contradiction statistics
            if contradictions:
                self.stats['contradictions_found'] += len(contradictions)
                self.stats['avg_contradiction_rate'] = (
                    self.stats['contradictions_found'] / self.stats['total_verifications']
                )
            
            # Step 6: Trace propagation chains
            propagation_chains = self.propagation_tracer.trace_propagation(
                facts, related_sources
            )
            
            # Update propagation statistics
            if propagation_chains:
                self.stats['propagation_chains_detected'] += len(propagation_chains)
            
            # Step 7: Generate conflict map
            conflict_map = self._generate_conflict_map(contradictions)
            
            # Create result
            result = {
                'consensus_confidence': consensus_confidence,
                'contradiction_flags': [c['description'] for c in contradictions] if contradictions else [],
                'conflict_map': conflict_map,
                'propagation_root': propagation_chains[0]['root'] if propagation_chains else None,
                'sources_analyzed': len(related_sources),
                'facts_verified': len(facts),
                'verification_details': {
                    'fact_matches': sum(1 for r in comparison_results if r['match_level'] >= self.config['comparison_thresholds']['fact_match']),
                    'partial_matches': sum(1 for r in comparison_results if 0.3 <= r['match_level'] < self.config['comparison_thresholds']['fact_match']),
                    'contradictions': len(contradictions)
                }
            }
            
            self.logger.log_info(f"Cross-reference verification complete. Consensus confidence: {consensus_confidence:.2f}")
            
            return result
            
        except Exception as e:
            self.logger.log_error(f"Cross-reference verification failed: {str(e)}")
            
            # Return default result on error
            return {
                'consensus_confidence': 0.5,  # Default confidence
                'contradiction_flags': [],
                'conflict_map': {},
                'propagation_root': None,
                'error': str(e)
            }
    
    def _retrieve_related_sources(self, facts: List[Dict[str, Any]], domain: str) -> List[Dict[str, Any]]:
        """
        Retrieve related sources from the knowledge base.
        
        Args:
            facts: List of extracted facts
            domain: Knowledge domain
            
        Returns:
            List of related sources
        """
        # This is a simplified implementation that would be replaced with actual
        # knowledge base retrieval in a production environment
        
        # For now, return mock related sources
        mock_sources = [
            {
                'id': 'source_1',
                'content': "The SHA-256 algorithm generates a 256-bit hash value and is widely used in security applications.",
                'domain': 'security',
                'credibility_score': 0.85,
                'source': {
                    'url': 'https://csrc.nist.gov/publications/detail/fips/180/4/final',
                    'type': 'technical',
                    'origin': 'NIST'
                }
            },
            {
                'id': 'source_2',
                'content': "SHA-256 is a cryptographic hash function that produces a 256-bit (32-byte) hash value.",
                'domain': 'security',
                'credibility_score': 0.9,
                'source': {
                    'url': 'https://en.wikipedia.org/wiki/SHA-2',
                    'type': 'web',
                    'origin': 'Wikipedia'
                }
            },
            {
                'id': 'source_3',
                'content': "The SHA-256 algorithm is part of the SHA-2 family and creates a unique 256-bit signature for a text.",
                'domain': 'security',
                'credibility_score': 0.75,
                'source': {
                    'url': 'https://www.example.com/blog/cryptography',
                    'type': 'web',
                    'origin': 'Example Blog'
                }
            }
        ]
        
        # In a real implementation, we would filter sources based on relevance to the facts
        # and domain, and retrieve them from the knowledge base
        
        return mock_sources
    
    def _compare_with_sources(self, facts: List[Dict[str, Any]], sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Compare facts with related sources.
        
        Args:
            facts: List of extracted facts
            sources: List of related sources
            
        Returns:
            List of comparison results
        """
        comparison_results = []
        
        for fact in facts:
            for source in sources:
                # Compare fact with source content
                comparison = self.fact_comparator.compare_fact(fact, source['content'])
                
                # Add source information to comparison result
                comparison['source_id'] = source['id']
                comparison['source_credibility'] = source.get('credibility_score', 0.5)
                
                comparison_results.append(comparison)
        
        return comparison_results
    
    def _generate_conflict_map(self, contradictions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a conflict map from detected contradictions.
        
        Args:
            contradictions: List of detected contradictions
            
        Returns:
            Conflict map
        """
        if not contradictions:
            return {}
        
        conflict_map = {
            'nodes': [],
            'edges': [],
            'conflicts': []
        }
        
        # Add nodes for each fact involved in contradictions
        fact_ids = set()
        for contradiction in contradictions:
            fact_ids.add(contradiction['fact1_id'])
            fact_ids.add(contradiction['fact2_id'])
        
        for fact_id in fact_ids:
            conflict_map['nodes'].append({
                'id': fact_id,
                'type': 'fact'
            })
        
        # Add edges for each contradiction
        for i, contradiction in enumerate(contradictions):
            conflict_id = f"conflict_{i}"
            
            # Add conflict node
            conflict_map['nodes'].append({
                'id': conflict_id,
                'type': 'conflict',
                'description': contradiction['description'],
                'severity': contradiction['severity']
            })
            
            # Add edges from facts to conflict
            conflict_map['edges'].append({
                'source': contradiction['fact1_id'],
                'target': conflict_id,
                'type': 'contradicts'
            })
            
            conflict_map['edges'].append({
                'source': contradiction['fact2_id'],
                'target': conflict_id,
                'type': 'contradicts'
            })
            
            # Add to conflicts list
            conflict_map['conflicts'].append({
                'id': conflict_id,
                'fact1_id': contradiction['fact1_id'],
                'fact2_id': contradiction['fact2_id'],
                'description': contradiction['description'],
                'severity': contradiction['severity']
            })
        
        return conflict_map
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get verification statistics.
        
        Returns:
            Verification statistics
        """
        return self.stats
    
    def print_stats(self) -> None:
        """Print verification statistics to console"""
        print("\n" + "="*50)
        print(" CROSS-REFERENCE VERIFICATION - STATISTICS")
        print("="*50)
        
        print(f"Total verifications: {self.stats['total_verifications']}")
        print(f"Facts extracted: {self.stats['facts_extracted']}")
        print(f"Sources compared: {self.stats['sources_compared']}")
        print(f"Contradictions found: {self.stats['contradictions_found']}")
        print(f"Propagation chains detected: {self.stats['propagation_chains_detected']}")
        
        print("\nAverages:")
        print(f"  Consensus confidence: {self.stats['avg_consensus_confidence']:
(Content truncated due to size limit. Use line ranges to read in chunks)