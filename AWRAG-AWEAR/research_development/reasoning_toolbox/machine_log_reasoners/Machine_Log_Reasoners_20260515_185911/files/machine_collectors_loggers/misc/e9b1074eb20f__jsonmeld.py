import os
import json
import glob
from tqdm import tqdm
from pathlib import Path

def main(input_path="processed_data", output_file="processed_data/merged_training_data_deduped.jsonl"):
    input_path = Path(input_path)
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    merged_data = []
    completion_set = set()
    entries_processed = 0

    # Prepare backup directory
    backup_dir = input_path / "backup"
    backup_dir.mkdir(exist_ok=True)

    # Find all JSON and JSONL files
    json_files = list(input_path.glob("*.json")) + list(input_path.glob("*.jsonl"))
    print(f"📂 Found {len(json_files)} JSON/JSONL files in {input_path}.")

    for file in tqdm(json_files, desc="🔄 Processing files"):
        with file.open('r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    completion_text = data.get("completion", "").strip()

                    if completion_text and completion_text not in completion_set:
                        merged_data.append({"prompt": "", "completion": completion_text})
                        completion_set.add(completion_text)
                        entries_processed += 1

                except json.JSONDecodeError:
                    print(f"⚠️ Skipped invalid JSON in {file.name}")

        # Backup file
        file.rename(backup_dir / file.name)

    # Word statistics
    word_counts = [len(entry["completion"].split()) for entry in merged_data]

    # Write final merged JSONL
    with output_path.open('w', encoding='utf-8') as out_f:
        for entry in tqdm(merged_data, desc="💾 Writing merged JSONL"):
            out_f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print("\n✅ Merge Complete!")
    print(f"Total entries processed: {entries_processed}")
    print(f"Total unique entries: {len(merged_data)}")
    print(f"Approx. total word count: {sum(word_counts):,}")
    print(f"Longest entry: {max(word_counts, default=0)} words")
    print(f"Shortest entry: {min(word_counts, default=0)} words")
    print(f"📄 Merged file saved as: {output_path}")


if __name__ == "__main__":
    import sys
    input_arg = sys.argv[1] if len(sys.argv) > 1 else "processed_data"
    output_arg = sys.argv[2] if len(sys.argv) > 2 else "processed_data/merged_training_data_deduped.jsonl"
    main(input_arg, output_arg)
