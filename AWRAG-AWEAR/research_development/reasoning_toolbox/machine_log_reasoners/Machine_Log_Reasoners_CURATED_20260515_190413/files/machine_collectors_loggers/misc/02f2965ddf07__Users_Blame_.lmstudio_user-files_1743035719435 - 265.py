import csv
import json
import os
from tqdm import tqdm

# Define file paths
directory = os.getcwd()
csv_file = os.path.join(directory, 'Final_Optimized_Word-Symbol_Mapping.csv')
jsonl_file = os.path.join(directory, 'training_data_from_csv.jsonl')

# Clean text function
def clean_text(text):
    return ' '.join(text.strip().split())

entries = []

# Process CSV file
if os.path.exists(csv_file):
    with open(csv_file, mode='r', encoding='utf-8', errors='ignore') as file:
        reader = csv.reader(file)
        all_lines = [clean_text(", ".join(row)) for row in reader]

    combined_content = "\n".join(all_lines)

    # Save to JSONL
    with open(jsonl_file, mode='w', encoding='utf-8') as jsonl_out:
        json.dump({"prompt": "Here is the content of Final_Optimized_Word-Symbol_Mapping:", "completion": combined_content}, jsonl_out)

    print(f"✅ Successfully converted {csv_file} into {jsonl_file}")
else:
    print(f"⚠️ CSV file not found in directory: {directory}")
