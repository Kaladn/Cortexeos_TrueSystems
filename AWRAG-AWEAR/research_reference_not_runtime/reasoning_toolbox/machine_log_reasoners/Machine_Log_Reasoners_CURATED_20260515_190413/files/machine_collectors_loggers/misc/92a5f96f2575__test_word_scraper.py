import os
import re
import shutil
import time
from collections import Counter

# Folders
READY_DIR = "C:/AI SYMBOLIS WORK/data/ready-for-scraping"
SCRAPED_DIR = "C:/AI SYMBOLIS WORK/data/scraped"
OUTPUT_FILE = "C:/AI SYMBOLIS WORK/word_frequencies.txt"

# Ensure directories exist
os.makedirs(SCRAPED_DIR, exist_ok=True)

def clean_word(word):
    """Keep only letters and hyphens, lowercase everything."""
    return re.sub(r"[^a-z-]", "", word.lower()).strip()

def process_file(file_path):
    """Extract words, count them, save results, move file."""
    word_count = Counter()

    print(f"🔍 Processing: {file_path}")

    # Read & process the file
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            for word in line.split():
                cleaned = clean_word(word)
                if cleaned:
                    word_count[cleaned] += 1  # Increment count

    # Show first 10 words found
    print(f"📝 Extracted first 10 words: {list(word_count.items())[:10]}")

    # Save results
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for word, count in word_count.items():
            f.write(f"{word} {count}\n")

    print(f"📄 Saved words to: {OUTPUT_FILE}")

    # Move the processed file
    shutil.move(file_path, os.path.join(SCRAPED_DIR, os.path.basename(file_path)))
    print(f"✅ Moved {file_path} → {SCRAPED_DIR}")

def process_all_files():
    """Process all files one by one with a 2-second wait in between."""
    files = [os.path.join(READY_DIR, f) for f in os.listdir(READY_DIR) if f.endswith(".txt")]
    
    if not files:
        print("❌ No files found in ready-for-scraping!")
        return

    total_files = len(files)
    print(f"🚀 Starting processing of {total_files} files...\n")

    for i, file_path in enumerate(files, start=1):
        process_file(file_path)
        print(f"⏳ Waiting 2 seconds before processing the next file... ({i}/{total_files})\n")
        time.sleep(2)  # 2-second wait

    print("\n🎉 All files processed!")
    print(f"📄 Word frequencies saved in: {OUTPUT_FILE}")

if __name__ == "__main__":
    process_all_files()
