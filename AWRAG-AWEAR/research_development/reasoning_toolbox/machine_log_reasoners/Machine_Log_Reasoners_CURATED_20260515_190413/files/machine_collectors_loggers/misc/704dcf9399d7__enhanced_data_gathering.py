"""
Integration Module for Automated Data Gathering System

This module integrates the automated data gathering system with the error handling
and monitoring components, providing a unified interface for data collection.

Author: Manus
Date: April 8, 2025
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# Import core components
sys.path.append('/home/ubuntu/nexus_project')
from automated_data_gathering_system import (
    DataGatheringOrchestrator, 
    CONFIG, 
    WebScraper, 
    ApiGatherer, 
    DataProcessor, 
    DataValidator,
    KnowledgeBaseIntegrator,
    ExperientialDataGenerator
)
from error_handling import ErrorHandler, HttpRequestHandler
from data_gathering_monitor import DataGatheringMonitor

class EnhancedDataGatheringSystem:
    """Enhanced data gathering system with improved error handling and monitoring"""
    
    def __init__(self, config=None):
        """Initialize the enhanced data gathering system"""
        self.config = config or CONFIG
        self.error_handler = ErrorHandler()
        self.monitor = DataGatheringMonitor()
        self.http_handler = HttpRequestHandler(self.error_handler, self.config)
        
        # Create base orchestrator
        self.orchestrator = DataGatheringOrchestrator(self.config)
        
        # Create output directories if they don't exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        directories = [
            '/home/ubuntu/nexus_project/data_gathering/raw',
            '/home/ubuntu/nexus_project/data_gathering/processed',
            '/home/ubuntu/nexus_project/data_gathering/validated',
            '/home/ubuntu/nexus_project/data_gathering/logs',
            '/home/ubuntu/nexus_project/knowledge_base/units',
            '/home/ubuntu/nexus_project/experiential_learning/scenarios'
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def run(self, domains=None, max_sources_per_domain=None):
        """
        Run the enhanced data gathering process
        
        Args:
            domains: Optional list of specific domains to gather data from
            max_sources_per_domain: Optional limit on sources per domain
        """
        print("\n=== Kali Ka Enhanced Data Gathering System ===")
        print(f"Starting data gathering process at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Filter domains if specified
        if domains:
            filtered_config = self.config.copy()
            filtered_config['domains'] = {
                domain: self.config['domains'][domain] 
                for domain in domains 
                if domain in self.config['domains']
            }
            self.orchestrator.config = filtered_config
        
        # Limit sources if specified
        if max_sources_per_domain:
            for domain in self.orchestrator.config['domains']:
                sources = self.orchestrator.config['domains'][domain]['sources']
                self.orchestrator.config['domains'][domain]['sources'] = sources[:max_sources_per_domain]
        
        # Print configuration summary
        self._print_config_summary()
        
        try:
            # Run the orchestrator
            start_time = time.time()
            self.orchestrator.run()
            
            # Integrate with knowledge base
            integrator = KnowledgeBaseIntegrator(self.orchestrator.validator.validated_data)
            knowledge_units = integrator.integrate()
            
            # Generate experiential data
            exp_generator = ExperientialDataGenerator(knowledge_units)
            experiences = exp_generator.generate_experiences()
            
            # Calculate execution time
            execution_time = time.time() - start_time
            
            # Generate final report
            self._generate_final_report(
                knowledge_units=knowledge_units,
                experiences=experiences,
                execution_time=execution_time
            )
            
            # Print status report
            self.monitor.print_status_report()
            
        except Exception as e:
            self.error_handler.log_error(
                error_type='system',
                source='orchestrator',
                details={'phase': 'main_execution'},
                exception=e
            )
            print(f"\nERROR: Data gathering process failed: {str(e)}")
            print("See error logs for details.")
    
    def _print_config_summary(self):
        """Print a summary of the current configuration"""
        domains = self.orchestrator.config['domains']
        
        print("\nConfiguration Summary:")
        print(f"- Max threads: {self.orchestrator.config['max_threads']}")
        print(f"- Request delay: {self.orchestrator.config['request_delay']} seconds")
        print(f"- Validation threshold: {self.orchestrator.config['validation_threshold']}")
        print(f"- Domains: {len(domains)}")
        
        for domain, domain_config in domains.items():
            sources = domain_config['sources']
            print(f"  - {domain} (priority: {domain_config['priority']}): {len(sources)} sources")
            
            web_sources = sum(1 for s in sources if s['type'] == 'web')
            api_sources = sum(1 for s in sources if s['type'] == 'api')
            
            print(f"    - Web sources: {web_sources}")
            print(f"    - API sources: {api_sources}")
        
        print("")
    
    def _generate_final_report(self, knowledge_units, experiences, execution_time):
        """Generate a comprehensive final report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "execution_time_seconds": execution_time,
            "configuration": {
                "max_threads": self.config['max_threads'],
                "request_delay": self.config['request_delay'],
                "validation_threshold": self.config['validation_threshold'],
                "domains": list(self.config['domains'].keys())
            },
            "results": {
                "raw_data_items": self.orchestrator.data_queue.qsize(),
                "processed_items": len(self.orchestrator.processor.processed_data),
                "validated_items": len(self.orchestrator.validator.validated_data),
                "knowledge_units": len(knowledge_units),
                "experiences": len(experiences)
            },
            "domain_stats": {},
            "error_summary": self.error_handler.get_error_summary()
        }
        
        # Add domain-specific stats
        for domain in self.config['domains']:
            validated_domain_items = [item for item in self.orchestrator.validator.validated_data 
                                     if item['metadata']['domain'] == domain]
            
            domain_knowledge_units = [unit for unit in knowledge_units 
                                     if unit['domain'] == domain]
            
            domain_experiences = [exp for exp in experiences 
                                 if exp.get('domain') == domain]
            
            report['domain_stats'][domain] = {
                "priority": self.config['domains'][domain]['priority'],
                "sources": len(self.config['domains'][domain]['sources']),
                "validated_items": len(validated_domain_items),
                "knowledge_units": len(domain_knowledge_units),
                "experiences": len(domain_experiences)
            }
        
        # Save report
        report_path = f"/home/ubuntu/nexus_project/data_gathering/enhanced_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\nEnhanced report generated: {report_path}")
        
        # Print summary
        print("\n=== Data Gathering Results ===")
        print(f"Execution time: {execution_time:.2f} seconds")
        print(f"Raw data items: {report['results']['raw_data_items']}")
        print(f"Processed items: {report['results']['processed_items']}")
        print(f"Validated items: {report['results']['validated_items']}")
        print(f"Knowledge units created: {report['results']['knowledge_units']}")
        print(f"Experiences generated: {report['results']['experiences']}")
        print(f"Total errors: {report['error_summary']['total_errors']}")
        print("=============================\n")

def main():
    """Main function to run the enhanced data gathering system"""
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Enhanced Data Gathering System for Kali Ka')
    parser.add_argument('--domains', nargs='+', help='Specific domains to gather data from')
    parser.add_argument('--max-sources', type=int, help='Maximum sources per domain')
    parser.add_argument('--test', action='store_true', help='Run in test mode with limited sources')
    args = parser.parse_args()
    
    # Create and run the system
    system = EnhancedDataGatheringSystem()
    
    if args.test:
        # Test mode - use only one source per domain
        print("Running in TEST MODE with limited sources")
        system.run(max_sources_per_domain=1)
    else:
        # Normal mode
        system.run(domains=args.domains, max_sources_per_domain=args.max_sources)

if __name__ == "__main__":
    main()
