import os
import json
import glob
from tqdm import tqdm

output_file = "merged_training_data_deduped.jsonl"
merged_data = []
completion_set = set()

# Create backup folder
backup_dir = os.path.join(os.getcwd(), "backup")
os.makedirs(backup_dir, exist_ok=True)

json_files = glob.glob("*.json") + glob.glob("*.jsonl")
print(f"Found {len(json_files)} JSON/JSONL files.")

entries_processed = 0

for file in tqdm(json_files, desc="Processing files"):
    with open(file, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                completion_text = data.get("completion", "").strip()

                if completion_text and completion_text not in completion_set:
                    merged_data.append({"prompt": "", "completion": completion_text})
                    completion_set.add(completion_text)
                    entries_processed += 1

            except json.JSONDecodeError:
                print(f"⚠️ Skipped invalid JSON in {file}")

    # Backup each file
    os.rename(file, os.path.join(backup_dir, os.path.basename(file)))

# Word statistics
word_counts = [len(entry["completion"].split()) for entry in merged_data]

with open(output_file, 'w', encoding='utf-8') as out_f:
    for entry in tqdm(merged_data, desc="Writing merged JSONL"):
        out_f.write(json.dumps(entry, ensure_ascii=False) + "\n")

print("\n✅ Merge Complete!")
print(f"Total entries processed: {entries_processed}")
print(f"Total unique entries: {len(merged_data)}")
print(f"Approx. total word count: {sum(word_counts):,}")
print(f"Longest entry: {max(word_counts)} words")
print(f"Shortest entry: {min(word_counts)} words")
print(f"Merged file saved as: {output_file}")
