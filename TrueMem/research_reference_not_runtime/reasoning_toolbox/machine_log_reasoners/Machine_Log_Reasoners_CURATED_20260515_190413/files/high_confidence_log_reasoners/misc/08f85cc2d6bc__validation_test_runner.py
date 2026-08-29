"""
Cross-Domain Validation Test Runner for Kali Ka's Knowledge Validation System

This module executes validation tests across all domains using the test cases
created by the test_data_collection.py script. It evaluates Kali Ka's knowledge
validation capabilities and generates comprehensive performance reports.

Author: Manus
Date: April 14, 2025
"""

import os
import sys
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union, Set
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm

# Import domain testing framework
sys.path.append('/home/ubuntu/nexus_project')
from domain_testing_framework import (
    TestCase, 
    TestSuite, 
    TestRunner,
    DomainTestingFramework
)
from knowledge_validation_system import KnowledgeValidationSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/nexus_project/knowledge_validation/logs/validation_test_runner.log'),
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
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt_tab')

# Constants
TEST_DIR = "/home/ubuntu/nexus_project/knowledge_validation/tests"
RESULTS_DIR = "/home/ubuntu/nexus_project/knowledge_validation/test_results"
REPORT_DIR = "/home/ubuntu/nexus_project/knowledge_validation/reports"

