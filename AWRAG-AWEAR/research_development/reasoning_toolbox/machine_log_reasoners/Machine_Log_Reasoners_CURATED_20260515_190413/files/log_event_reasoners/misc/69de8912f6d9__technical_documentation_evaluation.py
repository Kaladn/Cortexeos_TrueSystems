"""
Technical Documentation Evaluation for Kali Ka

This module implements specialized evaluation for technical documentation sources
for the Source Credibility Assessment module, featuring:
- Organization reputation assessment
- Documentation quality evaluation
- Update recency analysis
- Community endorsement measurement

Author: Manus
Date: April 14, 2025
"""

import os
import sys
import json
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Union

# Import enhancements
sys.path.append('/home/ubuntu/nexus_project')
from knowledge_validation_enhancements import ValidationContext, ValidationLogger
from domain_specific_credibility import DomainSpecificEvaluation

# Configure logging
logger = logging.getLogger(__name__)

class TechnicalDocumentationEvaluation:
    """
    Specialized evaluation for technical documentation sources.
    """
    
    def __init__(self, config_path=None, logger=None):
        """
        Initialize technical documentation evaluation.
        
        Args:
            config_path: Path to configuration file
            logger: ValidationLogger instance
        """
        # Set up logger
        self.logger = logger or ValidationLogger()
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize domain-specific evaluation
        self.domain_evaluator = DomainSpecificEvaluation(config_path, logger)
        
        # Initialize organization reputation database
        self.org_reputation = self._initialize_org_reputation()
    
    def _load_config(self, config_path=None):
        """
        Load configuration from file or use default.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        default_config = {
            "weights": {
                "organization_reputation": 0.40,
                "documentation_quality": 0.25,
                "update_recency": 0.25,
                "community_endorsement": 0.10
            },
            "quality_indicators": {
                "has_examples": 0.20,
                "has_code_samples": 0.15,
                "has_diagrams": 0.15,
                "has_references": 0.15,
                "has_version_history": 0.15,
                "has_author_info": 0.10,
                "has_changelog": 0.10
            },
            "recency_thresholds": {
                "excellent": 90,  # Days
                "good": 180,      # Days
                "acceptable": 365,  # Days
                "outdated": 730   # Days
            },
            "community_indicators": {
                "github_stars": {
                    "excellent": 10000,
                    "good": 1000,
                    "acceptable": 100
                },
                "stackoverflow_mentions": {
                    "excellent": 1000,
                    "good": 100,
                    "acceptable": 10
                },
                "github_contributors": {
                    "excellent": 100,
                    "good": 20,
                    "acceptable": 5
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
    
    def _initialize_org_reputation(self):
        """
        Initialize organization reputation database.
        
        Returns:
            Dictionary of organization reputations
        """
        return {
            # Major technology companies
            "microsoft": 0.95,
            "google": 0.95,
            "apple": 0.90,
            "amazon": 0.90,
            "meta": 0.85,
            "facebook": 0.85,
            "ibm": 0.90,
            "oracle": 0.85,
            "salesforce": 0.85,
            "adobe": 0.85,
            
            # Open source organizations
            "apache": 0.95,
            "mozilla": 0.90,
            "linux foundation": 0.95,
            "python software foundation": 0.95,
            "django software foundation": 0.90,
            "openai": 0.90,
            "hugging face": 0.85,
            "tensorflow": 0.90,
            "pytorch": 0.90,
            
            # Standards organizations
            "w3c": 0.95,
            "ietf": 0.95,
            "iso": 0.95,
            "ieee": 0.95,
            "ecma": 0.90,
            "nist": 0.95,
            "owasp": 0.90,
            
            # Cloud providers
            "aws": 0.95,
            "azure": 0.95,
            "google cloud": 0.95,
            "digitalocean": 0.85,
            "heroku": 0.85,
            "cloudflare": 0.90,
            
            # Programming language documentation
            "python": 0.95,
            "javascript": 0.90,
            "typescript": 0.90,
            "java": 0.90,
            "c#": 0.90,
            "go": 0.90,
            "rust": 0.90,
            "swift": 0.90,
            "kotlin": 0.90,
            
            # Framework documentation
            "react": 0.90,
            "angular": 0.90,
            "vue": 0.85,
            "django": 0.90,
            "flask": 0.85,
            "spring": 0.90,
            "laravel": 0.85,
            "rails": 0.85,
            "express": 0.85,
            
            # Database documentation
            "postgresql": 0.90,
            "mysql": 0.90,
            "mongodb": 0.85,
            "redis": 0.90,
            "elasticsearch": 0.85,
            "cassandra": 0.85,
            "neo4j": 0.85,
            
            # Security organizations
            "cert": 0.95,
            "sans": 0.90,
            "mitre": 0.95,
            "cisa": 0.95,
            "ncsc": 0.90,
            
            # Universities and research institutions
            "mit": 0.95,
            "stanford": 0.95,
            "berkeley": 0.95,
            "harvard": 0.95,
            "cambridge": 0.95,
            "oxford": 0.95,
            "eth zurich": 0.90,
            "max planck": 0.90,
            
            # Default for unknown organizations
            "default": 0.50
        }
    
    def evaluate_organization_reputation(self, organization, domain=None):
        """
        Evaluate the reputation of an organization.
        
        Args:
            organization: Organization name
            domain: Knowledge domain (optional)
            
        Returns:
            Reputation score and reasoning
        """
        if not organization:
            return 0.5, {"reason": "No organization information provided"}
        
        # Normalize organization name
        org_name = organization.lower().strip()
        
        # Check if organization is in database
        reputation = None
        matched_org = None
        
        # Try exact match
        if org_name in self.org_reputation:
            reputation = self.org_reputation[org_name]
            matched_org = org_name
        else:
            # Try partial match
            for known_org, rep in self.org_reputation.items():
                if known_org in org_name or org_name in known_org:
                    reputation = rep
                    matched_org = known_org
                    break
        
        # If no match found, check if it's a domain authority
        if not reputation and domain:
            is_authority, authority_weight = self.domain_evaluator.domain_factors.is_domain_authority(org_name, domain)
            if is_authority:
                reputation = authority_weight
                matched_org = f"domain authority in {domain}"
        
        # If still no match, use default
        if not reputation:
            reputation = self.org_reputation["default"]
            matched_org = "unknown organization"
        
        # Prepare reasoning
        reasoning = {
            "organization": organization,
            "matched_as": matched_org,
            "reputation_score": reputation
        }
        
        return reputation, reasoning
    
    def evaluate_documentation_quality(self, source_data):
        """
        Evaluate the quality of technical documentation.
        
        Args:
            source_data: Source information dictionary
            
        Returns:
            Quality score and reasoning
        """
        # Extract content for analysis
        content = ""
        for field in ["content", "description", "abstract"]:
            if field in source_data and source_data[field]:
                content += " " + source_data[field]
        
        # Initialize quality indicators
        quality_indicators = {
            "has_examples": False,
            "has_code_samples": False,
            "has_diagrams": False,
            "has_references": False,
            "has_version_history": False,
            "has_author_info": False,
            "has_changelog": False
        }
        
        # Check for examples
        example_patterns = [
            r"example[s]?", r"for instance", r"such as", r"e\.g\.", 
            r"sample[s]?", r"demonstration", r"illustration"
        ]
        quality_indicators["has_examples"] = any(re.search(pattern, content, re.IGNORECASE) for pattern in example_patterns)
        
        # Check for code samples
        code_patterns = [
            r"```", r"<code>", r"<pre>", r"function\s*\(", r"def\s+\w+\s*\(", 
            r"class\s+\w+", r"import\s+\w+", r"from\s+\w+\s+import"
        ]
        quality_indicators["has_code_samples"] = any(re.search(pattern, content, re.IGNORECASE) for pattern in code_patterns)
        
        # Check for diagrams
        diagram_patterns = [
            r"diagram", r"figure", r"illustration", r"chart", r"graph", 
            r"<img", r"![", r"<svg", r"<canvas"
        ]
        quality_indicators["has_diagrams"] = any(re.search(pattern, content, re.IGNORECASE) for pattern in diagram_patterns)
        
        # Check for references
        reference_patterns = [
            r"reference[s]?", r"citation[s]?", r"bibliography", r"works cited", 
            r"\[\d+\]", r"\(\d{4}\)", r"et al\.", r"^https?://"
        ]
        quality_indicators["has_references"] = any(re.search(pattern, content, re.IGNORECASE) for pattern in reference_patterns)
        
        # Check for version history
        version_patterns = [
            r"version history", r"release notes", r"v\d+\.\d+", r"version \d+\.\d+", 
            r"release \d+\.\d+", r"update history"
        ]
        quality_indicators["has_version_history"] = any(re.search(pattern, content, re.IGNORECASE) for pattern in version_patterns)
        
        # Check for author info
        author_patterns = [
            r"author[s]?", r"written by", r"created by", r"maintained by", 
            r"developed by", r"copyright", r"©"
        ]
        quality_indicators["has_author_info"] = any(re.search(pattern, content, re.IGNORECASE) for pattern in author_patterns)
        
        # Check for changelog
        changelog_patterns = [
            r"changelog", r"change log", r"what's new", r"release notes", 
            r"updates", r"changes in this version"
        ]
        quality_indicators["has_changelog"] = any(re.search(pattern, content, re.IGNORECASE) for pattern in changelog_patterns)
        
        # Calculate quality score
        quality_score = 0.0
        for indicator, present in quality_indicators.items():
            if present:
                quality_score += self.config["quality_indicators"][indicator]
        
        # Prepare reasoning
        reasoning = {
            "quality_indicators": quality_indicators,
            "quality_score": quality_score
        }
        
        return quality_score, reasoning
    
    def evaluate_update_recency(self, source_data):
        """
        Evaluate the recency of technical documentation updates.
        
        Args:
            source_data: Source information dictionary
            
        Returns:
            Recency score and reasoning
        """
        # Get current date
        current_date = datetime.now()
        
        # Extract update date
        update_date = None
        
        # Try to get date from source data
        for field in ["update_date", "last_modified", "date", "publication_date"]:
            if field in source_data and source_data[field]:
                try:
                    if isinstance(source_data[field], str):
                        update_date = datetime.fromisoformat(source_data[field].replace('Z', '+00:00'))
                    elif isinstance(source_data[field], datetime):
                        update_date = source_data[field]
                    break
                except (ValueError, TypeError):
                    continue
        
        # If no date found, use a default (1 year ago)
        if not update_date:
            update_date = current_date - timedelta(days=365)
            date_source = "default (assumed 1 year old)"
        else:
            date_source = "provided in source data"
        
        # Calculate days since update
        days_since_update = (current_date - update_date).days
        
        # Determine recency category
        recency_category = "outdated"
        for category, threshold in sorted(self.config["recency_thresholds"].items(), key=lambda x: x[1]):
            if days_since_update <= threshold:
                recency_category = category
                break
        
        # Calculate recency score
        recency_score = 0.0
        if recency_category == "excellent":
            recency_score = 1.0
        elif recency_category == "good":
            recency_score = 0.8
        elif recency_category == "acceptable":
            recency_score = 0.6
        else:  # outdated
            recency_score = 0.3
        
        # Apply domain-specific decay if domain is provided
        domain = source_data.get("domain")
        if domain:
            # Get domain-specific freshness requirement
            freshness_requirement = self.domain_evaluator.get_freshness_requirement(domain)
            
            # Adjust recency score based on domain-specific requirements
            if days_since_update <= freshness_requirement * 0.25:
                recency_score = 1.0
            elif days_since_update <= freshness_requirement * 0.5:
                recency_score = 0.8
            elif days_since_update <= freshness_requirement:
                recency_score = 0.6
            else:
                recency_score = max(0.1, 0.6 - (days_since_update - freshness_requirement) / freshness_requirement * 0.5)
        
        # Prepare reasoning
        reasoning = {
            "update_date": update_date.isoformat(),
            "date_source": date_source,
            "days_since_update": days_since_update,
            "recency_category": recency_category,
            "recency_score": recency_score
        }
        
        if domain:
            reasoning["domain"] = domain
            reasoning["domain_freshness_requirement"] = freshness_requirement
        
        return recency_score, reasoning
    
    def evaluate_community_endorsement(self, source_data):
        """
        Evaluate community endorsement of technical documentation.
        
        Args:
            source_data: Source information dictionary
            
        Returns:
            Endorsement score and reasoning
        """
        # Initialize endorsement indicators
     
(Content truncated due to size limit. Use line ranges to read in chunks)