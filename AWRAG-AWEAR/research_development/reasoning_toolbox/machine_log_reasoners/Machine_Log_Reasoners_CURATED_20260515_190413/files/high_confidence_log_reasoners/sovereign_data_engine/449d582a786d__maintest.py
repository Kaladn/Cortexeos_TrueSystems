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
        startup = EnhancedInteractiveStartup()
        mode, config = startup.run_startup()

        print(f"\n--- Running in {mode.replace('_', ' ').title()} Mode ---")

        data_loader = DataLoader()
        output_generator = OutputGenerator()

        print("Initializing mandatory pre-scan...")
        prescan = MandatoryPreScan()

        if mode == 'yaml_config':
            yaml_parser = YAMLParser()
            temp_config = yaml_parser.parse_config(config['yaml_path'])
            data = data_loader.load_data(temp_config['data_file'])
        else:
            data = data_loader.load_data(config['data_file'])

        global_mapping = prescan.perform_mandatory_scan(data, config)

        if mode == 'global_scan':
            print("Running global scan...")
            global_scanner = GlobalScanner()
            scan_results = global_scanner.perform_global_scan(data, config)
            global_mapping['scan_results'] = scan_results

        print("\n--- INTELLIGENT RECOMMENDATIONS ---")
        recommendations = global_mapping.get('recommendations', {})

        use_recommendations = input("\nUse AI-recommended configuration? (y/n): ").strip().lower()

        if use_recommendations == 'y':
            n1n_cfg = recommendations.get('optimal_n1n_config', {})
            config.update({
                'left_width': n1n_cfg.get('left_width', 10),
                'anchor_width': n1n_cfg.get('anchor_width', 1),
                'right_width': n1n_cfg.get('right_width', 10),
                'cascade_depth': recommendations.get('cascade_depth', {}).get('recommended_depth', 3),
                'target_selection': recommendations.get('target_selection', {}),
                'processing_mode_override': recommendations.get('processing_mode', {}).get('recommended_mode', 'default')
            })

        if mode == 'yaml_config':
            if 'yaml_path' in config:
                yaml_parser = YAMLParser()
                yaml_config = yaml_parser.parse_config(config['yaml_path'])
                if use_recommendations == 'y':
                    yaml_config.update(config)
                config = yaml_config

        elif mode == 'manual_config':
            save_yaml = input("\nSave configuration as YAML file? (y/n): ").strip().lower()
            if save_yaml == 'y':
                yaml_path = startup.generate_yaml_from_manual(config)
                print(f"Configuration saved to: {yaml_path}")

        elif mode == 'global_scan':
            scan_results = global_mapping.get('scan_results')

            if not scan_results:
                raise ValueError("Global scan failed to generate 'scan_results'. Please ensure your scanner is functioning.")

            if config.get('proceed_to_targeted'):
                n1n = recommendations.get('optimal_n1n_config', {})
                config.update({
                    'left_width': n1n.get('left_width', 10),
                    'anchor_width': n1n.get('anchor_width', 1),
                    'right_width': n1n.get('right_width', 10),
                    'cascade_depth': recommendations.get('cascade_depth', {}).get('recommended_depth', 3),
                    'data_type': 'auto_detected'
                })
                print("\n--- Proceeding to Targeted Analysis with AI Recommendations ---")
                modify = input("Modify recommended configuration? (y/n): ").strip().lower()
                if modify == 'y':
                    config = modify_config_interactive(config)

                mode = 'targeted_analysis'
            else:
                output = output_generator.generate_scan_report(scan_results)
                print("\n--- Global Scan Complete ---")
                print(output)
                return

        if mode == 'targeted_analysis':
            target_system = TargetSystem()
            target_config = recommendations.get('target_selection', {})
            config.update(target_config)

            data_size = len(data)
            optimization_params = target_system.optimize_for_massive_datasets(data_size)

            print(f"\nDataset size: {data_size:,} characters")
            print(f"Optimization: {config.get('estimated_size', 'unknown')} dataset mode")

            if data_size > 1e9:
                target_hits = target_system.process_massive_dataset(data, optimization_params, global_mapping)
            else:
                target_hits = target_system.scan_for_targets(
                    data,
                    target_types=config['target_selection'].get('primary_targets', []),
                    max_hits=config.get('max_hits_per_target', 100),
                    prescan_results=global_mapping
                )

            filtered_hits = [hit for hit in target_hits if hit.confidence >= config.get('confidence_threshold', 0.5)]

            print(f"Found {len(target_hits)} total targets, {len(filtered_hits)} above confidence threshold")

            if config.get('follow_patterns', {}).get('enabled', False):
                print("Following target patterns...")
                all_hits = []
                for hit in filtered_hits[:10]:
                    related_hits = target_system.follow_target_pattern(
                        data, hit, config['follow_patterns'].get('follow_distance', 50)
                    )
                    all_hits.extend(related_hits)
                all_hits.extend(filtered_hits)
                target_hits = target_system._remove_duplicate_hits(all_hits)
                print(f"Pattern following found {len(target_hits)} total targets")
            else:
                target_hits = filtered_hits

            if config.get('adaptive_sizing', False):
                cascade_configs = target_system.create_target_cascade_config(target_hits, config)
            else:
                cascade_configs = [config.copy() for _ in target_hits]

            all_results = []
            cascade_engine = CascadeEngine()

            for i, (hit, cascade_config) in enumerate(zip(target_hits, cascade_configs)):
                print(f"Processing target {i+1}/{len(target_hits)}: {hit.region.name} at position {hit.position}")
                start_pos = max(0, hit.position - hit.region.context_left)
                end_pos = min(len(data), hit.position + len(hit.sequence) + hit.region.context_right)
                target_data = data[start_pos:end_pos]
                target_results = cascade_engine.process(target_data, cascade_config)
                for result in target_results:
                    result['target_info'] = {
                        'name': hit.region.name,
                        'position': hit.position,
                        'confidence': hit.confidence,
                        'region_type': hit.region.region_type
                    }
                all_results.extend(target_results)

            target_stats = target_system.get_target_statistics(target_hits)
            print("\nTarget Analysis Complete:")
            print(f"  Total targets processed: {target_stats.get('total_hits', 0)}")
            print(f"  High confidence targets: {target_stats.get('high_confidence_hits', 0)}")
            print(f"  Average confidence: {target_stats.get('average_confidence', 0):.2f}")

            results = all_results
            output = output_generator.generate_output({
                'cascade_results': results,
                'target_results': target_hits,
                'prescan_results': global_mapping,
                'data_length': len(data),
                'segments_processed': len(results),
                'cascade_levels': config.get('cascade_depth', 0),
            }, config, config.get('output_format', 'markdown'))
            print("\n--- Final Results ---")
            print(output)

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nError: {e}")
        print("Please check your configuration and try again.")

def modify_config_interactive(config):
    print("\nCurrent Configuration:")
    for key, value in config.items():
        if key not in ['scan_results', 'data_file']:
            print(f"  {key}: {value}")

    print("\nModify configuration (press Enter to keep current value):")

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
