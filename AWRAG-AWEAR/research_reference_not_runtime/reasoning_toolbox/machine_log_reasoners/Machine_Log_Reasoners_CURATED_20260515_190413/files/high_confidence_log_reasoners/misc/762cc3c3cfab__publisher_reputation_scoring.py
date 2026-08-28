"""
Publisher Reputation Scoring System for Kali Ka

This module implements a robust publisher reputation scoring system
for the Source Credibility Assessment module, featuring:
- Hierarchical publisher database with imprints and journals
- Fuzzy matching for publisher recognition
- Automatic reputation discovery for new sources
- Domain-specific publisher authority recognition

Author: Manus
Date: April 14, 2025
"""

import os
import sys
import json
import re
import logging
import requests
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from urllib.parse import urlparse
from fuzzywuzzy import fuzz, process

# Import enhancements
sys.path.append('/home/ubuntu/nexus_project')
from knowledge_validation_enhancements import ValidationContext, ValidationLogger

# Configure logging
logger = logging.getLogger(__name__)

class PublisherDatabase:
    """
    Hierarchical publisher database with reputation scoring.
    """
    
    def __init__(self, db_path=None, logger=None):
        """
        Initialize the publisher database.
        
        Args:
            db_path: Path to publisher database file
            logger: ValidationLogger instance
        """
        # Set up logger
        self.logger = logger or ValidationLogger()
        
        # Set database path
        self.db_path = db_path or os.path.join(
            os.path.dirname(__file__), 
            'knowledge_validation', 
            'publisher_database.json'
        )
        
        # Load database
        self.publishers = self._load_database()
        
        # Initialize domain authority mapping
        self.domain_authorities = self._initialize_domain_authorities()
        
        # Track updates
        self.last_updated = datetime.now()
        self.update_count = 0
    
    def _load_database(self):
        """
        Load publisher database from file or create default.
        
        Returns:
            Publisher database dictionary
        """
        # Create comprehensive default database
        default_db = {
            # Academic Publishers
            "elsevier": {
                "reputation": 0.85,
                "domains": ["medicine", "biology", "chemistry", "physics", "computer_science"],
                "imprints": {
                    "cell_press": {
                        "reputation": 0.90,
                        "domains": ["biology", "medicine"],
                        "journals": {
                            "cell": {"reputation": 0.95, "impact_factor": 41.5},
                            "neuron": {"reputation": 0.92, "impact_factor": 17.2},
                            "cancer_cell": {"reputation": 0.91, "impact_factor": 31.7}
                        }
                    },
                    "academic_press": {
                        "reputation": 0.82,
                        "domains": ["general"]
                    },
                    "the_lancet": {
                        "reputation": 0.95,
                        "domains": ["medicine"],
                        "journals": {
                            "the_lancet": {"reputation": 0.97, "impact_factor": 79.3},
                            "lancet_oncology": {"reputation": 0.94, "impact_factor": 41.3},
                            "lancet_neurology": {"reputation": 0.93, "impact_factor": 44.2}
                        }
                    }
                }
            },
            "springer_nature": {
                "reputation": 0.88,
                "domains": ["medicine", "biology", "physics", "computer_science", "mathematics"],
                "imprints": {
                    "nature_publishing_group": {
                        "reputation": 0.95,
                        "domains": ["biology", "medicine", "physics"],
                        "journals": {
                            "nature": {"reputation": 0.98, "impact_factor": 49.9},
                            "nature_medicine": {"reputation": 0.96, "impact_factor": 53.4},
                            "nature_biotechnology": {"reputation": 0.95, "impact_factor": 54.9},
                            "nature_reviews_genetics": {"reputation": 0.94, "impact_factor": 46.3}
                        }
                    },
                    "springer": {
                        "reputation": 0.85,
                        "domains": ["computer_science", "mathematics", "engineering"],
                        "journals": {
                            "journal_of_machine_learning_research": {"reputation": 0.90, "impact_factor": 5.8},
                            "data_mining_and_knowledge_discovery": {"reputation": 0.85, "impact_factor": 3.2}
                        }
                    }
                }
            },
            "wiley": {
                "reputation": 0.80,
                "domains": ["chemistry", "biology", "medicine", "business"],
                "journals": {
                    "angewandte_chemie": {"reputation": 0.90, "impact_factor": 15.3},
                    "advanced_materials": {"reputation": 0.89, "impact_factor": 27.4}
                }
            },
            "ieee": {
                "reputation": 0.90,
                "domains": ["computer_science", "electrical_engineering", "telecommunications"],
                "journals": {
                    "ieee_transactions_on_pattern_analysis": {"reputation": 0.92, "impact_factor": 16.4},
                    "ieee_transactions_on_neural_networks": {"reputation": 0.90, "impact_factor": 8.8},
                    "ieee_transactions_on_information_theory": {"reputation": 0.89, "impact_factor": 3.2}
                }
            },
            "acm": {
                "reputation": 0.90,
                "domains": ["computer_science", "information_technology"],
                "journals": {
                    "communications_of_the_acm": {"reputation": 0.88, "impact_factor": 4.1},
                    "journal_of_the_acm": {"reputation": 0.91, "impact_factor": 3.8},
                    "acm_computing_surveys": {"reputation": 0.92, "impact_factor": 10.3}
                }
            },
            "oxford_university_press": {
                "reputation": 0.85,
                "domains": ["humanities", "social_sciences", "medicine", "law"],
                "journals": {
                    "nucleic_acids_research": {"reputation": 0.90, "impact_factor": 16.9},
                    "brain": {"reputation": 0.89, "impact_factor": 13.5}
                }
            },
            "cambridge_university_press": {
                "reputation": 0.85,
                "domains": ["humanities", "social_sciences", "mathematics"],
                "journals": {
                    "behavioral_and_brain_sciences": {"reputation": 0.88, "impact_factor": 14.2}
                }
            },
            "mit_press": {
                "reputation": 0.90,
                "domains": ["computer_science", "cognitive_science", "economics"],
                "journals": {
                    "journal_of_cognitive_neuroscience": {"reputation": 0.87, "impact_factor": 4.5},
                    "computational_linguistics": {"reputation": 0.86, "impact_factor": 3.1}
                }
            },
            "harvard_university_press": {
                "reputation": 0.90,
                "domains": ["humanities", "social_sciences", "law", "medicine"]
            },
            "aaas": {
                "reputation": 0.95,
                "domains": ["general_science", "medicine", "biology"],
                "journals": {
                    "science": {"reputation": 0.97, "impact_factor": 47.7},
                    "science_translational_medicine": {"reputation": 0.92, "impact_factor": 17.2}
                }
            },
            
            # Technical Documentation Publishers
            "microsoft": {
                "reputation": 0.90,
                "domains": ["computer_science", "software_development", "cloud_computing"],
                "documentation_quality": 0.92,
                "update_frequency": "high"
            },
            "google": {
                "reputation": 0.90,
                "domains": ["computer_science", "software_development", "artificial_intelligence"],
                "documentation_quality": 0.91,
                "update_frequency": "high"
            },
            "apple": {
                "reputation": 0.85,
                "domains": ["software_development", "mobile_development", "design"],
                "documentation_quality": 0.88,
                "update_frequency": "medium"
            },
            "amazon_web_services": {
                "reputation": 0.90,
                "domains": ["cloud_computing", "software_development", "devops"],
                "documentation_quality": 0.90,
                "update_frequency": "high"
            },
            "mozilla": {
                "reputation": 0.88,
                "domains": ["web_development", "browser_technologies"],
                "documentation_quality": 0.93,
                "update_frequency": "high"
            },
            "w3c": {
                "reputation": 0.95,
                "domains": ["web_standards", "web_development"],
                "documentation_quality": 0.95,
                "update_frequency": "medium"
            },
            "nist": {
                "reputation": 0.95,
                "domains": ["cybersecurity", "standards", "computer_science"],
                "documentation_quality": 0.94,
                "update_frequency": "medium"
            },
            "iso": {
                "reputation": 0.92,
                "domains": ["standards", "quality_management", "security"],
                "documentation_quality": 0.90,
                "update_frequency": "low"
            },
            "ietf": {
                "reputation": 0.93,
                "domains": ["internet_standards", "networking", "protocols"],
                "documentation_quality": 0.92,
                "update_frequency": "medium"
            }
        }
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Try to load existing database
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f:
                    db = json.load(f)
                    self.logger.log_info(f"Loaded publisher database with {len(db)} publishers")
                    return db
            except Exception as e:
                self.logger.log_error(f"Error loading publisher database: {str(e)}")
                # Fall back to default database
        
        # Save default database
        try:
            with open(self.db_path, 'w') as f:
                json.dump(default_db, f, indent=2)
            self.logger.log_info(f"Created default publisher database with {len(default_db)} publishers")
        except Exception as e:
            self.logger.log_error(f"Error saving publisher database: {str(e)}")
        
        return default_db
    
    def _initialize_domain_authorities(self):
        """
        Initialize mapping of domains to authoritative publishers.
        
        Returns:
            Dictionary mapping domains to lists of authoritative publishers
        """
        domain_authorities = {}
        
        # Process all publishers
        for publisher_name, publisher_data in self.publishers.items():
            # Get domains for this publisher
            domains = publisher_data.get("domains", [])
            
            # Add publisher to each domain's authorities
            for domain in domains:
                if domain not in domain_authorities:
                    domain_authorities[domain] = []
                
                # Add with reputation score
                domain_authorities[domain].append({
                    "name": publisher_name,
                    "reputation": publisher_data["reputation"]
                })
        
        # Sort authorities by reputation for each domain
        for domain, authorities in domain_authorities.items():
            domain_authorities[domain] = sorted(
                authorities, 
                key=lambda x: x["reputation"], 
                reverse=True
            )
        
        return domain_authorities
    
    def save_database(self):
        """
        Save the publisher database to file.
        """
        try:
            with open(self.db_path, 'w') as f:
                json.dump(self.publishers, f, indent=2)
            self.logger.log_info(f"Saved publisher database with {len(self.publishers)} publishers")
        except Exception as e:
            self.logger.log_error(f"Error saving publisher database: {str(e)}")
    
    def get_publisher(self, publisher_name):
        """
        Get publisher data by name.
        
        Args:
            publisher_name: Publisher name
            
        Returns:
            Publisher data dictionary or None if not found
        """
        if not publisher_name:
            return None
        
        # Normalize name
        normalized_name = publisher_name.lower().strip()
        
        # Exact match
        if normalized_name in self.publishers:
            return self.publishers[normalized_name]
        
        # Try fuzzy matching
        best_match, score = self.match_publisher(publisher_name)
        if best_match and score > 0.8:  # 80% confidence threshold
            return self.publishers[best_match]
        
        return None
    
    def match_publisher(self, publisher_name):
        """
        Match publisher using fuzzy matching with fallbacks.
        
        Args:
            publisher_name: Publisher name to match
            
        Returns:
            Tuple of (matched_publisher, match_score)
        """
        if not publisher_name:
            return None, 0.0
        
        # Normalize publisher name
        normalized_name = publisher_name.lower().strip()
        
        # Exact match
        if normalized_name in self.publishers:
            return normalized_name, 1.0
        
        # Try substring matching
        for db_name in self.publishers:
            if db_name in normalized_name or normalized_name in db_name:
                # Calculate match quality based on length ratio
                match_ratio = min(len(db_name), len(normalized_name)) / max(len(db_name), len(normalized_name))
                if match_ratio > 0.7:  # Threshold for substring match
                    return db_name, match_ratio
        
        # Try fuzzy matching
        best_match = None
        best_score = 0
        
        for db_name in self.publishers:
            score = fuzz.ratio(normalized_name, db_name.lower())
            if score > 80 and score > best_score:  # Threshold for fuzzy match
                best_match = db_name
                best_score = score
        
        if best_match:
            return best_match, best_score / 100.0
        
        # No match found
        return None, 0.0
    
    def get_journal(self, publisher_name, journal_name):
        """
        Get journal data by publisher and journal name.
        
        Args:
            publisher_name: Publisher name
            journal_name: Journal name
            
        Returns:
            Journal data dictionary or None if not found
        """
        if not publisher_name or not journal_name:
            return None
        
        # Normalize names
        publisher_name = publisher_name.lower().strip()
        journal_name = journal_name.lower().strip()
        
        # Get publisher
        publisher_data = self.get_publisher(publisher_name)
        if not publisher_data:
            return None
        
        # Check direct journals
        journals = publisher_data.get("journals", {})
        for j_name, j_data in journals.items():
            if fuzz.ratio(journal_name, j_nam
(Content truncated due to size limit. Use line ranges to read in chunks)