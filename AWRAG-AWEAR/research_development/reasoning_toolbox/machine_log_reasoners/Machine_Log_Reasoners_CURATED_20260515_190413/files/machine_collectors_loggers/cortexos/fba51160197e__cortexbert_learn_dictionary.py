import json
import os
import tqdm
from transformers import AutoTokenizer

# Load pre-trained BERT tokenizer (WordPiece)
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

# Define input/output directory
input_directory = r"a:\Json-Neuron-Storage - AI Translate"
output_directory = r"A:\Compression Engine\tokenized_dictionary"

# Ensure output directory exists
os.makedirs(output_directory, exist_ok=True)

def tokenize_word(word):
    """Tokenizes a word using BERT's WordPiece tokenizer."""
    tokenized = tokenizer.tokenize(word)
    return " ".join(tokenized)  # Convert list to string with spaces

# Get list of JSON files in the directory
json_files = [f for f in os.listdir(input_directory) if f.endswith(".json")]

if not json_files:
    print("❌ No JSON files found in:", input_directory)
    exit()

print(f"🚀 Found {len(json_files)} JSON files. Processing...")

for file_name in json_files:
    input_path = os.path.join(input_directory, file_name)
    output_path = os.path.join(output_directory, file_name)

    try:
        # Load the JSON dictionary
        with open(input_path, "r", encoding="utf-8") as f:
            dictionary = json.load(f)

        print(f"✅ Processing {file_name} ({len(dictionary)} words)...")

        processed_data = {}
        for word, details in tqdm.tqdm(dictionary.items(), desc=f"🔄 {file_name}"):
            # Remove "ascii" key and add tokenized words
            processed_data[word] = {
                "hex": details["hex"],
                "binary": details["binary"],
                "tokenized": tokenize_word(word),
                "font_symbol": details["font_symbol"]
            }

        # Save the modified dictionary
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(processed_data, f, indent=4, ensure_ascii=False)

        print(f"✅ Saved processed file: {output_path}")

    except MemoryError:
        print(f"❌ ERROR: {file_name} is too large! Try streaming instead.")
    except Exception as e:
        print(f"⚠️ Unexpected Error in {file_name}: {e}")

print("🚀 Processing Complete! All files saved in:", output_directory)
