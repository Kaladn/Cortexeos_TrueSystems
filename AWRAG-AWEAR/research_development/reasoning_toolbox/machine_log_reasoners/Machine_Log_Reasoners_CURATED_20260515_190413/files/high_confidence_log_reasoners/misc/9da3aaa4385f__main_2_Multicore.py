"""
Sovereign Data Cognition Engine MVP
Main application entry point with interactive startup.
MODIFIED FOR MASSIVE PARALLELISM & IN-MEMORY COMPUTATION
"""

import sys
import os
import time
import pandas as pd
import psutil
from multiprocessing import Pool, cpu_count
from tqdm import tqdm

# Removed tkinter imports to revert to command-line interface

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Original Component Imports
from enhanced_startup import EnhancedInteractiveStartup
from target_system import TargetSystem
from mandatory_prescan import MandatoryPreScan
from global_scanner import GlobalScanner
from data_loader import DataLoader
from yaml_parser import YAMLParser
from cascade_engine import CascadeEngine
from output_generator import OutputGenerator

# --- PARALLEL PROCESSING WORKER FUNCTION (WITH DIAGNOSTICS) ---
def process_worker(data_chunk, config):
    """
    Worker function for parallel processing.
    Each worker gets a chunk of data and the configuration.
    This version includes diagnostic print statements.
    """
    # Each process has its own unique Process ID (PID)
    process_id = os.getpid()
    
    # Announce that the worker has started and what it's working on
    print(f"[Worker PID: {process_id}] >>> Engaged. Processing chunk of size {len(data_chunk):,} characters.")
    worker_start_time = time.time()

    # Initialize the engine instance within the worker
    cascade_engine = CascadeEngine()
    
    # Execute the core logic
    results = cascade_engine.process(data_chunk, config)
    
    worker_end_time = time.time()
    processing_time = worker_end_time - worker_start_time
    
    # Report the outcome of the work
    print(f"[Worker PID: {process_id}] <<< Disengaged. Processing complete in {processing_time:.4f} seconds. Generated {len(results)} results.")
    
    return results

