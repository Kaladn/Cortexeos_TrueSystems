"""
Sovereign Data Cognition Engine MVP
Main application entry point with interactive startup
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from startup.enhanced_startup import EnhancedInteractiveStartup
from targeting.target_system import TargetSystem
from prescan.mandatory_prescan import MandatoryPreScan
from scanner.global_scanner import GlobalScanner
from loader.data_loader import DataLoader
from parser.yaml_parser import YAMLParser
from engine.cascade_engine import CascadeEngine
from output.output_generator import OutputGenerator

def main():
    """Main application entry point with interactive startup"""
    try:
        # Interactive startup
        startup = EnhancedInteractiveStartup()
        mode, config = startup.run_startup()
        
        print(f"\n--- Running in {mode.replace('_', ' ').title()} Mode ---")
        
        # Initialize components
        data_loader = DataLoader()
        output_generator = OutputGenerator()
        
        # MANDATORY PRE-SCAN - Always performed first
        print("Initializing mandatory pre-scan...")
        prescan = MandatoryPreScan()
        
        # Load data first for pre-scan
        if mode == 'yaml_config':
            yaml_parser = YAMLParser()
            temp_config = yaml_parser.parse_config(config['yaml_path'])
            data = data_loader.load_data(temp_config['data_file'])
        else:
            data = data_loader.load_data(config['data_file'])
        
        # Perform mandatory pre-scan
        global_mapping = prescan.perform_mandatory_scan(data, config)
        
        # Present recommendations to user
        print("\n--- INTELLIGENT RECOMMENDATIONS ---")
        recommendations = global_mapping['recommendations']
        
        # Ask user if they want to use AI recommendations
        use_recommendations = input("\nUse AI-recommended configuration? (y/n): ").strip().lower()
        
        if use_recommendations == 'y':
            # Override user config with AI recommendations
            config.update({
                'left_width': recommendations['optimal_n1n_config']['left_width'],
                'anchor_width': recommendations['optimal_n1n_config']['anchor_width'],
                'right_width': recommendations['optimal_n1n_config']['right_width'],
                'cascade_depth': recommendations['cascade_depth']['recommended_depth'],
                'target_selection': recommendations['target_selection'],
                'processing_mode_override': recommendations['processing_mode']['recommended_mode']
            })
            print("Configuration updated with AI recommendations.")
        else:
            print("Using original user configuration.")
            # Still add pre-scan results for reference
            config['prescan_results'] = global_mapping
        
        if mode == 'yaml_config':
            # YAML configuration mode (data already loaded for pre-scan)
            if 'yaml_path' in config:
                yaml_parser = YAMLParser()
                yaml_config = yaml_parser.parse_config(config['yaml_path'])
                # Merge YAML config with pre-scan recommendations if user accepted them
                if use_recommendations == 'y':
                    yaml_config.update(config)
                config = yaml_config
            
        elif mode == 'manual_config':
            # Manual configuration mode (data already loaded for pre-scan)
            
            # Optionally save manual config as YAML
            save_yaml = input("\nSave configuration as YAML file? (y/n): ").strip().lower()
            if save_yaml == 'y':
                yaml_path = startup.generate_yaml_from_manual(config)
                print(f"Configuration saved to: {yaml_path}")
            
        elif mode == 'global_scan':
            # Global scan mode (data already loaded for pre-scan)
            # The mandatory pre-scan already provides comprehensive analysis
            # Use pre-scan results as the global scan results
            scan_results = global_mapping['scan_results']
            
            if config.get('proceed_to_targeted'):
                # Create targeted configuration from pre-scan results
                # Use the AI recommendations from mandatory pre-scan
                config.update({
                    'left_width': recommendations['optimal_n1n_config']['left_width'],
                    'anchor_width': recommendations['optimal_n1n_config']['anchor_width'],
                    'right_width': recommendations['optimal_n1n_config']['right_width'],
                    'cascade_depth': recommendations['cascade_depth']['recommended_depth'],
                    'data_type': 'auto_detected'
                })
                print("\n--- Proceeding to Targeted Analysis with AI Recommendations ---")
                
                # Ask user to review/modify recommendations
                modify = input("Modify recommended configuration? (y/n): ").strip().lower()
                if modify == 'y':
                    config = modify_config_interactive(config)
            else:
                # Just output scan results
                output = output_generator.generate_scan_report(scan_results)
                print("\n--- Global Scan Complete ---")
                print(output)
                return
        
        elif mode == 'targeted_analysis':
            # Targeted analysis mode (data already loaded for pre-scan)
            
            # Initialize targeting system
            target_system = TargetSystem()
            
            # Use AI recommendations for targeting
            target_config = recommendations['target_selection']
            config.update(target_config)
            
            # Optimize for dataset size using pre-scan results
            data_size = len(data)
            optimization_params = target_system.optimize_for_massive_datasets(data_size)
            
            print(f"\nDataset size: {data_size:,} characters")
            print(f"Optimization: {config.get('estimated_size', 'unknown')} dataset mode")
            
            # Scan for targets using AI recommendations
            if data_size > 1e9:  # Use chunked processing for large datasets
                target_hits = target_system.process_massive_dataset(data, optimization_params, global_mapping)
            else:
                target_hits = target_system.scan_for_targets(
                    data, 
                    target_types=config['target_selection']['primary_targets'],
                    max_hits=config.get('max_hits_per_target', 100),
                    prescan_results=global_mapping
                )
            
            # Filter by confidence threshold
            filtered_hits = [hit for hit in target_hits if hit.confidence >= config['confidence_threshold']]
            
            print(f"Found {len(target_hits)} total targets, {len(filtered_hits)} above confidence threshold")
            
            # Follow patterns if enabled
            if config['follow_patterns']['enabled']:
                print("Following target patterns...")
                all_hits = []
                for hit in filtered_hits[:10]:  # Limit pattern following for performance
                    related_hits = target_system.follow_target_pattern(
                        data, hit, config['follow_patterns']['follow_distance']
                    )
                    all_hits.extend(related_hits)
                
                # Combine and deduplicate
                all_hits.extend(filtered_hits)
                target_hits = target_system._remove_duplicate_hits(all_hits)
                print(f"Pattern following found {len(target_hits)} total targets")
            else:
                target_hits = filtered_hits
            
            # Create cascade configurations for each target
            if config['adaptive_sizing']:
                cascade_configs = target_system.create_target_cascade_config(target_hits, config)
            else:
                # Use manual configuration for all targets
                cascade_configs = [config.copy() for _ in target_hits]
            
            # Process each target through cascade engine
            all_results = []
            cascade_engine = CascadeEngine()
            
            for i, (hit, cascade_config) in enumerate(zip(target_hits, cascade_configs)):
                print(f"Processing target {i+1}/{len(target_hits)}: {hit.region.name} at position {hit.position}")
                
                # Extract target region with context
                start_pos = max(0, hit.position - hit.region.context_left)
                end_pos = min(len(data), hit.position + len(hit.sequence) + hit.region.context_right)
                target_data = data[start_pos:end_pos]
                
                # Process through cascade engine
                target_results = cascade_engine.process(target_data, cascade_config)
                
                # Add target metadata to results
                for result in target_results:
                    result['target_info'] = {
                        'name': hit.region.name,
                        'position': hit.position,
                        'confidence': hit.confidence,
                        'region_type': hit.region.region_type
                    }
                
                all_results.extend(target_results)
            
            # Generate target statistics
            target_stats = target_system.get_target_statistics(target_hits)
            print(f"\nTarget Analysis Complete:")
            print(f"  Total targets processed: {target_stats.get('total_hits', 0)}")
            print(f"  High confidence targets: {target_stats.get('high_confidence_hits', 0)}")
            print(f"  Average confidence: {target_stats.get('average_confidence', 0):.2f}")
            
            results = all_results
        
        # Validate data (skip for targeted analysis as it's already processed)
        if mode != 'targeted_analysis':
            if not data_loader.validate_data(data, config.get('data_type', 'unknown')):
                print("Warning: Data validation failed. Proceeding anyway...")
        
        # Process through cascade engine (skip for targeted analysis as it's already done)
        if mode != 'targeted_analysis':
            cascade_engine = CascadeEngine()
            print(f"\nProcessing data through cascade engine...")
            print(f"Configuration: {config.get('left_width', 'N/A')}-{config.get('anchor_width', 'N/A')}-{config.get('right_width', 'N/A')}")
            
            results = cascade_engine.process(data, config)
            print(f"Processing complete: {len(results)} results generated")
        
        # Generate output with comprehensive formatting
        print("\n--- Generating Results ---")
        
        # Prepare results data
        final_results = {
            'cascade_results': results if isinstance(results, list) else [],
            'bloom_results': {},
            'anchor_results': {},
            'target_results': target_hits if mode == 'targeted_analysis' else [],
            'prescan_results': global_mapping if 'global_mapping' in locals() else {},
            'data_length': len(data),
            'segments_processed': len(results) if isinstance(results, list) else 0,
            'cascade_levels': config.get('cascade_depth', 0),
            'performance_metrics': {
                'total_time': 0,  # Would be calculated in real implementation
                'characters_per_second': 0,
                'memory_usage_ratio': 0,
                'cpu_utilization': 0
            }
        }
        
        # Generate output in requested format
        output_format = config.get('output_format', 'markdown')
        output = output_generator.generate_output(final_results, config, output_format)
        
        print("\n--- Final Results ---")
        if output_format == 'json':
            print("Results generated in JSON format")
        elif output_format == 'markdown':
            print(output)
        else:
            print(f"Results generated in {output_format} format")
        
        # Generate summary report
        summary = output_generator.generate_summary_report(final_results, config)
        print("\n--- Summary Report ---")
        print(summary)
        
        # Ask if user wants to save results
        save_results = input("\nSave results to file? (y/n): ").strip().lower()
        if save_results == 'y':
            # Ask for output format if not already specified
            if 'output_format' not in config:
                print("\nAvailable output formats: json, yaml, xml, csv, markdown, html")
                output_format = input("Choose output format (default: json): ").strip().lower()
                if output_format not in ['json', 'yaml', 'xml', 'csv', 'markdown', 'html']:
                    output_format = 'json'
            else:
                output_format = config['output_format']
            
            # Generate output in chosen format
            final_output = output_generator.generate_output(final_results, config, output_format)
            
            output_file = input(f"Enter output filename (default: results.{output_format}): ").strip()
            if not output_file:
                output_file = f"results.{output_format}"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(final_output)
            print(f"Results saved to: {output_file}")
            
            # Also save summary report
            summary_file = output_file.replace(f'.{output_format}', '_summary.md')
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary)
            print(f"Summary report saved to: {summary_file}")
        
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nError: {e}")
        print("Please check your configuration and try again.")

def modify_config_interactive(config):
    """Allow user to interactively modify configuration"""
    print("\nCurrent Configuration:")
    for key, value in config.items():
        if key not in ['scan_results', 'data_file']:
            print(f"  {key}: {value}")
    
    print("\nModify configuration (press Enter to keep current value):")
    
    # Modifiable parameters
    modifiable = ['left_width', 'right_width', 'anchor_width', 'cascade_depth']
    
    for param in modifiable:
        if param in config:
            current = config[param]
            new_value = input(f"{param} (current: {current}): ").strip()
            if new_value:
                try:
                    config[param] = int(new_value)
                except ValueError:
                    print(f"Invalid value for {param}, keeping current value.")
    
    return config

if __name__ == "__main__":
    main()
