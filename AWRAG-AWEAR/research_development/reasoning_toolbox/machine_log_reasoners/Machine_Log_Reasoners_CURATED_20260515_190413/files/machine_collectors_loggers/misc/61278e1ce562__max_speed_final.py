import os
import re
import shutil
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

    # Read & process the entire file
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            for word in line.split():
                cleaned = clean_word(word)
                if cleaned:
                    word_count[cleaned] += 1  # Increment count

    # Save results
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        for word, count in word_count.items():
            f.write(f"{word} {count}\n")

    print(f"📄 Saved words to: {OUTPUT_FILE}")

    # Move the processed file
    shutil.move(file_path, os.path.join(SCRAPED_DIR, os.path.basename(file_path)))
    print(f"✅ Moved {file_path} → {SCRAPED_DIR}")

def process_all_files():
    """Process all files **non-stop** at maximum speed."""
    files = [os.path.join(READY_DIR, f) for f in os.listdir(READY_DIR) if f.endswith(".txt")]
    
    if not files:
        print("❌ No files found in ready-for-scraping!")
        return

    total_files = len(files)
    print(f"🚀 Starting processing of {total_files} files...\n")

    for i, file_path in enumerate(files, start=1):
        process_file(file_path)
        print(f"🔥 Processed {i}/{total_files} files...")

    print("\n🎉 All files processed!")
    print(f"📄 Word frequencies saved in: {OUTPUT_FILE}")

if __name__ == "__main__":
    process_all_files()
