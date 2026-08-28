import os
import json
import re

# ✅ Paths
BASE_DIR = "A:/AI WORK/Symbolis_TXT_Conversion"
JSON_DICTIONARY_PATH = os.path.join(BASE_DIR, "A:\WIKI SCRAPED\MASTER_ALPHA")
INPUT_FILE = r"C:\Users\mydyi\OneDrive\Documents\Desktop\tesing\The Basement.txt"
OUTPUT_FILE = os.path.join(BASE_DIR, "processed", "The_Basement_symbolis.txt")

# ✅ Load Symbolis Dictionary
def load_symbolis_dictionary():
    if not os.path.exists(JSON_DICTIONARY_PATH):
        print(f"❌ ERROR: Symbolis dictionary not found at {JSON_DICTIONARY_PATH}")
        return {}

    with open(JSON_DICTIONARY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

# ✅ Convert Words to Symbolis
def convert_to_symbolis(text, symbol_dict):
    def replace_match(match):
        word = match.group(0)
        return symbol_dict.get(word.lower(), word)  # Replace if found, else keep original

    # Match words only (keep punctuation & unknown words intact)
    return re.sub(r"\b\w+\b", replace_match, text)

# ✅ Process File
def process_text_file():
    print(f"🚀 Processing: {INPUT_FILE}")

    # Load dictionary
    symbolis_dict = load_symbolis_dictionary()
    if not symbolis_dict:
        return

    # Read file
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        text = f.read()

    # Convert text
    converted_text = convert_to_symbolis(text, symbolis_dict)

    # Save to output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(converted_text)

    print(f"✅ Converted file saved: {OUTPUT_FILE}")

# ✅ Run Conversion
if __name__ == "__main__":
    process_text_file()
