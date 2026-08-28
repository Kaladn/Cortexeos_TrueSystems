import os
import json
import hashlib
import re

# ✅ Input & Output Directories
INPUT_DIR = "A:/WIKI SCRAPED/WORD_ANALYSIS/FINAL_ALPHA"
OUTPUT_DIR = "A:/Json-Dictionary_for_TXT_Conversion"
os.makedirs(OUTPUT_DIR, exist_ok=True)  # Create directory if it doesn't exist

# ✅ Symbol Generator
def generate_symbol(word):
    """Create a unique symbol for each word based on MD5 hashing."""
    return f"S{hashlib.md5(word.encode()).hexdigest()[:8]}"  # 8-char hash

# ✅ Clean Word Function
def clean_word(word):
    """Removes numbers, non-alphabet characters, and ensures it's a valid word."""
    word = word.strip().lower()
    return word if re.fullmatch(r"[a-z]+", word) else None  # Only letters allowed

# ✅ Process Each Letter's Dictionary File
for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    input_file = os.path.join(INPUT_DIR, f"{letter}.txt")
    output_file = os.path.join(OUTPUT_DIR, f"{letter}.json")

    if not os.path.exists(input_file):
        print(f"⚠️ Skipping {letter}: No file found.")
        continue  # Skip if file does not exist

    # ✅ Read and Clean Words
    with open(input_file, "r", encoding="utf-8") as f:
        words = {clean_word(line) for line in f if clean_word(line)}  # Use set to remove duplicates

    # ✅ Convert to JSON format
    words_json = {
        "letter": letter,
        "total_words": len(words),
        "words": {word: {"symbol": generate_symbol(word)} for word in sorted(words)}
    }

    # ✅ Save JSON File
    with open(output_file, "w", encoding="utf-8") as json_file:
        json.dump(words_json, json_file, indent=4)

    print(f"✅ Processed {letter}: {len(words)} clean words saved to {output_file}")

print("🔥 **A-Z Dictionary Successfully Cleaned & Converted to JSON!** 🔥")
