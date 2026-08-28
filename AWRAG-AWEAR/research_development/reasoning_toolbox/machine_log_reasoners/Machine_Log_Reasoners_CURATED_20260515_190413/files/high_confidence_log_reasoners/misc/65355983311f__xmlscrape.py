import os
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from tqdm import tqdm

# Updated paths
INPUT_FILE = "A:/WIKI XML/enwiki-latest-abstract.xml"
OUTPUT_FOLDER = "A:/WIKI SCRAPED"
WORD_FREQUENCY_FILE = os.path.join(OUTPUT_FOLDER, "wiki_word_frequency.txt")
UNIQUE_WORD_LIST_FILE = os.path.join(OUTPUT_FOLDER, "wiki_unique_word_list.txt")

# Ensure output directory exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Regex pattern to filter valid words (3+ letter English words only)
VALID_WORD_PATTERN = re.compile(r"^[a-zA-Z]{3,}$")

# Store word frequency
word_freq = defaultdict(int)
total_words = 0

# Define chunk size (reduce memory overhead)
CHUNK_SIZE = 500_000  # 500K lines before processing

def process_chunk(chunk_data):
    """Process a chunk of XML text and update word frequencies."""
    global total_words

    # Extract words from text
    words = [word.lower() for word in re.findall(r"\b[a-zA-Z]{3,}\b", chunk_data)]

    for word in words:
        word_freq[word] += 1
        total_words += 1

def save_word_data():
    """Save extracted word frequency and unique words."""
    print(f"💾 Saving results to {OUTPUT_FOLDER}...")

    try:
        # Save word frequency list
        with open(WORD_FREQUENCY_FILE, "w", encoding="utf-8") as wf:
            for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True):
                wf.write(f"{word} {freq}\n")

        # Save unique words
        with open(UNIQUE_WORD_LIST_FILE, "w", encoding="utf-8") as uf:
            for word in sorted(word_freq.keys()):
                uf.write(f"{word}\n")

        print(f"✅ Wiki data saved! Word count: {len(word_freq):,}")

    except Exception as e:
        print(f"❌ Error during file writing: {e}")

def parse_wiki_xml():
    """Parse Wikipedia XML and extract only English content."""
    global total_words

    print(f"🚀 Parsing Wiki XML: {INPUT_FILE}")

    chunk_data = []
    total_lines = sum(1 for _ in open(INPUT_FILE, "r", encoding="utf-8", errors="ignore"))

    with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        for line in tqdm(f, desc="📂 Extracting English Words", total=total_lines, unit="line"):
            
            # ✅ **Only extract from English pages** (ignore foreign articles)
            if '<doc' in line and 'lang="en"' not in line:
                continue  # Skip non-English pages
            
            # ✅ **Only extract text from articles**
            if not ("<title>" in line or "<url>" in line or "<doc" in line or "</doc>" in line):
                chunk_data.append(line.strip())

            # ✅ **Process every 500K lines**
            if len(chunk_data) >= CHUNK_SIZE:
                process_chunk(" ".join(chunk_data))
                chunk_data = []  # Reset chunk data for the next batch

                # Save data incrementally
                save_word_data()
                print(f"🔹 Processed {total_words:,} words so far...")

        # Process any remaining text after the last chunk
        if chunk_data:
            process_chunk(" ".join(chunk_data))
            save_word_data()
            print(f"🔹 Processed {total_words:,} words so far...")

    print(f"✅ Total words processed: {total_words:,}")
    print(f"✅ Processing completed!")

# Run processing
parse_wiki_xml()
