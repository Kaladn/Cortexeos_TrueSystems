import json
import os

# Path to dictionary folder
dataset_folder = r"A:\ai_ready_dictionary"

# Count words
total_word_count = 0
file_counts = {}

# Process all JSON files
for filename in os.listdir(dataset_folder):
    if filename.endswith(".json"):
        file_path = os.path.join(dataset_folder, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            word_count = len(data)
            total_word_count += word_count
            file_counts[filename] = word_count

# Print results
print(f"✅ Total Words Across All Files: {total_word_count}")
print(f"📊 File Breakdown: {file_counts}")
