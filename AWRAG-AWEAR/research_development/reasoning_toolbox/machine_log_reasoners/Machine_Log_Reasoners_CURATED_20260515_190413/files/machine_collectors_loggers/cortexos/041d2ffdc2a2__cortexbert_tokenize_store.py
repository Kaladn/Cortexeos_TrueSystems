import os
import json
import pymongo
from transformers import AutoTokenizer

# 🔹 Paths
INPUT_DIR = r"A:\Compression Engine\dictionary"
OUTPUT_DIR = r"A:\Compression Engine\tokenized_dictionary"

# 🔹 MongoDB Setup
client = pymongo.MongoClient("mongodb://localhost:27017/")
db = client["CortexBERT"]
collection = db["TokenizedWords"]

# 🔹 Load BERT Tokenizer
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

# 🔥 Function: Process a Single File
def process_file(filename):
    file_path = os.path.join(INPUT_DIR, filename)
    output_path = os.path.join(OUTPUT_DIR, filename)

    # 🔹 Read JSON file
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"✅ Processing {filename} ({len(data)} words)...")

    processed_data = {}
    
    for word, entry in data.items():
        tokenized = tokenizer.tokenize(word)
        token_ids = tokenizer.convert_tokens_to_ids(tokenized)

        # 🔹 Update Data Structure
        entry["tokens"] = tokenized
        entry["token_ids"] = token_ids

        processed_data[word] = entry

        # 🔹 Store in MongoDB
        collection.update_one({"word": word}, {"$set": entry}, upsert=True)

    # 🔹 Write the updated JSON file
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(processed_data, f, indent=4)

    print(f"✅ Saved processed file: {output_path}")

# 🔥 Process Each File One by One
for filename in sorted(os.listdir(INPUT_DIR)):  # Sort for consistent order
    if filename.endswith(".json"):
        process_file(filename)

print("🚀 All files processed successfully!")
