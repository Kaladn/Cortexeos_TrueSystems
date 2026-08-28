import os
import glob
import re
import collections
import concurrent.futures
import shutil

# Folder Paths
READY_DIR = "C:/AI SYMBOLIS WORK/ready-for-scraping"  # Input: Files to scrape
SCRAPED_DIR = "C:/AI SYMBOLIS WORK/scraped"  # Move processed files here
OUTPUT_FILE = "C:/AI SYMBOLIS WORK/word_frequencies.txt"  # Output: Word count list

BATCH_SIZE = 10  # Process 10 files at a time

# Ensure scraped directory exists
os.makedirs(SCRAPED_DIR, exist_ok=True)

def clean_word(word):
    """Cleans a word: removes non-alphabetic characters except hyphens and converts to lowercase."""
    word = word.strip().lower()
    word = re.sub(r"[^a-z-]", "", word)  # Keep only letters and hyphens
    return word if word else None

def process_file(file_path):
    """Extracts words from a file and counts frequency."""
    word_counts = collections.Counter()

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                for word in line.split():
                    cleaned = clean_word(word)
                    if cleaned:
                        word_counts[cleaned] += 1

        # Move file to `scraped/` after processing
        shutil.move(file_path, os.path.join(SCRAPED_DIR, os.path.basename(file_path)))
        print(f"✅ Processed & Moved {file_path} → {SCRAPED_DIR}")

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")

    return word_counts

def merge_word_counts(all_counts):
    """Merges multiple Counter objects into one."""
    final_counts = collections.Counter()
    for count in all_counts:
        final_counts.update(count)
    return final_counts

def process_batches():
    """Processes all files in batches, updates word frequency file."""
    all_word_counts = collections.Counter()

    while True:
        files = glob.glob(os.path.join(READY_DIR, "*.txt"))[:BATCH_SIZE]
        if not files:
            print("🎉 All files processed! Saving word frequencies...")
            break

        print(f"🔄 Processing {len(files)} files...")

       
