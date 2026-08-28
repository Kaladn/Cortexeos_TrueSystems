import os
from tqdm import tqdm

# Input Directories
DIR_1 = "C:/AI SYMBOLIS WORK/alphabetized_words"
DIR_2 = "A:/WIKI SCRAPED/EXTRACTED/mesh_english_words"
DIR_3 = "A:/WIKI SCRAPED/alphabetized_words"
DIR_4 = "C:/First Word Alpha Parsed Data"  # NEW DIRECTORY

# Output Directory
OUTPUT_DIR = "A:/WIKI SCRAPED/MASTER_ALPHA"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Get A-Z filenames
ALPHABET = [chr(i) for i in range(65, 91)]  # A-Z

def merge_files(letter):
    """Merge words from all four sources into a single unique, sorted list."""
    merged_words = set()

    # Possible file paths
    files_to_read = [
        os.path.join(DIR_1, f"{letter}.txt"),
        os.path.join(DIR_2, f"{letter}.txt"),
        os.path.join(DIR_3, f"{letter}.txt"),
        os.path.join(DIR_4, f"{letter}.txt"),  # NEW DIRECTORY
    ]

    # Read words from all sources
    for file_path in files_to_read:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                merged_words.update(word.strip().lower() for word in f if word.strip())

    # Sort words alphabetically
    sorted_words = sorted(merged_words)

    # Write merged data to new file
    output_file = os.path.join(OUTPUT_DIR, f"{letter}.txt")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted_words) + "\n")

# Progress Bar
for letter in tqdm(ALPHABET, desc="🛠 Merging A-Z Files"):
    merge_files(letter)

print(f"✅ Master Alphabetized Library Created at: {OUTPUT_DIR}")
