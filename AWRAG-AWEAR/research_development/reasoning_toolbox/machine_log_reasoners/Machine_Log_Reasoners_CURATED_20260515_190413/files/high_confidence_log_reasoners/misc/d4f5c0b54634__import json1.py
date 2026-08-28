import os
import json
import re
import random
import itertools
from tqdm import tqdm

# ✅ Base Directory (All Files Inside Will Be Processed)
BASE_DIR = "A:/WIKI SCRAPED"

# ✅ Output Directory (Where JSON Symbolis Files Go)
OUTPUT_DIR = "A:/Symbolis_TXT_Conversion/json_dictionary"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ✅ Regex: Valid Words (Allows Hyphenated & Apostrophized Words)
VALID_WORD_PATTERN = re.compile(r"^[a-zA-Z'-]+$")

# ✅ Matrix sizes for dot pattern generation
MATRIX_SIZES = [(6,6), (6,7), (7,8), (8,8), (10,10)]

# ✅ Symbol Storage
symbolis_dict = {}

# ✅ Hex & Binary Encoding
def generate_encoding(word):
    """Generate unique hex & binary encoding."""
    hash_val = abs(hash(word)) % (2**40)  # 40-bit hash
    hex_code = f"0x{hash_val:010X}"  # 10-char hex
    binary_code = f"{hash_val:040b}"  # 40-bit binary
    return hex_code, binary_code

# ✅ Dot Matrix Symbol Generator
def generate_dot_matrix():
    """Generate a random dot matrix symbol from available sizes."""
    rows, cols = random.choice(MATRIX_SIZES)
    grid = [[" " for _ in range(cols)] for _ in range(rows)]
    
    num_dots = random.randint(4, 6)  # Random number of dots
    positions = list(itertools.product(range(rows), range(cols)))
    random.shuffle(positions)

    for x, y in positions[:num_dots]:
        grid[x][y] = "█"  # ASCII Block

    return ["".join(row) for row in grid]  # Convert to list of strings

# ✅ Process All Files Recursively
def process_files():
    """Scans all text files in BASE_DIR & extracts words."""
    global symbolis_dict
    all_words = set()
    
    # 🔄 Walk through all directories & subdirectories
    for root, _, files in os.walk(BASE_DIR):
        for file in files:
            file_path = os.path.join(root, file)
            
            # ✅ Skip Non-Text Files
            if not file.endswith((".txt", ".csv", ".tsv", ".md")):
                print(f"⚠️ Skipping Non-Text File: {file_path}")
                continue
            
            print(f"📂 Processing File: {file_path}")
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        for word in line.strip().split():
                            word = word.lower()
                            if VALID_WORD_PATTERN.match(word):  # Valid words only
                                all_words.add(word)
            except Exception as e:
                print(f"🚨 ERROR: Cannot read {file_path} ({e})")
    
    print(f"🔥 Total Unique Words Found: {len(all_words)}")

    # 🔄 Assign Unique Symbols
    for word in tqdm(all_words, desc="🔵 Generating Symbols"):
        hex_code, binary_code = generate_encoding(word)
        dot_matrix = generate_dot_matrix()
        symbolis_dict[word] = {
            "hex": hex_code,
            "binary": binary_code,
            "ascii": dot_matrix,
            "font_symbol": None  # Placeholder for Font Generation
        }

# ✅ Save to JSON (Per Letter)
def save_json():
    """Saves generated symbols to letter-based JSON files."""
    alphabet_dict = {chr(c): {} for c in range(97, 123)}  # a-z

    for word, data in symbolis_dict.items():
        first_letter = word[0].lower()
        if first_letter in alphabet_dict:
            alphabet_dict[first_letter][word] = data

    for letter, words in alphabet_dict.items():
        json_path = os.path.join(OUTPUT_DIR, f"Symbols_{letter.upper()}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(words, f, indent=4)
        print(f"✅ Saved: {json_path} ({len(words)} words)")

# ✅ Run Everything
if __name__ == "__main__":
    print("🚀 Processing & Symbolizing Words...")
    process_files()
    save_json()
    print("✅ **Symbolis Dictionary Rebuilt!**")
