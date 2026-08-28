"""
Enhanced Academic Source Evaluation Module for Kali Ka

This module implements the improved academic source evaluation component
of the Source Credibility Assessment system, featuring:
- Field-normalized impact factor assessment
- Fuzzy publisher matching with fallback mechanisms
- Specialized handling for repositories and non-traditional sources
- Citation metrics and peer review quality indicators

Author: Manus
Date: April 14, 2025
"""

import os
import sys
import json
import math
import logging
import statistics
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from dataclasses import dataclass, field, asdict
from urllib.parse import urlparse
from fuzzywuzzy import fuzz, process

# Import enhancements
sys.path.append('/home/ubuntu/nexus_project')
from knowledge_validation_enhancements import ValidationContext, ValidationLogger

# Configure logging
logger = logging.getLogger(__name__)

class AcademicSourceEvaluation:
    """
    Enhanced academic source evaluation for Kali Ka's knowledge validation system.
    """
    
    def __init__(self, config_path=None, logger=None):
        """
        Initialize academic source evaluation.
        
        Args:
            config_path: Path to configuration file
            logger: ValidationLogger instance
        """
        # Set up logger
        self.logger = logger or ValidationLogger()
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Load academic publisher database
        self.publisher_db = self._load_publisher_database()
        
        # Load field-specific impact factor data
        self.field_impact_factors = self._load_field_impact_factors()
        
        # Initialize repository handlers
        self.repository_handlers = self._initialize_repository_handlers()
    
    def _load_config(self, config_path=None):
        """
        Load configuration from file or use default.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        default_config = {
            "academic": {
                "publisher_db_path": "/home/ubuntu/nexus_project/knowledge_validation/academic_publishers.json",
                "field_impact_factors_path": "/home/ubuntu/nexus_project/knowledge_validation/field_impact_factors.json",
                "weights": {
                    "impact_factor": 0.30,
                    "publisher_reputation": 0.25,
                    "author_history": 0.20,
                    "publication_date": 0.15,
                    "peer_reviewed": 0.10
                },
                "matching": {
                    "publisher_match_threshold": 80,  # Fuzzy matching threshold
                    "title_match_threshold": 85
                },
                "temporal": {
                    "recency_grace_period": 365,  # Days
                    "max_age_penalty": 0.3,
                    "field_specific_decay_rates": {
                        "computer_science": 0.15,  # Per year
                        "cybersecurity": 0.30,
                        "ai_ethics": 0.20,
                        "medicine": 0.25,
                        "physics": 0.05,
                        "mathematics": 0.02,
                        "philosophy": 0.01,
                        "default": 0.10
                    }
                }
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
                self.logger.log_error(f"Error loading configuration: {str(e)}")
                return default_config
        else:
            return default_config
    
    def _load_publisher_database(self):
        """
        Load academic publisher database.
        
        Returns:
            Publisher database dictionary
        """
        db_path = self.config["academic"]["publisher_db_path"]
        
        # Create default database if path doesn't exist
        if not os.path.exists(db_path):
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            default_db = {
                "publishers": {
                    "nature": {
                        "name": "Nature Publishing Group",
                        "reputation_score": 0.95,
                        "peer_review_quality": 0.98,
                        "impact_factor": 49.96,
                        "journals": [
                            {"name": "Nature", "impact_factor": 49.96},
                            {"name": "Nature Medicine", "impact_factor": 36.13},
                            {"name": "Nature Biotechnology", "impact_factor": 31.86}
                        ]
                    },
                    "science": {
                        "name": "American Association for the Advancement of Science",
                        "reputation_score": 0.94,
                        "peer_review_quality": 0.97,
                        "impact_factor": 41.84,
                        "journals": [
                            {"name": "Science", "impact_factor": 41.84},
                            {"name": "Science Advances", "impact_factor": 13.12},
                            {"name": "Science Translational Medicine", "impact_factor": 16.30}
                        ]
                    },
                    "elsevier": {
                        "name": "Elsevier",
                        "reputation_score": 0.88,
                        "peer_review_quality": 0.85,
                        "impact_factor": 4.76,
                        "journals": [
                            {"name": "Cell", "impact_factor": 38.64},
                            {"name": "The Lancet", "impact_factor": 79.32},
                            {"name": "Neuron", "impact_factor": 14.32}
                        ]
                    },
                    "ieee": {
                        "name": "Institute of Electrical and Electronics Engineers",
                        "reputation_score": 0.90,
                        "peer_review_quality": 0.87,
                        "impact_factor": 5.63,
                        "journals": [
                            {"name": "IEEE Transactions on Pattern Analysis and Machine Intelligence", "impact_factor": 16.39},
                            {"name": "IEEE Journal on Selected Areas in Communications", "impact_factor": 11.42},
                            {"name": "IEEE Transactions on Neural Networks and Learning Systems", "impact_factor": 10.45}
                        ]
                    },
                    "acm": {
                        "name": "Association for Computing Machinery",
                        "reputation_score": 0.89,
                        "peer_review_quality": 0.86,
                        "impact_factor": 7.23,
                        "journals": [
                            {"name": "Journal of the ACM", "impact_factor": 6.81},
                            {"name": "Communications of the ACM", "impact_factor": 4.03},
                            {"name": "ACM Computing Surveys", "impact_factor": 14.32}
                        ]
                    },
                    "springer": {
                        "name": "Springer Nature",
                        "reputation_score": 0.87,
                        "peer_review_quality": 0.84,
                        "impact_factor": 3.87,
                        "journals": [
                            {"name": "Journal of Machine Learning Research", "impact_factor": 5.71},
                            {"name": "Artificial Intelligence", "impact_factor": 9.09},
                            {"name": "Machine Learning", "impact_factor": 4.68}
                        ]
                    },
                    "oxford": {
                        "name": "Oxford University Press",
                        "reputation_score": 0.91,
                        "peer_review_quality": 0.89,
                        "impact_factor": 6.42,
                        "journals": [
                            {"name": "Bioinformatics", "impact_factor": 6.93},
                            {"name": "Brain", "impact_factor": 13.50},
                            {"name": "Nucleic Acids Research", "impact_factor": 16.97}
                        ]
                    },
                    "wiley": {
                        "name": "John Wiley & Sons",
                        "reputation_score": 0.85,
                        "peer_review_quality": 0.82,
                        "impact_factor": 3.45,
                        "journals": [
                            {"name": "Advanced Materials", "impact_factor": 27.40},
                            {"name": "Angewandte Chemie", "impact_factor": 12.96},
                            {"name": "Advanced Functional Materials", "impact_factor": 16.84}
                        ]
                    },
                    "arxiv": {
                        "name": "arXiv (Cornell University)",
                        "reputation_score": 0.75,
                        "peer_review_quality": 0.30,  # Limited peer review
                        "impact_factor": None,  # Not applicable
                        "is_repository": True,
                        "repository_type": "preprint"
                    },
                    "biorxiv": {
                        "name": "bioRxiv (Cold Spring Harbor Laboratory)",
                        "reputation_score": 0.72,
                        "peer_review_quality": 0.25,  # Limited peer review
                        "impact_factor": None,  # Not applicable
                        "is_repository": True,
                        "repository_type": "preprint"
                    },
                    "pubmed": {
                        "name": "PubMed (National Library of Medicine)",
                        "reputation_score": 0.85,
                        "peer_review_quality": 0.80,
                        "impact_factor": None,  # Aggregator
                        "is_repository": True,
                        "repository_type": "aggregator"
                    }
                },
                "universities": {
                    "harvard": {
                        "name": "Harvard University",
                        "reputation_score": 0.95,
                        "research_quality": 0.96
                    },
                    "mit": {
                        "name": "Massachusetts Institute of Technology",
                        "reputation_score": 0.94,
                        "research_quality": 0.95
                    },
                    "stanford": {
                        "name": "Stanford University",
                        "reputation_score": 0.93,
                        "research_quality": 0.94
                    },
                    "cambridge": {
                        "name": "University of Cambridge",
                        "reputation_score": 0.92,
                        "research_quality": 0.93
                    },
                    "oxford": {
                        "name": "University of Oxford",
                        "reputation_score": 0.92,
                        "research_quality": 0.93
                    }
                }
            }
            
            with open(db_path, 'w') as f:
                json.dump(default_db, f, indent=2)
            
            return default_db
        
        # Load existing database
        try:
            with open(db_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.log_error(f"Error loading publisher database: {str(e)}")
            return {"publishers": {}, "universities": {}}
    
    def _load_field_impact_factors(self):
        """
        Load field-specific impact factor data.
        
        Returns:
            Field impact factor dictionary
        """
        field_if_path = self.config["academic"]["field_impact_factors_path"]
        
        # Create default field impact factors if path doesn't exist
        if not os.path.exists(field_if_path):
            os.makedirs(os.path.dirname(field_if_path), exist_ok=True)
            
            default_field_ifs = {
                "computer_science": {
                    "median": 2.5,
                    "top_quartile": 4.8,
                    "top_decile": 8.2,
                    "max": 16.4
                },
                "medicine": {
                    "median": 3.2,
                    "top_quartile": 6.5,
                    "top_decile": 12.8,
                    "max": 79.3
                },
                "physics": {
                    "median": 2.8,
                    "top_quartile": 5.2,
                    "top_decile": 9.6,
                    "max": 50.0
                },
                "biology": {
                    "median": 3.5,
                    "top_quartile": 7.2,
                    "top_decile": 14.5,
                    "max": 38.6
                },
                "chemistry": {
                    "median": 3.0,
                    "top_quartile": 6.0,
                    "top_decile": 12.0,
                    "max": 27.4
                },
                "mathematics": {
                    "median": 1.2,
                    "top_quartile": 2.5,
                    "top_decile": 4.0,
                    "max": 6.8
                },
                "social_sciences": {
                    "median": 1.8,
                    "top_quartile": 3.6,
                    "top_decile": 6.5,
                    "max": 12.0
                },
                "humanities": {
                    "median": 0.8,
                    "top_quartile": 1.5,
                    "top_decile": 2.8,
                    "max": 5.0
                },
                "engineering": {
                    "median": 2.2,
                    "top_quartile": 4.0,
                    "top_decile": 7.5,
                    "max": 14.0
                },
                "ai_ethics": {
                    "median": 2.8,
                    "top_quartile": 5.5,
                    "top_decile": 10.0,
                    "max": 15.0
                },
                "cybersecurity": {
                    "median": 2.6,
                    "top_quartile": 5.0,
                    "top_decile": 9.0,
                    "max": 14.0
                },
                "default": {
                    "median": 2.0,
                    "top_quartile": 4.0,
                    "top_decile": 8.0,
                    "max": 20.0
                }
            }
            
            with open(field_if_path, 'w') as f:
                json.dump(default_field_ifs, f, indent=2)
            
            return default_field_ifs
        
        # Load existing field impact factors
        try:
            with open(field_if_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.log_error(f"Error loading field impact factors: {str(e)}")
            return {"default": {"median": 2.0, "top_quartile": 4.0, "top_decile": 8.0, "max": 20.0}}
    
    def _initialize_repository_handlers(self):
        """
        Initialize specialized handlers for academic repositories.
        
        Returns:
            Dictionary of repository handlers
        """
        return {
            "arxiv": self._handle_arxiv,
            "biorxiv": self._handle_biorxiv,
            "pubmed": self._handle_pubmed,
            "defaul
(Content truncated due to size limit. Use line ranges to read in chunks)