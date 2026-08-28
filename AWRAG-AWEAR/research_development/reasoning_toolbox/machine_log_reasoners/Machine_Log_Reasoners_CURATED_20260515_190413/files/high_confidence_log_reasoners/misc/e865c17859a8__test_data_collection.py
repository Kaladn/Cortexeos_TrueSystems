"""
Test Data Collection for Kali Ka's Domain Testing Framework

This module implements test data collection for the domain testing framework,
creating structured test cases for each of the five priority domains:
1. Cybersecurity
2. AI Ethics/Governance
3. Medicine/Health Informatics
4. Philosophy/Logic
5. Computer Science Fundamentals

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
import uuid

# Import domain testing framework
sys.path.append('/home/ubuntu/nexus_project')
from domain_testing_framework import (
    TestCase, 
    TestSuite, 
    DomainTestingFramework,
    create_knowledge_unit,
    create_test_case
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/nexus_project/knowledge_validation/logs/test_data_collection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Constants
TEST_DIR = "/home/ubuntu/nexus_project/knowledge_validation/tests"
RESULTS_DIR = "/home/ubuntu/nexus_project/knowledge_validation/test_results"

# Ensure directories exist
os.makedirs(TEST_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
for domain in ['cybersecurity', 'ai_ethics', 'medicine', 'philosophy', 'computer_science']:
    os.makedirs(os.path.join(TEST_DIR, domain), exist_ok=True)

class TestDataGenerator:
    """
    Generates test data for the domain testing framework.
    """
    
    def __init__(self, test_dir: str = TEST_DIR):
        """
        Initialize the test data generator.
        
        Args:
            test_dir: Directory for test cases
        """
        self.test_dir = test_dir
        self.framework = DomainTestingFramework(test_dir=test_dir, results_dir=RESULTS_DIR)
    
    def generate_cybersecurity_test_suite(self) -> TestSuite:
        """
        Generate test cases for the Cybersecurity domain.
        
        Returns:
            TestSuite for Cybersecurity
        """
        logger.info("Generating Cybersecurity test suite")
        
        # Create test suite
        suite = self.framework.create_test_suite(
            domain="cybersecurity",
            description="Test suite for Cybersecurity domain with focus on temporal relevance and domain verification"
        )
        
        # 1. Current, high-credibility CVE information
        suite.add_test_case(create_test_case(
            id="cyber-001",
            domain="cybersecurity",
            description="Current CVE information from NIST (high credibility)",
            content="CVE-2023-45180 affects OpenSSH versions prior to 9.5 and allows remote attackers to cause a denial of service via crafted packets during the handshake phase.",
            source_type="technical",
            source_url="https://nvd.nist.gov/vuln/detail/CVE-2023-45180",
            source_publisher="NIST",
            created_date=datetime.now().replace(day=1).isoformat(),  # First day of current month
            expected_validation_status="verified",
            expected_confidence_level="high"
        ))
        
        # 2. Outdated security advisory (should be flagged as outdated)
        outdated_date = (datetime.now() - timedelta(days=400)).isoformat()
        suite.add_test_case(create_test_case(
            id="cyber-002",
            domain="cybersecurity",
            description="Outdated security advisory (should be flagged as outdated)",
            content="The latest version of Windows Defender (4.18.2009.7) addresses critical vulnerabilities in the scanning engine. All users should update immediately.",
            source_type="technical",
            source_url="https://www.microsoft.com/security-advisories/outdated",
            source_publisher="Microsoft",
            created_date=outdated_date,
            expected_validation_status="unverified",
            expected_confidence_level="low",
            is_outdated=True
        ))
        
        # 3. Medium credibility source with current information
        suite.add_test_case(create_test_case(
            id="cyber-003",
            domain="cybersecurity",
            description="Medium credibility source with current information",
            content="Zero-day vulnerability in Chrome browser versions 112-114 allows attackers to execute arbitrary code. Google has released patch 114.0.5735.199 to address this issue.",
            source_type="web",
            source_url="https://medium.com/security-blog/chrome-zero-day",
            source_publisher="Medium Security Blog",
            created_date=datetime.now().replace(day=15).isoformat(),  # 15th of current month
            expected_validation_status="verified",
            expected_confidence_level="medium"
        ))
        
        # 4. Contradictory information (conflicts with other sources)
        suite.add_test_case(create_test_case(
            id="cyber-004",
            domain="cybersecurity",
            description="Contradictory information about a security protocol",
            content="The WPA3 protocol is completely immune to brute force attacks and cannot be compromised under any circumstances.",
            source_type="web",
            source_url="https://securityblog.example.com/wpa3-myths",
            source_publisher="Example Security Blog",
            created_date=datetime.now().replace(day=10).isoformat(),
            expected_validation_status="unverified",
            expected_confidence_level="low",
            has_contradictions=True
        ))
        
        # 5. Low credibility source with factual information
        suite.add_test_case(create_test_case(
            id="cyber-005",
            domain="cybersecurity",
            description="Low credibility source with factual information",
            content="SHA-256 is a cryptographic hash function that generates a 256-bit (32-byte) hash value and is part of the SHA-2 family.",
            source_type="web",
            source_url="https://crypto-blog.example.net/sha-algorithms",
            source_publisher="Unknown Publisher",
            created_date=datetime.now().replace(day=5).isoformat(),
            expected_validation_status="verified",
            expected_confidence_level="medium",
            has_credibility_issues=True
        ))
        
        # 6. High credibility source with outdated but still valid information
        slightly_old_date = (datetime.now() - timedelta(days=180)).isoformat()
        suite.add_test_case(create_test_case(
            id="cyber-006",
            domain="cybersecurity",
            description="High credibility source with older but still valid information",
            content="HTTPS uses TLS (Transport Layer Security) to encrypt HTTP requests and responses, providing security for data in transit.",
            source_type="technical",
            source_url="https://www.ietf.org/rfc/rfc2818.txt",
            source_publisher="IETF",
            created_date=slightly_old_date,
            expected_validation_status="verified",
            expected_confidence_level="high"
        ))
        
        # 7. Current information with partial inaccuracy
        suite.add_test_case(create_test_case(
            id="cyber-007",
            domain="cybersecurity",
            description="Current information with partial inaccuracy",
            content="The Log4j vulnerability (CVE-2021-44228) affects all Java applications and requires complete reinstallation of operating systems to mitigate.",
            source_type="web",
            source_url="https://tech-news.example.org/log4j-vulnerability",
            source_publisher="Tech News Blog",
            created_date=datetime.now().replace(day=3).isoformat(),
            expected_validation_status="unverified",
            expected_confidence_level="low",
            has_contradictions=True
        ))
        
        # 8. Very recent high-quality information
        suite.add_test_case(create_test_case(
            id="cyber-008",
            domain="cybersecurity",
            description="Very recent high-quality information",
            content="Multi-factor authentication that uses app-based verification provides stronger security than SMS-based verification due to SIM swapping vulnerabilities.",
            source_type="technical",
            source_url="https://csrc.nist.gov/publications/detail/sp/800-63b/final",
            source_publisher="NIST",
            created_date=datetime.now().isoformat(),  # Today
            expected_validation_status="verified",
            expected_confidence_level="high"
        ))
        
        # 9. Information at the edge of freshness threshold
        edge_date = (datetime.now() - timedelta(days=175)).isoformat()  # Just within 6 month window
        suite.add_test_case(create_test_case(
            id="cyber-009",
            domain="cybersecurity",
            description="Information at the edge of freshness threshold",
            content="The OWASP Top 10 for 2021 lists Broken Access Control as the most critical web application security risk, replacing Injection from the 2017 list.",
            source_type="technical",
            source_url="https://owasp.org/Top10/",
            source_publisher="OWASP",
            created_date=edge_date,
            expected_validation_status="verified",
            expected_confidence_level="medium"
        ))
        
        # 10. Technically accurate but from very low credibility source
        suite.add_test_case(create_test_case(
            id="cyber-010",
            domain="cybersecurity",
            description="Technically accurate but from very low credibility source",
            content="Password hashing should use algorithms like bcrypt, Argon2, or PBKDF2 rather than MD5 or SHA-1 to protect against rainbow table attacks.",
            source_type="web",
            source_url="https://random-hacker-blog.example.com/password-security",
            source_publisher="Anonymous Blogger",
            created_date=datetime.now().replace(day=7).isoformat(),
            expected_validation_status="verified",
            expected_confidence_level="low",
            has_credibility_issues=True
        ))
        
        # Save test suite
        suite_dir = os.path.join(self.test_dir, "cybersecurity")
        os.makedirs(suite_dir, exist_ok=True)
        suite_file = os.path.join(suite_dir, "cybersecurity_test_suite.json")
        suite.save(suite_file)
        
        logger.info(f"Generated Cybersecurity test suite with {suite.count()} test cases")
        return suite
    
    def generate_ai_ethics_test_suite(self) -> TestSuite:
        """
        Generate test cases for the AI Ethics/Governance domain.
        
        Returns:
            TestSuite for AI Ethics/Governance
        """
        logger.info("Generating AI Ethics/Governance test suite")
        
        # Create test suite
        suite = self.framework.create_test_suite(
            domain="ai_ethics",
            description="Test suite for AI Ethics/Governance domain with focus on cross-reference verification and credibility scoring"
        )
        
        # 1. High credibility source with consensus information
        suite.add_test_case(create_test_case(
            id="ethics-001",
            domain="ai_ethics",
            description="High credibility source with consensus information",
            content="AI systems should be designed and operated in a way that respects human autonomy, prevents harm, and ensures fairness and explicability.",
            source_type="academic",
            source_url="https://ec.europa.eu/digital-single-market/en/news/ethics-guidelines-trustworthy-ai",
            source_publisher="European Commission",
            created_date=datetime.now().replace(day=1).isoformat(),
            expected_validation_status="verified",
            expected_confidence_level="high"
        ))
        
        # 2. Politically charged statement with mixed consensus
        suite.add_test_case(create_test_case(
            id="ethics-002",
            domain="ai_ethics",
            description="Politically charged statement with mixed consensus",
            content="AI development should be halted immediately until comprehensive international regulations are in place to prevent existential risks to humanity.",
            source_type="web",
            source_url="https://ai-ethics-blog.example.com/halt-ai-now",
            source_publisher="AI Ethics Blog",
            created_date=datetime.now().replace(day=5).isoformat(),
            expected_validation_status="unverified",
            expected_confidence_level="low",
            has_contradictions=True
        ))
        
        # 3. Academic source with nuanced position
        suite.add_test_case(create_test_case(
            id="ethics-003",
            domain="ai_ethics",
            description="Academic source with nuanced position",
            content="Algorithmic bias can emerge even when protected attributes like race and gender are explicitly excluded from training data, due to proxy variables that correlate with these attributes.",
            source_type="academic",
            source_url="https://arxiv.org/abs/1810.01943",
            source_publisher="arXiv",
            created_date=datetime.now().replace(day=10).isoformat(),
            expected_validation_status="verified",
            expected_confidence_level="high"
        ))
        
        # 4. Corporate policy statement (medium credibility)
        suite.add_test_case(create_test_case(
            id="ethics-004",
            domain="ai_ethics",
            description="Corporate policy statement (medium credibility)",
            content="OpenAI's models are designed with safety mechanisms that prevent generation of harmful content, making them completely safe for all applications.",
            source_type="technical",
            source_url="https://openai.com/policies/usage-policies",
            source_publisher="OpenAI",
            created_date=datetime.now().replace(day=15).isoformat(),
            expected_validation_status="unverified",
            expected_confidence_level="medium",
            has_contradictions=True
        ))
        
        # 5. Consensus view from multiple sources
        suite.add_test_case(create_test_case(
            id="ethics-005",
            domain="ai_ethics",
            description="Consensus view from multiple sources",
            content="Transparency in AI systems includes providing explanations for decisions, disclosing the use of AI, and making information available about training data and model limitations.",
            source_type="academic",
            source_url="https://hai.stanford.edu/research/ai-index-2023",
            source_publisher="Stanford HAI",
            created_date=datetime.now().replace(day=20).isoformat(),
            expected_validation_status="verified",
            expected_confidence_level="high"
        ))
        
        # 6. Outdated governance framework
        old_date = (datetime.now() - timedelta(days=1000)).isoformat()
        suite.add_test_case(create_test_case(
            id="ethics-006",
            domain="ai_ethics",
            description="Outdated governance framework",
            content="The primary ethical concern for AI systems is preventing job displacement in manufacturing sectors.",
            source_type="academic",
            source_url="https://old-university.example.edu/ai-ethics-2018",
            source_publisher="Example University",
            created_date=old_date,
            expected_validation_status="unverified",
            expected_confidence_level="low",
            is_outdated=True
        ))
        
        # 7. Controversial but well-support
(Content truncated due to size limit. Use line ranges to read in chunks)