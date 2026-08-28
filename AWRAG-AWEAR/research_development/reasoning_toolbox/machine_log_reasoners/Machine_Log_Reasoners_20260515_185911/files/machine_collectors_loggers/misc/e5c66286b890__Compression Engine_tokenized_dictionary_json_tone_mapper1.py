import os
import json
import numpy as np
import time
from tqdm import tqdm

def binary_to_frequency(binary_code):
    """Converts binary code to a unique frequency in Hz."""
    return int(binary_code, 2) % 20000 + 100  # Ensures frequency is within 100Hz-20kHz

def process_json_file(input_path):
    """Reads a JSON dictionary file, assigns tones to words, and returns updated data."""
    with open(input_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    for word, details in data.items():
        if "binary" in details:
            details["tone_frequency"] = binary_to_frequency(details["binary"])
    
    return data

def process_directory(directory):
    """Processes all JSON files in the given directory, updates in RAM, and saves them efficiently."""
    tonal_dir = os.path.join(directory, "tonal_additions")
    os.makedirs(tonal_dir, exist_ok=True)
    
    json_files = [f for f in os.listdir(directory) if f.endswith(".json")]
    total_files = len(json_files)
    
    print(f"Processing {total_files} files...")
    start_time = time.time()
    
    for filename in tqdm(json_files, desc="Processing Files", unit="file"):
        input_path = os.path.join(directory, filename)
        output_path = os.path.join(tonal_dir, filename)
        
        updated_data = process_json_file(input_path)  # Process in RAM
        
        with open(output_path, 'w', encoding='utf-8') as file:
            json.dump(updated_data, file, indent=4, ensure_ascii=False)  # Save to disk
    
    end_time = time.time()
    print(f"Processing complete. Updated files saved in 'tonal_additions'.")
    print(f"Total time taken: {end_time - start_time:.2f} seconds")

# Example usage:
process_directory(r"E:\Compression Engine\tokenized_dictionary")

