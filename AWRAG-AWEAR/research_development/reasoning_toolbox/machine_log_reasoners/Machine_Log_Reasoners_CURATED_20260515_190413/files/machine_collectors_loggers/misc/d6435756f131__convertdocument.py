"""
Convert a Document to Symbolis Format (Unicode Symbols)
-------------------------------------------------------
Reads a document, replaces words with their assigned Unicode symbols,
and saves the output as a new file.
"""

import json
import os
import re

# File paths
DICT_FILE = "A:/Symbolis/data/symbolis_dict.json"
INPUT_FILE = "A:/Symbolis/data/document.txt"
OUTPUT_FILE = "A:/Symbolis/data/document_symbolis.txt"

def load_dictionary():
    """Loads the existing Symbolis dictionary."""
    if os.path.exists(DICT_FILE):
        with open(DICT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def convert_text_to_symbolis(text, dictionary):
    """Replaces words in text with their Symbolis symbols."""
    words = re.findall(r"\b\w+\b", text)  # Extract words only
    converted_text = [dictionary.get(word.lower(), word) for word in words]  # Preserve unknown words
    return " ".join(converted_text)

def convert_document():
    """Reads a document, converts it, and saves the Symbolis version."""
    dictionary = load_dictionary()

    if not os.path.exists(INPUT_FILE):
        print(f"⚠️ ERROR: {INPUT_FILE} not found!")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        text = f.read()

    converted_text = convert_text_to_symbolis(text, dictionary)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(converted_text)

    print(f"✅ Successfully converted document! Saved as {OUTPUT_FILE}")

if __name__ == "__main__":
    convert_document()
