"""
Modified Domain Testing Framework for Kali Ka's Knowledge Validation System

This module implements a comprehensive testing framework for evaluating
Kali Ka's knowledge validation capabilities across different knowledge domains.

The framework includes:
1. Test Case Structure - Standardized format for test cases with ground truth annotations
2. Test Runner - Executes test cases through the validation system
3. Metrics Collector - Compares results against ground truth and calculates performance metrics
4. Report Generator - Creates detailed reports on validation performance

Author: Manus
Date: April 14, 2025
"""

import os
import sys
import json
import time
import logging
import csv
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from dataclasses import dataclass, field, asdict
from collections import defaultdict

# Import Kali Ka validation system
sys.path.append('/home/ubuntu/nexus_project')
from knowledge_validation_system import KnowledgeValidationSystem
from knowledge_validation_enhancements import ValidationContext, ValidationLogger, ValidatedKnowledgeUnit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/nexus_project/knowledge_validation/logs/domain_testing.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import NLTK and download required resources
import nltk
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

@dataclass
class TestCase:
    """
    Represents a test case for the knowledge validation system.
    
    Each test case includes a knowledge unit to be validated and ground truth
    annotations for expected validation results.
    """
    # Test case metadata
    id: str
    domain: str
    description: str
    
    # Knowledge unit to validate
    knowledge_unit: Dict[str, Any]
    
    # Ground truth annotations
    expected_validation_status: str  # 'verified', 'unverified', 'rejected'
    expected_confidence_level: str  # 'high', 'medium', 'low'
    expected_module_results: Dict[str, Any] = field(default_factory=dict)
    
    # Test case properties
    is_outdated: bool = False
    has_contradictions: bool = False
    has_credibility_issues: bool = False
    
    # Test result (filled after execution)
    actual_result: Dict[str, Any] = field(default_factory=dict)
    passed: bool = False
    error: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert test case to dictionary"""
        return asdict(self)
    
    def to_json(self, indent=2) -> str:
        """Convert test case to JSON string"""
        return json.dumps(self.to_dict(), indent=indent)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TestCase':
        """Create a TestCase from a dictionary"""
        return cls(
            id=data.get('id', ''),
            domain=data.get('domain', ''),
            description=data.get('description', ''),
            knowledge_unit=data.get('knowledge_unit', {}),
            expected_validation_status=data.get('expected_validation_status', 'unverified'),
            expected_confidence_level=data.get('expected_confidence_level', 'low'),
            expected_module_results=data.get('expected_module_results', {}),
            is_outdated=data.get('is_outdated', False),
            has_contradictions=data.get('has_contradictions', False),
            has_credibility_issues=data.get('has_credibility_issues', False)
        )


class TestSuite:
    """
    Represents a collection of test cases for a specific domain.
    """
    
    def __init__(self, domain: str, description: str = ""):
        """
        Initialize a test suite for a specific domain.
        
        Args:
            domain: The knowledge domain for this test suite
            description: Description of the test suite
        """
        self.domain = domain
        self.description = description
        self.test_cases: List[TestCase] = []
        
    def add_test_case(self, test_case: TestCase) -> None:
        """Add a test case to the suite"""
        self.test_cases.append(test_case)
        
    def add_test_cases(self, test_cases: List[TestCase]) -> None:
        """Add multiple test cases to the suite"""
        self.test_cases.extend(test_cases)
        
    def get_test_case(self, test_id: str) -> Optional[TestCase]:
        """Get a test case by ID"""
        for test_case in self.test_cases:
            if test_case.id == test_id:
                return test_case
        return None
    
    def count(self) -> int:
        """Get the number of test cases in the suite"""
        return len(self.test_cases)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert test suite to dictionary"""
        return {
            'domain': self.domain,
            'description': self.description,
            'test_cases': [tc.to_dict() for tc in self.test_cases]
        }
    
    def to_json(self, indent=2) -> str:
        """Convert test suite to JSON string"""
        return json.dumps(self.to_dict(), indent=indent)
    
    def save(self, file_path: str) -> None:
        """Save test suite to file"""
        with open(file_path, 'w') as f:
            f.write(self.to_json())
    
    @classmethod
    def load(cls, file_path: str) -> 'TestSuite':
        """Load test suite from file"""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        suite = cls(
            domain=data.get('domain', ''),
            description=data.get('description', '')
        )
        
        for tc_data in data.get('test_cases', []):
            suite.add_test_case(TestCase.from_dict(tc_data))
        
        return suite


