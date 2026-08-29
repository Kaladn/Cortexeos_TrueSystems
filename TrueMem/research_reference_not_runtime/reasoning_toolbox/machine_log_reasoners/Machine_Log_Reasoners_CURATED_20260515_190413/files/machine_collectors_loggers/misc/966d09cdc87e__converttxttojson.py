"""
Convert Words TXT File to JSON Format for Symbolis
---------------------------------------------------
Reads a text file containing a word list (one word per line) and converts it into
a JSON file formatted for Symbolis bulk processing.
"""

import json
import os

# File paths
TXT_FILE = "A:/Symbolis/data/final_words_no_acronyms.txt"
JSON_FILE = "A:/Symbolis/data/wordlist.json"

def convert_txt_to_json():
    """Reads a text file and converts it into a JSON word list."""
    if not os.path.exists(TXT_FILE):
        print(f"⚠️ ERROR: {TXT_FILE} not found!")
        return

    with open(TXT_FILE, "r", encoding="utf-8") as f:
        words = [line.strip() for line in f.readlines() if line.strip()]

    word_list = {"words": words}

    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(word_list, f, ensure_ascii=False, indent=4)

    print(f"✅ Successfully converted {len(words)} words to JSON: {JSON_FILE}")

if __name__ == "__main__":
    convert_txt_to_json()
