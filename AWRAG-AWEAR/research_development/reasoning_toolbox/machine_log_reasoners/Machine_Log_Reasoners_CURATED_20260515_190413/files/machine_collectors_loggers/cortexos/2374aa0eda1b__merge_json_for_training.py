import json
import os
from tqdm import tqdm  # ✅ Progress bar

# ✅ Paths
INPUT_DIR = r"A:/Compression Engine/tokenized_dictionary"
OUTPUT_FILE = r"A:/Compression Engine/merged_trainable_dataset.json"

# ✅ Collect all JSON files
json_files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".json")]

print(f"🔄 Found {len(json_files)} JSON files. Merging...")

# ✅ Merge Data
merged_data = []
for file in tqdm(json_files, desc="📂 Merging Files", unit="file"):
    file_path = os.path.join(INPUT_DIR, file)

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()  # ✅ Ensure it's not empty
            if not content:
                print(f"⚠️ WARNING: {file} is empty. Skipping...")
                continue
            
            data = json.loads(content)  # ✅ Read JSON safely

            for word, details in data.items():
                if "tokenized" in details and "token_ids" in details:
                    merged_data.append({
                        "input": word,
                        "output": f"Tokenized: {' '.join(details['tokenized'])} | Token IDs: {', '.join(map(str, details['token_ids']))}"
                    })

    except json.JSONDecodeError:
        print(f"❌ ERROR: {file} is corrupted or not valid JSON. Skipping...")

if len(merged_data) == 0:
    print("❌ ERROR: No valid entries found! Check your JSON files.")
else:
    # ✅ Save the merged dataset
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(merged_data, f, indent=4)

    print(f"✅ Merged {len(merged_data)} entries. Saved to: {OUTPUT_FILE}")