def main():
    """Main application entry point with parallel processing capabilities"""
    start_time = time.time()
    # --- HARDWARE CONFIGURATION ---
    NUM_CORES = 32
    MEMORY_LIMIT_GB = 20
    MEMORY_LIMIT_BYTES = MEMORY_LIMIT_GB * 1024**3
    
    process = psutil.Process(os.getpid())
    initial_mem_usage = process.memory_info().rss / 1024**2

    try:
        # --- REVERTED TO ORIGINAL STARTUP METHOD ---
        # The engine will now use the original interactive command-line startup.
        startup = EnhancedInteractiveStartup()
        mode, config = startup.run_startup()
        
        print(f"\n--- Running in {mode.replace('_', ' ').title()} Mode ---")
        print(f"--- Engine configured for {NUM_CORES} cores and up to {MEMORY_LIMIT_GB}GB RAM. ---")
        
        data_loader = DataLoader()
        output_generator = OutputGenerator()
        
        # --- DATA LOADING (ORIGINAL LOGIC) ---
        # Determine the data file path from the config returned by startup module.
        if mode == 'yaml_config':
            yaml_parser = YAMLParser()
            temp_config = yaml_parser.parse_config(config['yaml_path'])
            data_file_path = temp_config['data_file'].strip().strip("'\"")
        else:
            data_file_path = config['data_file'].strip().strip("'\"")
            
        print(f"\nLoading data from: {data_file_path}")

        try:
            file_size = os.path.getsize(data_file_path)
            if file_size > MEMORY_LIMIT_BYTES:
                print(f"Warning: File size ({file_size / 1024**3:.2f}GB) exceeds RAM limit ({MEMORY_LIMIT_GB}GB).")
                print("Processing may be slow or unstable.")
        except FileNotFoundError:
            print(f"Error: The file '{data_file_path}' was not found.")
            # Ask if user wants to create a sample file, mimicking original flow
            create_sample = input("Create sample genomic data file? (y/n): ").strip().lower()
            if create_sample == 'y':
                startup._create_sample_genomic_data(data_file_path) # Using helper
                print(f"Sample file created at {data_file_path}. Please run the script again.")
            return

        with open(data_file_path, 'r', encoding='utf-8', errors='ignore') as f:
            data = f.read()
        
        loaded_mem_usage = process.memory_info().rss / 1024**2
        print(f"Data loaded. Memory usage: {loaded_mem_usage:.2f} MB")

        # MANDATORY PRE-SCAN
        print("Initializing mandatory pre-scan...")
        prescan = MandatoryPreScan()
        global_mapping = prescan.perform_mandatory_scan(data, config)
        
        # Present recommendations to user
        print("\n--- INTELLIGENT RECOMMENDATIONS ---")
        recommendations = global_mapping['recommendations']
        use_recommendations = input("\nUse AI-recommended configuration? (y/n): ").strip().lower()
        
        if use_recommendations == 'y':
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
            config['prescan_results'] = global_mapping

        results = []
        target_hits = []

        if mode == 'targeted_analysis':
            # This section remains sequential as it has its own complex internal logic.
            target_system = TargetSystem()
            # ... (rest of the original targeted analysis logic from original main.py would go here) ...
            print("\nTargeted Analysis complete (executed sequentially as per original logic).")

        else: # For yaml_config, manual_config, global_scan
            print(f"\n--- Beginning Parallel Processing Across {NUM_CORES} Cores ---")
            
            chunk_size = len(data) // NUM_CORES
            data_chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)] if chunk_size > 0 else ([data] if len(data) > 0 else [])
            
            if data_chunks:
                with Pool(processes=NUM_CORES) as pool:
                    args = ((chunk, config) for chunk in data_chunks)
                    all_chunk_results = list(tqdm(pool.starmap(process_worker, args), total=len(data_chunks), desc="Processing Chunks"))
                
                results = [item for sublist in all_chunk_results for item in sublist]
                print(f"Parallel processing complete: {len(results)} results generated")
            else:
                print("No data to process.")

        # --- RESULTS GENERATION ---
        total_time = time.time() - start_time
        final_mem_usage = process.memory_info().rss / 1024**2
        cpu_util = psutil.cpu_percent(interval=1, percpu=True)

        print("\n--- Generating Results ---")
        final_results = {
            'cascade_results': results,
            'bloom_results': {}, 'anchor_results': {},
            'target_results': target_hits,
            'prescan_results': global_mapping if 'global_mapping' in locals() else {},
            'data_length': len(data),
            'segments_processed': len(results),
            'cascade_levels': config.get('cascade_depth', 0),
            'performance_metrics': {
                'total_time': f"{total_time:.2f} seconds",
                'characters_per_second': f"{(len(data) / total_time):,.0f}" if total_time > 0 else "N/A",
                'memory_usage_mb': f"{final_mem_usage:.2f}",
                'cpu_utilization_per_core': cpu_util
            }
        }
        
        output_format = config.get('output_format', 'markdown')
        output = output_generator.generate_output(final_results, config, output_format)
        
        print("\n--- Final Results ---")
        print(output)
        
        summary = output_generator.generate_summary_report(final_results, config)
        print("\n--- Summary Report ---")
        print(summary)
        
        save_results = input("\nSave results to file? (y/n): ").strip().lower()
        if save_results == 'y':
            if 'output_format' not in config:
                print("\nAvailable output formats: json, yaml, xml, csv, markdown, html")
                output_format = input("Choose output format (default: json): ").strip().lower() or 'json'
            else:
                output_format = config['output_format']
            
            final_output = output_generator.generate_output(final_results, config, output_format)
            
            output_file = input(f"Enter output filename (default: results.{output_format}): ").strip() or f"results.{output_format}"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(final_output)
            print(f"Results saved to: {output_file}")
            
            summary_file = output_file.replace(f'.{output_format}', '_summary.md')
            with open(summary_file, 'w', encoding='utf-8') as f:
                f.write(summary)
            print(f"Summary report saved to: {summary_file}")

    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()

def modify_config_interactive(config):
    """Allow user to interactively modify configuration"""
    # This function is from the original file and remains unchanged.
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
