import json
import os
from tqdm import tqdm
import re

# Configuration
directory = os.getcwd()
output_file = "cleaned_training_data.jsonl"
profanity_filter = re.compile(r"\b(fuck|shit|cocksucker|bitch|asshole|faggot|damn)\b", re.IGNORECASE)

# Load and filter
def clean_text(text):
    # Strip HTML, weird chars, trim excessive whitespace
    text = re.sub(r'<.*?>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

cleaned_entries = []

json_files = [file for file in os.listdir(directory) if file.endswith(".jsonl") or file.endswith(".json")]

print(f"Found {len(json_files)} JSON/JSONL files.")

for file in tqdm(json_files, desc="Processing files"):
    with open(file, 'r', encoding='utf-8') as infile:
        for line in infile:
            try:
                data = json.loads(line)
                completion_text = data.get("completion", "")

                if profanity_filter.search(completion_text):
                    continue  # skip dirty data

                cleaned_text = clean_text(completion_text)
                data["completion"] = cleaned_text
                cleaned_entries.append(data)

            except Exception as e:
                print(f"Skipping line due to error: {e}")

# Save cleaned
with open(output_file, 'w', encoding='utf-8') as outfile:
    for entry in tqdm(cleaned_entries, desc="Writing cleaned JSONL"):
        json.dump(entry, outfile)
        outfile.write('\n')

print(f"✅ Cleaning complete! Cleaned file saved as {output_file} with {len(cleaned_entries)} entries.")