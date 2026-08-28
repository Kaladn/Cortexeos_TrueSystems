import json
import csv
import os

# Paths
json_file_path = r"A:\Compression Engine\tokenized_dictionary\Symbols_A.json"
save_dir = r"C:\Users\mydyi\OneDrive\Documents\Desktop\TOKENIZED CSV FILES"

# Ensure save directory exists
os.makedirs(save_dir, exist_ok=True)

# Output CSV file paths
word_csv = os.path.join(save_dir, "words.csv")
encoding_csv = os.path.join(save_dir, "encodings.csv")
token_csv = os.path.join(save_dir, "tokens.csv")
token_id_csv = os.path.join(save_dir, "token_ids.csv")

# Load the JSON file
with open(json_file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# Prepare CSV writers
with open(word_csv, "w", newline="", encoding="utf-8") as w, \
     open(encoding_csv, "w", newline="", encoding="utf-8") as e, \
     open(token_csv, "w", newline="", encoding="utf-8") as t, \
     open(token_id_csv, "w", newline="", encoding="utf-8") as tid:

    word_writer = csv.writer(w)
    encoding_writer = csv.writer(e)
    token_writer = csv.writer(t)
    token_id_writer = csv.writer(tid)

    # Write headers
    word_writer.writerow(["word_id", "text"])
    encoding_writer.writerow(["word_id", "type", "value"])
    token_writer.writerow(["word_id", "token"])
    token_id_writer.writerow(["word_id", "token_id"])

    # Counter for unique word IDs
    word_id = 1

    # Process each word in the JSON file
    for word, details in data.items():
        word_writer.writerow([word_id, word])

        # Process encodings
        if "hex" in details:
            encoding_writer.writerow([word_id, "Hex", details["hex"]])
        if "binary" in details:
            encoding_writer.writerow([word_id, "Binary", details["binary"]])

        # Process tokenized words
        if "tokenized" in details:
            for token in details["tokenized"]:
                token_writer.writerow([word_id, token])

        # Process token IDs
        if "token_ids" in details:
            for token_id in details["token_ids"]:
                token_id_writer.writerow([word_id, token_id])

        word_id += 1  # Increment word ID

print(f"✅ JSON successfully converted! CSVs saved in:\n📂 {save_dir}")
