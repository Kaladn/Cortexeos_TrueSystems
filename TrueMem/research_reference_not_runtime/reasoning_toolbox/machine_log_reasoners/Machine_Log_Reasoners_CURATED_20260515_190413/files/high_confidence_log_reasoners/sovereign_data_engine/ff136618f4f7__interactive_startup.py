"""
Interactive Startup Module
Handles user interaction for configuration and mode selection
"""

import os
from typing import Dict, Any, Tuple, Optional

class InteractiveStartup:
    """Handles interactive startup configuration"""
    
    def __init__(self):
        self.modes = {
            '1': 'yaml_config',
            '2': 'manual_config', 
            '3': 'global_scan'
        }
    
    def run_startup(self) -> Tuple[str, Dict[str, Any]]:
        """
        Run interactive startup process
        
        Returns:
            Tuple of (mode, configuration)
        """
        print("\n" + "="*50)
        print("SOVEREIGN DATA COGNITION ENGINE MVP")
        print("="*50)
        print("\nStartup Configuration Options:")
        print("1. Use YAML Configuration File")
        print("2. Manual N-1-N Configuration")
        print("3. Global Scan Mode (for massive datasets)")
        
        mode = self._get_mode_selection()
        
        if mode == 'yaml_config':
            return mode, self._configure_yaml_mode()
        elif mode == 'manual_config':
            return mode, self._configure_manual_mode()
        elif mode == 'global_scan':
            return mode, self._configure_global_scan_mode()
        else:
            raise ValueError(f"Invalid mode: {mode}")
    
    def _get_mode_selection(self) -> str:
        """Get user's mode selection"""
        while True:
            try:
                choice = input("\nSelect mode (1-3): ").strip()
                if choice in self.modes:
                    return self.modes[choice]
                else:
                    print("Invalid choice. Please select 1, 2, or 3.")
            except KeyboardInterrupt:
                print("\nExiting...")
                exit(0)
    
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
    
    def _get_data_file(self) -> str:
        """Get data file path from user"""
        while True:
            data_file = input("Enter data file path: ").strip()
            if os.path.exists(data_file):
                return data_file
            else:
                print(f"File not found: {data_file}")
                create_sample = input("Create sample data file? (y/n): ").strip().lower()
                if create_sample == 'y':
                    self._create_sample_data(data_file)
                    return data_file
    
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
    
    def _create_sample_data(self, file_path: str) -> None:
        """Create sample data file"""
        sample_data = """ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG
GCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCTAGCT
TTAAGGCCTTAAGGCCTTAAGGCCTTAAGGCCTTAAGGCCTTAAGGCCTTAAGGCCTTAAGGCCTTAA
CCGGAATTCCGGAATTCCGGAATTCCGGAATTCCGGAATTCCGGAATTCCGGAATTCCGGAATTCCGG"""
        
        os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else '.', exist_ok=True)
        with open(file_path, 'w') as f:
            f.write(sample_data)
        print(f"Sample data created: {file_path}")
    
    def generate_yaml_from_manual(self, config: Dict[str, Any], output_path: str = "generated_config.yaml") -> str:
        """Generate YAML file from manual configuration"""
        yaml_content = f"""data_type: {config['data_type']}
left_width: {config['left_width']}
right_width: {config['right_width']}
anchor_width: {config['anchor_width']}
anchor_function: {config['anchor_function']}
bloom_function: {config['bloom_function']}
cascade_depth: {config['cascade_depth']}
data_file: {config['data_file']}
fields: []
"""
        
        with open(output_path, 'w') as f:
            f.write(yaml_content)
        
        print(f"Configuration saved to: {output_path}")
        return output_path