class TestRunner:
    """
    Executes test cases through the knowledge validation system.
    """
    
    def __init__(self, 
                 validation_system: Optional[KnowledgeValidationSystem] = None,
                 results_dir: str = "/home/ubuntu/nexus_project/knowledge_validation/test_results"):
        """
        Initialize the test runner.
        
        Args:
            validation_system: KnowledgeValidationSystem instance
            results_dir: Directory for test results
        """
        # Set up validation system
        self.validation_system = validation_system or KnowledgeValidationSystem()
        
        # Set up results directory
        self.results_dir = results_dir
        os.makedirs(results_dir, exist_ok=True)
        
        # Set up logger
        self.logger = ValidationLogger(os.path.join(results_dir, "logs"))
        
        # Statistics
        self.stats = {
            'total_tests': 0,
            'passed_tests': 0,
            'failed_tests': 0,
            'error_tests': 0,
            'domains': defaultdict(lambda: {
                'total': 0,
                'passed': 0,
                'failed': 0,
                'error': 0
            }),
            'modules': {
                'source_credibility': {
                    'total': 0,
                    'passed': 0,
                    'failed': 0
                },
                'cross_reference': {
                    'total': 0,
                    'passed': 0,
                    'failed': 0
                },
                'temporal_relevance': {
                    'total': 0,
                    'passed': 0,
                    'failed': 0
                },
                'truth_engine': {
                    'total': 0,
                    'passed': 0,
                    'failed': 0
                }
            }
        }
    
    def run_test_case(self, test_case: TestCase) -> TestCase:
        """
        Run a single test case through the validation system.
        
        Args:
            test_case: The test case to run
            
        Returns:
            The test case with results
        """
        self.logger.log_info(f"Running test case: {test_case.id} ({test_case.domain})")
        
        try:
            # Update statistics
            self.stats['total_tests'] += 1
            self.stats['domains'][test_case.domain]['total'] += 1
            
            # Run validation
            start_time = time.time()
            validation_result = self.validation_system.validate_knowledge_unit(test_case.knowledge_unit)
            duration = time.time() - start_time
            
            # Store actual result
            test_case.actual_result = validation_result
            
            # Check if test passed
            validation_status = validation_result.get('validation_status', 'unverified')
            confidence_level = validation_result.get('confidence_level', 'low')
            
            status_match = validation_status == test_case.expected_validation_status
            confidence_match = confidence_level == test_case.expected_confidence_level
            
            test_case.passed = status_match and confidence_match
            
            # Update statistics
            if test_case.passed:
                self.stats['passed_tests'] += 1
                self.stats['domains'][test_case.domain]['passed'] += 1
            else:
                self.stats['failed_tests'] += 1
                self.stats['domains'][test_case.domain]['failed'] += 1
            
            # Check module-specific results
            self._check_module_results(test_case, validation_result)
            
            self.logger.log_info(f"Test case {test_case.id} {'passed' if test_case.passed else 'failed'} in {duration:.2f} seconds")
            
            return test_case
            
        except Exception as e:
            self.logger.log_error(f"Error running test case {test_case.id}: {str(e)}")
            
            # Update statistics
            self.stats['error_tests'] += 1
            self.stats['domains'][test_case.domain]['error'] += 1
            
            # Store error
            test_case.error = str(e)
            test_case.passed = False
            
            return test_case
    
    def _check_module_results(self, test_case: TestCase, validation_result: Dict[str, Any]) -> None:
        """
        Check module-specific results against expected values.
        
        Args:
            test_case: The test case
            validation_result: The validation result
        """
        # Check source credibility
        if 'source_credibility' in test_case.expected_module_results:
            self.stats['modules']['source_credibility']['total'] += 1
            expected = test_case.expected_module_results['source_credibility']
            actual = validation_result.get('module_results', {}).get('source_credibility', {})
            
            if self._compare_module_result(expected, actual):
                self.stats['modules']['source_credibility']['passed'] += 1
            else:
                self.stats['modules']['source_credibility']['failed'] += 1
        
        # Check cross reference
        if 'cross_reference' in test_case.expected_module_results:
            self.stats['modules']['cross_reference']['total'] += 1
            expected = test_case.expected_module_results['cross_reference']
            actual = validation_result.get('module_results', {}).get('cross_reference', {})
            
            if self._compare_module_result(expected, actual):
                self.stats['modules']['cross_reference']['passed'] += 1
            else:
                self.stats['modules']['cross_reference']['failed'] += 1
        
        # Check temporal relevance
        if 'temporal_relevance' in test_case.expected_module_results:
            self.stats['modules']['temporal_relevance']['total'] += 1
            expected = test_case.expected_module_results['temporal_relevance']
            actual = validation_result.get('module_results', {}).get('temporal_relevance', {})
            
            if self._compare_module_result(expected, actual):
                self.stats['modules']['temporal_relevance']['passed'] += 1
            else:
                self.stats['modules']['temporal_relevance']['failed'] += 1
        
        # Check truth engine
        if 'truth_engine' in test_case.expected_module_results:
            self.stats['modules']['truth_engine']['total'] += 1
            expected = test_case.expected_module_results['truth_engine']
            actual = validation_result.get('module_results', {}).get('truth_engine', {})
            
            if self._compare_module_result(expected, actual):
                self.stats['modules']['truth_engine']['passed'] += 1
            else:
                self.stats['modules']['truth_engine']['failed'] += 1
    
    def _compare_module_result(self, expected: Dict[str, Any], actual: Dict[str, Any]) -> bool:
        """
        Compare expected and actual module results.
        
        Args:
            expected: Expected module result
            actual: Actual module result
            
        Returns:
            True if results match, False otherwise
        """
        # Simple comparison for now - just check if the keys in expected exist in actual
        # and have the same values
        for key, value in expected.items():
            if key not in actual:
                return False
            
            if isinstance(value, (int, float)):
                # For numeric values, check if they're within 10%
                actual_value = actual[key]
                if not isinstance(actual_value, (int, float)):
                    return False
                
                if abs(value - actual_value) / max(abs(value), 0.001) > 0.1:
                    return False
            else:
                # For non-numeric values, check for exact match
                if actual[key] != value:
                    return False
        
        return True
    
    def run_test_suite(self, test_suite: TestSuite) -> List[TestCase]:
        """
        Run all test cases in a test suite.
        
        Args:
            test_suite: The test suite to run
            
        Returns:
            List of test cases with results
        """
        self.logger.log_info(f"Running test suite for domain: {test_suite.domain}")
        
        results = []
        for test_case in test_suite.test_cases:
            result = self.run_test_case(test_case)
            results.append(result)
        
        # Save results
        self._save_suite_results(test_suite.domain, results)
        
        return results
    
    def _save_suite_results(self, domain: str, results: List[TestCase]) -> None:
        """
        Save test suite results to file.
        
        Args:
            domain: The domain of the test suite
            results: List of test cases with results
        """
        # Create domain directory
        domain_dir = os.path.join(self.results_dir, domain)
        os.makedirs(domain_dir, exist_ok=True)
        
        # Save results as JSON
        results_file = os.path.join(domain_dir, f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(results_file, 'w') as f:
            json.dump([r.to_dict() for r in results], f, indent=2)
        
        # Save summary as CSV
        summary_file = os.path.join(domain_dir, f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        with open(summary_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Description', 'Expected Status', 'Actual Status', 'Expected Confidence', 'Actual Confidence', 'Passed', 'Error'])
            
            for result in results:
                writer.writerow([
                    result.id,
                    result.description,
                    result.expected_validation_status,
                    result.actual_result.g
(Content truncated due to size limit. Use line ranges to read in chunks)