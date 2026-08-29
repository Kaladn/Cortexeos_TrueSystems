import os
import json
from tqdm import tqdm
from transformers import AutoTokenizer

# ✅ Paths
INPUT_DIR = r"A:\json_dictionary"  # Original files
OUTPUT_DIR = r"A:\ai_ready_dictionary"  # Tokenized output
MODEL_PATH = "bert-base-uncased"  # Change if needed

# ✅ Ensure Output Directory Exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ✅ Load Tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

# ✅ Process each JSON file in the directory with a progress bar
json_files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".json")]

for file_name in tqdm(json_files, desc="📂 Processing Files", unit="file"):
    input_path = os.path.join(INPUT_DIR, file_name)
    output_path = os.path.join(OUTPUT_DIR, file_name)

    # ✅ Load JSON Data
    with open(input_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            print(f"❌ ERROR: Could not read {file_name}. Skipping...")
            continue  # Skip bad files

    if not isinstance(data, dict):
        print(f"❌ ERROR: {file_name} is not a dictionary. Skipping...")
        continue  # Skip if data isn't in the expected format

    processed_data = {}

    # ✅ Process each word entry with a progress bar
    for word, details in tqdm(data.items(), desc=f"🔄 Tokenizing {file_name}", unit="word", leave=False):
        # ✅ Tokenize Word
        tokenized = tokenizer(word, return_tensors="pt")["input_ids"].tolist()

        # ✅ Store Data
        processed_data[word] = {
            "hex": details.get("hex", ""),
            "binary": details.get("binary", ""),
            "ascii": details.get("ascii", []),
            "font_symbol": details.get("font_symbol", None),
            "tokenized_word": tokenizer.convert_ids_to_tokens(tokenized[0]),
            "token_ids": tokenized[0],
        }

    if not processed_data:
        print(f"⚠️ WARNING: {file_name} resulted in an empty dataset. Skipping save.")
        continue

    # ✅ Save Processed File
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(processed_data, f, indent=4, ensure_ascii=False)

    print(f"✅ Processed {file_name} → Saved to {output_path}")

print("\n🎉 All files processed and ready for training!")
