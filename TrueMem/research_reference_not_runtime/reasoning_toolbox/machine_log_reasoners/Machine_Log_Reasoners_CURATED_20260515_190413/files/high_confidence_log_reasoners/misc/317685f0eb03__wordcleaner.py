import os
import re
import time
from tqdm import tqdm

# 📂 Input and Output Directories
INPUT_FOLDER = "A:/WIKI SCRAPED/WORD_ANALYSIS/FINAL_ALPHA"  # Change to your actual path
OUTPUT_FOLDER = "A:/WIKI SCRAPED/WORD_ANALYSIS/CLEANED_ALPHA"
METADATA_FILE = "A:/WIKI SCRAPED/WORD_ANALYSIS/cleaning_metadata.txt"

# ✅ Ensure output directory exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# 📝 Regex Patterns
NUMERIC_PATTERN = re.compile(r"\d")  # Detects any number in a word
MERGED_WORD_PATTERN = re.compile(r"([a-z])([A-Z])")  # Splits CamelCase words

# 📊 Meta Data Counters
total_words = 0
total_unique_words = 0
total_scrubbed_words = 0
total_duplicates_removed = 0
start_time = time.time()

def clean_word(word):
    """Clean up word by splitting CamelCase and removing unwanted characters."""
    word = re.sub(MERGED_WORD_PATTERN, r"\1 \2", word)  # Split merged words
    word = word.lower().strip()  # Lowercase for consistency
    return word if not NUMERIC_PATTERN.search(word) else None  # Remove words with numbers

def process_alpha_files():
    """Cleans and processes all A-Z files in the alphabetized directory."""
    global total_words, total_unique_words, total_scrubbed_words, total_duplicates_removed
    file_stats = {}

    for filename in tqdm(os.listdir(INPUT_FOLDER), desc="📂 Processing A-Z Files", unit="file"):
        if filename.endswith(".txt"):
            input_path = os.path.join(INPUT_FOLDER, filename)
            output_path = os.path.join(OUTPUT_FOLDER, filename)

            cleaned_words = set()  # Use a set to remove duplicates
            initial_word_count = 0
            scrubbed_count = 0

            with open(input_path, "r", encoding="utf-8") as infile:
                lines = infile.readlines()
                initial_word_count = len(lines)

                progress_bar = tqdm(total=initial_word_count, desc=f"🔍 {filename}", unit="word", leave=False)

                for line in lines:
                    words = line.strip().split()  # Split line into words
                    for word in words:
                        cleaned = clean_word(word)
                        if cleaned:
                            cleaned_words.add(cleaned)
                        else:
                            scrubbed_count += 1

                        progress_bar.update(1)

                progress_bar.close()

            total_words += initial_word_count
            total_unique_words += len(cleaned_words)
            total_scrubbed_words += scrubbed_count
            total_duplicates_removed += (initial_word_count - len(cleaned_words) - scrubbed_count)

            # Save cleaned words
            with open(output_path, "w", encoding="utf-8") as outfile:
                outfile.write("\n".join(sorted(cleaned_words)) + "\n")

            # Store file stats
            file_stats[filename] = {
                "original_words": initial_word_count,
                "cleaned_words": len(cleaned_words),
                "scrubbed_words": scrubbed_count,
                "duplicates_removed": initial_word_count - len(cleaned_words) - scrubbed_count
            }

    # ⏱️ Calculate total processing time
    elapsed_time = time.time() - start_time

    # 📊 Save Metadata
    with open(METADATA_FILE, "w", encoding="utf-8") as meta_file:
        meta_file.write(f"🔹 Word Cleaning Metadata\n")
        meta_file.write(f"Total Words Processed: {total_words:,}\n")
        meta_file.write(f"Total Unique Words Kept: {total_unique_words:,}\n")
        meta_file.write(f"Total Words Scrubbed (Not Moved): {total_scrubbed_words:,}\n")
        meta_file.write(f"Total Duplicates Removed: {total_duplicates_removed:,}\n")
        meta_file.write(f"Total Processing Time: {elapsed_time:.2f} sec\n\n")

        meta_file.write("📂 File-Specific Stats:\n")
        for file, stats in file_stats.items():
            meta_file.write(f"{file} - Original: {stats['original_words']:,}, Cleaned: {stats['cleaned_words']:,}, Scrubbed: {stats['scrubbed_words']:,}, Duplicates Removed: {stats['duplicates_removed']:,}\n")

    print(f"\n✅ Cleaning complete! Metadata saved to {METADATA_FILE}")

# 🚀 Run the script
process_alpha_files()
