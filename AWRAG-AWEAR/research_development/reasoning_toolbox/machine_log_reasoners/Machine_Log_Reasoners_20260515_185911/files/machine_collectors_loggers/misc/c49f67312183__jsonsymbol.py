import os
import json
import re

# ✅ Paths
BASE_DIR = "A:/Symbolis_TXT_Conversion"
JSON_DICTIONARY_DIR = os.path.join(BASE_DIR, "json_dictionary")
INPUT_FILE = r"C:\Users\mydyi\OneDrive\Documents\Desktop\tesing\The Basement.txt"
OUTPUT_FILE = os.path.join(BASE_DIR, "processed", "The_Basement_symbolis.txt")

# ✅ Load Entire Dictionary into RAM
def load_symbolis_dictionary():
    symbol_dict = {}

    json_files = [f for f in os.listdir(JSON_DICTIONARY_DIR) if f.startswith("Symbols_") and f.endswith(".json")]

    print(f"🚀 Loading {len(json_files)} JSON Dictionary Files into RAM...")

    for json_file in json_files:
        json_path = os.path.join(JSON_DICTIONARY_DIR, json_file)
        with open(json_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                # ✅ Extract only symbols from each entry
                for word, entry in data.items():
                    if isinstance(entry, dict) and "symbol" in entry:
                        symbol_dict[word] = entry["symbol"]  # Keep only the symbol
                print(f"✅ Loaded: {json_file} ({len(data)} words)")
            except Exception as e:
                print(f"❌ Error loading {json_file}: {e}")

    print(f"🔥 Total Words in RAM: {len(symbol_dict)}")
    return symbol_dict

# ✅ Convert Words to Symbolis
def convert_to_symbolis(text, symbol_dict):
    def replace_match(match):
        word = match.group(0)
        return symbol_dict.get(word.lower(), word)  # Replace with symbol if found, else keep original

    return re.sub(r"\b\w+\b", replace_match, text)  # Match words only, keep punctuation

# ✅ Process File
def process_text_file():
    print(f"🚀 Processing: {INPUT_FILE}")

    # Load dictionary into RAM
    symbolis_dict = load_symbolis_dictionary()
    if not symbolis_dict:
        print("❌ ERROR: No valid Symbolis dictionary loaded. Aborting.")
        return

    # Read input file
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        text = f.read()

    # Convert text using RAM-based lookup
    converted_text = convert_to_symbolis(text, symbolis_dict)

    # Save the processed file
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(converted_text)

    print(f"✅ Converted file saved: {OUTPUT_FILE}")

# ✅ Run the Conversion
if __name__ == "__main__":
    process_text_file()
