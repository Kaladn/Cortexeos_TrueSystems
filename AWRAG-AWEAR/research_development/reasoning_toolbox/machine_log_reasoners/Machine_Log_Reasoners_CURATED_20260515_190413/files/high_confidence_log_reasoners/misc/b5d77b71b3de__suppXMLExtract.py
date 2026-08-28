import os
import re
import string
from tqdm import tqdm

# 🚀 File Paths
INPUT_FILE = "A:\WIKI SCRAPED\soildb_US_2003.mdb"
OUTPUT_FOLDER = "A:/WIKI SCRAPED/EXTRACTED"
ENGLISH_WORDS_FILE = os.path.join(OUTPUT_FOLDER, "mesh_english_words.txt")

# ✅ Ensure output directory exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# 🔍 Regex patterns
VALID_WORD_PATTERN = re.compile(r"\b[a-zA-Z]{3,}\b")  # English words (3+ letters)
CAMELCASE_PATTERN = re.compile(r'(?<=[a-z])(?=[A-Z])')  # Detect CamelCase boundaries
SNAKE_CASE_PATTERN = re.compile(r'[_-]')  # Detect snake_case or kebab-case

# 🚀 Process XML in 1GB Chunks
CHUNK_SIZE = 1 * 1024 * 1024 * 1024  # 1GB
SAVE_INTERVAL = 1_000_000  # Flush every 1M words
total_words = 0
buffer = ""

def split_compound_words(word):
    """Breaks CamelCase, PascalCase, and snake_case words into separate words."""
    word = SNAKE_CASE_PATTERN.sub(" ", word)  # Replace _ and - with spaces
    word = CAMELCASE_PATTERN.sub(" ", word)  # Insert space at CamelCase boundaries
    return word.split()

def extract_words_from_xml():
    """Stream through the XML file, extracting words in 1GB chunks."""
    global total_words, buffer

    print(f"🚀 Processing XML: {INPUT_FILE} in 1GB chunks...")

    try:
        with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as f, \
             open(ENGLISH_WORDS_FILE, "w", encoding="utf-8") as out_file:

            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break  # Stop if end of file

                buffer += chunk  # Append new chunk to buffer
                words = VALID_WORD_PATTERN.findall(buffer)  # Extract words
                
                # 🔹 Tokenize Compound Words
                final_words = []
                for word in words:
                    final_words.extend(split_compound_words(word))

                if final_words:
                    out_file.write("\n".join(final_words) + "\n")
                    out_file.flush()  # ✅ Force write to disk
                    total_words += len(final_words)

                buffer = buffer[-1000:]  # Keep last 1000 characters for continuity

                # 🔹 Show progress update
                print(f"✅ Processed {total_words:,} words so far...")

    except Exception as e:
        print(f"❌ ERROR: {e}")

    print(f"\n🎉 Extraction complete! Total English words: {total_words:,}")
    print(f"💾 Saved to: {ENGLISH_WORDS_FILE}")

# 🔥 Run Extraction
extract_words_from_xml()
