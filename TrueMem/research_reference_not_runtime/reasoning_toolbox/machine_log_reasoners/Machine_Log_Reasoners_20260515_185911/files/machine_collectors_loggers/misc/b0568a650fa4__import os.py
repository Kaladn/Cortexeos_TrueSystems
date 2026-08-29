import os
import json
import time
from tqdm import tqdm  # For progress bar

# Input directory (where alphabetized JSON files are stored)
input_directory = r"A:\Compression Engine\tokenized_dictionary"
# Output file path
output_file = r"A:\Compression Engine\merged_trainable_dataset.json"

# Metadata file path
metadata_file = r"A:\Compression Engine\dataset_metadata.json"

# Storage for merged dataset
merged_data = {}

# Initialize metadata tracking
metadata = {
    "total_words": 0,
    "total_files": 0,
    "processing_time": 0
}

# Get list of files
files = sorted([f for f in os.listdir(input_directory) if f.endswith(".json")])
metadata["total_files"] = len(files)

# Start processing
start_time = time.time()
print(f"📂 Merging {metadata['total_files']} JSON files...")

for filename in tqdm(files, desc="Processing Files", unit="file"):
    file_path = os.path.join(input_directory, filename)
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)  # Load JSON data
            merged_data.update(data)  # Merge into dictionary
            metadata["total_words"] += len(data)  # Count words
        except json.JSONDecodeError as e:
            print(f"❌ Error decoding {filename}: {e}")

# Save merged dataset
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(merged_data, f, indent=4)

# Save metadata
metadata["processing_time"] = round(time.time() - start_time, 2)
with open(metadata_file, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=4)

print(f"\n✅ Merging Complete! Data saved to: {output_file}")
print(f"📊 Metadata: {metadata}")
print(f"📁 Metadata saved at: {metadata_file}")
