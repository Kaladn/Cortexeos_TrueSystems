"""
Improved Source Credibility Assessment for Kali Ka

This module implements the improved Source Credibility Assessment module
for Kali Ka's knowledge validation system, integrating:
- Academic source evaluation
- Publisher reputation scoring
- Domain-specific credibility factors
- Technical documentation evaluation
- Dynamic credibility profiles

Author: Manus
Date: April 14, 2025
"""

import os
import sys
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union

# Import enhancements
sys.path.append('/home/ubuntu/nexus_project')
from knowledge_validation_enhancements import ValidationContext, ValidationLogger

# Import specialized evaluation modules
from academic_source_evaluation import AcademicSourceEvaluation
from publisher_reputation_scoring import PublisherReputationScoring
from domain_specific_credibility import DomainSpecificEvaluation
from technical_documentation_evaluation import TechnicalDocumentationEvaluation

# Configure logging
logger = logging.getLogger(__name__)

class CredibilityProfile:
    """
    Dynamic credibility profile for sources that evolves over time.
    """
    
    def __init__(self, source_id=None, source_name=None, profile_data=None):
        """
        Initialize credibility profile.
        
        Args:
            source_id: Unique identifier for the source
            source_name: Name of the source
            profile_data: Existing profile data (optional)
        """
        self.source_id = source_id or str(uuid.uuid4())
        self.source_name = source_name or "Unknown Source"
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at
        self.assessment_history = []
        self.domain_specific_scores = {}
        self.overall_score = 0.5  # Default score
        
        # Load existing profile data if provided
        if profile_data:
            self._load_profile_data(profile_data)
    
    def _load_profile_data(self, profile_data):
        """
        Load existing profile data.
        
        Args:
            profile_data: Existing profile data
        """
        for key, value in profile_data.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def add_assessment(self, assessment_result):
        """
        Add a new assessment to the profile history.
        
        Args:
            assessment_result: Assessment result dictionary
        """
        # Add timestamp to assessment
        assessment = assessment_result.copy()
        assessment["timestamp"] = datetime.now().isoformat()
        
        # Add to history
        self.assessment_history.append(assessment)
        
        # Update domain-specific scores
        domain = assessment.get("domain", "general")
        self.domain_specific_scores[domain] = assessment.get("final_score", assessment.get("credibility_score", 0.5))
        
        # Update overall score (weighted average of recent assessments)
        self._update_overall_score()
        
        # Update updated_at timestamp
        self.updated_at = datetime.now().isoformat()
    
    def _update_overall_score(self):
        """
        Update overall credibility score based on assessment history.
        """
        if not self.assessment_history:
            return
        
        # Get recent assessments (last 5)
        recent_assessments = self.assessment_history[-5:]
        
        # Calculate weighted average (more recent = higher weight)
        total_weight = 0
        weighted_sum = 0
        
        for i, assessment in enumerate(recent_assessments):
            # Weight increases with recency
            weight = i + 1
            total_weight += weight
            
            # Get score from assessment
            score = assessment.get("final_score", assessment.get("credibility_score", 0.5))
            
            weighted_sum += score * weight
        
        # Calculate weighted average
        self.overall_score = weighted_sum / total_weight if total_weight > 0 else 0.5
    
    def get_domain_score(self, domain):
        """
        Get credibility score for a specific domain.
        
        Args:
            domain: Knowledge domain
            
        Returns:
            Domain-specific credibility score
        """
        # Normalize domain name
        normalized_domain = domain.lower().strip() if domain else "general"
        
        # Try exact match
        if normalized_domain in self.domain_specific_scores:
            return self.domain_specific_scores[normalized_domain]
        
        # Try to find best match
        for domain_name, score in self.domain_specific_scores.items():
            if normalized_domain in domain_name or domain_name in normalized_domain:
                return score
        
        # Fall back to overall score
        return self.overall_score
    
    def to_dict(self):
        """
        Convert profile to dictionary.
        
        Returns:
            Profile as dictionary
        """
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "assessment_history": self.assessment_history,
            "domain_specific_scores": self.domain_specific_scores,
            "overall_score": self.overall_score
        }
    
    @classmethod
    def from_dict(cls, data):
        """
        Create profile from dictionary.
        
        Args:
            data: Profile data dictionary
            
        Returns:
            CredibilityProfile instance
        """
        return cls(
            source_id=data.get("source_id"),
            source_name=data.get("source_name"),
            profile_data=data
        )
    
    def save(self, directory):
        """
        Save profile to file.
        
        Args:
            directory: Directory to save profile
            
        Returns:
            Path to saved profile
        """
        # Create directory if it doesn't exist
        os.makedirs(directory, exist_ok=True)
        
        # Generate filename
        filename = os.path.join(directory, f"{self.source_id}.json")
        
        # Save profile
        with open(filename, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        
        return filename
    
    @classmethod
    def load(cls, filename):
        """
        Load profile from file.
        
        Args:
            filename: Path to profile file
            
        Returns:
            CredibilityProfile instance
        """
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            return cls.from_dict(data)
        except Exception as e:
            logger.error(f"Error loading profile: {str(e)}")
            return None


class ImprovedSourceCredibilityAssessment:
    """
    Improved Source Credibility Assessment for Kali Ka.
    """
    
    def __init__(self, config_path=None, logger=None):
        """
        Initialize improved source credibility assessment.
        
        Args:
            config_path: Path to configuration file
            logger: ValidationLogger instance
        """
        # Set up logger
        self.logger = logger or ValidationLogger()
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize specialized evaluation modules
        self.academic_evaluator = AcademicSourceEvaluation(config_path, self.logger)
        self.publisher_scoring = PublisherReputationScoring(config_path, self.logger)
        self.domain_evaluator = DomainSpecificEvaluation(config_path, self.logger)
        self.technical_evaluator = TechnicalDocumentationEvaluation(config_path, self.logger)
        
        # Initialize profile storage
        self.profile_directory = self.config.get("profile_directory", "/home/ubuntu/nexus_project/knowledge_validation/credibility_profiles")
        os.makedirs(self.profile_directory, exist_ok=True)
        
        # Load existing profiles
        self.profiles = self._load_profiles()
    
    def _load_config(self, config_path=None):
        """
        Load configuration from file or use default.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        default_config = {
            "profile_directory": "/home/ubuntu/nexus_project/knowledge_validation/credibility_profiles",
            "source_type_detection": {
                "academic_patterns": [
                    r"\.edu($|/)", r"\.ac\.[a-z]{2}($|/)", r"university", r"college",
                    r"journal", r"conference", r"proceedings", r"arxiv", r"research",
                    r"academia", r"scholar", r"sciencedirect", r"springer", r"ieee",
                    r"acm", r"pubmed", r"nature", r"science", r"elsevier", r"wiley"
                ],
                "technical_patterns": [
                    r"docs?\.([a-z0-9-]+\.)*[a-z0-9-]+", r"developer", r"api",
                    r"github", r"gitlab", r"bitbucket", r"stackoverflow", r"documentation",
                    r"manual", r"guide", r"reference", r"tutorial", r"howto",
                    r"microsoft", r"google", r"apple", r"amazon", r"ibm", r"oracle",
                    r"mozilla", r"w3c", r"ietf", r"rfc", r"standard"
                ],
                "web_patterns": [
                    r"news", r"blog", r"article", r"post", r"opinion", r"review",
                    r"wiki", r"forum", r"discussion", r"comment", r"social",
                    r"facebook", r"twitter", r"linkedin", r"instagram", r"youtube",
                    r"medium", r"quora", r"reddit", r"wikipedia"
                ]
            },
            "weights": {
                "academic": {
                    "impact_factor": 0.30,
                    "publisher_reputation": 0.25,
                    "author_history": 0.20,
                    "publication_date": 0.15,
                    "peer_reviewed": 0.10
                },
                "technical": {
                    "organization_reputation": 0.40,
                    "documentation_quality": 0.25,
                    "update_recency": 0.25,
                    "community_endorsement": 0.10
                },
                "web": {
                    "domain_authority": 0.35,
                    "content_quality": 0.25,
                    "reference_quality": 0.25,
                    "update_recency": 0.15
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
    
    def _load_profiles(self):
        """
        Load existing credibility profiles.
        
        Returns:
            Dictionary of credibility profiles
        """
        profiles = {}
        
        try:
            # Get profile files
            profile_files = [f for f in os.listdir(self.profile_directory) if f.endswith('.json')]
            
            # Load each profile
            for filename in profile_files:
                filepath = os.path.join(self.profile_directory, filename)
                profile = CredibilityProfile.load(filepath)
                if profile:
                    profiles[profile.source_id] = profile
            
            self.logger.log_info(f"Loaded {len(profiles)} credibility profiles")
        except Exception as e:
            self.logger.log_error(f"Error loading profiles: {str(e)}")
        
        return profiles
    
    def detect_source_type(self, source_data):
        """
        Detect source type from source data.
        
        Args:
            source_data: Source information dictionary
            
        Returns:
            Source type (academic, technical, web)
        """
        # Check if source type is explicitly provided
        if "source_type" in source_data and source_data["source_type"]:
            source_type = source_data["source_type"].lower()
            if source_type in ["academic", "technical", "web"]:
                return source_type
        
        # Extract URL for pattern matching
        url = source_data.get("url", "").lower()
        
        # Check academic patterns
        for pattern in self.config["source_type_detection"]["academic_patterns"]:
            if re.search(pattern, url, re.IGNORECASE):
                return "academic"
        
        # Check technical patterns
        for pattern in self.config["source_type_detection"]["technical_patterns"]:
            if re.search(pattern, url, re.IGNORECASE):
                return "technical"
        
        # Check web patterns
        for pattern in self.config["source_type_detection"]["web_patterns"]:
            if re.search(pattern, url, re.IGNORECASE):
                return "web"
        
        # Check publisher for clues
        publisher = source_data.get("publisher", "").lower()
        if publisher:
            # Academic publishers
            academic_publishers = ["elsevier", "springer", "wiley", "ieee", "acm", "oxford", "cambridge"]
            if any(pub in publisher for pub in academic_publishers):
                return "academic"
            
            # Technical organizations
            technical_orgs = ["microsoft", "google", "apple", "amazon", "ibm", "oracle", "mozilla"]
            if any(org in publisher for org in technical_orgs):
                return "technical"
            
            # News/web publishers
            web_publishers = ["news", "times", "post", "guardian", "bbc", "cnn", "nyt"]
            if any(pub in publisher for pub in web_publishers):
                return "web"
        
        # Default to web if no patterns match
        return "web"
    
    def get_source_profile(self, source_data):
        """
        Get or create credibility profile for a source.
        
        Args:
            source_data: Source information dictionary
            
        Returns:
            CredibilityProfile instance
        """
        # Generate source ID
        source_id = None
        
        # Try to use URL as ID
        url = source_data.get("url", "")
        if url:
            # Normalize URL
            url = url.lower().strip()
            # Remove protocol and www
            url = re.sub(r'^https?://(www\.)?', '', url)
            # Remove trailing slash
            url = url.rstrip('/')
            
            source_id = f"url:{url}"
        
        # If no URL, try to use publisher/organization
        if not source_id:
            publisher = source_data.get("publisher", source_data.get("organization", ""))
            if publisher:
                source_id = f"pub:{publisher.lower().strip()}"
        
        # If still no ID, generate a random one
        if not source_id:
            source_id = str(uuid.uuid4())
        
        # Get source name
        source_name = source_data.get("publisher", source_data.get("organization", "Unknown Source"))
        
        # Check if profile exists
        if source_id in self.profiles:
            return self.profiles[source_id]
        
        # Try to load from file
        profile_path = os.path.join(self.profile_directory, f"{source_id}.json")
        if os.path.exists(profile_path):
            profile =
(Content truncated due to size limit. Use line ranges to read in chunks)