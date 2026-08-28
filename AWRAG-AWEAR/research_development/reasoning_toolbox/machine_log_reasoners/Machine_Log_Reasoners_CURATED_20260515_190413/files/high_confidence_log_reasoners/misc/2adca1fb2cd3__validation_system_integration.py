"""
Integration of Improved Source Credibility Assessment with Knowledge Validation System

This module integrates the improved Source Credibility Assessment module
with Kali Ka's Knowledge Validation System.

Author: Manus
Date: April 14, 2025
"""

import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union

# Import validation system components
sys.path.append('/home/ubuntu/nexus_project')
from knowledge_validation_system import KnowledgeValidationSystem
from knowledge_validation_enhancements import ValidationContext, ValidationLogger
from improved_source_credibility_assessment import ImprovedSourceCredibilityAssessment

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/home/ubuntu/nexus_project/knowledge_validation/logs/integration.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ValidationSystemIntegration:
    """
    Integration of improved Source Credibility Assessment with Knowledge Validation System.
    """
    
    def __init__(self, config_path=None):
        """
        Initialize validation system integration.
        
        Args:
            config_path: Path to configuration file
        """
        # Set up logger
        self.logger = ValidationLogger()
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize improved source credibility assessment
        self.credibility_assessment = ImprovedSourceCredibilityAssessment(config_path, self.logger)
        
        # Initialize knowledge validation system
        self.validation_system = KnowledgeValidationSystem(config_path, self.logger)
        
        # Replace source credibility assessment in validation system
        self._integrate_credibility_assessment()
    
    def _load_config(self, config_path=None):
        """
        Load configuration from file or use default.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        default_config = {
            "integration": {
                "validation_system_path": "/home/ubuntu/nexus_project/knowledge_validation_system.py",
                "credibility_assessment_path": "/home/ubuntu/nexus_project/improved_source_credibility_assessment.py",
                "test_data_path": "/home/ubuntu/nexus_project/knowledge_validation/tests"
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
    
    def _integrate_credibility_assessment(self):
        """
        Replace source credibility assessment in validation system.
        """
        try:
            # Replace assess_source_credibility method in validation system
            self.validation_system.assess_source_credibility = self.credibility_assessment.assess_source_credibility
            
            self.logger.log_info("Successfully integrated improved source credibility assessment with validation system")
        except Exception as e:
            self.logger.log_error(f"Error integrating credibility assessment: {str(e)}")
    
    def validate_knowledge_unit(self, knowledge_unit, context=None):
        """
        Validate knowledge unit using integrated validation system.
        
        Args:
            knowledge_unit: Knowledge unit to validate
            context: ValidationContext instance (optional)
            
        Returns:
            Validation result
        """
        return self.validation_system.validate_knowledge_unit(knowledge_unit, context)
    
    def run_test_validation(self, test_data_path=None):
        """
        Run test validation using integrated validation system.
        
        Args:
            test_data_path: Path to test data directory
            
        Returns:
            Test results
        """
        # Use configured test data path if not provided
        if not test_data_path:
            test_data_path = self.config["integration"]["test_data_path"]
        
        # Check if test data path exists
        if not os.path.exists(test_data_path):
            self.logger.log_error(f"Test data path does not exist: {test_data_path}")
            return {"error": f"Test data path does not exist: {test_data_path}"}
        
        # Get test files
        test_files = [f for f in os.listdir(test_data_path) if f.endswith('.json')]
        
        if not test_files:
            self.logger.log_error(f"No test files found in {test_data_path}")
            return {"error": f"No test files found in {test_data_path}"}
        
        # Initialize test results
        test_results = {
            "total_tests": len(test_files),
            "successful_validations": 0,
            "failed_validations": 0,
            "validation_results": []
        }
        
        # Run validation for each test file
        for test_file in test_files:
            try:
                # Load test data
                with open(os.path.join(test_data_path, test_file), 'r') as f:
                    test_data = json.load(f)
                
                # Create validation context
                context = ValidationContext()
                if "domain" in test_data:
                    context.set_domain(test_data["domain"])
                
                # Validate knowledge unit
                validation_result = self.validate_knowledge_unit(test_data, context)
                
                # Add to results
                test_results["validation_results"].append({
                    "test_file": test_file,
                    "validation_result": validation_result
                })
                
                # Update counters
                if validation_result.get("validation_status") == "verified":
                    test_results["successful_validations"] += 1
                else:
                    test_results["failed_validations"] += 1
                
                self.logger.log_info(f"Validated {test_file}: {validation_result.get('validation_status', 'unknown')}")
            
            except Exception as e:
                self.logger.log_error(f"Error validating {test_file}: {str(e)}")
                test_results["validation_results"].append({
                    "test_file": test_file,
                    "error": str(e)
                })
                test_results["failed_validations"] += 1
        
        # Calculate success rate
        test_results["success_rate"] = test_results["successful_validations"] / test_results["total_tests"] if test_results["total_tests"] > 0 else 0
        
        # Log summary
        self.logger.log_info(f"Test validation complete: {test_results['successful_validations']} successful, {test_results['failed_validations']} failed")
        
        return test_results
    
    def generate_integration_report(self, test_results=None):
        """
        Generate integration report.
        
        Args:
            test_results: Test results (optional)
            
        Returns:
            Integration report
        """
        # Run test validation if not provided
        if not test_results:
            test_results = self.run_test_validation()
        
        # Generate report
        report = {
            "timestamp": datetime.now().isoformat(),
            "integration_status": "success" if not test_results.get("error") else "error",
            "test_results": test_results,
            "improvements": [
                "Implemented dynamic credibility profiles that evolve over time",
                "Added field-normalized impact factor assessment for academic sources",
                "Created fuzzy matching system for publisher recognition",
                "Implemented domain-specific authority recognition",
                "Added specialized handling for preprint repositories",
                "Developed robust technical documentation evaluation",
                "Integrated with domain-specific freshness requirements"
            ]
        }
        
        # Save report
        report_path = os.path.join("/home/ubuntu/nexus_project/knowledge_validation/reports", f"integration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.log_info(f"Integration report generated: {report_path}")
        
        return report


# Test the integration if run directly
if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("/home/ubuntu/nexus_project/knowledge_validation/logs", exist_ok=True)
    os.makedirs("/home/ubuntu/nexus_project/knowledge_validation/reports", exist_ok=True)
    
    # Create the integration
    integration = ValidationSystemIntegration()
    
    # Test with a sample knowledge unit
    sample_knowledge_unit = {
        "fact": "The speed of light in vacuum is approximately 299,792,458 meters per second.",
        "source": {
            "url": "https://physics.nist.gov/cuu/Constants/index.html",
            "publisher": "National Institute of Standards and Technology",
            "publication_date": "2022-01-01",
            "domain": "physics"
        },
        "domain": "physics",
        "confidence": 0.95
    }
    
    # Create validation context
    context = ValidationContext()
    context.set_domain("physics")
    
    # Validate knowledge unit
    print("\nValidating sample knowledge unit...")
    validation_result = integration.validate_knowledge_unit(sample_knowledge_unit, context)
    
    # Print validation result
    print("\nValidation result:")
    print(f"Validation status: {validation_result.get('validation_status', 'unknown')}")
    print(f"Confidence score: {validation_result.get('confidence_score', 0.0):.2f}")
    
    # Run test validation
    print("\nRunning test validation...")
    test_results = integration.run_test_validation()
    
    # Print test results
    print("\nTest results:")
    print(f"Total tests: {test_results.get('total_tests', 0)}")
    print(f"Successful validations: {test_results.get('successful_validations', 0)}")
    print(f"Failed validations: {test_results.get('failed_validations', 0)}")
    print(f"Success rate: {test_results.get('success_rate', 0.0):.2f}")
    
    # Generate integration report
    print("\nGenerating integration report...")
    report = integration.generate_integration_report(test_results)
    
    print("\nIntegration report generated.")
    print(f"Integration status: {report.get('integration_status', 'unknown')}")
    print("\nImprovements:")
    for improvement in report.get("improvements", []):
        print(f"- {improvement}")
