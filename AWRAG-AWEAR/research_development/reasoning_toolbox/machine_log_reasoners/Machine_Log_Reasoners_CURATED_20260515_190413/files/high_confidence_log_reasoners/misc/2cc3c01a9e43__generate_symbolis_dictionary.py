import os
import json
import re
import hashlib
import random

# ✅ Paths
SOURCE_FILES = [
    r"A:\WIKI SCRAPED\WORD_ANALYSIS\MISSING_WORDS\historical_words_missing.txt",
    r"A:\WIKI SCRAPED\WORD_ANALYSIS\MISSING_WORDS\scientific_terms_missing.txt",
    r"A:\WIKI SCRAPED\WORD_ANALYSIS\unique_words.txt",
    r"A:\WIKI SCRAPED\WORD_ANALYSIS\medical_terms.txt",
    r"A:\WIKI SCRAPED\WORD_ANALYSIS\CLEANED_ALPHA"
]
JSON_STORAGE_DIR = r"A:\Symbolis_TXT_Conversion\json_dictionary"

# ✅ Ensure Output Directory Exists
os.makedirs(JSON_STORAGE_DIR, exist_ok=True)

# ✅ ASCII Dot Matrix Generator (8x7 Grid)
def generate_ascii_matrix():
    """Creates an 8x7 dot-matrix pattern representation."""
    return ["".join(random.choice(["█", " "]) for _ in range(7)) for _ in range(8)]

# ✅ Hexadecimal Generator
def generate_hex_code(word):
    """Creates a unique hex code based on the word's hash."""
    hash_value = hashlib.sha256(word.encode()).hexdigest()
    return "0x" + hash_value[:6].upper()

# ✅ Unique Symbol Generator
def generate_symbol(word):
    """Creates an 8-digit unique symbol based on word properties."""
    return f"S{abs(hash(word)) % 10**8}"

# ✅ Process Words
def process_words():
    """Loads words, removes duplicates, and stores in structured JSON format."""
    symbolis_dict = {chr(i): {} for i in range(65, 91)}  # A-Z Structure
    reserved_slots = 10000  # Future expansion slots

    total_words = set()

    # **Load Words from All Source Files**
    for source in SOURCE_FILES:
        if os.path.isdir(source):  # Handle alphabetized folders
            for file in os.listdir(source):
                file_path = os.path.join(source, file)
                if file.endswith(".txt"):
                    with open(file_path, "r", encoding="utf-8") as f:
                        total_words.update(f.read().splitlines())
        else:  # Single files
            with open(source, "r", encoding="utf-8") as f:
                total_words.update(f.read().splitlines())

    print(f"🔥 Total Unique Words Loaded: {len(total_words)}")

    # **Process Words & Categorize by Letter**
    for word in sorted(total_words):
        clean_word = word.strip().lower()
        if not clean_word.isalpha():  # Skip non-word entries
            continue

        first_letter = clean_word[0].upper()  # A-Z classification
        if first_letter in symbolis_dict:
            symbolis_dict[first_letter][clean_word] = {
                "symbol": generate_symbol(clean_word),
                "ascii": generate_ascii_matrix(),
                "hex": generate_hex_code(clean_word),
                "font_map": None  # Reserved for future font mapping
            }

    # **Save to JSON**
    for letter, data in symbolis_dict.items():
        json_path = os.path.join(JSON_STORAGE_DIR, f"Symbols_{letter}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        print(f"✅ JSON Saved: {json_path} ({len(data)} words)")

    print("✅ **Symbolis Dictionary Generation Complete!**")

# ✅ Execute
if __name__ == "__main__":
    print("🚀 Generating Full Symbolis Dictionary with ASCII & Hex Encoding...")
    process_words()
