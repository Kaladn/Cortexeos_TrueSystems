"""
Bulk Import JSON Script for Symbolis (Unicode Symbols)
------------------------------------------------------
- Assigns words unique Unicode symbols from global alphabets.
- Uses real Chinese, Arabic, Greek, Hebrew, Cyrillic, and more.
- Displays real symbols instead of Unicode hex codes.
"""

import json
import os
import itertools

# File paths
DICT_FILE = "A:/Symbolis/data/symbolis_dict.json"
WORD_LIST_JSON = "A:/Symbolis/data/wordlist.json"

# Define Unicode symbol sets
UNICODE_SETS = [
    list(range(0x0400, 0x04FF)),  # Cyrillic
    list(range(0x0370, 0x03FF)),  # Greek
    list(range(0x0600, 0x06FF)),  # Arabic
    list(range(0x0900, 0x097F)),  # Devanagari
    list(range(0x0590, 0x05FF)),  # Hebrew
    list(range(0x4E00, 0x9FFF)),  # Chinese
    list(range(0x3040, 0x30FF)),  # Japanese
    list(range(0xAC00, 0xD7AF))   # Korean
]

# Flatten Unicode character lists
GLOBAL_SYMBOLS = [chr(code) for subset in UNICODE_SETS for code in subset]

# Track used symbols
used_symbols = set()

def get_unicode_symbol():
    """Assigns the next available Unicode symbol, ensuring uniqueness."""
    while GLOBAL_SYMBOLS:
        symbol = GLOBAL_SYMBOLS.pop(0)
        if symbol not in used_symbols:
            used_symbols.add(symbol)
            return symbol
    return "⚠️"  # Fallback symbol if all are exhausted

def load_dictionary():
    """Loads the existing Symbolis dictionary or creates a new one if missing."""
    if os.path.exists(DICT_FILE):
        with open(DICT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_dictionary(dictionary):
    """Saves the Symbolis dictionary to file."""
    with open(DICT_FILE, "w", encoding="utf-8") as f:
        json.dump(dictionary, f, ensure_ascii=False, indent=4)

def bulk_import():
    """Reads words from wordlist.json and assigns Unicode symbols."""
    dictionary = {}

    if not os.path.exists(WORD_LIST_JSON):
        print(f"⚠️ ERROR: {WORD_LIST_JSON} not found!")
        return

    with open(WORD_LIST_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
        words = sorted(data.get("words", []), key=len)  # Sort words by length (smallest first)

    total_words = len(words)
    print(f"🚀 Processing {total_words} words using Unicode characters...")

    for word in words:
        dictionary[word] = get_unicode_symbol()

    save_dictionary(dictionary)
    print(f"✅ Successfully processed {total_words} words with Unicode symbols!")

if __name__ == "__main__":
    bulk_import()
