import os
import glob
import re
import shutil
import concurrent.futures
from collections import Counter

# Folder Paths
READY_DIR = "C:/AI SYMBOLIS WORK/ready-for-scraping"  # Where .txt files are stored
SCRAPED_DIR = "C:/AI SYMBOLIS WORK/scraped"  # Where processed files go
OUTPUT_FILE = "C:/AI SYMBOLIS WORK/word_frequencies.txt"  # Final word frequency storage

BATCH_SIZE = 10  # Process 10 files at a time

# Ensure directories exist
os.makedirs(SCRAPED_DIR, exist_ok=True)

def clean_word(word):
    """Cleans a word, keeps only alphabetic characters & hyphens, and converts to lowercase."""
    word = word.strip().lower()
    word = re.sub(r"[^a-z-]", "", word)  # Remove non-letter characters except hyphens
    return word if word else None

def process_file(file_path):
    """Extracts words from a file and counts occurrences."""
    word_count = Counter()
    
    print(f"🔍 Processing: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                for word in line.split():
                    cleaned = clean_word(word)
                    if cleaned:
                        word_count[cleaned] += 1  # Increment count for the word

        # Move processed file to `scraped/`
        shutil.move(file_path, os.path.join(SCRAPED_DIR, os.path.basename(file_path)))
        print(f"✅ Processed & Moved {file_path} → {SCRAPED_DIR}")

    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")

    return word_count

def merge_word_counts(all_word_counts):
    """Merges multiple word count dictionaries into one."""
    final_count = Counter()
    for wc in all_word_counts:
        final_count.update(wc)
    return final_count

def save_word_frequencies(word_counts):
    """Saves word frequencies to a file, sorted by most common words first."""
    sorted_words = word_counts.most_common()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for word, count in sorted_words:
            f.write(f"{word} {count}\n")

    print(f"📄 Final word frequency list saved: {OUTPUT_FILE}")

def process_batches():
    """Processes text files in batches, counts word frequencies, and updates the master list."""
    total_word_counts = Counter()

    while True:
        files = glob.glob(os.path.join(READY_DIR, "*.txt"))[:BATCH_SIZE]

        if not files:
            print("🎉 All files processed! Saving final frequency list...")
            save_word_frequencies(total_word_counts)
            break

        print(f"🔄 Found {len(files)} files to process...")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(process_file, files)

        # Merge batch results into total count
        total_word_counts = merge_word_counts([total_word_counts, *results])

if __name__ == "__main__":
    process_batches()