# Ensure directories exist
os.makedirs(TEST_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

class ValidationTestRunner:
    """
    Executes validation tests across all domains and generates performance reports.
    """
    
    def __init__(self, 
                 test_dir: str = TEST_DIR, 
                 results_dir: str = RESULTS_DIR,
                 report_dir: str = REPORT_DIR):
        """
        Initialize the validation test runner.
        
        Args:
            test_dir: Directory containing test cases
            results_dir: Directory for test results
            report_dir: Directory for performance reports
        """
        self.test_dir = test_dir
        self.results_dir = results_dir
        self.report_dir = report_dir
        
        # Initialize validation system
        self.validation_system = KnowledgeValidationSystem()
        
        # Initialize testing framework
        self.framework = DomainTestingFramework(
            validation_system=self.validation_system,
            test_dir=test_dir,
            results_dir=results_dir
        )
        
        # Domain-specific metrics
        self.domain_metrics = {}
        
        # Module-specific metrics
        self.module_metrics = {
            'source_credibility': {'accuracy': 0, 'false_positives': 0, 'false_negatives': 0},
            'cross_reference': {'accuracy': 0, 'false_positives': 0, 'false_negatives': 0},
            'temporal_relevance': {'accuracy': 0, 'false_positives': 0, 'false_negatives': 0},
            'truth_engine': {'accuracy': 0, 'false_positives': 0, 'false_negatives': 0}
        }
        
        # Overall metrics
        self.overall_metrics = {
            'accuracy': 0,
            'false_positive_rate': 0,
            'false_negative_rate': 0,
            'precision': 0,
            'recall': 0,
            'f1_score': 0
        }
        
        # Weaknesses identified
        self.weaknesses = {
            'cybersecurity': [],
            'ai_ethics': [],
            'medicine': [],
            'philosophy': [],
            'computer_science': []
        }
    
    def run_all_tests(self, verbose: bool = True) -> Dict[str, Any]:
        """
        Run validation tests across all domains.
        
        Args:
            verbose: Whether to print progress information
            
        Returns:
            Dictionary of test results
        """
        logger.info("Starting cross-domain validation tests")
        
        if verbose:
            print("\nRunning Cross-Domain Validation Tests")
            print("=====================================")
        
        # Load test suites
        self.framework.load_test_suites()
        
        # Run all tests
        start_time = time.time()
        results = self.framework.run_all_tests()
        duration = time.time() - start_time
        
        # Generate report
        report_path = self.framework.generate_report()
        
        # Get statistics
        stats = self.framework.get_statistics()
        
        # Calculate metrics
        self._calculate_metrics(results, stats)
        
        # Identify weaknesses
        self._identify_weaknesses(results)
        
        if verbose:
            self._print_summary(stats, duration)
        
        logger.info(f"Cross-domain validation tests completed in {duration:.2f} seconds")
        logger.info(f"Report generated: {report_path}")
        
        return {
            'results': results,
            'stats': stats,
            'metrics': {
                'overall': self.overall_metrics,
                'domain': self.domain_metrics,
                'module': self.module_metrics
            },
            'weaknesses': self.weaknesses,
            'report_path': report_path,
            'duration': duration
        }
    
    def run_domain_tests(self, domain: str, verbose: bool = True) -> Dict[str, Any]:
        """
        Run validation tests for a specific domain.
        
        Args:
            domain: The knowledge domain
            verbose: Whether to print progress information
            
        Returns:
            Dictionary of test results
        """
        logger.info(f"Starting validation tests for domain: {domain}")
        
        if verbose:
            print(f"\nRunning Validation Tests for {domain}")
            print("=" * (30 + len(domain)))
        
        # Load test suites
        self.framework.load_test_suites()
        
        # Run domain tests
        start_time = time.time()
        results = self.framework.run_domain_tests(domain)
        duration = time.time() - start_time
        
        # Get statistics
        stats = self.framework.get_statistics()
        
        if verbose:
            print(f"\nDomain: {domain}")
            print(f"Total Tests: {len(results)}")
            print(f"Passed Tests: {sum(1 for r in results if r.passed)}")
            print(f"Failed Tests: {sum(1 for r in results if not r.passed and not r.error)}")
            print(f"Error Tests: {sum(1 for r in results if r.error)}")
            print(f"Duration: {duration:.2f} seconds")
        
        logger.info(f"Validation tests for domain {domain} completed in {duration:.2f} seconds")
        
        return {
            'results': results,
            'stats': stats,
            'duration': duration
        }
    
    def _calculate_metrics(self, results: Dict[str, List[TestCase]], stats: Dict[str, Any]) -> None:
        """
        Calculate performance metrics from test results.
        
        Args:
            results: Dictionary of domain to test results
            stats: Test statistics
        """
        # Calculate overall metrics
        total_tests = stats['total_tests']
        passed_tests = stats['passed_tests']
        
        if total_tests > 0:
            self.overall_metrics['accuracy'] = passed_tests / total_tests
            
            # Calculate precision, recall, and F1 score
            true_positives = sum(1 for domain in results for r in results[domain] 
                               if r.passed and r.expected_validation_status == 'verified')
            false_positives = sum(1 for domain in results for r in results[domain] 
                                if not r.passed and r.expected_validation_status == 'unverified' 
                                and r.actual_result.get('validation_status') == 'verified')
            false_negatives = sum(1 for domain in results for r in results[domain] 
                                if not r.passed and r.expected_validation_status == 'verified' 
                                and r.actual_result.get('validation_status') == 'unverified')
            
            # Avoid division by zero
            if true_positives + false_positives > 0:
                self.overall_metrics['precision'] = true_positives / (true_positives + false_positives)
            
            if true_positives + false_negatives > 0:
                self.overall_metrics['recall'] = true_positives / (true_positives + false_negatives)
            
            if self.overall_metrics['precision'] + self.overall_metrics['recall'] > 0:
                self.overall_metrics['f1_score'] = (
                    2 * self.overall_metrics['precision'] * self.overall_metrics['recall'] / 
                    (self.overall_metrics['precision'] + self.overall_metrics['recall'])
                )
            
            # Calculate false positive and false negative rates
            total_negatives = sum(1 for domain in results for r in results[domain] 
                                if r.expected_validation_status == 'unverified')
            total_positives = sum(1 for domain in results for r in results[domain] 
                                if r.expected_validation_status == 'verified')
            
            if total_negatives > 0:
                self.overall_metrics['false_positive_rate'] = false_positives / total_negatives
            
            if total_positives > 0:
                self.overall_metrics['false_negative_rate'] = false_negatives / total_positives
        
        # Calculate domain-specific metrics
        for domain, domain_stats in stats['domains'].items():
            domain_total = domain_stats['total']
            domain_passed = domain_stats['passed']
            
            if domain_total > 0:
                domain_accuracy = domain_passed / domain_total
            else:
                domain_accuracy = 0
            
            # Calculate domain-specific precision, recall, and F1 score
            domain_true_positives = sum(1 for r in results.get(domain, []) 
                                      if r.passed and r.expected_validation_status == 'verified')
            domain_false_positives = sum(1 for r in results.get(domain, []) 
                                       if not r.passed and r.expected_validation_status == 'unverified' 
                                       and r.actual_result.get('validation_status') == 'verified')
            domain_false_negatives = sum(1 for r in results.get(domain, []) 
                                       if not r.passed and r.expected_validation_status == 'verified' 
                                       and r.actual_result.get('validation_status') == 'unverified')
            
            domain_precision = 0
            domain_recall = 0
            domain_f1 = 0
            
            # Avoid division by zero
            if domain_true_positives + domain_false_positives > 0:
                domain_precision = domain_true_positives / (domain_true_positives + domain_false_positives)
            
            if domain_true_positives + domain_false_negatives > 0:
                domain_recall = domain_true_positives / (domain_true_positives + domain_false_negatives)
            
            if domain_precision + domain_recall > 0:
                domain_f1 = (
                    2 * domain_precision * domain_recall / 
                    (domain_precision + domain_recall)
                )
            
            self.domain_metrics[domain] = {
                'accuracy': domain_accuracy,
                'precision': domain_precision,
                'recall': domain_recall,
                'f1_score': domain_f1,
                'false_positives': domain_false_positives,
                'false_negatives': domain_false_negatives
            }
        
        # Calculate module-specific metrics
        for module, module_stats in stats['modules'].items():
            module_total = module_stats['total']
            module_passed = module_stats['passed']
            
            if module_total > 0:
                module_accuracy = module_passed / module_total
            else:
                module_accuracy = 0
            
            self.module_metrics[module]['accuracy'] = module_accuracy
    
    def _identify_weaknesses(self, results: Dict[str, List[TestCase]]) -> None:
        """
        Identify domain-specific weaknesses from test results.
        
        Args:
            results: Dictionary of domain to test results
        """
        # Identify weaknesses for each domain
        for domain, domain_results in results.items():
            domain_weaknesses = []
            
            # Check for patterns in failed tests
            outdated_fails = sum(1 for r in domain_results 
                               if not r.passed and r.is_outdated)
            contradiction_fails = sum(1 for r in domain_results 
                                    if not r.passed and r.has_contradictions)
            credibility_fails = sum(1 for r in domain_results 
                                  if not r.passed and r.has_credibility_issues)
            
            # Identify specific weaknesses
            if outdated_fails > 0:
                domain_weaknesses.append(f"Temporal relevance issues: {outdated_fails} outdated knowledge units not properly identified")
            
            if contradiction_fails > 0:
                domain_weaknesses.append(f"Cross-reference issues: {contradiction_fails} contradictory knowledge units not properly identified")
            
            if credibility_fails > 0:
                domain_weaknesses.append(f"Source credibility issues: {credibility_fails} low-credibility sources not properly evaluated")
            
            # Check for specific test case failures
            for test_case in domain_results:
                if not test_case.passed:
                    weakness = f"Failed test case {test_case.id}: {test_case.description}"
                    domain_weaknesses.append(weakness)
            
            self.weaknesses[domain] = domain_weaknesses
    
    def _print_summary(self, stats: Dict[str, Any], duration: float) -> None:
        """
        Print a summary of test results.
        
        Args:
            stats: Test statistics
            duration: Test duration in seconds
        """
        print("\nCross-Domain Validation Test Summary")
        print("===================================")
        print(f"Total Tests: {stats['total_tests']}")
        print(f"Passed Tests: {stats['passed_tests']} ({self._percentage(stats['passed_tests'], stats['total_tests'])}%)")
        print(f"Failed Tests: {stats['failed_tests']} ({self._percentage(stats['failed_tests'], stats['total_tests'])}%)")
        print(f"Error Tests: {stats['error_tests']} ({self._percentage(stats['error_tests'], stats['total_tests'])}%)")
        print(f"Duration: {duration:.2f} seconds")
        
        print("\nDomain Performance")
        print("-----------------")
        for domain, domain_stats in stats['domains'].items():
            pass_rate = self._percentage(domain_stats['passed'], domain_stats['total'])
            print(f"{domain}: {pass_rate}% pass rate ({domain_stats['passed']}/{domain_stats['total']})")
        
        print("\nModule Performance")
        print("-----------------")
        for module, module_stats in stats['modules'].items():
            if module_stats['total'] > 0:
                pass_rate = self._percentage(module_stats['passed'], module_stats['total'])
                print(f"{module}: {pass_rate}% pass rate ({module_stats['passed']}/{module_stats['total']})")
        
(Content truncated due to size limit. Use line ranges to read in chunks)