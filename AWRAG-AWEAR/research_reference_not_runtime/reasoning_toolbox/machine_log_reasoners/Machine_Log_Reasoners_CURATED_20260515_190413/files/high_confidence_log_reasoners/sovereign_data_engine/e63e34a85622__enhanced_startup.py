"""
Enhanced Interactive Startup with Targeting Options
"""

import os
from typing import Dict, Any, Tuple, Optional, List

class EnhancedInteractiveStartup:
    """Enhanced startup with targeting capabilities"""
    
    def __init__(self):
        self.modes = {
            '1': 'yaml_config',
            '2': 'manual_config', 
            '3': 'global_scan',
            '4': 'targeted_analysis'
        }
    
    def run_startup(self) -> Tuple[str, Dict[str, Any]]:
        """
        Run enhanced interactive startup process
        
        Returns:
            Tuple of (mode, configuration)
        """
        print("\n" + "="*60)
        print("SOVEREIGN DATA COGNITION ENGINE MVP")
        print("Advanced Genomic Analysis with Intelligent Targeting")
        print("="*60)
        print("\nStartup Configuration Options:")
        print("1. Use YAML Configuration File")
        print("2. Manual N-1-N Configuration")
        print("3. Global Scan Mode (for massive datasets)")
        print("4. Targeted Analysis (pre-programmed genomic targets)")
        
        mode = self._get_mode_selection()
        
        if mode == 'yaml_config':
            return mode, self._configure_yaml_mode()
        elif mode == 'manual_config':
            return mode, self._configure_manual_mode()
        elif mode == 'global_scan':
            return mode, self._configure_global_scan_mode()
        elif mode == 'targeted_analysis':
            return mode, self._configure_targeted_analysis_mode()
        else:
            raise ValueError(f"Invalid mode: {mode}")
    
    def _get_mode_selection(self) -> str:
        """Get user's mode selection"""
        while True:
            try:
                choice = input("\nSelect mode (1-4): ").strip()
                if choice in self.modes:
                    return self.modes[choice]
                else:
                    print("Invalid choice. Please select 1, 2, 3, or 4.")
            except KeyboardInterrupt:
                print("\nExiting...")
                exit(0)
    
    def _configure_targeted_analysis_mode(self) -> Dict[str, Any]:
        """Configure targeted analysis mode"""
        print("\n--- Targeted Analysis Mode ---")
        print("This mode uses pre-programmed genomic targets for intelligent analysis")
        print("Perfect for massive datasets (trillions of genomes)")
        
        config = {}
        
        # Get data file
        config['data_file'] = self._get_data_file()
        
        # Get dataset size estimate for optimization
        config['estimated_size'] = self._get_dataset_size_estimate()
        
        # Get target selection
        config['target_selection'] = self._get_target_selection()
        
        # Get targeting parameters
        config.update(self._get_targeting_parameters())
        
        # Get follow pattern options
        config['follow_patterns'] = self._get_follow_pattern_options()
        
        # Get cascade configuration for targets
        config.update(self._get_target_cascade_config())
        
        return config
    
    def _get_dataset_size_estimate(self) -> str:
        """Get user's estimate of dataset size"""
        print("\nDataset Size Estimation (for optimization):")
        print("1. Small (< 1 million characters)")
        print("2. Medium (1 million - 1 billion characters)")
        print("3. Large (1 billion - 1 trillion characters)")
        print("4. Massive (> 1 trillion characters)")
        
        size_map = {
            '1': 'small',
            '2': 'medium', 
            '3': 'large',
            '4': 'massive'
        }
        
        while True:
            choice = input("Select dataset size (1-4): ").strip()
            if choice in size_map:
                return size_map[choice]
            else:
                print("Invalid choice. Please select 1, 2, 3, or 4.")
    
    def _get_target_selection(self) -> Dict[str, Any]:
        """Get target selection from user"""
        print("\nTarget Selection:")
        print("Available pre-programmed targets:")
        
        available_targets = {
            '1': {'name': 'Essential Genes', 'targets': ['start_codon', 'stop_codon', 'TATA_box']},
            '2': {'name': 'Regulatory Elements', 'targets': ['TATA_box', 'CAAT_box', 'GC_box', 'CpG_island']},
            '3': {'name': 'Splice Sites', 'targets': ['splice_donor', 'start_codon', 'stop_codon']},
            '4': {'name': 'Repetitive Elements', 'targets': ['tandem_repeat', 'CpG_island']},
            '5': {'name': 'All Targets', 'targets': None},
            '6': {'name': 'Custom Selection', 'targets': 'custom'}
        }
        
        for key, value in available_targets.items():
            print(f"{key}. {value['name']}")
        
        while True:
            choice = input("Select target group (1-6): ").strip()
            if choice in available_targets:
                selection = available_targets[choice]
                if selection['targets'] == 'custom':
                    return self._get_custom_target_selection()
                else:
                    return {
                        'target_group': selection['name'],
                        'target_types': selection['targets']
                    }
            else:
                print("Invalid choice. Please select 1-6.")
    
    def _get_custom_target_selection(self) -> Dict[str, Any]:
        """Get custom target selection"""
        print("\nCustom Target Selection:")
        print("Available individual targets:")
        
        all_targets = [
            'TATA_box', 'start_codon', 'stop_codon', 'splice_donor',
            'CpG_island', 'poly_A_signal', 'ribosome_binding',
            'CAAT_box', 'GC_box', 'tandem_repeat'
        ]
        
        for i, target in enumerate(all_targets, 1):
            print(f"{i}. {target}")
        
        print("\nEnter target numbers separated by commas (e.g., 1,2,5):")
        while True:
            try:
                choices = input("Target selection: ").strip().split(',')
                selected_indices = [int(choice.strip()) - 1 for choice in choices]
                
                if all(0 <= idx < len(all_targets) for idx in selected_indices):
                    selected_targets = [all_targets[idx] for idx in selected_indices]
                    return {
                        'target_group': 'Custom',
                        'target_types': selected_targets
                    }
                else:
                    print("Invalid selection. Please use numbers 1-10.")
            except ValueError:
                print("Invalid format. Please use numbers separated by commas.")
    
    def _get_targeting_parameters(self) -> Dict[str, Any]:
        """Get targeting parameters"""
        config = {}
        
        print("\nTargeting Parameters:")
        
        # Priority threshold
        while True:
            try:
                threshold = int(input("Minimum target priority (1-10, higher = more important): "))
                if 1 <= threshold <= 10:
                    config['priority_threshold'] = threshold
                    break
                else:
                    print("Priority must be between 1 and 10.")
            except ValueError:
                print("Please enter a valid integer.")
        
        # Max hits per target type
        while True:
            try:
                max_hits = int(input("Maximum hits per target type (recommended: 100-1000): "))
                if max_hits > 0:
                    config['max_hits_per_target'] = max_hits
                    break
                else:
                    print("Max hits must be positive.")
            except ValueError:
                print("Please enter a valid integer.")
        
        # Confidence threshold
        while True:
            try:
                confidence = float(input("Minimum confidence threshold (0.0-1.0): "))
                if 0.0 <= confidence <= 1.0:
                    config['confidence_threshold'] = confidence
                    break
                else:
                    print("Confidence must be between 0.0 and 1.0.")
            except ValueError:
                print("Please enter a valid number.")
        
        return config
    
    def _get_follow_pattern_options(self) -> Dict[str, Any]:
        """Get pattern following options"""
        print("\nPattern Following Options:")
        
        follow = input("Enable pattern following? (y/n): ").strip().lower() == 'y'
        
        if not follow:
            return {'enabled': False}
        
        config = {'enabled': True}
        
        # Follow distance
        while True:
            try:
                distance = int(input("Follow distance (base pairs, recommended: 500-2000): "))
                if distance > 0:
                    config['follow_distance'] = distance
                    break
                else:
                    print("Follow distance must be positive.")
            except ValueError:
                print("Please enter a valid integer.")
        
        # Follow strategy
        print("\nFollow Strategy:")
        print("1. Related targets only (genes -> promoters, etc.)")
        print("2. All targets within distance")
        print("3. Same target type only")
        
        strategy_map = {
            '1': 'related',
            '2': 'all',
            '3': 'same_type'
        }
        
        while True:
            choice = input("Select follow strategy (1-3): ").strip()
            if choice in strategy_map:
                config['follow_strategy'] = strategy_map[choice]
                break
            else:
                print("Invalid choice. Please select 1, 2, or 3.")
        
        return config
    
    def _get_target_cascade_config(self) -> Dict[str, Any]:
        """Get cascade configuration for targeted analysis"""
        print("\nCascade Configuration for Targets:")
        
        config = {}
        
        # Adaptive sizing
        adaptive = input("Use adaptive N-1-N sizing based on target type? (y/n): ").strip().lower() == 'y'
        config['adaptive_sizing'] = adaptive
        
        if not adaptive:
            # Manual sizing
            config.update(self._get_n1n_configuration())
        else:
            print("Adaptive sizing will automatically adjust N-1-N parameters based on target type")
            
            # Base parameters for adaptation
            while True:
                try:
                    base_width = int(input("Base width for adaptation (10-100): "))
                    if 10 <= base_width <= 100:
                        config['base_width'] = base_width
                        break
                    else:
                        print("Base width must be between 10 and 100.")
                except ValueError:
                    print("Please enter a valid integer.")
        
        # Cascade depth
        while True:
            try:
                depth = int(input("Cascade depth for target analysis (2-5 recommended): "))
                if 1 <= depth <= 10:
                    config['cascade_depth'] = depth
                    break
                else:
                    print("Cascade depth should be between 1 and 10.")
            except ValueError:
                print("Please enter a valid integer.")
        
        return config
    
    def _get_n1n_configuration(self) -> Dict[str, Any]:
        """Get N-1-N configuration from user"""
        print("\nN-1-N Configuration:")
        print("Configure the cascade structure (Left-Anchor-Right)")
        
        config = {}
        
        # Get left width
        while True:
            try:
                left_width = int(input("Enter left width (N): "))
                if left_width >= 0:
                    config['left_width'] = left_width
                    break
                else:
                    print("Left width must be non-negative.")
            except ValueError:
                print("Please enter a valid integer.")
        
        # Get anchor width
        while True:
            try:
                anchor_width = int(input("Enter anchor width (1 recommended): "))
                if anchor_width >= 1:
                    config['anchor_width'] = anchor_width
                    break
                else:
                    print("Anchor width must be at least 1.")
            except ValueError:
                print("Please enter a valid integer.")
        
        # Get right width
        while True:
            try:
                right_width = int(input("Enter right width (N): "))
                if right_width >= 0:
                    config['right_width'] = right_width
                    break
                else:
                    print("Right width must be non-negative.")
            except ValueError:
                print("Please enter a valid integer.")
        
        print(f"Configuration: {left_width}-{anchor_width}-{right_width}")
        return config
    
    def _get_data_file(self) -> str:
        """Get data file path from user"""
        while True:
            data_file = input("Enter data file path: ").strip()
            if os.path.exists(data_file):
                return data_file
            else:
                print(f"File not found: {data_file}")
                create_sample = input("Create sample genomic data file? (y/n): ").strip().lower()
                if create_sample == 'y':
                    self._create_sample_genomic_data(data_file)
                    return data_file
    
    def _create_sample_genomic_data(self, file_path: str) -> None:
        """Create sample genomic data file with targets"""
        sample_data = """GCTAGCTAGCTAGCTATAAAGCTAGCTAGCTAGCATGAAACCCGGGTTTAAAGCTAGCTAGCTAG
CCAATGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG
GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG
ATGCCCGGGTTTAAAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG
GCTAGCTAGCTAGCTAGCTATAAAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG
CCAATGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG
GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG
ATGCCCGGGTTTAAAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG
GCTAGCTAGCTAGCTAGCTATAAAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG
CCAATGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG
GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG
ATGCCCGGGTTTAAAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG
GCTAGCTAGCTAGCTAGCTATAAAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG
CCAATGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG
GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG
ATGCCCGGGTTTAAAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAG"""
        
        os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(sample_data)
        print(f"Sample genomic data created: {file_path}")
        print("Contains: TATA boxes, start codons (ATG), CAAT boxes, and other targets")
    
    # Include other methods from original InteractiveStartup class
    def _configure_yaml_mode(self) -> Dict[str, Any]:
        """Configure YAML mode"""
        print("\n--- YAML Configuration Mode ---")
        
        while True:
            yaml_path = input("Enter YAML configuration file path: ").strip()
            if os.path.exists(yaml_path):
                return {'yaml_path': yaml_path}
            else:
                print(f"File not found: {yaml_path}")
                retry = input("Try again? (y/n): ").strip().lower()
                if retry != 'y':
                    print("Switching to manual configuration...")
                    return self._configure_manual_mode()
    
    def _configure_manual_mode(self) -> Dict[str, Any]:
        """Configure manual N-1-N mode"""
        print("\n--- Manual N-1-N Configuration Mode ---")
        
        config = {}
        
        # Get data file
        config['data_file'] = self._get_data_file()
        
        # Get N-1-N configuration
        config.update(self._get_n1n_configuration())
        
        # Get data type
        config['data_type'] = self._get_data_type()
        
        # Get function configuration
        config.update(self._get_function_configuration())
        
        # Get cascade depth
        config['cascade_depth'] = self._get_cascade_depth()
        
        return config
    
    def _configure_global_scan_mode(self) -> Dict[str, Any]:
        """Configure global scan mode for massive datasets"""
        print("\n--- Global Scan Mode ---")
        print("This mode performs pre-analysis on massive datasets")
        print("to identify patterns before targeted analysis.")
        
        config = {}
        
        # Get data file
        config['data_file'] = self._get_data_file()
        
        # Get scan parameters
        config['scan_sample_size'] = self._get_scan_sample_size()
        config['scan_window_size'] = self._get_scan_window_size()
        config['pattern_threshold'] = self._get_pattern_threshold()
        
        # Ask if user wants to proceed to targeted analysis
        proceed = input("\nAfter global scan, proceed to targeted analysis? (y/n): ").strip().lower()
        config['proceed_to_targeted'] = proceed == 'y'
        
        if config['proceed_to_targeted']:
            print("Targeted analysis will use results from global scan to configure N-1-N parameters.")
        
        return config
    
    def _get_data_type(self) -> str:
        """Get data type from user"""
        data_types = ['genome', 'text', 'tabular', 'custom']
        print(f"\nAvailable data types: {', '.join(data_types)}")
        
        while True:
            data_type = input("Enter data type: ").strip().lower()
            if data_type in data_types:
                return data_type
            else:
                print(f"Invalid data type. Choose from: {', '.join(data_types)}")
    
    def _get_function_configuration(self) -> Dict[str, Any]:
        """Get function configuration from user"""
        config = {}
        
        print("\nFunction Configuration:")
        config['anchor_function'] = input("Enter anchor function name (e.g., anchor_genome): ").strip()
        config['bloom_function'] = input("Enter bloom function name (e.g., bloom_genome): ").strip()
        
        return config
    
    def _get_cascade_depth(self) -> int:
        """Get cascade depth from user"""
        while True:
            try:
                depth = int(input("Enter cascade depth (2-5 recommended): "))
                if 1 <= depth <= 10:
                    return depth
                else:
                    print("Cascade depth should be between 1 and 10.")
            except ValueError:
                print("Please enter a valid integer.")
    
    def _get_scan_sample_size(self) -> int:
        """Get scan sample size for global scan mode"""
        while True:
            try:
                size = int(input("Enter sample size for global scan (e.g., 10000): "))
                if size > 0:
                    return size
                else:
                    print("Sample size must be positive.")
            except ValueError:
                print("Please enter a valid integer.")
    
    def _get_scan_window_size(self) -> int:
        """Get scan window size for global scan mode"""
        while True:
            try:
                size = int(input("Enter scan window size (e.g., 100): "))
                if size > 0:
                    return size
                else:
                    print("Window size must be positive.")
            except ValueError:
                print("Please enter a valid integer.")
    
    def _get_pattern_threshold(self) -> float:
        """Get pattern threshold for global scan mode"""
        while True:
            try:
                threshold = float(input("Enter pattern detection threshold (0.0-1.0): "))
                if 0.0 <= threshold <= 1.0:
                    return threshold
                else:
                    print("Threshold must be between 0.0 and 1.0.")
            except ValueError:
                print("Please enter a valid number.")


    def generate_yaml_from_manual(self, config: Dict[str, Any]) -> str:
        """Generate YAML configuration from manual settings"""
        yaml_content = f"""# Sovereign Data Cognition Engine Configuration
# Generated from manual configuration

data_type: {config.get('data_type', 'text')}
left_width: {config.get('left_width', 10)}
right_width: {config.get('right_width', 10)}
anchor_width: {config.get('anchor_width', 1)}
anchor_function: {config.get('anchor_function', 'anchor_auto')}
bloom_function: {config.get('bloom_function', 'bloom_auto')}
cascade_depth: {config.get('cascade_depth', 2)}
processing_mode: manual_config

# Optional settings
fields:
  - field1
  - field2
  - field3

# Performance settings
optimization:
  enable_sampling: true
  sample_rate: {config.get('sample_rate', 100)}
  
# Output settings
output:
  format: markdown
  include_analysis: true
  save_results: true
"""
        return yaml_content
    
    def save_yaml_config(self, config: Dict[str, Any], filename: str = None) -> str:
        """Save configuration as YAML file"""
        if filename is None:
            filename = f"config_manual_{config.get('left_width', 10)}-{config.get('anchor_width', 1)}-{config.get('right_width', 10)}.yaml"
        
        yaml_content = self.generate_yaml_from_manual(config)
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(yaml_content)
            print(f"✅ Configuration saved to: {filename}")
            return filename
        except Exception as e:
            print(f"❌ Error saving YAML: {e}")
            return ""

