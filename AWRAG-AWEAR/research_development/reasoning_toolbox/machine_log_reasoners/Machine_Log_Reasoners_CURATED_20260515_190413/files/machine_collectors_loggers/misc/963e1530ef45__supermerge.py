import os
import re
import time
from tqdm import tqdm
from collections import defaultdict, Counter

# 📂 **File Paths - Update as Needed**
DIRS_TO_COMPARE = [
    "A:/WIKI SCRAPED/EXTRACTED/mesh_sorted_words.txt", 
    "A:/WIKI SCRAPED/wiki_unique_word_list.txt", 
    "C:/First Word Alpha Parsed Data"
]
MASTER_ALPHA_DIR = "A:/WIKI SCRAPED/MASTER_ALPHA"
ANALYSIS_OUTPUT = "A:/WIKI SCRAPED/WORD_ANALYSIS"
FREQUENCY_FILE = os.path.join(ANALYSIS_OUTPUT, "word_frequencies.txt")
UNIQUE_WORDS_FILE = os.path.join(ANALYSIS_OUTPUT, "unique_words.txt")
ALPHABETIZED_FINAL_DIR = os.path.join(ANALYSIS_OUTPUT, "FINAL_ALPHA")

# 📂 Ensure all necessary directories exist
os.makedirs(ANALYSIS_OUTPUT, exist_ok=True)
os.makedirs(ALPHABETIZED_FINAL_DIR, exist_ok=True)

# 🔄 **Load Words into RAM**
def load_words(file_path):
    """Loads words from a file into a set for comparison."""
    words = set()
    if os.path.isdir(file_path):  # If it's a directory, process A-Z files
        for filename in os.listdir(file_path):
            full_path = os.path.join(file_path, filename)
            if filename.endswith(".txt"):
                with open(full_path, "r", encoding="utf-8") as f:
                    words.update(word.strip().lower() for word in f if word.strip())
    elif os.path.isfile(file_path):  # If it's a single file
        with open(file_path, "r", encoding="utf-8") as f:
            words.update(word.strip().lower() for word in f if word.strip())
    return words

# 🔄 **Load Data from All Sources**
word_sets = {}
for directory in DIRS_TO_COMPARE:
    print(f"🔄 Loading words from: {directory}...")
    start_time = time.time()
    word_sets[directory] = load_words(directory)
    print(f"✅ Loaded {len(word_sets[directory]):,} words in {time.time() - start_time:.2f} sec.")

# 📊 **Compare & Find Unique Words**
print("\n🔍 Comparing word sets for uniqueness...")
combined_words = set().union(*word_sets.values())  # All words from all sources
word_counts = Counter(word for dataset in word_sets.values() for word in dataset)

# 🏆 **Find Unique Words**
unique_words = {word for word, count in word_counts.items() if count == 1}

# 💾 **Save Unique Words**
with open(UNIQUE_WORDS_FILE, "w", encoding="utf-8") as uf:
    for word in sorted(unique_words):
        uf.write(word + "\n")

print(f"✅ Unique words saved: {len(unique_words):,} to {UNIQUE_WORDS_FILE}")

# 📊 **Generate Word Frequency Report**
print("\n📊 Generating frequency analysis...")
sorted_frequencies = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)

with open(FREQUENCY_FILE, "w", encoding="utf-8") as ff:
    for word, count in sorted_frequencies:
        ff.write(f"{word}: {count}\n")

print(f"✅ Word frequencies saved to {FREQUENCY_FILE}")

# 🗂️ **Create Final Master Alphabetized Library**
print("\n📂 Merging words into a new alphabetized directory...")
alphabetized_words = defaultdict(set)
for word in combined_words:
    first_letter = word[0].upper() if word[0].isalpha() else "#"
    alphabetized_words[first_letter].add(word)

# 💾 **Save Alphabetized Data**
for letter, words in tqdm(alphabetized_words.items(), desc="📂 Creating A-Z Files"):
    file_path = os.path.join(ALPHABETIZED_FINAL_DIR, f"{letter}.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(sorted(words)) + "\n")

print(f"\n✅ Master Alphabetized Library saved to {ALPHABETIZED_FINAL_DIR}")
print("🚀 **ALL PROCESSING COMPLETE!** ✅")
